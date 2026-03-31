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

## Clients — rattachement entreprise(s) (`ClientEntreprise`)

Il existe un endpoint de lecture dédié `/api/client-entreprises/` (table d’association). Le rattachement d’un **même** contact (`Client`) à une ou plusieurs **entreprises** se fait toujours via le **CRUD standard** des clients (module **stock**), documenté dans Swagger / ReDoc sous la ressource **`clients`**.

| Action | Méthode | URL | Détail |
|--------|---------|-----|--------|
| Créer un client + liens | `POST` | `/api/clients/` | **Sans authentification** : possible pour l’inscription ; dans ce cas **`liens`** est **obligatoire** (au moins une entreprise). Avec **JWT staff** : **`liens`** optionnel si l’entreprise est déjà dans le token (liaison automatique). Champs : `nom`, `email`, `password` optionnel pour le portail, etc. |
| Mettre à jour les liens | `PATCH` ou `PUT` | `/api/clients/{id}/` | Envoyer **`liens`** pour **remplacer** tous les rattachements (anciens liens supprimés puis recréés). |
| Lire les liens | `GET` | `/api/clients/{id}/` | Réponse : **`liens_entreprise`** (lecture seule), détail par entreprise / succursale / `is_special`. |

**Chaque élément de `liens` (écriture)** : `entreprise` (id), `succursale` (id, optionnel), `is_special` (bool).  
Si **`liens` est absent** à la création et que le JWT porte une entreprise : un lien **`ClientEntreprise`** est créé **automatiquement** pour ce tenant (et la succursale du contexte si applicable).

**Auth** : **`POST /api/clients/`** accepté **sans** en-tête (inscription) ou avec **JWT staff** pour le back-office. Les autres opérations sur **`/api/clients/`** restent réservées aux **admin / agent** (JWT). Schémas : **`ClientSerializer`** dans l’UI OpenAPI.

### EN — Linking clients to companies

Use **`POST /api/clients/`** (allowed **without** auth for self-signup; then **`liens`** is **required**) and **`PATCH /api/clients/{id}/`** with the **`liens`** array (or rely on auto-link when the staff JWT tenant is set). Read **`liens_entreprise`** on **`GET /api/clients/{id}/`**. For a flat association list, use **`GET /api/client-entreprises/`**.

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

## Fournisseurs & marchandises en transit (module `order`)

### Rôle requis

- **Administrateur d’entreprise** (`Membership.role = admin`) : **CRUD complet** sur les fournisseurs et sur les lots en transit (lots, frais, lignes de lot).
- **Agent** (`Membership.role = user`) : **aucun accès** à ces endpoints (réponse **403**). Ce périmètre est volontairement restreint (données d’achat / transit sensibles).

### Pagination

Toutes les **listes** de ce module utilisent la pagination globale **`StandardResultsSetPagination`** :

| Paramètre | Description |
|-----------|-------------|
| `page` | Numéro de page |
| `page_size` | Taille (défaut **25**, maximum **200**) |

### URLs (préfixe `/api/`)

| Ressource | Chemin |
|-----------|--------|
| Fournisseurs | `/api/fournisseurs/` |
| Lots en transit | `/api/lots/` |
| Frais de lot | `/api/frais-lots/` |
| Lignes d’articles dans un lot | `/api/lot-items/` |

### Filtres & recherche (liste)

**Fournisseurs** — `GET /api/fournisseurs/`

- `search` ou `q` : nom, code, téléphone, e-mail, NIF (recherche « contient », insensible à la casse).
- `is_active` : `true` / `false`.
- `created_at_min`, `created_at_max` : plage sur la date de création (`YYYY-MM-DD`).
- `ordering` : `nom`, `-nom`, `code`, `-code`, `created_at`, `-created_at`.

**Lots** — `GET /api/lots/`

- `fournisseur_id` : filtrer les lots **par fournisseur** (clé étrangère).
- `statut` : `EN_TRANSIT`, `ARRIVE`, `CLOTURE`.
- `reference` : sous-chaîne sur la référence du lot.
- `search` : référence du lot **ou** nom/code du fournisseur (jointure indexée).
- Dates : `date_expedition_min` / `date_expedition_max` (alias `date_expedition_from` / `date_expedition_to`), `date_arrivee_prevue_min` / `date_arrivee_prevue_max` (alias `date_arrivee_prevue_from` / `date_arrivee_prevue_to`).
- `ordering` : `created_at`, `date_expedition`, `reference`, `statut`, etc. (voir paramètre documenté dans Swagger).

**Frais de lot** — `GET /api/frais-lots/`

- `lot_id`, `type_frais` (`TRANSPORT`, `DOUANE`, `MANUTENTION`), `devise_id`, plage `created_at_min` / `created_at_max`.

**Lignes de lot** — `GET /api/lot-items/`

- `lot_id`, `article_id` (identifiant métier de l’article), quantités et prix d’achat du lot.

