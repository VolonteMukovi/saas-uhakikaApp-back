"""
Paramètres et schémas documentés pour Swagger / ReDoc (drf-yasg) — transit, fournisseurs, commandes.
"""
from drf_yasg import openapi

PAGINATION_PARAMS = [
    openapi.Parameter(
        "page",
        openapi.IN_QUERY,
        description="Numéro de page (pagination DRF `PageNumberPagination`).",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "page_size",
        openapi.IN_QUERY,
        description="Taille de page (défaut 25, max 200, via `StandardResultsSetPagination`).",
        type=openapi.TYPE_INTEGER,
    ),
]

ORDERING_FOURNISSEUR = openapi.Parameter(
    "ordering",
    openapi.IN_QUERY,
    description="Tri : `nom`, `-nom`, `code`, `-code`, `created_at`, `-created_at`.",
    type=openapi.TYPE_STRING,
)

ORDERING_LOT = openapi.Parameter(
    "ordering",
    openapi.IN_QUERY,
    description="Tri : `created_at`, `-created_at`, `date_expedition`, `-date_expedition`, `reference`, `-reference`, `statut`, `-statut`.",
    type=openapi.TYPE_STRING,
)

ORDERING_FRAIS = openapi.Parameter(
    "ordering",
    openapi.IN_QUERY,
    description="Tri : `created_at`, `-created_at`, `montant`, `-montant`, `type_frais`, `-type_frais`.",
    type=openapi.TYPE_STRING,
)

ORDERING_LOT_ITEM = openapi.Parameter(
    "ordering",
    openapi.IN_QUERY,
    description="Tri : `created_at`, `-created_at`, `quantite`, `-quantite`, `prix_achat_unitaire`, `-prix_achat_unitaire`.",
    type=openapi.TYPE_STRING,
)

