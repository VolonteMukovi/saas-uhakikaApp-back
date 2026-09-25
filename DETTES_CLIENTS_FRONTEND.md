# Dettes & paiements clients — guide frontend

Logique **simple** : une dette = une sortie `EN_CREDIT` ; les paiements partiels mettent à jour `paye` / `reste` / `status`.

Alignement **CURSOR.md** (HTTP natif) : ETag / 304, `Idempotency-Key`, pagination curseur, RFC 9457, `X-Correlation-ID`.

---

## Création automatique

`POST /api/sorties/` avec `statut: "EN_CREDIT"` + `client_id` obligatoire → crée `DettesClients` :

| Champ   | Valeur initiale                          |
|---------|------------------------------------------|
| montant | Σ (`prix_unitaire` × `quantite`) des lignes |
| paye    | `0`                                      |
| reste   | `montant`                                |
| status  | `ENCOURS`                                |
| date    | date de la sortie                        |

Statuts uniquement : `ENCOURS` | `TERMINE` (`reste = 0` → `TERMINE`).

---

## En-têtes HTTP (obligatoires côté FE)

Configurer l’instance Axios globale (voir `CURSOR.md`) :

| En-tête | Usage |
|---------|--------|
| `Accept: application/json; version=1.0` | Négociation de version |
| `X-Correlation-ID` | UUID par cycle de requête (support) |
| `If-None-Match` | Rejouer l’`ETag` du dernier GET → **304** si inchangé |
| `Idempotency-Key` | UUID sur chaque `POST` paiement (anti double-clic / retry) |

Erreurs : Content-Type `application/problem+json` (RFC 9457) → afficher `detail`.

---

## Endpoints

### Liste des dettes (légère — sans articles)

```http
GET /api/dettes-clients/
GET /api/dettes-clients/?date_debut=2026-09-01&date_fin=2026-09-30
GET /api/dettes-clients/?client_id=CLI0001&status=ENCOURS
GET /api/dettes-clients/?cursor=...&page_size=25
GET /api/dettes-clients/?page=1&page_size=25
```

Champs liste : `id`, `sortie_id`, `client_id`, `client_nom`, `date`, `montant`, `paye`, `reste`, `status`, `updated_at`.

Pagination :

- `?page=` → `{ count, next, previous, results }`
- `?cursor=` (sans `page`) → `{ next_cursor, previous_cursor, results }`

### Détail (articles + historique paiements)

```http
GET /api/dettes-clients/{id}/
```

```json
{
  "id": 1,
  "sortie_id": 42,
  "client_id": "CLI0001",
  "client_nom": "Client A",
  "date": "2026-09-01",
  "montant": "500.00000",
  "paye": "300.00000",
  "reste": "200.00000",
  "status": "ENCOURS",
  "updated_at": "2026-09-10T14:22:01Z",
  "articles": [
    {
      "ligne_sortie_id": 9,
      "article_id": 3,
      "article_nom": "Produit X",
      "quantite": "2.00000",
      "prix_unitaire": "250.00000",
      "montant_ligne": "500.00000",
      "devise": "USD"
    }
  ],
  "paiements": [
    { "id": 1, "dettes_clients": 1, "montant": "100.00000", "date": "2026-09-01", "created_at": "..." },
    { "id": 2, "dettes_clients": 1, "montant": "200.00000", "date": "2026-09-05", "created_at": "..." }
  ]
}
```

### Liste clients → reste dû (écran principal)

```http
GET /api/dettes-clients/par-clients/
GET /api/dettes-clients/par-clients/?date_debut=2026-09-01&date_fin=2026-09-30
GET /api/dettes-clients/par-clients/?page=1&page_size=50
```

```json
{
  "clients": [
    { "client_id": "CLI0001", "client_nom": "Client A", "total_reste": "400.00000" },
    { "client_id": "CLI0002", "client_nom": "Client B", "total_reste": "250.00000" }
  ],
  "total_reste": "650.00000",
  "results": [ "... idem clients si paginé ..." ],
  "count": 2
}
```

`total_reste` d’un client = **somme des `reste`** de ses dettes (filtrées).  
`total_reste` racine = somme **globale** (hors page).

### Total général

```http
GET /api/dettes-clients/totaux/
```

```json
{
  "total_reste": "800.00000",
  "nombre_dettes": 5,
  "nombre_encours": 4,
  "nombre_termine": 1
}
```

### Enregistrer un paiement (partiel ou total)

```http
POST /api/paiements-dettes-clients/
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json
Accept: application/json; version=1.0

{
  "dettes_clients": 1,
  "montant": "100.00000",
  "date": "2026-09-10"
}
```

Réponse `201` (extrait) :

```json
{
  "id": 3,
  "dettes_clients": 1,
  "montant": "100.00000",
  "date": "2026-09-10",
  "created_at": "2026-09-10T08:00:00Z",
  "dette": {
    "id": 1,
    "montant": "500.00000",
    "paye": "400.00000",
    "reste": "100.00000",
    "status": "ENCOURS",
    "updated_at": "2026-09-10T08:00:00Z"
  }
}
```

Règles :

- `date` optionnelle (défaut : aujourd’hui).
- Montant ≤ `reste` ; dette `TERMINE` refusée (`400` problem+json).
- Après paiement : utiliser `dette` dans la réponse — **pas besoin** d’un 2ᵉ GET.
- Retry réseau : **même** `Idempotency-Key` → réponse historisée, pas de double débit.

### Historique des paiements

```http
GET /api/paiements-dettes-clients/?dettes_clients=1
```

(également inclus dans `GET /api/dettes-clients/{id}/` → `paiements`).

---

## Écrans recommandés

1. **Liste clients endettés** → `GET .../par-clients/` + `total_reste` global ; cache via `ETag`.
2. **Dettes d’un client** → `GET /api/dettes-clients/?client_id=...` (liste légère).
3. **Fiche dette** → `GET /{id}/` + formulaire paiement avec `Idempotency-Key`.
4. **Filtres** → `date_debut` / `date_fin` / `status`.

Pas de KPI secondaires : rester sur **reste**, **payé**, **montant**, **articles**, **paiements**.

---

## Swagger / Redoc

Tags OpenAPI :

- **Dettes clients** — `/api/dettes-clients/`
- **Paiements dettes clients** — `/api/paiements-dettes-clients/`

Disponibles sur `/swagger/` et `/redoc/` après déploiement.
