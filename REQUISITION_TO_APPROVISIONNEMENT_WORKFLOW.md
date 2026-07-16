# Workflow Réquisition → Approvisionnement (implémenté)

La réquisition exprime le **besoin d’achat**. L’approvisionnement (`Entree`) matérialise la **réception réelle**. Aucune logique stock / lots / prix n’est dupliquée : la transformation pré-remplit puis réutilise le pipeline `Entree` existant.

```text
Analyse du stock
        ↓
Création de la réquisition (+ conditionnement par ligne)
        ↓
Validation de la réquisition
        ↓
Transformation / pré-remplissage → Approvisionnement
        ↓
Ajustement livraison (qty / suppressions / ajouts)
        ↓
Entrée en stock (pipeline Entree actuel)
```

---

## 1. Conditionnement sur les lignes de réquisition

Chaque ligne `ARTICLE` porte un `conditionnement_id`. La quantité est exprimée **dans ce packing**.

| Champ API | Description |
| --------- | ----------- |
| `conditionnement_id` | FK packing (écriture create/update ligne) |
| `conditionnement_nom` | Libellé (lecture) |
| `conditionnement_multiplicateur` | Unités de base / packing (lecture) |
| `quantite` | Qté à commander dans le packing |

Unicité ligne : même `article` + même `conditionnement` = doublon ; packings différents autorisés.

---

## 2. Endpoints de transformation

### Preview (sans créer l’Entree)

```http
GET /api/requisitions/{id}/transformation-preview/
```

Prérequis : statut `VALIDEE`.

Réponse :

```json
{
  "cree": false,
  "requisition_id": 12,
  "requisition_numero": "REQ-2026-00012",
  "prefill": {
    "libele": "Approvisionnement — REQ-2026-00012 — …",
    "description": "Issu de la réquisition …",
    "source_requisition_id": 12,
    "source_requisition_numero": "REQ-2026-00012",
    "succursale_id": null,
    "lignes": [
      {
        "article_id": "…",
        "conditionnement_id": 5,
        "conditionnement_nom": "Carton 24",
        "quantite_saisie": "5.00000",
        "prix_achat_conditionnement": "18.00000",
        "prix_vente_conditionnement": "24.00000",
        "seuil_alerte": "10",
        "remarque_source": "",
        "requisition_ligne_id": 3
      }
    ],
    "lignes_ignorees": []
  }
}
```

### Transformer

```http
POST /api/requisitions/{id}/transform-to-approvisionnement/
Content-Type: application/json

{ "creer": true, "force": false }
```

| Paramètre | Défaut | Effet |
| --------- | ------ | ----- |
| `creer` | `true` | `true` : crée l’`Entree` (stock via pipeline existant). `false` : retourne uniquement le `prefill` (comme la preview). |
| `force` | `false` | Si déjà transformée, `true` autorise une nouvelle `Entree` liée. |

Bouton UI : action `transformer_approvisionnement` dans `actions_disponibles` quand statut = `VALIDEE`.

---

## 3. Deux flux frontend recommandés

### A — Bouton « Transformer » (création immédiate)

1. `POST …/transform-to-approvisionnement/` avec `{ "creer": true }`
2. Rediriger vers l’édition de l’`Entree` créée (`entree_id`)
3. Ajuster quantités / lignes via `PUT/PATCH /api/entrees/{id}/` (service d’update existant)

### B — Pré-remplir le formulaire puis confirmer (recommandé si écarts fournisseur avant stock)

1. `GET …/transformation-preview/` **ou** `POST …` avec `{ "creer": false }`
2. Ouvrir le **même** formulaire Approvisionnement avec le `prefill`
3. Modifier / supprimer / ajouter des lignes
4. `POST /api/entrees/` en passant `source_requisition_id` + lignes éditées

Le backend marque alors la réquisition `TRANSFORMEE` et journalise l’historique.

---

## 4. Prix par conditionnement

Suggestions (réquisition + prefill) :

- **Prix d’achat** : dernier `prix_achat_conditionnement` (ou dérivé unitaire × multiplicateur) pour le couple article + packing
- **Prix de vente** : même logique sur `prix_vente_conditionnement`

Toujours modifiables avant / après création de l’`Entree`.

---

## 5. Traçabilité

### Sur l’approvisionnement (`Entree`)

| Champ | Rôle |
| ----- | ---- |
| `source_requisition` | ID réquisition (lecture) |
| `source_requisition_id` | Écriture optionnelle au `POST /api/entrees/` |
| `source_requisition_numero` | Copie figée du numéro (`REQ-…`) |

### Sur la réquisition

| Champ | Rôle |
| ----- | ---- |
| `transformation_status` | `NON_TRANSFORMEE` \| `TRANSFORMEE` |
| `transformed_at` | Horodatage |
| `approvisionnements[]` | Liste `{ id, libele, date_op, source_requisition_numero }` |

---

## 6. Cas limites

| Cas | Comportement |
| --- | ------------ |
| Ligne `LIBRE` sans article | Listée dans `lignes_ignorees` ; non reprise dans l’Entree |
| Aucune ligne article | Erreur 400 |
| Déjà transformée + `force=false` | Erreur 400 + liste des `approvisionnements` existants |
| Prix packing inconnu | Fallback unitaire × multiplicateur, sinon `0` / min vente |

---

## 7. Migration

`stock/migrations/0042_requisition_to_approvisionnement.py`

- `Entree.source_requisition` / `source_requisition_numero`
- `Requisition.transformation_status` / `transformed_at`
- `RequisitionLigne.conditionnement`

---

## 8. Principe non négociable

> Une réquisition transformée devient un **approvisionnement standard**. Validations, lots, expirations, coûts, stock et rapports restent ceux du module Approvisionnements.