FOURNISSEUR_LIST_PARAMS = PAGINATION_PARAMS + [
    ORDERING_FOURNISSEUR,
    openapi.Parameter(
        "search",
        openapi.IN_QUERY,
        description="Recherche texte sur nom, code, téléphone, e-mail, NIF (insensible à la casse).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "q",
        openapi.IN_QUERY,
        description="Alias de `search` (même comportement).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "is_active",
        openapi.IN_QUERY,
        description="Filtrer les fournisseurs actifs (`true` / `false`).",
        type=openapi.TYPE_BOOLEAN,
    ),
    openapi.Parameter(
        "created_at_min",
        openapi.IN_QUERY,
        description="Date de création minimale (inclus), format `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "created_at_max",
        openapi.IN_QUERY,
        description="Date de création maximale (inclus), format `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
]

LOT_LIST_PARAMS = PAGINATION_PARAMS + [
    ORDERING_LOT,
    openapi.Parameter(
        "fournisseur_id",
        openapi.IN_QUERY,
        description="Filtrer par identifiant du fournisseur (recherche de lots par fournisseur).",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "statut",
        openapi.IN_QUERY,
        description="Statut du lot : `EN_TRANSIT`, `ARRIVE`, `CLOTURE`.",
        type=openapi.TYPE_STRING,
        enum=["EN_TRANSIT", "ARRIVE", "CLOTURE"],
    ),
    openapi.Parameter(
        "reference",
        openapi.IN_QUERY,
        description="Sous-chaîne sur la référence du lot (insensible à la casse).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "search",
        openapi.IN_QUERY,
        description="Recherche sur référence du lot, nom ou code du fournisseur.",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "date_expedition_min",
        openapi.IN_QUERY,
        description="Date d'expédition minimale `YYYY-MM-DD` (alias `date_expedition_from`).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "date_expedition_max",
        openapi.IN_QUERY,
        description="Date d'expédition maximale `YYYY-MM-DD` (alias `date_expedition_to`).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "date_arrivee_prevue_min",
        openapi.IN_QUERY,
        description="Date d'arrivée prévue minimale `YYYY-MM-DD` (alias `date_arrivee_prevue_from`).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "date_arrivee_prevue_max",
        openapi.IN_QUERY,
        description="Date d'arrivée prévue maximale `YYYY-MM-DD` (alias `date_arrivee_prevue_to`).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
]

# Documentation Swagger — détail / mise à jour lot (hors liste).
LOT_CREATE_DESCRIPTION = (
    "Création d'un lot (`statut` par défaut `EN_TRANSIT`). **Impossible** de créer directement "
    "en `CLOTURE` — ajouter les lignes via `/api/lot-items/`, puis **PATCH** le lot avec "
    "`statut=CLOTURE` et le payload `approvisionnement`."
)

LOT_RETRIEVE_DESCRIPTION = (
    "Réponse : métadonnées du lot, `items` (quantités + prix d'achat par article), `frais`, "
    "`total_frais`, `entree_stock` (présent après clôture). Les données d'approvisionnement "
    "(prix de vente, seuil d'alerte, expiration) ne sont pas stockées sur les lignes de lot."
)

LOT_UPDATE_DESCRIPTION = (
    "**Corps** : champs modifiables (`reference`, `statut`, `date_cloture`, `fournisseur_id`, dates, etc.).\n\n"
    "**Clôture (`statut=CLOTURE`)** : inclure **`approvisionnement`** (obligatoire) — tableau d'objets "
    "`{ \"article_id\": \"<pk métier>\", \"prix_vente\": \"0.00\", \"seuil_alerte\": 0, "
    "\"date_expiration\": null }` avec **une entrée par article** du lot. Ces champs ne sont pas "
    "enregistrés sur `LotItem` ; ils servent uniquement à créer les **`LigneEntree`** et mettre à jour "
    "le **stock** (aucun débit caisse à la clôture — approvisionnement issu du lot)."
)

FRAIS_LOT_LIST_PARAMS = PAGINATION_PARAMS + [
    ORDERING_FRAIS,
    openapi.Parameter(
        "lot_id",
        openapi.IN_QUERY,
        description="Filtrer par lot.",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "type_frais",
        openapi.IN_QUERY,
        description="Type : `TRANSPORT`, `DOUANE`, `MANUTENTION`.",
        type=openapi.TYPE_STRING,
        enum=["TRANSPORT", "DOUANE", "MANUTENTION"],
    ),
    openapi.Parameter(
        "devise_id",
        openapi.IN_QUERY,
        description="Filtrer par devise.",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "created_at_min",
        openapi.IN_QUERY,
        description="Date de création minimale `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "created_at_max",
        openapi.IN_QUERY,
        description="Date de création maximale `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
]

LOT_ITEM_LIST_PARAMS = PAGINATION_PARAMS + [
    ORDERING_LOT_ITEM,
    openapi.Parameter(
        "lot_id",
        openapi.IN_QUERY,
        description="Filtrer par lot.",
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "article_id",
        openapi.IN_QUERY,
        description="Filtrer par identifiant article (`article_id` métier).",
        type=openapi.TYPE_STRING,
    ),
]

TAG_TRANSIT = "Transit — lots, frais & lignes"
TAG_FOURNISSEUR = "Fournisseurs (achats)"
TAG_COMMANDE = "Commandes clients (portail & admin)"
TAG_PORTAIL_CLIENT = "Portail client (JWT dédié)"

ORDERING_COMMANDE = openapi.Parameter(
    "ordering",
    openapi.IN_QUERY,
    description="Tri : `created_at`, `-created_at`, `updated_at`, `-updated_at`, `statut`, `-statut`, `reference`, `-reference`, `id`, `-id`.",
    type=openapi.TYPE_STRING,
)

COMMANDE_LIST_PARAMS = PAGINATION_PARAMS + [
    ORDERING_COMMANDE,
    openapi.Parameter(
        "succursale_id",
        openapi.IN_QUERY,
        description=(
            "**Administrateur (JWT staff)** : filtre les commandes sur cette succursale "
            "(doit appartenir à l’entreprise du JWT). Si le JWT impose déjà une succursale, "
            "doit être identique. **Client portail** : ignoré (périmètre imposé par le compte)."
        ),
        type=openapi.TYPE_INTEGER,
    ),
    openapi.Parameter(
        "statut",
        openapi.IN_QUERY,
        description="`EN_ATTENTE`, `ACCEPTEE`, `LIVREE`, `REJETEE`.",
        type=openapi.TYPE_STRING,
        enum=["EN_ATTENTE", "ACCEPTEE", "LIVREE", "REJETEE"],
    ),
    openapi.Parameter(
        "client_id",
        openapi.IN_QUERY,
        description="Filtrer par identifiant client (`CLI0001`, …). Réservé au back-office (admin).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "reference",
        openapi.IN_QUERY,
        description="Sous-chaîne sur la référence commande (ex. `CMD-1-000042`).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "search",
        openapi.IN_QUERY,
        description="Recherche : référence, note client, nom client, désignations d’articles (catalogue ou libre).",
        type=openapi.TYPE_STRING,
    ),
    openapi.Parameter(
        "created_at_min",
        openapi.IN_QUERY,
        description="Date de création minimale (jour calendaire, inclus), `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "created_at_max",
        openapi.IN_QUERY,
        description="Date de création maximale (jour calendaire, inclus), `YYYY-MM-DD`.",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "date_debut",
        openapi.IN_QUERY,
        description="Alias de `created_at_min` (période).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
    openapi.Parameter(
        "date_fin",
        openapi.IN_QUERY,
        description="Alias de `created_at_max` (période).",
        type=openapi.TYPE_STRING,
        format=openapi.FORMAT_DATE,
    ),
]

COMMANDE_ITEM_LINE_UPDATE_SCHEMA = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    description="Ligne : `article_id` **ou** `nom_article` (exclusif), `quantite` ≥ 1.",
    properties={
        "article_id": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Identifiant métier de l’article (catalogue).",
        ),
        "nom_article": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="Désignation libre si l’article n’est pas au catalogue.",
        ),
        "quantite": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="Quantité demandée (≥ 1).",
        ),
    },
)

COMMANDE_UPDATE_REQUEST_BODY = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    title="Corps — variante selon le JWT",
    description=(
        "Deux variantes selon le **contexte d’authentification** (ne pas mélanger les champs) :\n\n"
        "**JWT portail (client)** : `nom`, `note_client`, `succursale` (ID), `items` (tableau). "
        "Uniquement si la commande est **EN_ATTENTE**. Si `items` est présent, il **remplace** "
        "toutes les lignes existantes.\n\n"
        "**JWT staff (admin ou employé)** : **`statut` uniquement** — **`REJETEE`** ou **`LIVREE`**."
    ),
    properties={
        "statut": openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=["REJETEE", "LIVREE"],
            description="[Staff uniquement] Nouveau statut (rejet ou livraison).",
        ),
        "nom": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="[Client uniquement] Libellé optionnel.",
        ),
        "note_client": openapi.Schema(
            type=openapi.TYPE_STRING,
            description="[Client uniquement] Commentaire ou instructions.",
        ),
        "succursale": openapi.Schema(
            type=openapi.TYPE_INTEGER,
            description="[Client uniquement] ID de la succursale (cohérent avec le lien portail).",
        ),
        "items": openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=COMMANDE_ITEM_LINE_UPDATE_SCHEMA,
            description="[Client uniquement] Nouvelles lignes (remplace l’existant si fourni).",
        ),
    },
)
