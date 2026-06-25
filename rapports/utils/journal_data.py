"""
Construction des données JSON du journal complet des opérations.
"""
from __future__ import annotations

from calendar import monthrange
from decimal import Decimal, ROUND_DOWN

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext as _

from caisse.models import MouvementCaisse
from stock.models import DetteClient, Entree, Sortie


def _format_amount(amount, devise):
    if amount is None:
        return '-'
    sigle = devise.sigle if devise else ''
    try:
        val = Decimal(str(amount)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        return f"{val:.5f} {sigle}".strip()
    except Exception:
        return str(amount)


def build_journal_report_data(
    *,
    request,
    user,
    tenant_id: int,
    branch_id: int | None,
    principal_devise,
) -> dict:
    now = timezone.now()
    month_param = request.query_params.get('month')
    year_param = request.query_params.get('year')
    date_min = request.query_params.get('date_min')
    date_max = request.query_params.get('date_max')

    use_month_year = (month_param is not None or year_param is not None) or not (date_min or date_max)
    if use_month_year:
        try:
            year = int(year_param) if year_param else now.year
            month = int(month_param) if month_param else now.month
        except (TypeError, ValueError):
            year, month = now.year, now.month
        if not (1 <= month <= 12):
            month = now.month
        if year < 1900 or year > 2100:
            year = now.year
        last_day = monthrange(year, month)[1]
        date_min = f"{year}-{month:02d}-01"
        date_max = f"{year}-{month:02d}-{last_day}"
        periode_label = f"{month:02d}/{year}"
    else:
        periode_label = _("Du %(debut)s au %(fin)s") % {
            'debut': date_min or '...',
            'fin': date_max or '...',
        }

    filtres = {
        'month': month_param,
        'year': year_param,
        'date_min': date_min,
        'date_max': date_max,
    }

    qs_entrees = Entree.objects.filter(entreprise_id=tenant_id)
    if branch_id is not None:
        qs_entrees = qs_entrees.filter(succursale_id=branch_id)
    qs_entrees = qs_entrees.prefetch_related('lignes', 'lignes__article', 'lignes__devise')
    if date_min:
        qs_entrees = qs_entrees.filter(date_op__date__gte=date_min)
    if date_max:
        qs_entrees = qs_entrees.filter(date_op__date__lte=date_max)

    qs_sorties = Sortie.objects.filter(entreprise_id=tenant_id)
    if branch_id is not None:
        qs_sorties = qs_sorties.filter(succursale_id=branch_id)
    qs_sorties = qs_sorties.prefetch_related('lignes', 'lignes__article', 'lignes__devise', 'client')
    if date_min:
        qs_sorties = qs_sorties.filter(date_creation__date__gte=date_min)
    if date_max:
        qs_sorties = qs_sorties.filter(date_creation__date__lte=date_max)

    qs_caisse = MouvementCaisse.objects.filter(entreprise_id=tenant_id).select_related(
        'devise', 'sortie', 'entree'
    )
    if branch_id is not None:
        qs_caisse = qs_caisse.filter(succursale_id=branch_id)
    if date_min:
        qs_caisse = qs_caisse.filter(date__date__gte=date_min)
    if date_max:
        qs_caisse = qs_caisse.filter(date__date__lte=date_max)

    ct_dette = ContentType.objects.get_for_model(DetteClient)
    qs_paiements = MouvementCaisse.objects.filter(
        entreprise_id=tenant_id,
        content_type=ct_dette,
        type='ENTREE',
    ).select_related('devise', 'content_type')
    if branch_id is not None:
        qs_paiements = qs_paiements.filter(succursale_id=branch_id)
    if date_min:
        qs_paiements = qs_paiements.filter(date__date__gte=date_min)
    if date_max:
        qs_paiements = qs_paiements.filter(date__date__lte=date_max)

    events = []

    for e in qs_entrees:
        total_par_devise = {}
        for lig in e.lignes.all():
            dev = lig.devise or principal_devise
            sigle = dev.sigle if dev else 'N/A'
            total_par_devise[sigle] = (
                total_par_devise.get(sigle, Decimal('0')) + lig.quantite * lig.prix_unitaire
            )
        montant_str = (
            ', '.join(
                f"{Decimal(str(v)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN):.5f} {s}"
                for s, v in total_par_devise.items()
            )
            if total_par_devise
            else '-'
        )
        events.append({
            'date': e.date_op.isoformat() if e.date_op else None,
            'date_display': e.date_op.strftime('%Y-%m-%d %H:%M') if e.date_op else '',
            'type': 'APPROVISIONNEMENT',
            'type_display': str(_('Approvisionnement')),
            'designation': (e.libele or str(_('Entrée')))[:80],
            'montant_texte': montant_str,
            'montants_par_devise': {k: str(v) for k, v in total_par_devise.items()},
            'ref': f'Entrée#{e.id}',
            'source_id': e.id,
        })

    for s in qs_sorties:
        total_par_devise = {}
        for lig in s.lignes.all():
            dev = lig.devise or principal_devise
            sigle = dev.sigle if dev else 'N/A'
            total_par_devise[sigle] = (
                total_par_devise.get(sigle, Decimal('0')) + lig.quantite * lig.prix_unitaire
            )
        montant_str = (
            ', '.join(
                f"{Decimal(str(v)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN):.5f} {s}"
                for s, v in total_par_devise.items()
            )
            if total_par_devise
            else '-'
        )
        client_nom = (s.client.nom if s.client else 'Anonyme')[:40]
        events.append({
            'date': s.date_creation.isoformat() if s.date_creation else None,
            'date_display': s.date_creation.strftime('%Y-%m-%d %H:%M') if s.date_creation else '',
            'type': 'VENTE',
            'type_display': str(_('Vente')),
            'designation': f"{(s.motif or str(_('Vente')))[:50]} - {_('Client')}: {client_nom}",
            'montant_texte': montant_str,
            'montants_par_devise': {k: str(v) for k, v in total_par_devise.items()},
            'ref': f'Sortie#{s.id}',
            'source_id': s.id,
            'client': client_nom,
            'statut_paiement': s.statut,
        })

    for mv in qs_caisse:
        caisse_type_label = str(_('Caisse Entrée')) if mv.type == 'ENTREE' else str(_('Caisse Sortie'))
        events.append({
            'date': mv.date.isoformat() if mv.date else None,
            'date_display': mv.date.strftime('%Y-%m-%d %H:%M') if mv.date else '',
            'type': f'CAISSE_{mv.type}',
            'type_display': caisse_type_label,
            'designation': (mv.motif_affiche() or '')[:80].replace('\n', ' '),
            'montant_texte': _format_amount(mv.montant, mv.devise),
            'montant': str(mv.montant) if mv.montant is not None else '0',
            'devise_sigle': mv.devise.sigle if mv.devise else None,
            'moyen': mv.moyen or '',
            'ref': mv.reference_piece or f"MC#{mv.id}",
            'source_id': mv.id,
        })

    ct_dette_model = ContentType.objects.get_for_model(DetteClient)
    for p in qs_paiements:
        dette = None
        if p.content_type_id == ct_dette_model.id and p.object_id:
            dette = DetteClient.objects.filter(pk=p.object_id).select_related('client').first()
        client_nom = (dette.client.nom if dette and dette.client else '')[:40]
        events.append({
            'date': p.date.isoformat() if p.date else None,
            'date_display': p.date.strftime('%Y-%m-%d %H:%M') if p.date else '',
            'type': 'PAIEMENT_DETTE',
            'type_display': str(_('Paiement dette')),
            'designation': f"{_('Paiement dette')} - {client_nom}".strip()[:80],
            'montant_texte': _format_amount(p.montant, p.devise),
            'montant': str(p.montant) if p.montant is not None else '0',
            'devise_sigle': p.devise.sigle if p.devise else None,
            'ref': p.reference_piece or f"Paiement#{p.id}",
            'source_id': p.id,
            'client': client_nom,
            'dette_id': dette.pk if dette else None,
        })

    events.sort(key=lambda x: x.get('date') or '')

    resume = {
        'total_operations': len(events),
        'approvisionnements': sum(1 for e in events if e.get('type') == 'APPROVISIONNEMENT'),
        'ventes': sum(1 for e in events if e.get('type') == 'VENTE'),
        'caisse_entrees': sum(1 for e in events if e.get('type') == 'CAISSE_ENTREE'),
        'caisse_sorties': sum(1 for e in events if e.get('type') == 'CAISSE_SORTIE'),
        'paiements_dettes': sum(1 for e in events if e.get('type') == 'PAIEMENT_DETTE'),
    }

    return {
        'titre': str(_('JOURNAL COMPLET DES OPÉRATIONS')),
        'periode': {
            'label': periode_label,
            'date_debut': date_min,
            'date_fin': date_max,
        },
        'filtres': filtres,
        'resume': resume,
        'details': events,
        'operations': events,
    }
