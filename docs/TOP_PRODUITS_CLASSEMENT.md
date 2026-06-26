# Top Produits - Critere de classement

## Ce qui a ete fait

Le rapport `Top Produits` utilise deja un classement par `nombre_ventes`.

J'ai ajoute une information explicite dans la reponse JSON de l'endpoint pour eviter toute ambiguite cote frontend et cote metier.

Endpoint concerne :

- `GET /api/sorties/produits-plus-vendus/`

## Regle de calcul

Le classement est fait par :

- `nombre_ventes` = nombre de lignes de vente pour un article

Ce classement ne se fait pas par :

- `quantite_vendue`
- `chiffre_affaires`

## Champs calcules

Pour chaque article, le backend calcule :

- `quantite_vendue` : somme de `quantite`
- `nombre_ventes` : `Count('id', distinct=True)`
- `chiffre_affaires` : somme de `quantite * prix_unitaire`

Puis le tri est applique avec :

- `order_by('-nombre_ventes')`

## Exemple

Un produit peut etre classe premier meme si :

- il n'a pas la plus grande quantite vendue
- il n'a pas le plus grand chiffre d'affaires

Il suffit qu'il apparaisse dans plus de ventes que les autres produits.

## Changement ajoute dans la reponse API

La reponse inclut maintenant un bloc :

```json
"classement": {
  "critere": "nombre_ventes",
  "description": "Classement par nombre de ventes (nombre de lignes de vente par article), pas par quantite ni par chiffre d'affaires."
}
```

## Impact frontend

Le frontend peut maintenant afficher clairement :

- `Top produits par nombre de ventes`

au lieu de laisser penser que le classement est base sur la quantite ou le chiffre d'affaires.