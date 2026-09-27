# Détail client — achats & dettes (guide frontend)

Page concernée : `/fr/clients/{id}/lifecycle`

Logique backend **simple**. Plus de CA, solde évolutif, débit/crédit, graphiques ni répartition.

---

## Endpoints

### Dashboard (source principale)

```http
GET /api/clients/{client_id}/dashboard/
GET /api/clients/{client_id}/dashboard/?date_debut=2026-09-01&date_fin=2026-09-25
```

Sans `date_debut` / `date_fin` → **toutes** les données du client (pas de période arbitraire).

### Réponse

```json
{
  "client": {
    "id": "CLI0207",
    "nom": "GLOIRE A DIEU",
    "telephone": "...",
    "email": null,
    "adresse": null,
    "type": "STANDARD"
  },
  "periode": {
    "date_debut": "2026-09-01",
    "date_fin": "2026-09-25",
    "mode": "periode_personnalisee"
  },
  "nombre_achats": 12,
  "total_achete": "1250.00000",
  "dette_restante": "350.00000",
  "produits_achetes": [
    {
      "date": "2026-09-25",
      "produit": "Riz",
      "article_id": 3,
      "quantite": "2.00000",
      "prix_unitaire": "10.00000",
      "total": "20.00000",
      "devise": "USD",
      "sortie_id": 42,
      "statut_vente": "EN_CREDIT"
    }
  ],
  "nombre_lignes_produits": 1
}
```

`type` = `SPECIAL` si `ClientEntreprise.is_special`, sinon `STANDARD`. **Aucun impact** sur les calculs.

### Produits paginés (ex-mouvements)

```http
GET /api/clients/{client_id}/mouvements/?page=1&page_size=25
GET /api/clients/{client_id}/mouvements/?date_debut=2026-09-01&date_fin=2026-09-25
```

Retourne la **même liste de produits** que `produits_achetes` (paginée).  
Plus de champs `debit`, `credit`, `solde_apres_operation`.

---

## Règles métier (source de vérité backend)

| Champ | Source | Inclus | Exclu |
|-------|--------|--------|-------|
| `nombre_achats` | Nb de `Sortie` | `PAYEE` + `EN_CREDIT` | `PaiementDettesClients` |
| `total_achete` | Σ `qté × PU` des `LigneSortie` | Comptant + crédit | Paiements de dettes |
| `dette_restante` | Σ `DettesClients.reste` | Dettes filtrées par **date de dette** | — |
| `produits_achetes` | `LigneSortie` → Article | Lignes des sorties période | Paiements |

Exemple :

```text
01/09 vente crédit 500 $
05/09 paiement 200 $
10/09 paiement 100 $
```

→ `nombre_achats = 1`, `total_achete = 500`, `dette_restante = 200`.

### Dates de filtre

| Donnée | Champ date |
|--------|------------|
| Achats / produits | `Sortie.date_creation` |
| Dette restante | `DettesClients.date` |

---

## Affichage FE recommandé

```text
Client + type
Période
Nombre d'achats
Total acheté
Dette restante
Tableau produits (date, produit, qté, PU, total)
```

Ne **pas** recalculer côté front. Ne plus afficher CA / solde / écart / graphiques / débit-crédit.

### Solde (léger)

```http
GET /api/clients/{client_id}/solde/
```

Même totaux que le dashboard **sans** `produits_achetes` (payload réduit → ETag plus efficace).

| Endpoint | Comportement |
|----------|--------------|
| `GET .../statistiques/` | Même payload que `dashboard` |
| `GET .../solde/` | `dette_restante` + totaux achats (sans ancien solde) |
| `GET .../ventes/` | Liste des sorties (achats) paginée |

---

## HTTP (CURSOR.md)

- `Accept: application/json; version=1.0`
- `If-None-Match` / ETag sur GET
- `X-Correlation-ID`
- Erreurs : `application/problem+json`

Swagger / Redoc : tag **Clients — détail**.
