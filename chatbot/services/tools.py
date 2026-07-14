"""Outils métier — données filtrées tenant pour le chatbot."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from chatbot.context import ChatbotContext
from chatbot.services.intent_classifier import IntentResult
from stock.models import Article, DetteClient, Entree, LigneEntree, LigneSortie, Sortie, Stock
from stock.services.stock_stats import (
    aggregate_stock_stats,
    list_articles_expiration_dans_fenetre,
)


def _money(value) -> str:
    if value is None:
        return '0'
    return str(Decimal(str(value)).quantize(Decimal('0.01')))


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, monthrange(y, m)[1])
    return date(y, m, day)


def _period_start(period: str):
    now = timezone.now()
    if period == 'week':
        return now - timedelta(days=7)
    if period == 'month':
        return now - timedelta(days=30)
    if period == 'all_time':
        return None
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _search_clients(ctx: ChatbotContext, hint: str, limit: int = 10) -> list[dict]:
    from stock.models import ClientEntreprise

    qs = (
        ClientEntreprise.objects.filter(
            entreprise_id=ctx.tenant_id,
            client__nom__icontains=hint,
        )
        .select_related('client')
        .order_by('client__nom')
    )
    if ctx.branch_id is not None:
        qs = qs.filter(Q(succursale_id=ctx.branch_id) | Q(succursale_id__isnull=True))
    return [
        {
            'id': lien.client_id,
            'nom': lien.client.nom,
            'telephone': lien.client.telephone or '',
        }
        for lien in qs[:limit]
    ]


def _client_sales_summary(ctx: ChatbotContext, client_id: int, period: str = 'all_time') -> dict:
    sorties = Sortie.objects.filter(entreprise_id=ctx.tenant_id, client_id=client_id)
    if ctx.branch_id is not None:
        sorties = sorties.filter(succursale_id=ctx.branch_id)
    start = _period_start(period)
    if start is not None:
        sorties = sorties.filter(date_creation__gte=start)

    nb = sorties.count()
    lignes = LigneSortie.objects.filter(sortie__in=sorties)
    total = lignes.aggregate(t=Coalesce(Sum(F('quantite') * F('prix_unitaire')), Decimal('0')))['t']
    dernier = sorties.order_by('-date_creation').first()
    details = []
    for s in sorties.order_by('-date_creation')[:10]:
        ls = list(
            LigneSortie.objects.filter(sortie=s).select_related('article')[:20]
        )
        details.append({
            'sortie_id': s.pk,
            'heure': s.date_creation.strftime('%H:%M') if s.date_creation else '',
            'date': s.date_creation.date().isoformat() if s.date_creation else '',
            'statut': s.statut,
            'lignes': [
                {
                    'nom': (l.article.nom_commercial or l.article.nom_scientifique) if l.article else 'Article',
                    'quantite': str(l.quantite),
                    'total': _money(Decimal(str(l.quantite)) * Decimal(str(l.prix_unitaire))),
                }
                for l in ls
            ],
            'montant': _money(
                sum(
                    (Decimal(str(l.quantite)) * Decimal(str(l.prix_unitaire)) for l in ls),
                    Decimal('0'),
                )
            ),
        })
    return {
        'nombre_ventes': nb,
        'montant_total': _money(total),
        'dernier_achat': dernier.date_creation.isoformat() if dernier else None,
        'ventes': details,
    }


def _client_debts_summary(ctx: ChatbotContext, client_id: int) -> dict:
    dettes = (
        DetteClient.objects.filter(entreprise_id=ctx.tenant_id, client_id=client_id)
        .exclude(statut='PAYEE')
        .with_paiements_aggregate()
        .filter(solde_restant_agg__gt=0)
        .select_related('devise')
    )
    if ctx.branch_id is not None:
        dettes = dettes.filter(succursale_id=ctx.branch_id)
    total = dettes.aggregate(t=Coalesce(Sum('solde_restant_agg'), Decimal('0')))['t']
    items = []
    for d in dettes[:10]:
        items.append({
            'solde': _money(getattr(d, 'solde_restant_agg', 0)),
            'statut': d.statut,
            'devise': d.devise.sigle if d.devise else '',
            'montant_total': _money(d.montant_total),
        })
    return {
        'nombre_dettes': dettes.count(),
        'solde_restant': _money(total),
        'dettes': items,
        'statut': 'retard' if dettes.filter(statut='RETARD').exists() else (
            'dette en cours' if dettes.exists() else 'à jour'
        ),
    }


def fetch_stock_data(ctx: ChatbotContext, intent_result: IntentResult) -> dict:
    stats = aggregate_stock_stats(
        entreprise_id=ctx.tenant_id,
        succursale_id=ctx.branch_id,
    )
    ctx.sources.append('stocks_stats')
    today = timezone.now().date()

    ruptures = []
    alertes = []
    if intent_result.intent in ('stock_rupture_list', 'stock_summary', 'stock_requisition_pdf', 'stock'):
        qs = Stock.objects.filter(article__entreprise_id=ctx.tenant_id, Qte=0).select_related('article')
        if ctx.branch_id is not None:
            qs = qs.filter(article__succursale_id=ctx.branch_id)
        ruptures = [
            {'id': s.article_id, 'nom': s.article.nom_commercial or s.article.nom_scientifique, 'code': s.article.article_id}
            for s in qs[:25]
        ]
        ctx.sources.append('stocks')

    if intent_result.intent in ('stock_alert_list', 'stock_summary', 'stock_requisition_pdf', 'stock'):
        qs = Stock.objects.filter(
            article__entreprise_id=ctx.tenant_id,
            Qte__gt=0,
            Qte__lte=F('seuilAlert'),
        ).select_related('article')
        if ctx.branch_id is not None:
            qs = qs.filter(article__succursale_id=ctx.branch_id)
        alertes = [
            {
                'id': s.article_id,
                'nom': s.article.nom_commercial or s.article.nom_scientifique,
                'quantite': str(s.Qte),
                'seuil': str(s.seuilAlert),
            }
            for s in qs[:25]
        ]

    fin_30 = today + timedelta(days=30)
    fin_90 = _add_months(today, 3)
    exp_30 = list_articles_expiration_dans_fenetre(
        entreprise_id=ctx.tenant_id,
        succursale_id=ctx.branch_id,
        date_fin_inclusive=fin_30,
        today=today,
        limit=50,
    )
    exp_90 = list_articles_expiration_dans_fenetre(
        entreprise_id=ctx.tenant_id,
        succursale_id=ctx.branch_id,
        date_fin_inclusive=fin_90,
        today=today,
        limit=100,
    )
    ctx.sources.append('lignes_entree_expiration')

    product_detail = None
    product_matches: list[dict] = []
    hint = intent_result.product_hint
    if hint:
        arts = Article.objects.filter(entreprise_id=ctx.tenant_id).filter(
            Q(nom_scientifique__icontains=hint)
            | Q(nom_commercial__icontains=hint)
            | Q(article_id__icontains=hint)
        )
        if ctx.branch_id is not None:
            arts = arts.filter(succursale_id=ctx.branch_id)
        for art in arts[:8]:
            st = Stock.objects.filter(article=art).first()
            product_matches.append({
                'id': art.pk,
                'nom': art.nom_commercial or art.nom_scientifique,
                'code': art.article_id,
                'quantite': str(st.Qte if st else 0),
                'seuil_alerte': str(st.seuilAlert if st else 0),
            })
        if len(product_matches) == 1:
            product_detail = product_matches[0]

    return {
        'resume': stats,
        'articles_en_rupture_total': stats['rupture'],
        'articles_en_alerte_total': stats['alerte'],
        'expiration_sous_30_jours': stats['expiration_sous_30_jours'],
        'expiration_sous_3_mois': stats['expiration_sous_3_mois'],
        'articles_expiration_30_jours': exp_30,
        'articles_expiration_90_jours': exp_90,
        'exemples_rupture': ruptures,
        'exemples_alerte': alertes,
        'produit_recherche': product_detail,
        'produits_candidats': product_matches,
        'hint_produit': hint,
    }


def fetch_caisse_data(ctx: ChatbotContext) -> dict:
    from caisse.constants import CAISSE_DEFAUT_CODE
    from caisse.models import MouvementCaisse, SessionCaisse
    from caisse.services.session_caisse import calculer_totaux_session

    ctx.sources.append('caisse')
    sessions = SessionCaisse.objects.filter(
        entreprise_id=ctx.tenant_id,
        statut='OUVERTE',
        type_caisse__est_defaut=True,
        type_caisse__code_type=CAISSE_DEFAUT_CODE,
    ).select_related('devise', 'type_caisse')
    if ctx.branch_id is not None:
        sessions = sessions.filter(succursale_id=ctx.branch_id)

    soldes = []
    for session in sessions[:5]:
        totaux = calculer_totaux_session(session)
        soldes.append({
            'caisse': session.type_caisse.nom or session.type_caisse.libelle,
            'devise': session.devise.sigle if session.devise else '',
            'solde_theorique': str(totaux['solde_theorique']),
            'entrees_session': str(totaux['total_entrees']),
            'sorties_session': str(totaux['total_sorties']),
        })

    today = timezone.now().date()
    mvts = MouvementCaisse.objects.filter(entreprise_id=ctx.tenant_id, date__date=today)
    if ctx.branch_id is not None:
        mvts = mvts.filter(succursale_id=ctx.branch_id)
    encaisse_jour = mvts.filter(type='ENTREE').aggregate(total=Coalesce(Sum('montant'), Decimal('0')))['total']
    sorties_jour = mvts.filter(type='SORTIE').aggregate(total=Coalesce(Sum('montant'), Decimal('0')))['total']
    ctx.sources.append('mouvements_caisse')
    return {
        'sessions_ouvertes': len(soldes),
        'soldes_par_devise': soldes,
        'encaisse_aujourdhui': _money(encaisse_jour),
        'sorties_aujourdhui': _money(sorties_jour),
        'succursale': ctx.succursale_nom,
    }


def fetch_ventes_data(ctx: ChatbotContext, intent_result: IntentResult) -> dict:
    ctx.sources.append('sorties')
    period = intent_result.period
    start = _period_start(period if period != 'all_time' else 'today')
    if intent_result.intent == 'top_selling_products' and period == 'all_time':
        start = None

    sorties = Sortie.objects.filter(entreprise_id=ctx.tenant_id)
    if ctx.branch_id is not None:
        sorties = sorties.filter(succursale_id=ctx.branch_id)
    if start is not None:
        sorties = sorties.filter(date_creation__gte=start)

    nb_ventes = sorties.count()
    nb_credit = sorties.filter(statut='EN_CREDIT').count()
    nb_comptant = sorties.exclude(statut='EN_CREDIT').count()

    lignes = LigneSortie.objects.filter(sortie__in=sorties)
    total_jour = lignes.aggregate(t=Coalesce(Sum(F('quantite') * F('prix_unitaire')), Decimal('0')))['t']

    credit_details = []
    if intent_result.intent == 'credit_sales_today':
        for s in sorties.filter(statut='EN_CREDIT').select_related('client', 'devise')[:20]:
            montant = LigneSortie.objects.filter(sortie=s).aggregate(
                t=Coalesce(Sum(F('quantite') * F('prix_unitaire')), Decimal('0'))
            )['t']
            credit_details.append({
                'client': s.client.nom if s.client else 'Sans client',
                'montant': _money(montant),
                'sortie_id': s.pk,
            })

    top_limit = intent_result.top_n or 5
    top_qs = LigneSortie.objects.filter(sortie__entreprise_id=ctx.tenant_id)
    if ctx.branch_id is not None:
        top_qs = top_qs.filter(sortie__succursale_id=ctx.branch_id)
    if intent_result.intent == 'top_selling_products' and period != 'all_time' and start:
        top_qs = top_qs.filter(sortie__date_creation__gte=start)
    elif intent_result.intent != 'top_selling_products' and start:
        top_qs = top_qs.filter(sortie__date_creation__gte=start)

    top = (
        top_qs.values('article__nom_scientifique', 'article__nom_commercial', 'article__article_id')
        .annotate(
            nb_ventes=Count('sortie_id', distinct=True),
            qte=Coalesce(Sum('quantite'), Decimal('0')),
        )
        .order_by('-nb_ventes')[:top_limit]
    )
    top_list = [
        {
            'nom': row['article__nom_commercial'] or row['article__nom_scientifique'],
            'code': row['article__article_id'],
            'nombre_ventes': row['nb_ventes'],
            'quantite': str(row['qte']),
        }
        for row in top
    ]
    ctx.sources.append('lignesorties')
    return {
        'periode': period,
        'ventes_aujourdhui': nb_ventes,
        'ventes_credit': nb_credit,
        'ventes_comptant': nb_comptant,
        'montant_total': _money(total_jour),
        'produits_plus_vendus': top_list,
        'ventes_credit_details': credit_details,
    }


def fetch_approvisionnements(ctx: ChatbotContext, intent_result: IntentResult) -> dict:
    ctx.sources.append('entrees')
    qs = Entree.objects.filter(entreprise_id=ctx.tenant_id).order_by('-date_op', '-id')
    if ctx.branch_id is not None:
        qs = qs.filter(succursale_id=ctx.branch_id)
    if intent_result.intent == 'approvisionnement_today' or intent_result.period == 'today':
        today = timezone.now().date()
        qs = qs.filter(date_op__date=today)

    items = []
    for e in qs[:15]:
        lignes = LigneEntree.objects.filter(entree=e).select_related('article', 'devise')
        nb_art = lignes.values('article').distinct().count()
        total = sum(
            (Decimal(str(l.quantite)) * Decimal(str(l.prix_unitaire or 0)) for l in lignes),
            Decimal('0'),
        )
        date_val = e.date_op.date().isoformat() if e.date_op else ''
        items.append({
            'id': e.pk,
            'libelle': e.libele,
            'date': date_val,
            'nb_articles': nb_art,
            'total': _money(total),
        })
    return {
        'nombre': qs.count() if intent_result.intent == 'approvisionnement_today' else len(items),
        'nombre_total_filtre': qs.count(),
        'approvisionnements': items,
        'periode': intent_result.period,
    }


def fetch_dettes_data(ctx: ChatbotContext, intent_result: IntentResult) -> dict:
    ctx.sources.append('dettes')
    hint = intent_result.client_hint
    if hint:
        matches = _search_clients(ctx, hint)
        if len(matches) == 1:
            debts = _client_debts_summary(ctx, matches[0]['id'])
            return {
                'mode': 'client',
                'client': matches[0],
                'dettes_client': debts,
                'clients_candidats': [],
            }
        if len(matches) > 1:
            return {'mode': 'ambiguous', 'clients_candidats': matches, 'hint': hint}
        return {'mode': 'not_found', 'hint': hint, 'clients_candidats': []}

    dettes = (
        DetteClient.objects.filter(entreprise_id=ctx.tenant_id)
        .exclude(statut='PAYEE')
        .with_paiements_aggregate()
        .filter(solde_restant_agg__gt=0)
        .select_related('client', 'devise')
    )
    if ctx.branch_id is not None:
        dettes = dettes.filter(succursale_id=ctx.branch_id)
    total_solde = dettes.aggregate(t=Coalesce(Sum('solde_restant_agg'), Decimal('0')))['t']
    clients_dette = [
        {
            'id': d.client_id,
            'nom': d.client.nom,
            'solde': _money(d.solde_restant_agg),
            'devise': d.devise.sigle if d.devise else '',
            'statut': d.statut,
        }
        for d in dettes.order_by('-solde_restant_agg')[:15]
    ]
    return {
        'mode': 'global',
        'nombre_dettes_en_cours': dettes.count(),
        'nombre_en_retard': dettes.filter(statut='RETARD').count(),
        'solde_total': _money(total_solde),
        'principaux_debiteurs': clients_dette,
    }


def fetch_clients_data(ctx: ChatbotContext, intent_result: IntentResult) -> dict:
    from stock.models import ClientEntreprise

    ctx.sources.append('clients')
    hint = intent_result.client_hint

    if hint:
        matches = _search_clients(ctx, hint)
        if not matches:
            return {'mode': 'not_found', 'hint': hint, 'nombre_clients': 0, 'exemples_clients': []}
        if len(matches) > 1 and intent_result.intent in (
            'client_situation', 'client_purchase_history', 'client_invoice_pdf',
            'client_debt_detail', 'client_debt_pdf', 'client_search',
        ):
            # exact match preferred
            exact = [m for m in matches if m['nom'].lower() == hint.lower()]
            if len(exact) == 1:
                matches = exact
            else:
                return {
                    'mode': 'ambiguous',
                    'hint': hint,
                    'clients_candidats': matches,
                    'nombre_clients': len(matches),
                }

        client = matches[0]
        sales = _client_sales_summary(
            ctx,
            client['id'],
            period=intent_result.period if intent_result.intent == 'client_purchase_history' else 'all_time',
        )
        if intent_result.intent == 'client_purchase_history':
            sales = _client_sales_summary(ctx, client['id'], period=intent_result.period or 'today')
        debts = _client_debts_summary(ctx, client['id'])
        return {
            'mode': 'detail',
            'client': client,
            'ventes': sales,
            'dettes': debts,
            'existe': True,
        }

    qs = (
        ClientEntreprise.objects.filter(entreprise_id=ctx.tenant_id)
        .select_related('client')
        .order_by('client__nom')
    )
    if ctx.branch_id is not None:
        qs = qs.filter(Q(succursale_id=ctx.branch_id) | Q(succursale_id__isnull=True))
    total = qs.count()
    exemples = [
        {'id': lien.client_id, 'nom': lien.client.nom, 'telephone': lien.client.telephone or ''}
        for lien in qs[:25]
    ]
    return {
        'mode': 'list',
        'nombre_clients': total,
        'exemples_clients': exemples,
        'liste_tronquee': total > len(exemples),
    }


def fetch_abonnement_data(ctx: ChatbotContext) -> dict:
    from abonnements.services.licence import build_etat_licence

    ctx.sources.append('abonnement')
    etat = build_etat_licence(ctx.tenant_id) if ctx.tenant_id else {}
    return {
        'licence': {
            'statut': etat.get('statut'),
            'est_actif': etat.get('est_actif'),
            'est_essai': etat.get('est_essai'),
            'jours_restants': etat.get('jours_restants'),
            'formule': (etat.get('formule') or {}).get('nom') if isinstance(etat.get('formule'), dict) else None,
        },
    }


def fetch_subscription_plans(ctx: ChatbotContext) -> dict:
    from abonnements.models import FormuleAbonnement

    ctx.sources.append('formules')
    qs = FormuleAbonnement.objects.filter(est_active=True, est_visible_catalogue=True).order_by('ordre_affichage', 'id')
    plans = []
    for f in qs:
        plans.append({
            'nom': f.nom,
            'description': f.description or '',
            'prix_mensuel': str(f.prix_mensuel),
            'prix_annuel': str(f.prix_annuel) if f.prix_annuel is not None else None,
            'devise': f.devise or 'USD',
            'limites': f.limites if isinstance(f.limites, dict) else {},
            'fonctionnalites': f.fonctionnalites if isinstance(getattr(f, 'fonctionnalites', None), (dict, list)) else [],
        })
    return {'plans': plans}


def fetch_platform_data(ctx: ChatbotContext) -> dict:
    from abonnements.models import AbonnementEntreprise
    from stock.models import Entreprise

    ctx.sources.append('plateforme')
    return {
        'entreprises_total': Entreprise.objects.count(),
        'abonnements_en_attente': AbonnementEntreprise.objects.filter(
            statut=AbonnementEntreprise.STATUT_EN_ATTENTE,
        ).count(),
        'abonnements_actifs': AbonnementEntreprise.objects.filter(
            statut=AbonnementEntreprise.STATUT_ACTIF,
        ).count(),
        'abonnements_essai': AbonnementEntreprise.objects.filter(
            statut=AbonnementEntreprise.STATUT_ESSAI,
        ).count(),
    }


def fetch_for_intent(ctx: ChatbotContext, intent_result: IntentResult) -> dict | None:
    intent = intent_result.intent
    if intent in (
        'stock', 'stock_summary', 'stock_article_count', 'stock_rupture_list',
        'stock_alert_list', 'stock_expiration_30_days', 'stock_expiration_90_days',
        'stock_article_detail', 'stock_sheet_pdf', 'stock_requisition_pdf',
    ):
        return fetch_stock_data(ctx, intent_result)
    if intent in ('caisse', 'caisse_balance'):
        return fetch_caisse_data(ctx)
    if intent in ('ventes', 'vente_today_summary', 'credit_sales_today', 'top_selling_products'):
        return fetch_ventes_data(ctx, intent_result)
    if intent in ('approvisionnement_list', 'approvisionnement_today'):
        return fetch_approvisionnements(ctx, intent_result)
    if intent in (
        'dettes', 'debt_summary', 'client_debt_detail', 'client_debt_pdf',
        'debt_clients_pdf', 'clients_with_debts',
    ):
        # Force liste débiteurs sans recherche par nom parasite
        if intent == 'clients_with_debts':
            intent_result.client_hint = None
        return fetch_dettes_data(ctx, intent_result)
    if intent in (
        'clients', 'client_count', 'client_list', 'client_search', 'client_situation',
        'client_purchase_history', 'client_invoice_pdf',
    ):
        return fetch_clients_data(ctx, intent_result)
    if intent == 'abonnement':
        return fetch_abonnement_data(ctx)
    if intent == 'subscription_plans_list':
        return fetch_subscription_plans(ctx)
    if intent == 'platform':
        return fetch_platform_data(ctx)
    if intent == 'rapports':
        return {
            'stock': fetch_stock_data(ctx, intent_result),
            'ventes': fetch_ventes_data(ctx, intent_result),
            'caisse': fetch_caisse_data(ctx),
            'dettes': fetch_dettes_data(ctx, intent_result),
        }
    if intent == 'aide':
        return {'mode': 'documentation'}
    return None
