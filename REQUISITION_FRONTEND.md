# Documentation Frontend — Module Réquisitions

Ce document décrit l’API backend livrée pour le **nouveau module métier Réquisition**.

> **Important** : le rapport historique `GET /api/rapports/bon-entree/` reste disponible (snapshot rupture/alerte).  
> Il n’est **plus** la source de vérité des réquisitions. Utilisez `/api/requisitions/`.

---

## 1. Architecture

### Backend (Django / DRF)

| Élément | Emplacement |
|---------|-------------|
| Modèles | `stock.models.Requisition`, `RequisitionLigne`, `RequisitionHistorique` |
| Service métier | `stock.services.requisition` |
| Document d'impression | `stock.services.requisition_document.build_requisition_document` (**JSON**, pas de PDF serveur) |
| Serializers | `stock.requisition_serializers` |
| ViewSet | `stock.requisition_views.RequisitionViewSet` |
| URLs | `/api/requisitions/` (router stock) |
| Permissions | `IsAdminOrUser` + filtre tenant (`entreprise` / `succursale`) |
| Plan SaaS | règle `^/api/requisitions` → fonctionnalité `stock` |

### Modèles (résumé)

**Requisition**

- `numero` unique par entreprise (`REQ-YYYY-NNNNN`)
- `titre`, `description`, `observations`, `commentaires`
- `priorite` : `BASSE` \| `NORMALE` \| `HAUTE` \| `URGENTE`
- `statut` : voir section États
- `entreprise`, `succursale` (optionnelle)
- `cree_par`, `valide_par`, `rejete_par`
- `date_creation`, `date_modification`, `date_validation`, `date_rejet`, `date_cloture`
- `motif_rejet`, `archived`

**RequisitionLigne**

- `type_ligne` : `ARTICLE` (FK `article`) ou `LIBRE` (nom libre)
- `designation`, `quantite`, `unite`
- `prix_estime` : `null` = jamais approvisionné → afficher `.....`
- `prix_source` : `DERNIER_ACHAT` \| `MANUEL`
- `remarque`, `ordre`
- snapshot optionnel : `statut_stock`, `stock_actuel`, `seuil_alerte`

**Règle prix estimé**

1. Article déjà approvisionné (au moins une `LigneEntree`) → `prix_estime` = **dernier prix d’achat** (obligatoire / prérempli).
2. Jamais approvisionné ou ligne libre sans prix → `prix_estime = null`, UI/PDF affichent **`.....`** ; saisie manuelle ensuite.
3. Tout pointillé (`...`, `.....`, `......`, `…`) est interprété comme « prix manquant ».

---

## 2. Endpoints API

Base : `/api/requisitions/`  
Auth : JWT + contexte entreprise.

### Liste / CRUD document

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/requisitions/` | Liste paginée + filtres |
| `POST` | `/api/requisitions/` | Création |
| `GET` | `/api/requisitions/{id}/` | Détail (lignes + historique + actions) |
| `PATCH` | `/api/requisitions/{id}/` | Modifier en-tête (si modifiable) |
| `DELETE` | `/api/requisitions/{id}/` | Suppression (`BROUILLON` ou `ANNULEE` uniquement) |

#### Query params liste

- `statut`, `priorite`, `cree_par` / `utilisateur`
- `succursale` / `succursale_id`
- `date_from` / `date_debut`, `date_to` / `date_fin`
- `archived=true|false`
- `search` / `q` (n°, titre, description, désignation lignes)

#### Body création

```json
{
  "titre": "Réassort semaine 28",
  "description": "",
  "observations": "",
  "commentaires": "",
  "priorite": "NORMALE",
  "succursale_id": null,
  "avec_suggestions": true,
  "sources": ["rupture", "alerte"]
}
```

`sources` possibles : `rupture`, `alerte`, `expiration_30`, `expiration_90`, `tous`.

### Suggestions

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/requisitions/suggestions-preview/?sources=rupture&sources=alerte` | Aperçu sans créer |
| `POST` | `/api/requisitions/{id}/suggestions/` | Injecter les suggestions |

```json
{ "sources": ["rupture", "alerte", "expiration_30"], "replace": false }
```

`replace: true` remplace toutes les lignes ; sinon n’ajoute que les articles absents.

### Lignes

