"""Outils métier — données filtrées tenant."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from chatbot.context import ChatbotContext
from chatbot.services.intent_classifier import extract_client_hint, extract_product_hint
from stock.models import Article, DetteClient, LigneSortie, Sortie, Stock
from stock.services.stock_stats import (
    aggregate_stock_stats,
    list_articles_expiration_dans_fenetre,
)


def _money(value) -> str:
    if value is None:
        return '0'
    return str(Decimal(str(value)).quantize(Decimal('0.01')))


def fetch_stock_data(ctx: ChatbotContext, message: str) -> dict:
    stats = aggregate_stock_stats(
        entreprise_id=ctx.tenant_id,
        succursale_id=ctx.branch_id,
    )
    ctx.sources.append('stocks_stats')

    ruptures_qs = Stock.objects.filter(
        article__entreprise_id=ctx.tenant_id,
        Qte=0,
    ).select_related('article')
    if ctx.branch_id is not None:
        ruptures_qs = ruptures_qs.filter(article__succursale_id=ctx.branch_id)

    ruptures = [
        {
            'nom': s.article.nom_commercial or s.article.nom_scientifique,
            'code': s.article.article_id,
        }
        for s in ruptures_qs[:10]
    ]
    ctx.sources.append('stocks')

    today = timezone.now().date()
    fin_30 = today + timedelta(days=30)
    articles_expiration_30 = list_articles_expiration_dans_fenetre(
        entreprise_id=ctx.tenant_id,
        succursale_id=ctx.branch_id,
        date_fin_inclusive=fin_30,
        today=today,
        limit=30,
    )
    ctx.sources.append('lignes_entree_expiration')

    product_hint = extract_product_hint(message)
    product_detail = None
    if product_hint:
        art = Article.objects.filter(
            entreprise_id=ctx.tenant_id,
        ).filter(
            Q(nom_scientifique__icontains=product_hint)
            | Q(nom_commercial__icontains=product_hint)
            | Q(article_id__iexact=product_hint)
        )
        if ctx.branch_id is not None:
            art = art.filter(succursale_id=ctx.branch_id)
        art = art.first()
        if art:
            st = Stock.objects.filter(article=art).first()
            product_detail = {
                'nom': art.nom_commercial or art.nom_scientifique,
                'code': art.article_id,
                'quantite': str(st.Qte if st else 0),
                'seuil_alerte': str(st.seuilAlert if st else 0),
            }

    return {
        'resume': stats,
        'articles_en_rupture_total': stats['rupture'],
        'articles_en_alerte_total': stats['alerte'],
        'expiration_sous_30_jours': stats['expiration_sous_30_jours'],
        'expiration_sous_3_mois': stats['expiration_sous_3_mois'],
        'articles_expiration_30_jours': articles_expiration_30,
        'exemples_rupture': ruptures,
        'produit_recherche': product_detail,
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
    mvts = MouvementCaisse.objects.filter(
        entreprise_id=ctx.tenant_id,
        date__date=today,
    )
    if ctx.branch_id is not None:
        mvts = mvts.filter(succursale_id=ctx.branch_id)

    encaisse_jour = mvts.filter(type='ENTREE').aggregate(
        total=Coalesce(Sum('montant'), Decimal('0'))
    )['total']
    ctx.sources.append('mouvements_caisse')

    return {
        'sessions_ouvertes': len(soldes),
        'soldes_par_devise': soldes,
        'encaisse_aujourdhui': _money(encaisse_jour),
        'succursale': ctx.succursale_nom,
    }


def fetch_ventes_data(ctx: ChatbotContext) -> dict:
    ctx.sources.append('sorties')

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    sorties = Sortie.objects.filter(
        entreprise_id=ctx.tenant_id,
        date_creation__gte=today_start,
    )
    if ctx.branch_id is not None:
        sorties = sorties.filter(succursale_id=ctx.branch_id)

    nb_ventes = sorties.count()
    nb_credit = sorties.filter(statut='EN_CREDIT').count()

    lignes = LigneSortie.objects.filter(sortie__in=sorties)
    montant_expr = Sum(F('quantite') * F('prix_unitaire'))
    total_jour = lignes.aggregate(t=Coalesce(montant_expr, Decimal('0')))['t']

    top = (
        lignes.values('article__nom_scientifique', 'article__nom_commercial', 'article__article_id')
        .annotate(nb_ventes=Count('sortie_id', distinct=True))
        .order_by('-nb_ventes')[:10]
    )
    top_list = [
        {
            'nom': row['article__nom_commercial'] or row['article__nom_scientifique'],
            'code': row['article__article_id'],
            'nombre_ventes': row['nb_ventes'],
        }
        for row in top
    ]
    ctx.sources.append('lignesorties')

    return {
        'ventes_aujourdhui': nb_ventes,
        'ventes_credit_aujourdhui': nb_credit,
        'montant_total_jour': _money(total_jour),
        'produits_plus_vendus': top_list,
    }


def fetch_dettes_data(ctx: ChatbotContext, message: str) -> dict:
    ctx.sources.append('dettes')

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
    nb_dettes = dettes.count()
    nb_retard = dettes.filter(statut='RETARD').count()

    clients_dette = [
        {
            'nom': d.client.nom,
            'solde': _money(d.solde_restant_agg),
            'devise': d.devise.sigle if d.devise else '',
            'statut': d.statut,
        }
        for d in dettes.order_by('-solde_restant_agg')[:10]
    ]

    client_hint = extract_client_hint(message)
    client_detail = None
    if client_hint:
        from stock.models import ClientEntreprise

        lien = ClientEntreprise.objects.filter(
            entreprise_id=ctx.tenant_id,
            client__nom__icontains=client_hint,
        ).select_related('client')
        if ctx.branch_id is not None:
            lien = lien.filter(succursale_id=ctx.branch_id)
        lien = lien.first()
        if lien:
            client = lien.client
            client_dettes = (
                DetteClient.objects.filter(client=client, entreprise_id=ctx.tenant_id)
                .exclude(statut='PAYEE')
                .with_paiements_aggregate()
                .filter(solde_restant_agg__gt=0)
            )
            client_detail = {
                'nom': client.nom,
                'dettes': [
                    {
                        'solde': _money(d.solde_restant_agg),
                        'devise': d.devise.sigle if d.devise else '',
                        'statut': d.statut,
                    }
                    for d in client_dettes[:5]
                ],
            }

    return {
        'nombre_dettes_en_cours': nb_dettes,
        'nombre_en_retard': nb_retard,
        'solde_total': _money(total_solde),
        'principaux_debiteurs': clients_dette,
        'client_recherche': client_detail,
    }


def fetch_clients_data(ctx: ChatbotContext) -> dict:
    from stock.models import ClientEntreprise

    ctx.sources.append('clients')
    qs = (
        ClientEntreprise.objects.filter(entreprise_id=ctx.tenant_id)
        .select_related('client')
        .order_by('client__nom')
    )
    if ctx.branch_id is not None:
        qs = qs.filter(succursale_id=ctx.branch_id)

    total = qs.count()
    exemples = [
        {
            'nom': lien.client.nom,
            'telephone': getattr(lien.client, 'telephone', None) or '',
        }
        for lien in qs[:25]
    ]
    return {
        'nombre_clients': total,
        'exemples_clients': exemples,
        'liste_tronquee': total > len(exemples),
    }


def fetch_rapports_data(ctx: ChatbotContext, message: str) -> dict:
    ctx.sources.append('rapports')
    return {
        'stock': fetch_stock_data(ctx, message),
        'ventes': fetch_ventes_data(ctx),
        'caisse': fetch_caisse_data(ctx),
        'dettes': fetch_dettes_data(ctx, message),
    }


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


def fetch_for_intent(ctx: ChatbotContext, intent: str, message: str) -> dict | None:
    if intent == 'stock':
        return fetch_stock_data(ctx, message)
    if intent == 'caisse':
        return fetch_caisse_data(ctx)
    if intent == 'ventes':
        return fetch_ventes_data(ctx)
    if intent == 'dettes':
        return fetch_dettes_data(ctx, message)
    if intent == 'clients':
        return fetch_clients_data(ctx)
    if intent == 'rapports':
        return fetch_rapports_data(ctx, message)
    if intent == 'platform':
        return fetch_platform_data(ctx)
    if intent == 'abonnement':
        return fetch_abonnement_data(ctx)
    if intent == 'aide':
        return {'mode': 'documentation'}
    return None
