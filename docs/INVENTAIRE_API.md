# Inventaire physique — API backend

Module opérationnel : comparaison **stock théorique** (logiciel) vs **stock physique** (comptage), puis **ajustements tracés** à la validation.

> **Guide intégration frontend (écrans, parcours, cohérence) :** voir **§ 4.18** du [readme.md](../readme.md).

> Distinction : `GET /api/rapports/inventaire/` reste un **rapport lecture seule** (état du stock).  
> Les endpoints ci-dessous gèrent le **processus d'inventaire**.

---

## Workflow

```text
1. POST /api/inventaires/              → créer session (BROUILLON ou EN_COURS si demarrer=true)
2. POST /api/inventaires/{id}/demarrer/ → figer stock théorique par article
3. PATCH .../lignes/{ligne_id}/        → saisir stock_physique
   POST .../lignes/bulk/               → saisie groupée
4. POST /api/inventaires/{id}/valider/ → écarts → Entree/Sortie d'ajustement
5. POST /api/inventaires/{id}/annuler/ → annuler (sauf si déjà VALIDÉ)
```

---

## Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/inventaires/` | Liste des sessions |
| POST | `/api/inventaires/` | Créer |
| GET | `/api/inventaires/{id}/` | Détail + lignes |
| PATCH | `/api/inventaires/{id}/` | Modifier libellé, date, commentaire |
| DELETE | `/api/inventaires/{id}/` | Supprimer (interdit si VALIDÉ) |
| POST | `/api/inventaires/{id}/demarrer/` | Générer les lignes |
| PATCH | `/api/inventaires/{id}/lignes/{ligne_id}/` | Saisir quantité comptée |
| POST | `/api/inventaires/{id}/lignes/bulk/` | Saisie groupée |
| GET | `/api/inventaires/{id}/resume/` | Statistiques de comptage |
| POST | `/api/inventaires/{id}/valider/` | Valider et créer ajustements |
| POST | `/api/inventaires/{id}/annuler/` | Annuler |

---

## Création

```http
POST /api/inventaires/
Content-Type: application/json
```

```json
{
  "libelle": "Inventaire magasin juin 2026",
  "date_inventaire": "2026-06-21",
  "perimetre": "EN_STOCK",
  "type_article_filtre": "",
  "commentaire": "",
  "demarrer": true,
  "article_ids": []
}
```

### Périmètre (`perimetre`)

| Valeur | Effet |
|--------|--------|
| `COMPLET` | Tous les articles du tenant |
| `EN_STOCK` | Articles avec `Stock.Qte > 0` (défaut) |
| `PARTIEL` | Liste `article_ids` obligatoire |

---

## Ligne d'inventaire

Chaque ligne expose :

| Champ | Description |
|-------|-------------|
| `stock_theorique` | Stock logiciel **figé** au démarrage |
| `stock_physique` | Quantité comptée (saisie) |
| `ecart` | `stock_physique - stock_theorique` (calculé) |
| `motif_ligne` | Commentaire optionnel |

### Saisie unitaire

```http
PATCH /api/inventaires/1/lignes/42/
```

```json
{
  "stock_physique": "115.00000",
  "motif_ligne": "5 sacs manquants — zone réserve"
}
```

### Saisie groupée

```http
POST /api/inventaires/1/lignes/bulk/
```

```json
{
  "lignes": [
    { "article_id": "PRLI0001", "stock_physique": "120.00000" },
    { "article_id": "PRLI0002", "stock_physique": "82.00000", "motif_ligne": "Erreur réception?" }
  ]
}
```

---

## Validation

```http
POST /api/inventaires/1/valider/
```

**Règles :**

- Session en statut `EN_COURS`
- Toutes les lignes doivent avoir un `stock_physique` saisi
- Écart positif → **entrée** d'ajustement (`Entree` + `LigneEntree`, sans impact caisse)
- Écart négatif → **sortie** d'ajustement (`Sortie` FIFO, prix 0, sans caisse)
- Session passe à `VALIDE` ; liens `entree_ajustement_id` / `sortie_ajustement_id` renvoyés

**Motif enregistré :** `Ajustement inventaire #{id} — {libelle}`

---

## Statuts session

| Statut | Signification |
|--------|----------------|
| `BROUILLON` | Créée, lignes non générées |
| `EN_COURS` | Fiche générée, comptage en cours |
| `VALIDE` | Ajustements appliqués, historique conservé |
| `ANNULE` | Session abandonnée |

---

## Résumé (`resume`)

```json
{
  "total_lignes": 11,
  "lignes_comptees": 8,
  "lignes_non_comptees": 3,
  "ecarts_positifs": 1,
  "ecarts_negatifs": 2,
  "ecarts_nuls": 5,
  "lignes_avec_ecart": 3
}
```

---

## Frontend — colonnes fiche d'inventaire

| Colonne UI | Champ JSON |
|------------|------------|
| Article | `nom_scientifique`, `article_id` |
| Stock logiciel | `stock_theorique` |
| Stock physique | `stock_physique` (saisie) |
| Écart | `ecart` |

---

## Rapport vs inventaire opérationnel

| | Rapport `/rapports/inventaire/` | Module `/inventaires/` |
|--|-------------------------------|------------------------|
| Rôle | **Rapport d'inventaire** JSON (affichage / export) | Saisie + validation |
| Mode catalogue | Stock logiciel, statuts stock, colonnes vides pour comptage | — |
| Mode session | `?session_id=` → écarts, statuts ligne, `session.statut` | CRUD session |
| Ajustement stock | Non | Oui (`POST .../valider/`) |

```http
GET /api/rapports/inventaire/?seulement_en_stock=true
GET /api/rapports/inventaire/?session_id=1
```