**Cycle de vie du lot et stock**

- Statuts : `EN_TRANSIT` → `ARRIVE` → `CLOTURE`. **Aucune entrée en stock** n’est créée tant que le statut n’est pas **`CLOTURE`**.
- **Détail d’un lot** — `GET /api/lots/{id}/` : lecture du lot (lignes et frais préchargés selon le viewset).
- **Mise à jour** — `PUT` / `PATCH /api/lots/{id}/` : modification des champs autorisés (voir schéma Swagger). Pour **clôturer** le lot (`statut=CLOTURE`), envoyer **`approvisionnement`** (tableau JSON) — **une entrée par article** présent dans le lot : `article_id` (PK métier), `prix_vente`, `seuil_alerte`, `date_expiration` (optionnelle). Ces champs **ne sont pas persistés** sur `LotItem` ; ils servent uniquement à remplir les **`LigneEntree`** à la clôture. En cas de succès : **`Entree`** liée (`entree_stock`), `LigneEntree`, **`Stock`** — **sans** mouvement de caisse (stock uniquement). Les lignes d’un lot clôturé ne sont plus modifiables.
- **Suppression** — `DELETE /api/lots/{id}/` : uniquement si le lot **n’est pas** arrivé, clôturé ou lié à une entrée en stock (sinon erreur de validation).
- L’`Entree` créée à la clôture a un **libellé imposé** côté API ; la réponse **`GET /api/entrees/{id}/`** inclut **`lot_id`** lorsque l’entrée provient d’un lot.

Les paramètres détaillés sont également décrits sur chaque endpoint **liste** dans **Swagger UI** (`/swagger/`) et **ReDoc** (`/redoc/`).

---

## Portail client & commandes (FR) / Client portal & orders (EN)

### FR — Authentification dédiée (distincte du staff)

- **Modèle** : une fiche **`Client`** (identité + e-mail + mot de passe portail) ; les rattachements aux entreprises passent par **`ClientEntreprise`** (succursale préférée optionnelle, `is_special` par entreprise).
- **Connexion** : `POST /api/client-auth/login/` avec **`email`** et **`password`**. Réponse : **`entreprises`** (pour chaque lien : `entreprise` complète au format `EntrepriseSerializer`, liste **`succursales`**, métadonnées du **`lien`**), plus **`access`** / **`refresh`** et **`contexte`** (`membership_id`, `entreprise_id`, `succursale_id`).
- Si le client a **plusieurs** entreprises : envoyer aussi **`entreprise_id`** pour choisir le contexte des JWT ; sinon **400** avec la liste `entreprises` pour sélection côté UI.
- Les jetons incluent **`membership_id`** (clé `ClientEntreprise`) + **`entreprise_id`** + **`succursale_id`**.
- **Rafraîchissement** : `POST /api/client-auth/refresh/` avec `refresh`.
- **Changer de contexte** : `POST /api/client-auth/select-context/` (authentifié portail) avec `entreprise_id` et optionnellement `succursale_id` → nouveaux tokens.
- **Header** : `Authorization: Bearer <access>` (tokens **portail**, pas `/api/auth/`).
- **Tableau de bord** : `GET /api/client-portal/dashboard/` — aperçu agrégé (dettes, ventes, commandes) pour le **membership** actif (JWT).
- **Dettes (consultation uniquement)** : `GET /api/client-portal/dettes/` (liste paginée), `GET /api/client-portal/dettes/{id}/`, `GET /api/client-portal/dettes/{id}/paiements/` (historique des paiements). Filtrage **client + entreprise** du JWT + périmètre succursale du lien ; **aucune** création, mise à jour ou suppression.
- **Ventes (consultation uniquement)** : `GET /api/client-portal/ventes/` et `GET /api/client-portal/ventes/{id}/` — sorties de stock du client pour l’entreprise connectée ; **pas** de modification via ces URLs.
- **Commandes** : voir ci‑dessous — `GET/POST/PATCH/DELETE` sur `/api/commandes/` selon les règles métier (le client ne modifie pas les dettes ni les ventes via l’API portail).

**Rôles** : mot de passe portail défini côté staff sur la fiche `Client`. Les **agents** n’accèdent pas à ces endpoints.

### EN — Dedicated authentication (separate from staff)

