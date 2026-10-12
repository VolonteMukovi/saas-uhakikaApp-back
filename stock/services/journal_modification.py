"""
Journal des modifications d'entrées et de sorties : état avant / après et changements
rédigés en phrases (affichés tels quels dans la page Audit).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from stock.models import Entree, ModificationMouvement, Sortie

STATUTS = {'PAYEE': 'Comptant', 'EN_CREDIT': 'Crédit'}


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def _fmt(value) -> str:
    texte = f'{_d(value).normalize():f}'
    return texte.rstrip('0').rstrip('.') if '.' in texte else texte


def _nom_article(article) -> str:
    return article.nom_commercial or article.nom_scientifique or article.article_id


def _nom_utilisateur(user) -> str:
    if user is None:
        return ''
    full = (user.get_full_name() or '').strip() if hasattr(user, 'get_full_name') else ''
    return full or getattr(user, 'username', '') or ''


# ---------------------------------------------------------------------------
# Sorties
# ---------------------------------------------------------------------------

def photo_sortie(sortie: Sortie) -> dict:
    lignes = []
    totaux: dict[str, Decimal] = defaultdict(Decimal)
    for ligne in sortie.lignes.select_related('article', 'devise', 'conditionnement').order_by('id'):
        devise = ligne.devise.sigle if ligne.devise else ''
        montant = ligne.get_montant_total()
        totaux[devise] += _d(montant)
        lignes.append({
            'article_id': ligne.article_id,
            'article': _nom_article(ligne.article),
            'quantite': _fmt(ligne.quantite),
            'conditionnement': ligne.conditionnement.nom if ligne.conditionnement_id else '',
            'prix_unitaire': _fmt(ligne.prix_unitaire),
            'montant': _fmt(montant),
            'devise': devise,
        })
    return {
        'motif': sortie.motif,
        'est_commerciale': sortie.est_commerciale,
        'statut': sortie.statut,
        'client_id': sortie.client_id,
        'client': sortie.client.nom if sortie.client_id else '',
        'retire_par': sortie.retire_par,
        'totaux': {k: _fmt(v) for k, v in totaux.items()},
        'lignes': lignes,
    }


def _par_article(lignes: list[dict]) -> dict[str, dict]:
    regroupe: dict[str, dict] = {}
    for ligne in lignes:
        cle = ligne['article_id']
        if cle in regroupe:
            regroupe[cle]['quantite'] = _fmt(_d(regroupe[cle]['quantite']) + _d(ligne['quantite']))
            regroupe[cle]['montant'] = _fmt(_d(regroupe[cle]['montant']) + _d(ligne['montant']))
        else:
            regroupe[cle] = dict(ligne)
    return regroupe


def changements_sortie(avant: dict, apres: dict) -> tuple[list[str], bool]:
    changements: list[str] = []
    sensible = False
    if avant['motif'] != apres['motif']:
        changements.append(f"Motif : « {avant['motif'] or '—'} » → « {apres['motif'] or '—'} »")
    if avant['est_commerciale'] != apres['est_commerciale']:
        sensible = True
        changements.append(
            'Nature : vente au client → sortie non commerciale'
            if avant['est_commerciale'] else 'Nature : sortie non commerciale → vente au client'
        )
    if avant['statut'] != apres['statut']:
        sensible = True
        changements.append(
            f"Type de vente : {STATUTS.get(avant['statut'], avant['statut'])} → "
            f"{STATUTS.get(apres['statut'], apres['statut'])}"
        )
    if avant['client_id'] != apres['client_id']:
        sensible = True
        changements.append(f"Client : {avant['client'] or 'aucun'} → {apres['client'] or 'aucun'}")

    lignes_avant, lignes_apres = _par_article(avant['lignes']), _par_article(apres['lignes'])
    for cle, ligne in lignes_avant.items():
        nouvelle = lignes_apres.get(cle)
        if nouvelle is None:
            sensible = True
            changements.append(f"{ligne['article']} retiré ({ligne['quantite']} × {ligne['prix_unitaire']} {ligne['devise']})")
            continue
        if _d(ligne['quantite']) != _d(nouvelle['quantite']):
            sensible = sensible or _d(nouvelle['quantite']) < _d(ligne['quantite'])
            changements.append(f"{ligne['article']} : quantité {ligne['quantite']} → {nouvelle['quantite']}")
        if _d(ligne['prix_unitaire']) != _d(nouvelle['prix_unitaire']) or ligne['devise'] != nouvelle['devise']:
            sensible = sensible or _d(nouvelle['prix_unitaire']) < _d(ligne['prix_unitaire'])
            changements.append(
                f"{ligne['article']} : prix unitaire {ligne['prix_unitaire']} {ligne['devise']} → "
                f"{nouvelle['prix_unitaire']} {nouvelle['devise']}"
            )
    for cle, ligne in lignes_apres.items():
        if cle not in lignes_avant:
            changements.append(f"{ligne['article']} ajouté ({ligne['quantite']} × {ligne['prix_unitaire']} {ligne['devise']})")

    devises = sorted(set(avant['totaux']) | set(apres['totaux']))
    if any(_d(avant['totaux'].get(dv)) != _d(apres['totaux'].get(dv)) for dv in devises):
        total_avant = ', '.join(f"{avant['totaux'][dv]} {dv}" for dv in devises if dv in avant['totaux']) or '0'
        total_apres = ', '.join(f"{apres['totaux'][dv]} {dv}" for dv in devises if dv in apres['totaux']) or '0'
        changements.append(f'Total : {total_avant} → {total_apres}')
        if any(_d(apres['totaux'].get(dv)) < _d(avant['totaux'].get(dv)) for dv in devises):
            sensible = True
    return changements, sensible


# ---------------------------------------------------------------------------
# Entrées
# ---------------------------------------------------------------------------

def photo_entree(entree: Entree) -> dict:
    return {
        'libele': entree.libele,
        'description': entree.description,
        'lignes': [
            {
                'id': lot.pk,
                'article_id': lot.article_id,
                'article': _nom_article(lot.article),
                'quantite': _fmt(lot.quantite),
                'prix_achat': _fmt(lot.prix_unitaire),
                'prix_vente': _fmt(lot.prix_vente),
                'devise': lot.devise.sigle if lot.devise_id else '',
                'date_expiration': lot.date_expiration.isoformat() if lot.date_expiration else None,
            }
            for lot in entree.lignes.select_related('article', 'devise').order_by('id')
        ],
    }


def changements_entree(avant: dict, apres: dict) -> tuple[list[str], bool]:
    changements: list[str] = []
    sensible = False
    if avant['libele'] != apres['libele']:
        changements.append(f"Libellé : « {avant['libele']} » → « {apres['libele']} »")
    if (avant['description'] or '') != (apres['description'] or ''):
        changements.append('Description modifiée')
    lots_apres = {lot['id']: lot for lot in apres['lignes']}
    ids_avant = set()
    for lot in avant['lignes']:
        ids_avant.add(lot['id'])
        nouveau = lots_apres.get(lot['id'])
        if nouveau is None:
            sensible = True
            changements.append(f"Lot {lot['article']} supprimé ({lot['quantite']} unités)")
            continue
        nom = lot['article']
        if lot['article_id'] != nouveau['article_id']:
            sensible = True
            changements.append(f"Lot #{lot['id']} : article {lot['article']} → {nouveau['article']}")
            nom = nouveau['article']
        if _d(lot['quantite']) != _d(nouveau['quantite']):
            sensible = sensible or _d(nouveau['quantite']) < _d(lot['quantite'])
            changements.append(f"{nom} : quantité {lot['quantite']} → {nouveau['quantite']}")
        if _d(lot['prix_achat']) != _d(nouveau['prix_achat']) or lot['devise'] != nouveau['devise']:
            sensible = True
            changements.append(
                f"{nom} : prix d'achat {lot['prix_achat']} {lot['devise']} → {nouveau['prix_achat']} {nouveau['devise']}"
            )
        if _d(lot['prix_vente']) != _d(nouveau['prix_vente']):
            changements.append(f"{nom} : prix de vente {lot['prix_vente']} → {nouveau['prix_vente']}")
        if lot['date_expiration'] != nouveau['date_expiration']:
            changements.append(
                f"{nom} : date d'expiration {lot['date_expiration'] or '—'} → {nouveau['date_expiration'] or '—'}"
            )
    for lot in apres['lignes']:
        if lot['id'] not in ids_avant:
            changements.append(f"Lot {lot['article']} ajouté ({lot['quantite']} × {lot['prix_achat']} {lot['devise']})")
    return changements, sensible


def journaliser(
    *,
    type_mouvement: str,
    piece,
    libelle: str,
    utilisateur,
    avant: dict,
    apres: dict,
    changements: list[str],
    sensible: bool,
    impact_caisse: list[dict] | None = None,
) -> ModificationMouvement | None:
    if not changements and not impact_caisse:
        return None
    return ModificationMouvement.objects.create(
        entreprise_id=piece.entreprise_id,
        succursale_id=piece.succursale_id,
        type_mouvement=type_mouvement,
        reference_id=piece.pk,
        reference_libelle=libelle,
        utilisateur=utilisateur if getattr(utilisateur, 'is_authenticated', False) else None,
        utilisateur_nom=_nom_utilisateur(utilisateur),
        changements=changements,
        avant=avant,
        apres=apres,
        impact_caisse=impact_caisse or [],
        sensible=sensible or any(i.get('type') == 'SORTIE' or i.get('nature') == 'CORRECTION' for i in impact_caisse or []),
    )
