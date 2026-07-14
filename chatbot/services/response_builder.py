"""Construction des réponses métier structurées (texte + actions frontend)."""
from __future__ import annotations

from datetime import datetime


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return '—'
    try:
        if 'T' in iso:
            return datetime.fromisoformat(iso.replace('Z', '+00:00')).strftime('%d/%m/%Y')
        return datetime.strptime(iso[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return iso


def _action_pdf(label: str, url: str) -> dict:
    return {'type': 'open_pdf', 'label': label, 'url': url}


def _action_select_client(label: str, value: int) -> dict:
    return {'type': 'select_client', 'label': label, 'value': value}


def _action_select_article(label: str, value: int) -> dict:
    return {'type': 'select_article', 'label': label, 'value': value}


def build_response(intent: str, context_payload: dict) -> dict | None:
    """
    Retourne {answer, actions?, file?, entities?} ou None.
    """
    data = context_payload.get('donnees_autorisees')
    if data is None and intent not in ('aide',):
        return None

    entreprise = context_payload.get('entreprise') or 'votre entreprise'
    succursale = context_payload.get('succursale')
    scope = f'l’entreprise {entreprise}'
    if succursale:
        scope = f'l’entreprise {entreprise}, succursale {succursale}'

    builders = {
        'stock': _stock_summary,
        'stock_summary': _stock_summary,
        'stock_article_count': _stock_count,
        'stock_rupture_list': _stock_rupture,
        'stock_alert_list': _stock_alert,
        'stock_expiration_30_days': lambda d, s: _stock_expiration(d, s, days=30),
        'stock_expiration_90_days': lambda d, s: _stock_expiration(d, s, days=90),
        'stock_article_detail': _stock_article_detail,
        'stock_sheet_pdf': _stock_sheet_pdf,
        'stock_requisition_pdf': _stock_requisition_pdf,
        'clients': _clients,
        'client_count': _clients,
        'client_list': _clients,
        'client_search': _client_detail_or_search,
        'client_situation': _client_situation,
        'client_purchase_history': _client_purchases,
        'client_invoice_pdf': _client_invoice_pdf,
        'client_debt_detail': _client_debt,
        'client_debt_pdf': _client_debt_pdf,
        'debt_clients_pdf': _debt_clients_pdf,
        'dettes': _debt_global,
        'debt_summary': _debt_global,
        'clients_with_debts': _clients_with_debts,
        'ventes': _ventes,
        'vente_today_summary': _ventes,
        'credit_sales_today': _credit_sales,
        'top_selling_products': _top_products,
        'approvisionnement_list': _appro,
        'approvisionnement_today': _appro,
        'caisse': _caisse,
        'caisse_balance': _caisse,
        'abonnement': _abonnement,
        'subscription_plans_list': _plans,
        'platform': _platform,
        'rapports': _rapports,
    }
    fn = builders.get(intent)
    if not fn:
        return None
    return fn(data or {}, scope)


def _stock_summary(data: dict, scope: str) -> dict:
    resume = data.get('resume') or {}
    lines = [
        f'Voici l’état du stock pour {scope} :',
        f'- {resume.get("total", 0)} article(s) suivis',
        f'- {resume.get("normal", 0)} en stock normal',
        f'- {resume.get("alerte", 0)} en alerte',
        f'- {resume.get("rupture", 0)} en rupture',
    ]
    exp30 = data.get('articles_expiration_30_jours') or []
    if exp30:
        lines.append('')
        lines.append(f'Expiration sous 30 jours ({len(exp30)}) :')
        for i, item in enumerate(exp30[:5], 1):
            lines.append(
                f'{i}. {item.get("nom")} — expire le {_fmt_date(item.get("date_expiration"))}'
            )
    return {'answer': '\n'.join(lines), 'actions': []}


def _stock_count(data: dict, scope: str) -> dict:
    resume = data.get('resume') or {}
    answer = (
        f'Vous avez actuellement {resume.get("total", 0)} articles suivis dans {scope} :\n'
        f'- {resume.get("normal", 0)} en stock normal\n'
        f'- {resume.get("alerte", 0)} en alerte\n'
        f'- {resume.get("rupture", 0)} en rupture'
    )
    return {'answer': answer, 'actions': []}


def _stock_rupture(data: dict, scope: str) -> dict:
    items = data.get('exemples_rupture') or []
    total = data.get('articles_en_rupture_total', len(items))
    lines = [f'{total} article(s) en rupture dans {scope}.']
    if items:
        lines.append('')
        lines.append('Liste :')
        for i, it in enumerate(items, 1):
            lines.append(f'{i}. {it.get("nom")}')
    return {'answer': '\n'.join(lines), 'actions': []}


def _stock_alert(data: dict, scope: str) -> dict:
    items = data.get('exemples_alerte') or []
    total = data.get('articles_en_alerte_total', len(items))
    lines = [f'{total} article(s) en alerte dans {scope}.']
    if items:
        lines.append('')
        for i, it in enumerate(items, 1):
            lines.append(f'{i}. {it.get("nom")} — qté {it.get("quantite")} (seuil {it.get("seuil")})')
    return {'answer': '\n'.join(lines), 'actions': []}


def _stock_expiration(data: dict, scope: str, *, days: int) -> dict:
    key = 'articles_expiration_30_jours' if days <= 30 else 'articles_expiration_90_jours'
    items = data.get(key) or []
    label = '30 prochains jours' if days <= 30 else '3 prochains mois'
    count_key = 'expiration_sous_30_jours' if days <= 30 else 'expiration_sous_3_mois'
    resume = data.get('resume') or {}
    n = resume.get(count_key, len(items))
    lines = [f'Pour {scope}, {n} article(s) expirent dans les {label} :', '']
    if items:
        for i, it in enumerate(items, 1):
            qte = it.get('quantite_restante')
            extra = f' — reste : {qte}' if qte is not None else ''
            lines.append(
                f'{i}. {it.get("nom")} — expire le {_fmt_date(it.get("date_expiration"))}{extra}'
            )
    else:
        lines.append('Aucun article trouvé pour cette période.')
    other = resume.get('expiration_sous_3_mois') if days <= 30 else resume.get('expiration_sous_30_jours')
    if days <= 30 and other and other != n:
        lines.append('')
        lines.append(f'Il y a aussi {other} article(s) qui expirent dans les 3 prochains mois.')
    return {'answer': '\n'.join(lines), 'actions': []}


def _stock_article_detail(data: dict, scope: str) -> dict:
    candidats = data.get('produits_candidats') or []
    produit = data.get('produit_recherche')
    if len(candidats) > 1 and not produit:
        actions = [_action_select_article(c['nom'], c['id']) for c in candidats]
        lines = [
            f'J’ai trouvé plusieurs articles correspondant à « {data.get("hint_produit")} ». '
            'Lequel voulez-vous consulter ?',
        ]
        for i, c in enumerate(candidats, 1):
            lines.append(f'{i}. {c["nom"]} (stock : {c["quantite"]})')
        return {'answer': '\n'.join(lines), 'actions': actions}
    if not produit and not candidats:
        return {
            'answer': (
                f'Je n’ai pas trouvé l’article « {data.get("hint_produit") or "…"} » dans {scope}. '
                'Précisez le nom complet.'
            ),
            'actions': [],
        }
    p = produit or candidats[0]
    answer = (
        f'Stock de {p["nom"]} dans {scope} :\n'
        f'- Quantité : {p.get("quantite", "0")}\n'
        f'- Seuil d’alerte : {p.get("seuil_alerte", "0")}'
    )
    actions = []
    if p.get('id'):
        actions.append(_action_pdf(
            f'Fiche stock {p["nom"]}',
            f'/api/rapports/{p["id"]}/fiche-stock/',
        ))
    return {'answer': answer, 'actions': actions, 'entities': {'article': p.get('nom'), 'article_id': p.get('id')}}


def _stock_sheet_pdf(data: dict, scope: str) -> dict:
    base = _stock_article_detail(data, scope)
    produit = data.get('produit_recherche')
    candidats = data.get('produits_candidats') or []
    if not produit and len(candidats) != 1:
        if not data.get('hint_produit'):
            return {
                'answer': (
                    'Je n’ai pas assez d’informations pour identifier l’article.\n'
                    'Veuillez préciser le nom complet de l’article pour générer la fiche de stock.'
                ),
                'actions': [],
            }
        return base
    p = produit or candidats[0]
    url = f'/api/rapports/{p["id"]}/fiche-stock/'
    answer = (
        f'J’ai trouvé l’article « {p["nom"]} » (stock : {p.get("quantite", "0")}).\n\n'
        'La fiche de stock est prête (mouvements, lots, quantités).'
    )
    return {
        'answer': answer,
        'actions': [
            _action_pdf('Ouvrir la fiche stock', url),
            {'type': 'download_pdf', 'label': 'Télécharger', 'url': url},
        ],
        'file': {'type': 'pdf', 'label': f'Fiche stock - {p["nom"]}', 'url': url},
        'entities': {'article': p['nom'], 'article_id': p['id']},
    }


def _stock_requisition_pdf(data: dict, scope: str) -> dict:
    resume = data.get('resume') or {}
    rupture = resume.get('rupture', data.get('articles_en_rupture_total', 0))
    alerte = resume.get('alerte', data.get('articles_en_alerte_total', 0))
    ruptures = data.get('exemples_rupture') or []
    alertes = data.get('exemples_alerte') or []
    # Snapshot historique conservé ; module CRUD = /api/requisitions/
    snapshot_url = '/api/rapports/bon-entree/'
    module_url = '/api/requisitions/'
    lines = [
        f'D’accord. Voici un aperçu des produits à réapprovisionner pour {scope}.',
        '',
        'Vous pouvez créer une vraie réquisition (modifiable, validable, PDF) via le module Réquisitions.',
        f'- {rupture} article(s) en rupture',
        f'- {alerte} article(s) en alerte',
    ]
    if ruptures:
        lines.append('')
        lines.append('Exemples en rupture (à commander en priorité) :')
        for i, it in enumerate(ruptures[:15], 1):
            lines.append(f'{i}. {it.get("nom")}')
    if alertes:
        lines.append('')
        lines.append('Exemples en alerte (stock faible) :')
        for i, it in enumerate(alertes[:15], 1):
            lines.append(
                f'{i}. {it.get("nom")} — qté {it.get("quantite")} '
                f'(seuil {it.get("seuil")})'
            )
    lines.append('')
    lines.append('Créez ensuite une réquisition personnalisable dans le module dédié.')
    return {
        'answer': '\n'.join(lines),
        'actions': [
            {
                'type': 'open_module',
                'label': 'Ouvrir les réquisitions',
                'url': module_url,
            },
            _action_pdf('Aperçu rupture/alerte (JSON)', snapshot_url),
        ],
        'file': {
            'type': 'module',
            'label': f'Réquisitions - {scope}',
            'url': module_url,
        },
    }


def _clients(data: dict, scope: str) -> dict:
    if data.get('mode') == 'detail':
        return _client_situation(data, scope)
    nb = data.get('nombre_clients', 0)
    exemples = data.get('exemples_clients') or []
    lines = [f'Vous avez {nb} client(s) enregistré(s) dans {scope}.']
    if exemples:
        lines.append('')
        lines.append(f'Voici les {len(exemples)} premiers :')
        for i, c in enumerate(exemples, 1):
            lines.append(f'{i}. {c.get("nom")}')
        if data.get('liste_tronquee'):
            lines.append('')
            lines.append(
                'La liste est limitée. Vous pouvez me demander de rechercher un client précis.'
            )
    return {'answer': '\n'.join(lines), 'actions': []}


def _ambiguous_clients(data: dict) -> dict:
    candidats = data.get('clients_candidats') or []
    hint = data.get('hint') or ''
    lines = [f'J’ai trouvé plusieurs clients correspondant à « {hint} » :', '']
    actions = []
    for i, c in enumerate(candidats, 1):
        lines.append(f'{i}. {c["nom"]}')
        actions.append(_action_select_client(c['nom'], c['id']))
    lines.append('')
    lines.append('Lequel voulez-vous consulter ?')
    return {'answer': '\n'.join(lines), 'actions': actions}


def _client_detail_or_search(data: dict, scope: str) -> dict:
    if data.get('mode') == 'ambiguous':
        return _ambiguous_clients(data)
    if data.get('mode') == 'not_found':
        return {
            'answer': f'Je ne retrouve pas « {data.get("hint")} » parmi vos clients dans {scope}.',
            'actions': [],
        }
    client = data.get('client') or {}
    return {
        'answer': f'Oui, {client.get("nom")} fait partie de vos clients dans {scope}.',
        'actions': [],
        'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
    }


def _client_situation(data: dict, scope: str) -> dict:
    if data.get('mode') == 'ambiguous':
        return _ambiguous_clients(data)
    if data.get('mode') == 'not_found':
        return {
            'answer': f'Je n’ai pas trouvé le client « {data.get("hint")} » dans {scope}.',
            'actions': [],
        }
    client = data.get('client') or {}
    ventes = data.get('ventes') or {}
    dettes = data.get('dettes') or {}
    lines = [
        f'Voici la situation du client {client.get("nom")} dans {scope} :',
        '',
        f'Client : {client.get("nom")}',
        f'Téléphone : {client.get("telephone") or "—"}',
        f'Nombre de ventes : {ventes.get("nombre_ventes", 0)}',
        f'Montant total des ventes : {ventes.get("montant_total", "0")}',
        f'Dernier achat : {_fmt_date((ventes.get("dernier_achat") or "")[:10]) if ventes.get("dernier_achat") else "—"}',
        f'Solde dettes restant : {dettes.get("solde_restant", "0")}',
        f'Statut : {dettes.get("statut", "à jour")}',
        '',
        'Voulez-vous que je génère sa fiche client / dettes en PDF ?',
    ]
    actions = []
    if client.get('id'):
        actions.append(_action_pdf(
            'Fiche dettes PDF',
            f'/api/rapports/clients-dettes/?client_id={client["id"]}',
        ))
    return {
        'answer': '\n'.join(lines),
        'actions': actions,
        'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
    }


def _client_purchases(data: dict, scope: str) -> dict:
    if data.get('mode') == 'ambiguous':
        return _ambiguous_clients(data)
    if data.get('mode') == 'not_found':
        return {
            'answer': f'Je n’ai pas trouvé le client « {data.get("hint")} » dans {scope}.',
            'actions': [],
        }
    client = data.get('client') or {}
    ventes = data.get('ventes') or {}
    details = ventes.get('ventes') or []
    if not details:
        return {
            'answer': (
                f'Je n’ai trouvé aucun achat de {client.get("nom")} '
                f'pour la période demandée dans {scope}.'
            ),
            'actions': [],
            'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
        }
    lines = [
        f'{client.get("nom")} a effectué {ventes.get("nombre_ventes", len(details))} achat(s) '
        f'dans {scope} (total : {ventes.get("montant_total", "0")}).',
        '',
        'Détails :',
    ]
    actions = []
    for v in details:
        lines.append(f'- Vente {v.get("heure") or v.get("date")} — {v.get("montant")} ({v.get("statut")})')
        for l in v.get('lignes') or []:
            lines.append(f'  • {l.get("nom")} — qté {l.get("quantite")} — {l.get("total")}')
        if v.get('sortie_id'):
            actions.append(_action_pdf(
                f'Facture {v.get("heure") or v.get("date")}',
                f'/api/sorties/{v["sortie_id"]}/facture-pos/',
            ))
    if actions:
        lines.append('')
        lines.append('Voulez-vous ouvrir une facture PDF ?')
    return {
        'answer': '\n'.join(lines),
        'actions': actions[:5],
        'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
        'file': {
            'type': 'pdf',
            'label': f'Facture {client.get("nom")}',
            'url': actions[0]['url'],
        } if len(actions) == 1 else None,
    }


def _client_invoice_pdf(data: dict, scope: str) -> dict:
    base = _client_purchases(data, scope)
    ventes = (data.get('ventes') or {}).get('ventes') or []
    client = data.get('client') or {}
    if data.get('mode') in ('ambiguous', 'not_found'):
        return base
    if not ventes:
        return {
            'answer': f'Aucune vente trouvée pour {client.get("nom")} à facturer dans {scope}.',
            'actions': [],
        }
    if len(ventes) > 1:
        lines = [
            f'{client.get("nom")} a effectué {len(ventes)} achats. Lequel voulez-vous en PDF ?',
            '',
        ]
        actions = []
        for i, v in enumerate(ventes, 1):
            lines.append(f'{i}. Vente {v.get("heure") or v.get("date")} — {v.get("montant")}')
            actions.append(_action_pdf(
                f'Facture {v.get("heure")}',
                f'/api/sorties/{v["sortie_id"]}/facture-pos/',
            ))
        return {'answer': '\n'.join(lines), 'actions': actions}
    v = ventes[0]
    url = f'/api/sorties/{v["sortie_id"]}/facture-pos/'
    return {
        'answer': f'J’ai trouvé une vente de {client.get("nom")}. La facture PDF est prête.',
        'actions': [_action_pdf('Ouvrir la facture', url)],
        'file': {'type': 'pdf', 'label': f'Facture {client.get("nom")}', 'url': url},
        'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
    }


def _client_debt(data: dict, scope: str) -> dict:
    if data.get('mode') == 'ambiguous':
        return _ambiguous_clients(data)
    if data.get('mode') == 'not_found':
        return {
            'answer': f'Je n’ai pas trouvé « {data.get("hint")} » dans {scope}.',
            'actions': [],
        }
    if data.get('mode') == 'client':
        client = data.get('client') or {}
        d = data.get('dettes_client') or {}
        if not d.get('nombre_dettes'):
            return {
                'answer': f'{client.get("nom")} n’a pas de dette en cours dans {scope}.',
                'actions': [],
                'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
            }
        lines = [
            f'J’ai trouvé le client {client.get("nom")}.',
            '',
            f'- Dettes en cours : {d.get("nombre_dettes")}',
            f'- Solde restant : {d.get("solde_restant")}',
            f'- Statut : {d.get("statut")}',
            '',
            'Voulez-vous générer sa fiche de dettes en PDF ?',
        ]
        url = f'/api/rapports/clients-dettes/?client_id={client["id"]}'
        return {
            'answer': '\n'.join(lines),
            'actions': [_action_pdf('Fiche dettes PDF', url)],
            'entities': {'client': client.get('nom'), 'client_id': client.get('id')},
        }
    return _debt_global(data, scope)


def _client_debt_pdf(data: dict, scope: str) -> dict:
    base = _client_debt(data, scope)
    if data.get('mode') == 'client' and data.get('client', {}).get('id'):
        cid = data['client']['id']
        url = f'/api/rapports/clients-dettes/?client_id={cid}'
        base['file'] = {
            'type': 'pdf',
            'label': f'Fiche dettes - {data["client"].get("nom")}',
            'url': url,
        }
        base['answer'] = (
            f'La fiche de dettes du client {data["client"].get("nom")} est prête.'
            if (data.get('dettes_client') or {}).get('nombre_dettes')
            else base.get('answer', '')
        )
    return base


def _debt_clients_pdf(data: dict, scope: str) -> dict:
    url = '/api/rapports/clients-dettes-general/'
    n = data.get('nombre_dettes_en_cours', 0)
    answer = (
        f'Je génère la fiche des dettes de tous les clients ayant un solde restant '
        f'dans {scope} ({n} dette(s) en cours).\n\nLe rapport est prêt.'
    )
    return {
        'answer': answer,
        'actions': [_action_pdf('Ouvrir le rapport dettes', url)],
        'file': {'type': 'pdf', 'label': f'Dettes clients - {scope}', 'url': url},
    }


def _debt_global(data: dict, scope: str) -> dict:
    if data.get('mode') in ('client', 'ambiguous', 'not_found'):
        return _client_debt(data, scope)
    lines = [
        f'Pour {scope}, vous avez actuellement :',
        f'- {data.get("nombre_dettes_en_cours", 0)} dette(s) en cours',
        f'- {data.get("nombre_en_retard", 0)} dette(s) en retard',
        f'- Solde total restant : {data.get("solde_total", "0")}',
        '',
        'Voulez-vous voir la liste des clients qui ont des dettes ?',
    ]
    return {
        'answer': '\n'.join(lines),
        'actions': [_action_pdf('Rapport dettes PDF', '/api/rapports/clients-dettes-general/')],
    }


def _clients_with_debts(data: dict, scope: str) -> dict:
    if data.get('mode') in ('client', 'ambiguous', 'not_found'):
        # Ne devrait pas arriver si client_hint est vidé
        data = {**data, 'mode': 'global'} if data.get('mode') == 'not_found' else data
    debiteurs = data.get('principaux_debiteurs') or []
    n = data.get('nombre_dettes_en_cours', len(debiteurs))
    lines = [
        f'Voici quelques clients qui ont des dettes dans {scope} ({n} dette(s) en cours) :',
        '',
    ]
    if not debiteurs:
        lines.append('Aucun client avec un solde restant pour le moment.')
    else:
        for i, d in enumerate(debiteurs[:10], 1):
            devise = d.get('devise') or ''
            lines.append(f'{i}. {d.get("nom")} — solde restant : {d.get("solde")} {devise}'.strip())
        lines.append('')
        lines.append('Voulez-vous que je génère le rapport PDF des dettes clients ?')
    return {
        'answer': '\n'.join(lines),
        'actions': [_action_pdf('Rapport dettes PDF', '/api/rapports/clients-dettes-general/')],
    }


def _ventes(data: dict, scope: str) -> dict:
    lines = [
        f'Pour {scope} : {data.get("ventes_aujourdhui", 0)} vente(s), '
        f'montant total {data.get("montant_total", "0")}.',
        f'- Comptant : {data.get("ventes_comptant", 0)}',
        f'- Crédit : {data.get("ventes_credit", 0)}',
    ]
    top = data.get('produits_plus_vendus') or []
    if top:
        lines.append('')
        lines.append('Produits les plus vendus :')
        for i, p in enumerate(top[:5], 1):
            lines.append(f'{i}. {p.get("nom")} — {p.get("nombre_ventes")} vente(s)')
    return {'answer': '\n'.join(lines), 'actions': []}


def _credit_sales(data: dict, scope: str) -> dict:
    n_credit = data.get('ventes_credit', 0)
    n_total = data.get('ventes_aujourdhui', 0)
    lines = [
        f'Aujourd’hui, vous avez effectué {n_total} vente(s) dans {scope}.',
        f'Ventes à crédit : {n_credit}',
        f'Ventes au comptant : {data.get("ventes_comptant", 0)}',
    ]
    if n_credit == 0:
        lines.append('')
        lines.append('Donc non, aucune vente à crédit n’a été enregistrée aujourd’hui.')
    else:
        lines.append('')
        lines.append('Clients concernés :')
        for i, d in enumerate(data.get('ventes_credit_details') or [], 1):
            lines.append(f'{i}. {d.get("client")} — {d.get("montant")}')
    return {'answer': '\n'.join(lines), 'actions': []}


def _top_products(data: dict, scope: str) -> dict:
    periode = data.get('periode') or 'all_time'
    label = {
        'all_time': 'toutes périodes confondues',
        'today': 'aujourd’hui',
        'week': 'cette semaine',
        'month': 'ce mois-ci',
    }.get(periode, periode)
    top = data.get('produits_plus_vendus') or []
    n = len(top)
    lines = [
        f'Voici le top {n} des articles les plus vendus dans {scope}, {label} :',
        '',
    ]
    if not top:
        lines.append('Aucune vente trouvée pour cette période.')
    for i, p in enumerate(top, 1):
        lines.append(f'{i}. {p.get("nom")} — {p.get("nombre_ventes")} vente(s)')
    return {'answer': '\n'.join(lines), 'actions': []}


def _appro(data: dict, scope: str) -> dict:
    items = data.get('approvisionnements') or []
    n = data.get('nombre_total_filtre', len(items))
    periode = data.get('periode') or ''
    if periode == 'today' or n == len(items):
        header = f'Aujourd’hui, vous avez effectué {n} approvisionnement(s) dans {scope}.'
    else:
        header = f'Voici vos approvisionnements pour {scope} ({n}) :'
    lines = [header, '']
    if not items:
        if periode == 'today' or 'aujourd' in header.lower():
            return {
                'answer': f'Aucun approvisionnement n’a été enregistré aujourd’hui dans {scope}.',
                'actions': [],
            }
        lines.append('Aucun approvisionnement trouvé pour cette période.')
    else:
        for i, a in enumerate(items, 1):
            lines.append(
                f'{i}. {a.get("libelle") or "Approvisionnement"} du {_fmt_date(a.get("date"))} '
                f'— {a.get("nb_articles")} article(s) — total : {a.get("total")}'
            )
        lines.append('')
        lines.append('Voulez-vous que je génère le bon d’entrée ou le rapport PDF ?')
    return {
        'answer': '\n'.join(lines),
        'actions': [_action_pdf('Bon d’entrée', '/api/rapports/bon-entree/')],
    }


def _caisse(data: dict, scope: str) -> dict:
    lines = [f'État de la caisse pour {scope} :']
    soldes = data.get('soldes_par_devise') or []
    if soldes:
        for s in soldes:
            lines.append(
                f'- {s.get("caisse")} : {s.get("solde_theorique")} {s.get("devise") or ""}'.strip()
            )
    else:
        lines.append('- Aucune session ouverte.')
    lines.append(f'- Encaissements du jour : {data.get("encaisse_aujourdhui", "0")}')
    lines.append(f'- Sorties du jour : {data.get("sorties_aujourdhui", "0")}')
    return {'answer': '\n'.join(lines), 'actions': []}


def _abonnement(data: dict, scope: str) -> dict:
    lic = data.get('licence') or {}
    lines = [
        f'Votre abonnement UHAKIKAAPP : formule {lic.get("formule") or "—"}, '
        f'statut {lic.get("statut") or "—"}.',
    ]
    if lic.get('jours_restants') is not None:
        lines.append(f'Jours restants : {lic.get("jours_restants")}.')
    lines.append('')
    lines.append('Demandez « quels sont les autres abonnements » pour voir les plans disponibles.')
    return {'answer': '\n'.join(lines), 'actions': []}


def _plans(data: dict, scope: str) -> dict:
    plans = data.get('plans') or []
    if not plans:
        return {
            'answer': 'Aucun plan d’abonnement n’est visible pour le moment.',
            'actions': [],
        }
    lines = ['Voici les formules UHAKIKAAPP disponibles :', '']
    for i, p in enumerate(plans, 1):
        lines.append(f'{i}. {p.get("nom")}')
        if p.get('description'):
            lines.append(f'   {p["description"][:200]}')
        prix = p.get('prix_mensuel') or '0'
        devise = p.get('devise') or 'USD'
        if str(prix) in ('0', '0.00'):
            lines.append(f'   Tarif : gratuit / essai')
        else:
            lines.append(f'   Tarif : {prix} {devise} / mois')
        limites = p.get('limites') or {}
        if limites:
            parts = [f'{k}: {v}' for k, v in list(limites.items())[:4]]
            lines.append(f'   Limites : {", ".join(parts)}')
        lines.append('')
    return {'answer': '\n'.join(lines).strip(), 'actions': []}


def _platform(data: dict, scope: str) -> dict:
    return {
        'answer': (
            f'Plateforme : {data.get("entreprises_total", 0)} entreprise(s), '
            f'{data.get("abonnements_actifs", 0)} abonnement(s) actif(s), '
            f'{data.get("abonnements_en_attente", 0)} en attente.'
        ),
        'actions': [],
    }


def _rapports(data: dict, scope: str) -> dict:
    parts = [f'Synthèse pour {scope} :']
    if data.get('stock'):
        parts.append(_stock_summary(data['stock'], scope)['answer'])
    if data.get('ventes'):
        parts.append(_ventes(data['ventes'], scope)['answer'])
    return {'answer': '\n\n'.join(parts), 'actions': []}


# Compat pour l'ancien formateur
def format_business_answer(intent: str, context_payload: dict) -> str | None:
    built = build_response(intent, context_payload)
    return built['answer'] if built else None
