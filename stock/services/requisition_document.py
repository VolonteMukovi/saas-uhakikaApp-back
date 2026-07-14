"""
Payload JSON d'impression / export pour une réquisition.

Le backend ne génère ni PDF ni HTML : uniquement des données métier
structurées pour que le frontend compose le document.
"""
from __future__ import annotations

from typing import Any

from django.utils import timezone

from rapports.utils.report_envelope import (
    build_metadata,
    get_devise_principale,
    serialize_agence,
    serialize_entreprise,
)
from stock.services.requisition import PRIX_PLACEHOLDER, resume_requisition


def _iso(value) -> str | None:
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _display_dt(value) -> str | None:
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%d/%m/%Y %H:%M')


def _user_block(user) -> dict[str, Any]:
    if not user:
        return {
            'id': None,
            'username': '',
            'full_name': '',
            'display_name': '',
        }
    full = user.get_full_name() or ''
    username = user.username or ''
    return {
        'id': user.pk,
        'username': username,
        'full_name': full,
        'display_name': full or username,
    }


def _signature_block(*, nom: str = '', date: str | None = None) -> dict[str, Any]:
    """Bloc prêt pour le rendu FE (zones manuscrites après impression)."""
    return {
        'nom': nom or '',
        'signature': None,
        'signature_placeholder': True,
        'date': date,
        'date_placeholder': date is None,
        'libelle_zone_signature': 'Signature',
        'libelle_zone_date': 'Date',
    }


def _categorie_article(article) -> dict[str, Any] | None:
    if article is None:
        return None
    sous = getattr(article, 'sous_type_article', None)
    if sous is None:
        return None
    typ = getattr(sous, 'type_article', None)
    return {
        'sous_type_id': sous.pk,
        'sous_type': sous.libelle or '',
        'type_id': typ.pk if typ else None,
        'type': (typ.libelle if typ else '') or '',
        'libelle': (
            f'{(typ.libelle if typ else "")} / {sous.libelle}'.strip(' /')
            if typ or sous.libelle
            else ''
        ),
    }


def _origine_suggestion(ligne) -> str:
    if ligne.type_ligne == 'LIBRE':
        return 'MANUEL'
    statut = (ligne.statut_stock or '').upper()
    if statut in ('RUPTURE', 'ALERTE'):
        return statut
    if statut == 'NORMAL':
        return 'CATALOGUE'
    return 'MANUEL'


def _ligne_document(ligne, *, statut_requisition: str) -> dict[str, Any]:
    montant = ligne.montant_ligne
    quantite_demandee = str(ligne.quantite) if ligne.quantite is not None else None
    # Pas de champ dédié « validée » : si réquisition validée/clôturée,
    # la quantité figée du document = quantité demandée.
    quantite_validee = (
        quantite_demandee
        if statut_requisition in ('VALIDEE', 'CLOTUREE')
        else None
    )
    article = ligne.article
    if article is not None:
        article_payload = {
            'code': ligne.article_id,
            'nom': (article.nom_commercial or article.nom_scientifique or ligne.designation),
            'nom_scientifique': article.nom_scientifique,
            'nom_commercial': article.nom_commercial,
        }
    else:
        article_payload = {
            'code': None,
            'nom': ligne.designation,
            'nom_scientifique': None,
            'nom_commercial': None,
        }
    return {
        'id': ligne.pk,
        'ordre': ligne.ordre,
        'type_ligne': ligne.type_ligne,
        'type_ligne_libelle': ligne.get_type_ligne_display(),
        'article': article_payload,
        'code_article': ligne.article_id,
        'designation': ligne.designation,
        'categorie': _categorie_article(article),
        'unite': ligne.unite or '',
        'quantite_demandee': quantite_demandee,
        'quantite_validee': quantite_validee,
        'quantite': quantite_demandee,
        'prix_estimatif': str(ligne.prix_estime) if ligne.prix_estime is not None else None,
        'prix_estimatif_affiche': (
            PRIX_PLACEHOLDER if ligne.prix_estime is None else str(ligne.prix_estime)
        ),
        'prix_manquant': ligne.prix_estime is None,
        'prix_source': ligne.prix_source,
        'montant_estimatif': str(montant) if montant is not None else None,
        'montant_estimatif_affiche': (
            PRIX_PLACEHOLDER if montant is None else str(montant)
        ),
        'commentaire': ligne.remarque or '',
        'remarque': ligne.remarque or '',
        'origine_suggestion': _origine_suggestion(ligne),
        'statut_ligne': ligne.statut_stock or None,
        'statut_stock': ligne.statut_stock or None,
        'stock_actuel': str(ligne.stock_actuel) if ligne.stock_actuel is not None else None,
        'seuil_alerte': str(ligne.seuil_alerte) if ligne.seuil_alerte is not None else None,
    }


def _historique_document(requisition) -> list[dict[str, Any]]:
    rows = []
    for h in requisition.historique.all().select_related('utilisateur'):
        rows.append({
            'id': h.pk,
            'action': h.action,
            'ancien_statut': h.ancien_statut or None,
            'nouveau_statut': h.nouveau_statut or None,
            'commentaire': h.detail or '',
            'detail': h.detail or '',
            'utilisateur': _user_block(h.utilisateur),
            'date': _iso(h.date_action),
            'date_affichee': _display_dt(h.date_action),
            'metadata': h.metadata or {},
        })
    return rows