| Méthode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/requisitions/{id}/lignes/` | Ajouter |
| `PATCH` | `/api/requisitions/{id}/lignes/{ligne_id}/` | Modifier |
| `DELETE` | `/api/requisitions/{id}/lignes/{ligne_id}/` | Supprimer |
| `POST` | `/api/requisitions/{id}/lignes/{ligne_id}/dupliquer/` | Dupliquer |
| `POST` | `/api/requisitions/{id}/reordonner/` | Réordonner |

#### Ajout article catalogue

```json
{
  "type_ligne": "ARTICLE",
  "article_id": "CODI0001",
  "quantite": "10",
  "unite": "pcs",
  "prix_estime": null,
  "remarque": ""
}
```

Si `prix_estime` omis : dernier achat ou `null` (`.....`).

#### Ajout ligne libre (produit inexistant)

```json
{
  "type_ligne": "LIBRE",
  "designation": "Café Premium",
  "quantite": "24",
  "unite": "boîtes",
  "prix_estime": ".....",
  "remarque": "Nouveau produit à créer à l’appro"
}
```

#### Réordonner

```json
{ "ordre": [12, 8, 15, 9] }
```

Liste ordonnée des **ids de lignes**.

### Workflow statut

| Méthode | URL | Vers |
|---------|-----|------|
| `POST` | `.../ouvrir/` | `OUVERTE` |
| `POST` | `.../preparer/` | `EN_PREPARATION` |
| `POST` | `.../soumettre/` | `EN_ATTENTE_VALIDATION` |
| `POST` | `.../valider/` | `VALIDEE` |
| `POST` | `.../rejeter/` | `REJETEE` (body `motif` **obligatoire**) |
| `POST` | `.../annuler/` | `ANNULEE` |
| `POST` | `.../cloturer/` | `CLOTUREE` (reste visible, **ne plus archiver**) |
| `POST` | `.../reouvrir/` | `BROUILLON` (depuis `REJETEE`) |

Body optionnel (sauf rejet) :

```json
{ "motif": "...", "commentaires": "..." }
```

### Affichage liste (frontend) — clôturées visibles

**Ne pas** appeler la liste avec `?archived=false` si tu veux voir les clôturées (anciennes données pouvaient être archivées ; désormais `cloturer` ne touche plus `archived`).

Appels recommandés :

```http
GET /api/requisitions/
```

Sans filtre `archived` → toutes les réquisitions du tenant (y compris `CLOTUREE`).

Filtres utiles :

```http
GET /api/requisitions/?statut=CLOTUREE
GET /api/requisitions/?statut=VALIDEE
```

Affichage badge :

| `statut` | Libellé API | Badge UI suggéré |
|----------|-------------|------------------|
| `BROUILLON` | Brouillon | gris |
| `OUVERTE` | Ouverte | bleu |
| `EN_PREPARATION` | En préparation | bleu clair |
| `EN_ATTENTE_VALIDATION` | En attente de validation | orange |
| `VALIDEE` | Validée | vert |
| `REJETEE` | Rejetée | rouge |
| `ANNULEE` | Annulée | gris foncé |
| `CLOTUREE` | Clôturée | violet / neutre |

Utiliser `statut_libelle` renvoyé par l’API pour le texte du badge.

`archived` reste un champ séparé (archivage manuel éventuel), **indépendant** de `CLOTUREE`.

### Document d'impression (JSON → PDF côté frontend)

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/requisitions/{id}/document/` | **Payload JSON** complet pour impression / export |
| `GET` | `/api/requisitions/{id}/pdf/` | Alias du même JSON (plus de binaire PDF) |

> Voir le détail du contrat dans [`REQUISITION_RAPPORT_JSON.md`](REQUISITION_RAPPORT_JSON.md).  
> Le backend ne dessine plus de PDF/HTML ; le frontend génère le document.

---

## 3. Workflow UI recommandé

```
Créer → (option) Suggestions → Personnaliser lignes → Enregistrer brouillon
  → Ouvrir / Préparer → Soumettre → Valider → Imprimer PDF → Clôturer / Archiver
```

Les suggestions **ne sont jamais obligatoires**. L’utilisateur peut tout supprimer / modifier / ajouter (y compris articles « sains » ou lignes libres).

---

## 4. États & boutons

Champ API `actions_disponibles` (détail) = source de vérité pour les boutons.

| Statut | Afficher | Masquer |
|--------|----------|---------|
| **Brouillon** | Modifier, lignes, suggestions, Ouvrir, Préparer, Soumettre, Annuler, Supprimer, Imprimer | Valider / Clôturer |
| **Ouverte** | Idem édition + Préparer / Soumettre / Annuler | Valider |
| **En préparation** | Édition + Soumettre / Annuler | — |
| **En attente validation** | Valider, Rejeter, Annuler, (édition encore autorisée backend) | — |
| **Validée** | PDF / Imprimer, Clôturer, Annuler | Toute édition lignes |
| **Rejetée** | Motif rejet, Réouvrir, Annuler, (édition possible) | Valider direct |
| **Annulée** | Consultation + PDF, Suppression éventuelle | Édition |
| **Clôturée** | Consultation + PDF uniquement | Tout le reste |

`est_modifiable === false` → formulaires en **lecture seule**.

---

## 5. Interface — spécifications UI

### Tableau desktop

Colonnes utiles uniquement :

