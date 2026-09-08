"""
Performance commerciale : gains / pertes / CA par article (source BeneficeLot).

- Gain  : benefice_total >= 0
- Perte : benefice_total < 0 (hors crédit EN_CREDIT par défaut pour les totaux « perte »)
- CA    : sum(prix_vente × quantite_vendue)
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Any

from django.db.models import Count, F, Q, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone

from stock.models import Article, BeneficeLot
from stock.services.requisition import designation_article

MONEY = Decimal('0.00001')


def _q(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal('0').quantize(MONEY, rounding=ROUND_DOWN)
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_DOWN)


def _fmt(value: Decimal | None) -> str:
    return str(_q(value))


def _parse_periode(params) -> tuple[int, int, datetime, datetime]:
    """Retourne (year, month, debut, fin) — mois calendaire par défaut."""
    now = timezone.now()
    try:
        year = int(params.get('year', now.year))
        month = int(params.get('month', now.month))
    except (TypeError, ValueError):
        year, month = now.year, now.month
    if not (1 <= month <= 12):
        month = now.month
    if year < 1900 or year > 2100:
        year = now.year

    debut = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        fin = timezone.make_aware(datetime(year + 1, 1, 1))
    else:
        fin = timezone.make_aware(datetime(year, month + 1, 1))
    return year, month, debut, fin


def base_queryset(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    year: int,
    month: int,
    include_credit: bool = True,
):
    qs = BeneficeLot.objects.filter(
        date_calcul__year=year,
        date_calcul__month=month,
        lot_entree__entree__entreprise_id=entreprise_id,
    ).select_related(
        'lot_entree__article',
        'lot_entree__article__unite',
        'ligne_sortie__sortie',
        'ligne_sortie__sortie__client',
    )
    if succursale_id is not None:
        qs = qs.filter(lot_entree__entree__succursale_id=succursale_id)
    if not include_credit:
        qs = qs.exclude(ligne_sortie__sortie__statut='EN_CREDIT')
    return qs


def _ca_expr():
    return ExpressionWrapper(
        F('prix_vente') * F('quantite_vendue'),
        output_field=DecimalField(max_digits=20, decimal_places=5),
    )


def _cout_expr():
    return ExpressionWrapper(
        F('prix_achat') * F('quantite_vendue'),
        output_field=DecimalField(max_digits=20, decimal_places=5),
    )


def _origine_mouvement(benefice: BeneficeLot) -> dict[str, Any]:
    """Classifie la ligne : vente, inventaire, autre."""
    sortie = benefice.ligne_sortie.sortie if benefice.ligne_sortie_id else None
    if sortie is None:
        return {
            'type': 'AUTRE',
            'type_libelle': 'Autre',
            'sortie_id': None,
            'statut_sortie': None,
            'motif': '',
        }
    motif = (sortie.motif or '').strip()
    motif_l = motif.casefold()
    if 'inventaire' in motif_l or 'ajustement inventaire' in motif_l:
        typ, lib = 'INVENTAIRE', 'Perte inventaire / ajustement stock'
    elif sortie.statut == 'EN_CREDIT':
        typ, lib = 'VENTE_CREDIT', 'Vente à crédit'
    else:
        typ, lib = 'VENTE', 'Vente'
    return {
        'type': typ,
        'type_libelle': lib,
        'sortie_id': sortie.pk,
        'statut_sortie': sortie.statut,
        'motif': motif,
        'client_nom': sortie.client.nom if sortie.client_id else None,
        'date_sortie': sortie.date_creation.isoformat() if sortie.date_creation else None,
    }


def _performance(benefice_net: Decimal) -> dict[str, str]:
    if benefice_net > 0:
        return {
            'statut': 'EXCELLENTE',
            'message': f'Période profitable : bénéfice net {_fmt(benefice_net)}.',
        }
    if benefice_net == 0:
        return {
            'statut': 'NEUTRE',
            'message': 'Équilibre sur la période (bénéfice net nul).',
        }
    if benefice_net >= Decimal('-500'):
        return {
            'statut': 'A_SURVEILLER',
            'message': f'Légère perte nette ({_fmt(benefice_net)}). Revoir marges et remises.',
        }
    if benefice_net >= Decimal('-5000'):
        return {
            'statut': 'PREOCCUPANTE',
            'message': f'Perte significative ({_fmt(benefice_net)}). Analyser coûts et tarifs.',
        }
    return {
        'statut': 'CRITIQUE',
        'message': f'Perte très importante ({_fmt(benefice_net)}). Action urgente requise.',
    }


def build_resume(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    year: int,
    month: int,
) -> dict[str, Any]:
    qs = base_queryset(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        year=year,
        month=month,
        include_credit=True,
    )
    qs_perte = qs.filter(benefice_total__lt=0).exclude(
        ligne_sortie__sortie__statut='EN_CREDIT',
    )

    ca_expr = _ca_expr()
    cout_expr = _cout_expr()

    agg = qs.aggregate(
        ca=Sum(ca_expr),
        cout=Sum(cout_expr),
        benefice_net=Sum('benefice_total'),
        quantite=Sum('quantite_vendue'),
        nb=Count('id'),
    )
    gains = qs.filter(benefice_total__gte=0).aggregate(
        total=Sum('benefice_total'),
        ca=Sum(ca_expr),
        nb=Count('id'),
    )
    pertes = qs_perte.aggregate(
        total=Sum('benefice_total'),
        ca=Sum(ca_expr),
        nb=Count('id'),
    )

    benefice_net = _q(agg['benefice_net'])
    total_gain = _q(gains['total'])
    total_perte = abs(_q(pertes['total']))

    return {
        'rapport': 'benefices_resume',
        'periode': {
            'annee': year,
            'mois': month,
            'libelle': f'{year}-{month:02d}',
        },
        'contexte': {
            'entreprise_id': entreprise_id,
            'succursale_id': succursale_id,
        },
        'resume': {
            'chiffre_affaires': _fmt(agg['ca']),
            'cout_achat': _fmt(agg['cout']),
            'benefice_net': _fmt(benefice_net),
            'total_gain': _fmt(total_gain),
            'total_perte': _fmt(total_perte),
            'quantite_totale': _fmt(agg['quantite']),
            'nombre_mouvements': agg['nb'] or 0,
            'nombre_mouvements_gagnants': gains['nb'] or 0,
            'nombre_mouvements_perdants': pertes['nb'] or 0,
            'nombre_articles': qs.values('lot_entree__article_id').distinct().count(),
        },
        'performance': {
            **_performance(benefice_net),
            'benefice_net': _fmt(benefice_net),
        },
        'gains': {
            'montant': _fmt(total_gain),
            'chiffre_affaires': _fmt(gains['ca']),
            'nombre_mouvements': gains['nb'] or 0,
        },
        'pertes': {
            'montant': _fmt(total_perte),
            'chiffre_affaires': _fmt(pertes['ca']),
            'nombre_mouvements': pertes['nb'] or 0,
            'note': 'Les ventes à crédit déficitaires sont exclues des pertes (non définitives).',
        },
    }


def aggregate_par_article(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    year: int,
    month: int,
    filtre: str = 'tous',
    search: str | None = None,
) -> list[dict[str, Any]]:
    """
    Une ligne par article avec CA, coût, bénéfice, statut Gain/Perte.
    filtre: tous | gains | pertes
    """
    qs = base_queryset(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        year=year,
        month=month,
        include_credit=True,
    )
    if search:
        q = search.strip()
        if q:
            qs = qs.filter(
                Q(lot_entree__article_id__icontains=q)
                | Q(lot_entree__article__nom_scientifique__icontains=q)
                | Q(lot_entree__article__nom_commercial__icontains=q)
            )

    ca_expr = _ca_expr()
    cout_expr = _cout_expr()

    rows = (
        qs.values(
            'lot_entree__article_id',
            'lot_entree__article__nom_scientifique',
            'lot_entree__article__nom_commercial',
            'lot_entree__article__unite__libelle',
        )
        .annotate(
            chiffre_affaires=Coalesce(Sum(ca_expr), Decimal('0')),
            cout_achat=Coalesce(Sum(cout_expr), Decimal('0')),
            benefice_net=Coalesce(Sum('benefice_total'), Decimal('0')),
            quantite_vendue=Coalesce(Sum('quantite_vendue'), Decimal('0')),
            nombre_mouvements=Count('id'),
            gain_brut=Coalesce(
                Sum('benefice_total', filter=Q(benefice_total__gte=0)),
                Decimal('0'),
            ),
            perte_brute=Coalesce(
                Sum(
                    'benefice_total',
                    filter=Q(benefice_total__lt=0)
                    & ~Q(ligne_sortie__sortie__statut='EN_CREDIT'),
                ),
                Decimal('0'),
            ),
        )
        .order_by('benefice_net')  # pertes d'abord si on filtre pertes ; on réordonne après
    )

    results: list[dict[str, Any]] = []
    for row in rows:
        benef = _q(row['benefice_net'])
        perte = abs(_q(row['perte_brute']))
        gain = _q(row['gain_brut'])
        if filtre == 'gains' and benef < 0:
            continue
        if filtre == 'pertes' and benef >= 0:
            continue

        if benef > 0:
            statut, statut_libelle = 'GAIN', 'Gain'
        elif benef < 0:
            statut, statut_libelle = 'PERTE', 'Perte'
        else:
            statut, statut_libelle = 'NEUTRE', 'Neutre'

        aid = row['lot_entree__article_id']
        nom_s = row['lot_entree__article__nom_scientifique'] or ''
        nom_c = row['lot_entree__article__nom_commercial'] or ''
        results.append({
            'article_id': aid,
            'nom_scientifique': nom_s,
            'nom_commercial': nom_c,
            'designation': (nom_c.strip() or nom_s.strip() or aid),
            'unite': row['lot_entree__article__unite__libelle'] or '',
            'chiffre_affaires': _fmt(row['chiffre_affaires']),
            'cout_achat': _fmt(row['cout_achat']),
            'benefice_net': _fmt(benef),
            'total_gain': _fmt(gain),
            'total_perte': _fmt(perte),
            'quantite_vendue': _fmt(row['quantite_vendue']),
            'nombre_mouvements': row['nombre_mouvements'],
            'statut': statut,
            'statut_libelle': statut_libelle,
            'marge_pourcent': (
                str(((benef / _q(row['chiffre_affaires'])) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_DOWN))
                if _q(row['chiffre_affaires']) > 0 else None
            ),
        })

    if filtre == 'gains':
        results.sort(key=lambda x: Decimal(x['benefice_net']), reverse=True)
    elif filtre == 'pertes':
        results.sort(key=lambda x: Decimal(x['benefice_net']))  # plus négatif d'abord
    else:
        results.sort(key=lambda x: Decimal(x['benefice_net']), reverse=True)

    return results


def detail_article(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    article_id: str,
    year: int,
    month: int,
) -> dict[str, Any] | None:
    """Détail d'un article : résumé + chaque mouvement (pourquoi gain/perte)."""
    try:
        article = Article.objects.select_related('unite', 'sous_type_article__type_article').get(
            pk=article_id,
            entreprise_id=entreprise_id,
        )
    except Article.DoesNotExist:
        return None

    qs = base_queryset(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        year=year,
        month=month,
        include_credit=True,
    ).filter(lot_entree__article_id=article_id).order_by('-date_calcul', '-id')

    ca_expr = _ca_expr()
    cout_expr = _cout_expr()
    agg = qs.aggregate(
        ca=Sum(ca_expr),
        cout=Sum(cout_expr),
        benefice_net=Sum('benefice_total'),
        quantite=Sum('quantite_vendue'),
        nb=Count('id'),
        gain=Sum('benefice_total', filter=Q(benefice_total__gte=0)),
        perte=Sum(
            'benefice_total',
            filter=Q(benefice_total__lt=0) & ~Q(ligne_sortie__sortie__statut='EN_CREDIT'),
        ),
    )

    mouvements: list[dict[str, Any]] = []
    for b in qs:
        ca_m = _q(b.prix_vente) * _q(b.quantite_vendue)
        cout_m = _q(b.prix_achat) * _q(b.quantite_vendue)
        benef = _q(b.benefice_total)
        origine = _origine_mouvement(b)
        if benef > 0:
            statut, explication = 'GAIN', (
                f"Vendu à {_fmt(b.prix_vente)} alors que le coût du lot était {_fmt(b.prix_achat)} "
                f"(+{_fmt(b.benefice_unitaire)} / unité)."
            )
        elif benef < 0:
            if origine['type'] == 'INVENTAIRE':
                statut, explication = 'PERTE', (
                    f"Ajustement inventaire : stock manquant valorisé au coût d'achat {_fmt(b.prix_achat)} "
                    f"(perte {_fmt(abs(benef))})."
                )
            elif origine['type'] == 'VENTE_CREDIT':
                statut, explication = 'PERTE', (
                    f"Vente à crédit sous le coût : PV {_fmt(b.prix_vente)} < achat {_fmt(b.prix_achat)} "
                    f"(écart {_fmt(b.benefice_unitaire)} / unité). Non comptée dans total_perte tant que non soldée."
                )
            else:
                statut, explication = 'PERTE', (
                    f"Vendu à {_fmt(b.prix_vente)} sous le coût d'achat {_fmt(b.prix_achat)} "
                    f"(écart {_fmt(b.benefice_unitaire)} / unité) — remise, sous-tarification ou lot cher."
                )
        else:
            statut, explication = 'NEUTRE', 'Marge égale au coût (marge nulle).'

        mouvements.append({
            'id': b.pk,
            'date': b.date_calcul.isoformat() if b.date_calcul else None,
            'lot_entree_id': b.lot_entree_id,
            'ligne_sortie_id': b.ligne_sortie_id,
            'quantite': _fmt(b.quantite_vendue),
            'prix_achat_unitaire': _fmt(b.prix_achat),
            'prix_vente_unitaire': _fmt(b.prix_vente),
            'chiffre_affaires': _fmt(ca_m),
            'cout_achat': _fmt(cout_m),
            'benefice_unitaire': _fmt(b.benefice_unitaire),
            'benefice_total': _fmt(benef),
            'statut': statut,
            'statut_libelle': 'Gain' if statut == 'GAIN' else ('Perte' if statut == 'PERTE' else 'Neutre'),
            'explication': explication,
            'origine': origine,
        })

    benef_net = _q(agg['benefice_net'])
    if benef_net > 0:
        statut_art = 'GAIN'
    elif benef_net < 0:
        statut_art = 'PERTE'
    else:
        statut_art = 'NEUTRE'

    return {
        'rapport': 'benefices_article_detail',
        'periode': {
            'annee': year,
            'mois': month,
            'libelle': f'{year}-{month:02d}',
        },
        'article': {
            'article_id': article.article_id,
            'nom_scientifique': article.nom_scientifique or '',
            'nom_commercial': article.nom_commercial or '',
            'designation': designation_article(article),
            'unite': article.unite.libelle if article.unite_id else '',
        },
        'resume': {
            'chiffre_affaires': _fmt(agg['ca']),
            'cout_achat': _fmt(agg['cout']),
            'benefice_net': _fmt(benef_net),
            'total_gain': _fmt(agg['gain']),
            'total_perte': _fmt(abs(_q(agg['perte']))),
            'quantite_vendue': _fmt(agg['quantite']),
            'nombre_mouvements': agg['nb'] or 0,
            'statut': statut_art,
            'statut_libelle': 'Gain' if statut_art == 'GAIN' else ('Perte' if statut_art == 'PERTE' else 'Neutre'),
            'marge_pourcent': (
                str(((benef_net / _q(agg['ca'])) * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_DOWN))
                if _q(agg['ca']) > 0 else None
            ),
        },
        'mouvements': mouvements,
        'instructions_frontend': {
            'expliquer_chaque_ligne': True,
            'ca_egal_prix_vente_fois_qte': True,
            'benefice_egal_ca_moins_cout': True,
            'pertes_inventaire_incluses': True,
        },
    }
