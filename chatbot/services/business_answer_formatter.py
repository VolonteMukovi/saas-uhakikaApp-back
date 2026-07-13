"""Formulation naturelle des réponses métier sans appel Gemini."""
from __future__ import annotations


def format_business_answer(intent: str, context_payload: dict) -> str | None:
    data = context_payload.get('donnees_autorisees') or {}
    if not data:
        return None

    entreprise = context_payload.get('entreprise') or 'votre entreprise'
    succursale = context_payload.get('succursale')
    question = (context_payload.get('question') or '').lower()

    scope = f'l’entreprise {entreprise}'
    if succursale:
        scope = f'l’entreprise {entreprise}, succursale {succursale}'

    if intent == 'stock':
        return _format_stock(data, scope, question=question)
    if intent == 'ventes':
        return _format_ventes(data, scope)
    if intent == 'clients':
        return _format_clients(data, scope)
    if intent == 'caisse':
        return _format_caisse(data, scope)
    if intent == 'dettes':
        return _format_dettes(data, scope)
    if intent == 'abonnement':
        return _format_abonnement(data)
    if intent == 'rapports':
        return _format_rapports(data, scope)
    if intent == 'platform':
        return _format_platform(data)
    return None


def _format_stock(data: dict, scope: str, *, question: str = '') -> str:
    resume = data.get('resume') or {}
    exp_list = data.get('articles_expiration_30_jours') or []
    exp30 = resume.get('expiration_sous_30_jours', data.get('expiration_sous_30_jours', 0))
    exp3m = resume.get('expiration_sous_3_mois', data.get('expiration_sous_3_mois', 0))

    focus_expiration = any(
        w in question
        for w in ('expir', 'dlc', 'perime', 'périmé', '30 jour', 'prochains jours')
    )

    if focus_expiration:
        lines = [
            f'Pour {scope}, {exp30} article(s) expirent dans les 30 prochains jours.',
        ]
        if exp_list:
            lines.append('')
            lines.append('Voici la liste :')
            for item in exp_list:
                nom = item.get('nom') or item.get('code') or 'Article'
                date_exp = item.get('date_expiration') or '—'
                qte = item.get('quantite_restante')
                extra = f' (reste : {qte})' if qte is not None else ''
                lines.append(f'- {nom} — expire le {date_exp}{extra}')
        elif exp30:
            lines.append(
                'Je n’ai pas pu récupérer le détail des noms pour le moment. '
                'Réessayez ou consultez le module Stock.'
            )
        else:
            lines.append('Aucun article n’expire dans les 30 prochains jours.')
        if exp3m and exp3m != exp30:
            lines.append('')
            lines.append(
                f'À plus long terme : {exp3m} article(s) expirent dans les 3 prochains mois.'
            )
        return '\n'.join(lines)

    total = resume.get('total', 0)
    rupture = resume.get('rupture', data.get('articles_en_rupture_total', 0))
    alerte = resume.get('alerte', data.get('articles_en_alerte_total', 0))
    normal = resume.get('normal', 0)

    lines = [f'Voici l’état du stock pour {scope} :']
    lines.append(f'- {total} article(s) suivis au total')
    lines.append(f'- {normal} en stock normal')
    lines.append(f'- {alerte} en alerte (seuil bas)')
    lines.append(f'- {rupture} en rupture')

    if exp30 or exp_list:
        lines.append('')
        lines.append(f'Expiration sous 30 jours : {exp30} article(s)')
        for item in exp_list[:10]:
            nom = item.get('nom') or item.get('code') or 'Article'
            date_exp = item.get('date_expiration') or '—'
            lines.append(f'- {nom} — expire le {date_exp}')

    exemples = data.get('exemples_rupture') or []
    if exemples:
        lines.append('')
        lines.append('Exemples d’articles en rupture :')
        for item in exemples[:5]:
            nom = item.get('nom') or item.get('code') or 'Article'
            lines.append(f'- {nom}')

    produit = data.get('produit_recherche')
    if produit:
        lines.append('')
        lines.append(
            f'Stock de {produit.get("nom")} : {produit.get("quantite", "0")} '
            f'(seuil d’alerte : {produit.get("seuil_alerte", "0")})'
        )

    return '\n'.join(lines)