| Colonne | Source |
|---------|--------|
| Numéro | `numero` |
| Date | `date_creation` |
| Titre | `titre` |
| Nb articles | `resume.nombre_lignes` |
| Priorité | `priorite_libelle` (badge couleur) |
| Statut | `statut_libelle` (badge) |
| Créateur | `cree_par_nom` |
| Montant estimatif | `resume.montant_estime` (+ hint si `lignes_prix_manquants`) |
| Actions | menu **Ellipse (⋮)** |

Actions menu ⋮ (selon `actions_disponibles`) : Voir, Modifier, Valider, Rejeter, PDF, Clôturer, Annuler, Supprimer.

### Cartes mobile

Chaque réquisition = carte :

- titre + numéro
- badges priorité / statut
- montant + nb lignes
- ⋮ en haut à droite (mêmes actions)

**Rien ne disparaît** : les colonnes secondaires passent dans le menu ou sous le titre.

### Formulaire création / édition

1. Titre (obligatoire), priorité, succursale, description, observations.
2. Toggle « Ajouter suggestions » + multi-select sources.
3. Tableau lignes éditable :
   - type badge ARTICLE / LIBRE
   - designation (éditable)
   - quantité, unité
   - prix : afficher `prix_estime_affiche` (`.....` si manquant) — input number si saisie
   - montant ligne (calculé)
   - remarque
   - actions ligne : modifier, dupliquer, supprimer, drag reorder
4. Boutons footer selon statut.

### Modales

- Confirmation validation / annulation / clôture
- Rejet avec champ motif obligatoire
- Ajout article (autocomplete catalogue)
- Ajout ligne libre (nom + qté + unité + prix + remarque)
- Suggestions (preview puis appliquer)

### Notifications toast

- Création / sauvegarde OK
- Transition statut OK
- Erreurs métier (`detail` du problem+json backend)
- Warning soft : « X prix à compléter » (`resume.lignes_prix_manquants`)

### Validations frontend

- Quantité > 0
- Ligne libre : designation obligatoire
- Ne pas appeler PATCH/POST lignes si `!est_modifiable`
- Afficher `.....` quand `prix_manquant === true` (ne pas forcer `0`)

---

## 6. Exemple de réponse détail (extrait)

```json
{
  "id": 12,
  "numero": "REQ-2026-00001",
  "titre": "Réassort semaine 28",
  "statut": "BROUILLON",
  "statut_libelle": "Brouillon",
  "priorite": "HAUTE",
  "est_modifiable": true,
  "resume": {
    "nombre_lignes": 3,
    "quantite_totale": "34.00000",
    "montant_estime": "50.00000",
    "montant_estime_complet": false,
    "lignes_prix_manquants": 1
  },
  "lignes": [
    {
      "id": 1,
      "type_ligne": "ARTICLE",
      "article_id": "CODI0001",
      "designation": "Café Premium",
      "quantite": "10.00000",
      "unite": "pcs",
      "prix_estime": "2.50000",
      "prix_estime_affiche": "2.50000",
      "prix_manquant": false,
      "prix_source": "DERNIER_ACHAT",
      "montant_estime": "25.00000",
      "montant_estime_affiche": "25.00000",
      "ordre": 1,
      "statut_stock": "RUPTURE"
    },
    {
      "id": 2,
      "type_ligne": "LIBRE",
      "article_id": null,
      "designation": "Produit nouveau",
      "prix_estime": null,
      "prix_estime_affiche": ".....",
      "prix_manquant": true,
      "montant_estime_affiche": "....."
    }
  ],
  "actions_disponibles": ["ajouter_ligne", "imprimer", "modifier", "soumettre", "..."],
  "historique": []
}
```

---

## 7. Compatibilité

| Ancien | Nouveau |
|--------|---------|
| `GET /api/rapports/bon-entree/` | Conservé (rapport / snapshot) |
| Chatbot « réquisition PDF » | Oriente vers `/api/requisitions/` + snapshot bon-entree |
| Approvisionnements / Inventaire / Ventes | **Non modifiés** |

Lorsqu’un article de la réquisition sera créé à l’approvisionnement, créer l’`Article` puis éventuellement relier manuellement (évolution future possible : « convertir ligne libre → article »).

---

## 8. Checklist intégration frontend

- [ ] Page liste + filtres + ⋮ + cartes mobile
- [ ] Page / drawer détail avec édition conditionnelle `est_modifiable`
- [ ] Wizard création + suggestions optionnelles
- [ ] Ajout ARTICLE / LIBRE
- [ ] Affichage prix `.....` + saisie manuelle
- [ ] Drag & drop ou up/down + `POST .../reordonner/`
- [ ] Boutons workflow branchés sur `actions_disponibles`
- [ ] Viewer / export à partir de `GET .../document/` (JSON → PDF côté client)
- [ ] Ne plus attendre un binaire `application/pdf` sur `/pdf/`
- [ ] Toasts + gestion erreurs 400
- [ ] Responsive : aucune action uniquement desktop sans équivalent ⋮

---

*Document généré pour la refonte module Réquisitions — API UHAKIKA.*
