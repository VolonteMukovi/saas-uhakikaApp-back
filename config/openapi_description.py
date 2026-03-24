"""
Description affichée en tête de Swagger UI et ReDoc (drf-yasg).
"""

API_DESCRIPTION = """
## API Gestion de Stock — Multi-tenant

### Authentification
- **JWT** : `POST /api/auth/` avec `username` et `password` → récupérer `access` et `refresh`.
- Header : `Authorization: Bearer <access>`
- **Rafraîchissement** : `POST /api/auth/refresh/` avec le body `{"refresh": "..."}`.
- **Contexte entreprise / succursale** : les claims JWT peuvent contenir `entreprise_id`, `succursale_id`, `membership_id`.
- **Changer de contexte** : `POST /api/auth/select-context/` (authentifié) avec `entreprise_id` et optionnellement `succursale_id`.

### Flux typique (nouvel utilisateur)
1. `POST /api/users/` — inscription (sans token).
2. `POST /api/auth/` — connexion.
3. `POST /api/entreprises/` — création entreprise (utilisateur connecté ; Membership admin créé automatiquement).
4. `POST /api/users/{id}/assign_entreprise/` — liaison à une entreprise existante si besoin (`entreprise_id`, `role`).
5. `POST /api/succursales/` — si `has_branches` sur l’entreprise.
6. `GET` / `POST /api/users/{id}/succursales/` — succursale par défaut + liste autorisée (`UserBranch`).

### Endpoints utiles
- `GET /api/users/me/` — profil connecté.
- `GET /api/entreprises/my_entreprise/` — entreprise du contexte.
- `GET /api/entreprises/{id}/users/` — utilisateurs d’une entreprise.

### Branding (logo, slogan) — une seule forme de lecture
Le payload entreprise est le même partout : **`EntrepriseSerializer`** (champ `logo` en URL absolue si requête HTTP, `slogan`, etc.) sur `POST /api/auth/`, `POST /api/auth/select-context/`, `GET /api/users/me/`, `GET /api/entreprises/{id}/` et `GET /api/entreprises/my_entreprise/`. Les **agents** (`Membership.role=user`) ont **lecture seule** sur leur entreprise (pas de PATCH entreprise).

### Caisse — mouvements (montant + motif + moyen)
- **`GET` / `POST` / `PATCH` `/api/mouvements-caisse/`** : montant global, devise, type (`ENTREE` / `SORTIE`), champs libres **`motif`** et **`moyen`**. En lecture, **`details`** peut encore exposer d’anciennes lignes de ventilation (données historiques) ; **`resume`** agrège motif / anciens détails pour l’affichage.
- **`GET` / `POST` / `PATCH` `/api/types-caisse/`** : référentiel des canaux (libellé, description, image) par entreprise / succursale.
- **`/api/paiements-dettes/`** : mêmes URLs qu’avant ; chaque paiement est un **`MouvementCaisse`** lié à la dette (`content_type` = `DetteClient`, `object_id`), en **`ENTREE`**, avec **`motif`** et **`moyen`** (comme les autres mouvements de caisse).

### Rôles
- **Superadmin** : `is_superuser` (createsuperuser).
- **Admin / Agent** : via `Membership.role` (`admin` ou `user`) pour chaque entreprise.

---

## Recherche avancée — articles et clients

Deux endpoints dédiés permettent une recherche **rapide** et **bornée au tenant** (entreprise, et éventuellement succursale), sans parcourir les données des autres entreprises.

### Endpoints

| Ressource | Méthode | URL |
|-----------|---------|-----|
| Articles | `GET` | `/api/articles/search/` |
| Clients | `GET` | `/api/clients/search/` |

Ce ne sont **pas** les listes paginées `/api/articles/` ou `/api/clients/` : ce sont des actions personnalisées (`search`) optimisées pour l’autocomplétion et la saisie utilisateur.

### Authentification et périmètre (obligatoire)

- **Header** : `Authorization: Bearer <access>` (JWT).
- Le serveur déduit **`entreprise_id`** (et **`succursale_id`** si présent dans le JWT ou la succursale par défaut du membership) comme pour le reste de l’API métier.
- **Toute requête ne voit que les enregistrements de cette entreprise** ; si une succursale est dans le contexte, la recherche est **restreinte à cette succursale** (comportement aligné sur `TenantFilterMixin`).
- Si le contexte entreprise est absent : réponse **403** avec `detail` explicatif.

### Paramètres de requête (query string)

| Paramètre | Obligatoire | Défaut | Description |
|-----------|-------------|--------|-------------|
| **`q`** | **Oui** | — | Texte recherché (un ou plusieurs mots). Sans `q` ou si vide : **400** avec un message indiquant d’utiliser `?q=...`. |
| **`limit`** | Non | `25` | Nombre maximum de résultats retournés (plafonné à **100**). |
| **`offset`** | Non | `0` | Décalage pour pagination (ex. page suivante). |

**Exemples**

- `GET /api/articles/search/?q=café`
- `GET /api/clients/search/?q=dupont&limit=10&offset=0`

### Champs côté données

**Articles** — recherche sur : `nom_scientifique`, `nom_commercial`, `article_id` (code produit).

**Clients** — recherche sur : `nom`, `telephone`, `adresse`, `email`, `id` (ex. `CLI0001`).

### Réponses (HTTP 200)

Corps JSON typique :

```json
{
  "results": [ ... ],
  "meta": {
    "total": 42,
    "limit": 25,
    "offset": 0,
    "has_more": true
  }
}
```

- **`results`** : liste d’objets sérialisés ; chaque élément inclut un champ **`relevance`** (score de pertinence, nombre flottant ; sémantique selon le moteur SGBDR).
- **`meta.total`** : nombre total de correspondances (pour la requête courante, avant découpe `limit`/`offset`).
- **`meta.has_more`** : `true` s’il reste des résultats après la page courante.

**Aucun résultat** (`total` = 0) : un champ supplémentaire **`message`** est renvoyé (texte en français par défaut) pour guider l’utilisateur (orthographe, autres mots-clés, périmètre succursale). Ce message est **traduit** selon la langue active (voir ci‑dessous).

### Langue des messages (internationalisation)

- En-tête **`Accept-Language`** : `fr` ou `en` (ex. `Accept-Language: en`).
- **Option** : paramètre `?lang=en` ou `?lang=fr` (prioritaire sur l’en-tête, utile pour les tests).
- S’applique aux messages **« aucun résultat »** et aux erreurs **400** (paramètre `q` manquant).

### Comportement technique (résumé)

Le backend adapte la stratégie au **SGBDR** :

- **MySQL** : index **FULLTEXT** (`MATCH ... AGAINST`) en mode naturel puis repli booléen / sous-chaînes ; si l’index est absent (erreur 1191), repli automatique sur **LIKE** borné au tenant.
- **PostgreSQL** : extension **`pg_trgm`** et similarité sur les champs texte (seuil minimal configurable côté code).
- **SQLite** (souvent en dev) : table **FTS5** liée + triggers de synchronisation ; repli **LIKE** si besoin.

Dans tous les cas, le **filtre entreprise** (et succursale si applicable) est appliqué **en premier** dans la requête SQL.

### Bonnes pratiques (frontend)

- **Debouncer** la saisie (ex. 200–400 ms) avant d’appeler l’API pour éviter une rafale de requêtes.
- Ne pas appeler l’API sans `q` (ou gérer le **400** côté UI).
- Afficher **`message`** lorsque `results` est vide et `meta.total` est 0.
- Utiliser **`meta.has_more`** / **`offset`** pour le scroll infini ou « charger plus ».

### Statistiques stocks par statut (indicateurs)

- **`GET /api/stocks/stats/`** : réponse **hors pagination**. Périmètre : **entreprise** du JWT (et **succursale** si le contexte l’impose, comme pour `GET /api/stocks/`).
- **Statuts (1 requête agrégée sur `Stock`)** : **`total`**, **`normal`**, **`alerte`**, **`faible`** (identique à `alerte`), **`rupture`**, **`sum_statuts`** (= `normal + alerte + rupture`, égal à **`total`**), **`by_code`** (`NORMAL`, `ALERTE`, `RUPTURE`). Règles comme la liste des stocks : rupture si `Qte = 0` ; alerte / faible si `0 < Qte ≤ seuilAlert` ; sinon normal.
- **Expirations (requêtes séparées sur `LigneEntree`)** — mêmes règles : `quantite_restante > 0`, `date_expiration` renseignée, date **entre `date_debut` et `date_fin` (inclus)**, lots **déjà expirés** exclus. Ces comptages peuvent **chevaucher** les statuts NORMAL / ALERTE / RUPTURE.
  - **`expiration_sous_30_jours`** : articles distincts avec au moins un lot dont l’expiration tombe dans les **30 prochains jours** (fenêtre glissante). Métadonnées : **`expiration_periode_30_jours`** (`date_debut`, `date_fin`).
  - **`expiration_sous_3_mois`** : idem sur **3 mois calendaires**. Métadonnées : **`expiration_periode`** (`date_debut`, `date_fin`).
  - Un article peut apparaître dans les deux comptages si pertinent ; **`expiration_sous_30_jours`** ≤ **`expiration_sous_3_mois`** en général (30 jours ⊂ 3 mois sauf cas limite de calendrier).

### Schéma OpenAPI

Les opérations **`search`** des viewsets `articles` et `clients`, ainsi que **`stats`** sur `stocks`, sont documentées dans cette interface (paramètres, réponses).

---
*Pour plus de détail, voir le fichier `README.md` à la racine du projet.*
""".strip()
