# Rapport des ventes par session

## Objectif

Le rapport des ventes fonctionne maintenant par session de caisse, et non plus avec des dates obligatoires.

Endpoint concerne :

- `GET /api/rapports/ventes/`

## Nouveau comportement

### Par defaut

Si aucun parametre de session n'est fourni, le backend cherche la session actuellement ouverte dans le contexte courant :

- entreprise
- agence / succursale
- caisse cash par defaut

Si une session ouverte existe, le rapport charge automatiquement les ventes de cette session.

### Si une session est fournie

Le rapport accepte :

- `session_id`
- `session_numero`

Dans ce cas, la session est chargee quel que soit son statut :

- `OUVERTE`
- `CLOTUREE`
- `CLOTUREE_EN_ATTENTE_VALIDATION`
- `ANNULEE`

## Exemples

```txt
GET /api/rapports/ventes/
GET /api/rapports/ventes/?session_id=12&page=1&page_size=25&lang=fr
GET /api/rapports/ventes/?session_numero=SESS-2026-00012&statut_paiement=CREDIT
```

## Si aucune session en cours n'existe

Le backend retourne une reponse JSON vide avec un message explicite.

Exemple :

```json
{
  "success": false,
  "message": "Aucune session en cours. Veuillez selectionner une session pour consulter le rapport des ventes.",
  "ventes": [],
  "details": []
}
```

## Logique de rattachement des ventes

Le rattachement des ventes a la session se fait par :

- la fenetre temporelle de la session (`ouvert_le` -> `cloture_le` ou maintenant si session ouverte)
- l'entreprise de la session
- l'agence / succursale de la session si elle existe

Ce choix permet d'inclure :

- les ventes comptant
- les ventes a credit

meme quand une vente a credit n'a pas d'encaissement immediat rattache a une session de caisse.

## Filtres pris en charge

Le rapport supporte maintenant principalement :

- `session_id`
- `session_numero`
- `agence_id` / `succursale_id`
- `client_id`
- `client_nom`
- `reference`
- `statut_paiement` (`COMPTANT` ou `CREDIT`)
- `montant_min`
- `montant_max`
- `page`
- `page_size`
- `complet=true`

## Structure JSON retournee

La reponse inclut notamment :

- `session`
- `periode`
- `ventes`
- `lignes_ventes`
- `details`
- `totaux`
- `resume`
- `metadata`

## Champs importants de la session

```json
"session": {
  "id": 12,
  "uuid": null,
  "numero": "SESS-2026-00012",
  "statut": "OUVERTE",
  "date_ouverture": "2026-06-26T04:30:00+00:00",
  "date_cloture": null,
  "utilisateur": "Admin",
  "caisse": "Caisse principale",
  "agence_id": 1,
  "entreprise_id": 1,
  "selection_automatique": true
}
```

## Resume et totaux

Le rapport retourne maintenant des totaux adaptes a la lecture par session :

- `nombre_ventes`
- `sorties_comptant`
- `sorties_credit`
- `total_comptant`
- `total_credit`
- `total_general`
- `total_quantite`
- `total_benefice`
- `total_remises` (0 par defaut)
- `total_taxes` (0 par defaut)
- `total_annulations` (0 par defaut)

## Compatibilite frontend

Pour limiter les regressions, le backend conserve :

- `lignes_ventes`
- `details`

et ajoute aussi :

- `ventes` : liste groupee par sortie
- `session` : contexte de session utilise pour le rapport

Le frontend peut donc afficher :

- un resume par session
- une liste des ventes
- le detail ligne par ligne
- un export ou un PDF genere cote client a partir du JSON
