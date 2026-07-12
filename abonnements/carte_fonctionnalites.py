"""
Cartographie URL → fonctionnalité de plan (étape 4).

Chaque règle associe un chemin API à une clé `fonctionnalites` du catalogue.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ECRITURE = frozenset({'POST', 'PUT', 'PATCH', 'DELETE'})
LECTURE = frozenset({'GET', 'HEAD', 'OPTIONS'})
TOUTES = ECRITURE | LECTURE


@dataclass(frozen=True)
class RegleFonctionnalite:
    pattern: re.Pattern
    methodes: frozenset
    fonctionnalite: str
    bloquer_lecture: bool = False


def _p(regex: str) -> re.Pattern:
    return re.compile(regex)


REGLES_FONCTIONNALITES: tuple[RegleFonctionnalite, ...] = (
    # Approvisionnement
    RegleFonctionnalite(_p(r'^/api/import-excel'), ECRITURE, 'approvisionnement'),
    RegleFonctionnalite(_p(r'^/api/stock/import-excel'), ECRITURE, 'approvisionnement'),
    RegleFonctionnalite(_p(r'^/api/order'), ECRITURE, 'approvisionnement'),
    RegleFonctionnalite(_p(r'^/api/entrees'), ECRITURE, 'approvisionnement'),
    RegleFonctionnalite(_p(r'^/api/ligneentrees'), ECRITURE, 'approvisionnement'),
    # Articles & stock
    RegleFonctionnalite(_p(r'^/api/articles'), ECRITURE, 'articles'),
    RegleFonctionnalite(_p(r'^/api/stocks'), ECRITURE, 'stock'),
    RegleFonctionnalite(_p(r'^/api/inventaires'), ECRITURE, 'stock'),
    RegleFonctionnalite(_p(r'^/api/typearticles'), ECRITURE, 'articles'),
    RegleFonctionnalite(_p(r'^/api/soustypearticles'), ECRITURE, 'articles'),
    RegleFonctionnalite(_p(r'^/api/unites'), ECRITURE, 'articles'),
    # Clients
    RegleFonctionnalite(_p(r'^/api/clients'), ECRITURE, 'clients'),
    RegleFonctionnalite(_p(r'^/api/client-entreprises'), ECRITURE, 'clients'),
    # Dettes
    RegleFonctionnalite(_p(r'^/api/dettes'), ECRITURE, 'dettes'),
    RegleFonctionnalite(_p(r'^/api/paiements-dettes'), ECRITURE, 'dettes'),
    # Caisse
    RegleFonctionnalite(_p(r'^/api/caisse'), ECRITURE, 'caisse'),
    RegleFonctionnalite(_p(r'^/api/mouvements-caisse'), ECRITURE, 'caisse'),
    RegleFonctionnalite(_p(r'^/api/sessions-caisse'), ECRITURE, 'caisse'),
    RegleFonctionnalite(_p(r'^/api/types-caisse'), ECRITURE, 'caisse'),
    # Ventes (crédit contrôlé séparément dans SortieViewSet)
    RegleFonctionnalite(_p(r'^/api/sorties'), ECRITURE, 'vente_comptant'),
    RegleFonctionnalite(_p(r'^/api/lignesorties'), ECRITURE, 'vente_comptant'),
    # Impression POS
    RegleFonctionnalite(_p(r'^/api/sorties/\d+/facture-pos-print'), ECRITURE, 'impression_pos'),
    RegleFonctionnalite(_p(r'^/api/sorties/\d+/bon-pos-print'), ECRITURE, 'impression_pos'),
    RegleFonctionnalite(_p(r'^/api/paiements-dettes/\d+/recu-print'), ECRITURE, 'impression_pos'),
    RegleFonctionnalite(_p(r'^/api/paiements-dettes/recu-groupe-print'), ECRITURE, 'impression_pos'),
    # Rapports avancés (lecture + export)
    RegleFonctionnalite(_p(r'^/api/rapports/bon-achat'), TOUTES, 'rapports_avances', True),
    RegleFonctionnalite(_p(r'^/api/rapports/.+/fiche-stock'), TOUTES, 'rapports_avances', True),
    RegleFonctionnalite(_p(r'^/api/rapports/clients-dettes-general'), TOUTES, 'rapports_avances', True),
    RegleFonctionnalite(_p(r'^/api/rapports/clients-dettes'), TOUTES, 'dettes', True),
    RegleFonctionnalite(_p(r'^/api/rapports'), TOUTES, 'rapports_simples', True),
    RegleFonctionnalite(_p(r'^/api/chatbot'), TOUTES, 'chatbot', True),
)


# Succursales : contrôle quota + multi_succursales (middleware dédié)
CHEMIN_SUCCURSALES = re.compile(r'^/api/succursales/?$')
CHEMIN_UTILISATEURS = re.compile(r'^/api/users/?$')


def fonctionnalite_pour_requete(chemin: str, methode: str) -> tuple[str | None, bool]:
    """
    Retourne (cle_fonctionnalite, bloquer_lecture) ou (None, False).
    """
    chemin = chemin.rstrip('/') or '/'
    methode = methode.upper()
    for regle in REGLES_FONCTIONNALITES:
        if not regle.pattern.search(chemin):
            continue
        if methode not in regle.methodes:
            continue
        if methode in LECTURE and not regle.bloquer_lecture:
            continue
        return regle.fonctionnalite, regle.bloquer_lecture
    return None, False