- **Model**: one **`Client`** record (identity + email + portal password); links to companies use **`ClientEntreprise`** (optional preferred branch, `is_special` per company).
- **Login**: `POST /api/client-auth/login/` with **`email`** and **`password`**. Response: **`entreprises`** (per link: full **`entreprise`** as in `EntrepriseSerializer`, **`succursales`** list, **`lien`** metadata), plus **`access`** / **`refresh`** and **`contexte`** (`membership_id`, `entreprise_id`, `succursale_id`).
- If the client has **several** companies: also send **`entreprise_id`** to choose JWT context; otherwise **400** with `entreprises` for UI selection.
- Tokens carry **`membership_id`** + **`entreprise_id`** + **`succursale_id`**.
- **Refresh**: `POST /api/client-auth/refresh/` with `refresh`.
- **Select context**: `POST /api/client-auth/select-context/` (portal-authenticated) with `entreprise_id` and optional `succursale_id` → new tokens.
- **Header**: `Authorization: Bearer <access>` (**portal** tokens, not `/api/auth/`).
- **Dashboard**: `GET /api/client-portal/dashboard/` — aggregated snapshot (debts, sales, orders) for the active **membership** (JWT).
- **Debts (read-only)**: `GET /api/client-portal/dettes/` (paginated list), `GET /api/client-portal/dettes/{id}/`, `GET /api/client-portal/dettes/{id}/paiements/`. Scoped to **client + enterprise** in the JWT and the membership branch; **no** create/update/delete.
- **Sales (read-only)**: `GET /api/client-portal/ventes/` and `GET /api/client-portal/ventes/{id}/` — the connected client’s stock-out records for the current company; **no** edits through these routes.
- **Orders**: see below — `/api/commandes/` for CRUD rules; clients do **not** change debts or sales through these portal debt/sale endpoints.

**Roles**: portal password set by staff on `Client`. **Agents** have no access.

### FR — Commandes

- **CRUD** : `/api/commandes/` (liste paginée, création, détail, mise à jour, suppression).
- **Réponses métier** : `POST /api/commandes/{id}/reponses/` — ajouter un commentaire (**administrateur ou employé**) ; `PATCH` / `DELETE` sur `/api/commandes/{id}/reponses/{reponse_id}/` — **modifier** ou **supprimer** une réponse existante.
- **Client** : **ses** commandes uniquement (même logique **succursale** que le tableau de bord). **Mise à jour** et **suppression** seulement si la commande est **en attente** (`EN_ATTENTE`) ; le corps de **PUT/PATCH** est documenté dans Swagger (**variante client** : `nom`, `note_client`, `succursale`, `items`). Le **statut** n’est pas modifiable par le client.
- **Administrateur / employé (JWT staff)** : voit les commandes du périmètre ; comme le reste de l’API, le **`succursale_id` du JWT** (ou la succursale par défaut du membership) **filtre la liste** ; sans succursale : **toute l’entreprise** ; **`?succursale_id=`** pour cibler (cohérent avec le JWT si celui-ci impose une succursale). **PUT/PATCH** : **`statut`** uniquement (**`REJETEE`** ou **`LIVREE`** — schéma **variante staff** dans Swagger). **Suppression** : **client** ou **administrateur** uniquement (pas l’employé).
- **Création / articles** : la succursale de la commande est déduite du **corps**, du **client**, ou du **contexte JWT** ; les **articles catalogue** doivent être de la même entreprise et, si la commande a une succursale, soit **sans succursale** (catalogue global), soit **de cette succursale**.
- **Lignes** : pour chaque item, **`article_id` OU `nom_article`** (exclusif, pas les deux vides).

### EN — Orders

- **CRUD**: `/api/commandes/` (paginated list, create, detail, update, delete).
- **Official replies**: `POST /api/commandes/{id}/reponses/` — add a comment (**administrator or staff agent**) ; `PATCH` / `DELETE` on `/api/commandes/{id}/reponses/{reponse_id}/` — **update** or **delete** an existing reply.
- **Client**: **own** orders only (**branch scope** consistent with the dashboard). **Update** and **delete** only while **pending** (`EN_ATTENTE`); **PUT/PATCH** body is documented in Swagger (**client variant**: `nom`, `note_client`, `succursale`, `items`). Clients **cannot** set **status**.
- **Administrator / agent (staff JWT)**: branch-wide visibility; like the rest of the API, **`succursale_id` in the JWT** (or membership default) **filters the list**; no branch in context → **whole company**; **`?succursale_id=`** must match the JWT when locked. **PUT/PATCH**: **`statut`** only (**`REJETEE`** or **`LIVREE`** — **staff variant** in Swagger). **Delete**: **client** or **administrator** only (not agents).
- **Create / articles**: order branch comes from the **body**, **target client**, or **JWT context**; **catalog articles** must match the company and, if the order has a branch, be either **branch-less** (global catalog) or **on that branch**.
- **Lines**: each item is **`article_id` OR `nom_article`** (XOR, not both empty).

### Documentation OpenAPI

Tags **« Portail client (JWT dédié) »** et **« Commandes clients (portail & admin) »** regroupent les opérations ; paramètres de liste et erreurs sont décrits dans Swagger / ReDoc. Messages d’erreur et libellés métier suivent **`Accept-Language`** / `?lang=` comme le reste de l’API.

---
*Pour plus de détail, voir le fichier `README.md` à la racine du projet.*
""".strip()