def _date_preparation(requisition):
    """Première occurrence EN_PREPARATION dans l'historique, sinon None."""
    for h in requisition.historique.all():
        if h.nouveau_statut == 'EN_PREPARATION':
            return h.date_action
    return None


def build_requisition_document(requisition, *, request=None) -> dict[str, Any]:
    """
    Document d'impression / export — JSON uniquement.

    Le frontend utilise ce payload pour mise en page, PDF, thèmes et impression.
    """
    user = getattr(request, 'user', None) if request else None
    entreprise = requisition.entreprise
    resume = resume_requisition(requisition)
    lignes_qs = (
        requisition.lignes.select_related(
            'article',
            'article__sous_type_article',
            'article__sous_type_article__type_article',
            'article__unite',
        ).order_by('ordre', 'id')
    )
    lignes = [
        _ligne_document(l, statut_requisition=requisition.statut)
        for l in lignes_qs
    ]

    auteur = _user_block(requisition.cree_par)
    validateur = _user_block(requisition.valide_par)
    date_prep = _date_preparation(requisition)

    document = {
        'rapport': 'requisition',
        'titre': 'Réquisition d\'approvisionnement',
        'format': 'json',
        'rendu': 'frontend',
        'entreprise': serialize_entreprise(entreprise, request=request),
        'agence': serialize_agence(requisition.succursale_id, entreprise=entreprise),
        'devise': get_devise_principale(entreprise),
        'requisition': {
            'id': requisition.pk,
            'numero': requisition.numero,
            'reference': requisition.numero,
            'titre': requisition.titre,
            'description': requisition.description or '',
            'observations': requisition.observations or '',
            'commentaires': requisition.commentaires or '',
            'priorite': requisition.priorite,
            'priorite_libelle': requisition.get_priorite_display(),
            'statut': requisition.statut,
            'statut_libelle': requisition.get_statut_display(),
            'auteur': auteur,
            'cree_par': auteur,
            'valide_par': validateur,
            'rejete_par': _user_block(requisition.rejete_par),
            'motif_rejet': requisition.motif_rejet or '',
            'archived': bool(requisition.archived),
            'succursale_id': requisition.succursale_id,
            'dates': {
                'creation': _iso(requisition.date_creation),
                'modification': _iso(requisition.date_modification),
                'preparation': _iso(date_prep),
                'validation': _iso(requisition.date_validation),
                'rejet': _iso(requisition.date_rejet),
                'cloture': _iso(requisition.date_cloture),
            },
            'dates_affichees': {
                'creation': _display_dt(requisition.date_creation),
                'modification': _display_dt(requisition.date_modification),
                'preparation': _display_dt(date_prep),
                'validation': _display_dt(requisition.date_validation),
                'rejet': _display_dt(requisition.date_rejet),
                'cloture': _display_dt(requisition.date_cloture),
            },
        },
        'lignes': lignes,
        'resume': {
            **resume,
            'nombre_articles': resume.get('nombre_lignes', 0),
            'nombre_lignes': resume.get('nombre_lignes', 0),
            'quantite_totale': resume.get('quantite_totale'),
            'montant_estimatif': resume.get('montant_estime'),
            'montant_estime': resume.get('montant_estime'),
            'lignes_prix_manquants': resume.get('lignes_prix_manquants', 0),
            'montant_estime_complet': resume.get('montant_estime_complet', False),
            'statistiques': {
                'lignes_article': sum(1 for l in lignes if l['type_ligne'] == 'ARTICLE'),
                'lignes_libres': sum(1 for l in lignes if l['type_ligne'] == 'LIBRE'),
                'lignes_rupture': sum(1 for l in lignes if l.get('statut_stock') == 'RUPTURE'),
                'lignes_alerte': sum(1 for l in lignes if l.get('statut_stock') == 'ALERTE'),
                'prix_manquants': resume.get('lignes_prix_manquants', 0),
            },
        },
        'historique': _historique_document(requisition),
        'sections_impression': {
            'prepare_par': _signature_block(
                nom=auteur.get('display_name') or '',
                date=_display_dt(requisition.date_creation),
            ),
            'valide_par': _signature_block(
                nom=validateur.get('display_name') or '',
                date=_display_dt(requisition.date_validation),
            ),
            'reception': _signature_block(nom='', date=None),
            'observations_finales': {
                'texte_prerempli': requisition.observations or '',
                'zone_manuscrite': True,
                'hauteur_suggeree': 'large',
                'placeholder': (
                    'Zone réservée aux observations manuscrites '
                    'après impression.'
                ),
            },
        },
        'instructions_frontend': {
            'generer_pdf': True,
            'generer_html': True,
            'backend_ne_genere_pas_pdf': True,
            'afficher_placeholder_prix': PRIX_PLACEHOLDER,
            'sections_signatures_obligatoires': [
                'prepare_par',
                'valide_par',
                'reception',
            ],
        },
        'metadata': build_metadata(user, request=request),
    }
    return document