def _format_ventes(data: dict, scope: str) -> str:
    nb = data.get('ventes_aujourdhui', 0)
    montant = data.get('montant_total_jour', '0')
    lines = [
        f'Aujourd’hui, pour {scope}, vous avez effectué {nb} vente(s), '
        f'pour un montant total de {montant}.',
    ]
    top = data.get('produits_plus_vendus') or []
    if top:
        lines.append('')
        lines.append('Les produits les plus vendus sont :')
        for item in top[:5]:
            lines.append(
                f'- {item.get("nom", "Produit")} : {item.get("nombre_ventes", 0)} vente(s)'
            )
    return '\n'.join(lines)


def _format_clients(data: dict, scope: str) -> str:
    nb = data.get('nombre_clients', 0)
    exemples = data.get('exemples_clients') or []
    lines = [f'Vous avez actuellement {nb} client(s) enregistré(s) dans {scope}.']
    if exemples:
        lines.append('')
        lines.append('Voici quelques clients :')
        for c in exemples:
            nom = c.get('nom') or 'Client'
            tel = c.get('telephone') or ''
            if tel:
                lines.append(f'- {nom} ({tel})')
            else:
                lines.append(f'- {nom}')
        if data.get('liste_tronquee'):
            lines.append('')
            lines.append(
                f'La liste est limitée aux {len(exemples)} premiers. '
                'Consultez le module Clients pour voir l’ensemble.'
            )
    return '\n'.join(lines)


def _format_caisse(data: dict, scope: str) -> str:
    lines = [f'État de la caisse pour {scope} :']
    soldes = data.get('soldes_par_devise') or []
    if soldes:
        for solde in soldes:
            devise = solde.get('devise') or ''
            lines.append(
                f'- {solde.get("caisse", "Caisse")} : solde théorique '
                f'{solde.get("solde_theorique", "0")} {devise}'.strip()
            )
    else:
        lines.append('- Aucune session de caisse ouverte pour le moment.')
    encaisse = data.get('encaisse_aujourdhui')
    if encaisse is not None:
        lines.append(f'- Encaissements du jour : {encaisse}')
    return '\n'.join(lines)


def _format_dettes(data: dict, scope: str) -> str:
    lines = [
        f'Pour {scope} :',
        f'- {data.get("nombre_dettes_en_cours", 0)} dette(s) en cours',
        f'- {data.get("nombre_en_retard", 0)} en retard',
        f'- Solde total restant : {data.get("solde_total", "0")}',
    ]
    debiteurs = data.get('principaux_debiteurs') or []
    if debiteurs:
        lines.append('')
        lines.append('Principaux débiteurs :')
        for d in debiteurs[:5]:
            devise = d.get('devise') or ''
            lines.append(
                f'- {d.get("nom", "Client")} : {d.get("solde", "0")} {devise}'.strip()
            )
    return '\n'.join(lines)


def _format_abonnement(data: dict) -> str:
    licence = data.get('licence') or {}
    formule = licence.get('formule') or '—'
    statut = licence.get('statut') or '—'
    jours = licence.get('jours_restants')
    lines = [
        f'Votre abonnement UHAKIKAAPP : formule {formule}, statut {statut}.',
    ]
    if jours is not None:
        lines.append(f'Jours restants : {jours}.')
    return '\n'.join(lines)


def _format_platform(data: dict) -> str:
    return (
        f'Plateforme UHAKIKAAPP : {data.get("entreprises_total", 0)} entreprise(s), '
        f'{data.get("abonnements_actifs", 0)} abonnement(s) actif(s), '
        f'{data.get("abonnements_en_attente", 0)} en attente, '
        f'{data.get("abonnements_essai", 0)} en essai.'
    )


def _format_rapports(data: dict, scope: str) -> str:
    parts = [f'Synthèse pour {scope} :', '']
    if data.get('stock'):
        parts.append(_format_stock(data['stock'], scope))
        parts.append('')
    if data.get('ventes'):
        parts.append(_format_ventes(data['ventes'], scope))
        parts.append('')
    if data.get('caisse'):
        parts.append(_format_caisse(data['caisse'], scope))
        parts.append('')
    if data.get('dettes'):
        parts.append(_format_dettes(data['dettes'], scope))
    return '\n'.join(parts).strip()
