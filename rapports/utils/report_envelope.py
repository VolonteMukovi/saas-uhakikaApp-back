"""
Enveloppe JSON standardisée pour tous les rapports API.
Le backend fournit les données ; le frontend gère affichage, impression et export PDF.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from stock.models import Devise, Succursale


def _devise_to_dict(devise: Devise | None) -> dict | None:
    if not devise:
        return None
    return {
        'id': devise.pk,
        'sigle': devise.sigle,
        'nom': devise.nom,
        'symbole': devise.symbole,
        'est_principal': bool(devise.est_principal),
    }


def get_devise_principale(entreprise) -> dict | None:
    if not entreprise:
        return None
    dev = Devise.objects.filter(entreprise=entreprise, est_principal=True).first()
    if not dev:
        dev = Devise.objects.filter(entreprise=entreprise).first()
    return _devise_to_dict(dev)


def serialize_entreprise(entreprise, request=None) -> dict | None:
    if not entreprise:
        return None
    logo_url = None
    if getattr(entreprise, 'logo', None):
        try:
            if request is not None:
                logo_url = request.build_absolute_uri(entreprise.logo.url)
            else:
                logo_url = entreprise.logo.url
        except Exception:
            logo_url = None
    return {
        'id': entreprise.pk,
        'nom': entreprise.nom or '',
        'secteur': getattr(entreprise, 'secteur', '') or '',
        'pays': getattr(entreprise, 'pays', '') or '',
        'adresse': getattr(entreprise, 'adresse', '') or '',
        'telephone': getattr(entreprise, 'telephone', '') or '',
        'email': getattr(entreprise, 'email', '') or '',
        'nif': getattr(entreprise, 'nif', '') or '',
        'responsable': getattr(entreprise, 'responsable', '') or '',
        'slogan': getattr(entreprise, 'slogan', '') or '',
        'has_branches': bool(getattr(entreprise, 'has_branches', False)),
        'logo_url': logo_url,
    }


def serialize_agence(branch_id: int | None, entreprise=None) -> dict | None:
    if not branch_id:
        return None
    succ = Succursale.objects.filter(pk=branch_id).first()
    if not succ:
        return {'id': branch_id, 'nom': ''}
    if entreprise and succ.entreprise_id != entreprise.pk:
        return None
    return {
        'id': succ.pk,
        'nom': succ.nom or '',
        'adresse': succ.adresse or '',
        'telephone': succ.telephone or '',
        'email': succ.email or '',
        'is_active': bool(succ.is_active),
    }


def build_metadata(user, request=None, legacy_meta: dict | None = None) -> dict:
    legacy_meta = legacy_meta or {}
    membership = None
    if user and request is not None and hasattr(user, 'get_current_membership'):
        membership = user.get_current_membership(request)

    generated_by_name = (
        legacy_meta.get('printed_by')
        or (user.get_full_name() if user and user.get_full_name() else '')
        or (user.username if user else '')
    )
    generated_at_display = legacy_meta.get('printed_at') or timezone.now().strftime('%d/%m/%Y %H:%M')

    session = {}
    if request is not None:
        session = {
            'entreprise_id': getattr(request, 'tenant_id', None),
            'succursale_id': getattr(request, 'branch_id', None),
            'membership_id': getattr(membership, 'pk', None) if membership else None,
            'language': getattr(request, 'LANGUAGE_CODE', None),
        }

    return {
        'generated_at': timezone.now().isoformat(),
        'generated_at_display': generated_at_display,
        'generated_by': {
            'id': user.pk if user else None,
            'username': user.username if user else '',
            'full_name': user.get_full_name() if user else '',
            'display_name': generated_by_name,
        },
        'session': session,
    }


def wrap_report_response(
    *,
    rapport: str,
    titre: str,
    request,
    user,
    data: dict[str, Any],
    eid: int | None = None,
    branch_id: int | None = None,
) -> dict[str, Any]:
    """
    Enveloppe un corps de rapport existant dans le format API standard.
    Conserve toutes les clés métier (articles, lignes, clients, etc.).
    """
    body = dict(data or {})
    body.pop('entete', None)
    legacy_meta = body.pop('meta_generation', None)

    entreprise = user.get_entreprise(request) if user else None
    if eid is None and entreprise:
        eid = entreprise.pk
    if branch_id is None and request is not None:
        branch_id = getattr(request, 'branch_id', None)
        if branch_id is None and user and hasattr(user, 'is_agent') and user.is_agent(request):
            m = user.get_current_membership(request)
            branch_id = m.default_succursale_id if m else None

    devise = get_devise_principale(entreprise)

    resume = (
        body.get('resume')
        or body.get('resume_global')
        or body.get('statistiques')
    )
    totaux = (
        body.get('totaux')
        or body.get('totaux_globaux')
        or body.get('totaux_encours')
    )

    filtres = body.pop('filtres', None)
    if filtres is None:
        filtres = {}

    envelope: dict[str, Any] = {
        'rapport': rapport,
        'titre': titre,
        'periode': body.pop('periode', None),
        'entreprise': serialize_entreprise(entreprise, request),
        'agence': serialize_agence(branch_id, entreprise),
        'devise': devise,
        'filtres': filtres,
        'resume': resume,
        'totaux': totaux,
        'metadata': build_metadata(user, request, legacy_meta),
    }

    if 'instructions' in data:
        envelope['instructions'] = data['instructions']

    # Corps métier : tout le reste (articles, lignes_ventes, clients, pagination, etc.)
    envelope.update(body)

    return envelope
