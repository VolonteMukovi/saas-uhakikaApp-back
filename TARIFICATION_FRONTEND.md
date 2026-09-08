# Tarification — Guide d’intégration Frontend

> **Date** : septembre 2026  
> **Endpoint** : `GET /api/tarification/`  
> **Objectif** : lister **tous** les produits de l’entreprise avec leur **dernier prix de vente**, y compris ceux **sans prix** (jamais approvisionnés).

---

## 1. Résumé

| Élément | Détail |
|---------|--------|
| Méthode | `GET` |
| URL | `/api/tarification/` |
| Auth | JWT staff + contexte entreprise |
| Pagination | Oui (`page`, `page_size`) — défaut 25 |
| Écriture | Non (lecture seule pour l’instant) |

**Règle métier** : le prix affiché est le **dernier prix de vente** issu du dernier approvisionnement (`LigneEntree`).  
S’il n’y a **aucun** approvisionnement → `prix_* = null`, `prix_manquant = true`, afficher **`.....`**.

---

## 2. Query params

| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page (défaut 1) |
| `page_size` | int | Taille page |
| `search` / `q` | string | Recherche code / nom scientifique / commercial |
| `succursale` / `succursale_id` | int | Filtre succursale (sinon branche JWT) |
| `type_article` / `type_article_id` | int | Filtre type |
| `sous_type_article` / `sous_type_article_id` | int | Filtre sous-type |
| `prix_manquant` | bool | `true` = articles sans prix / jamais entrés ; `false` = articles avec au moins un approvisionnement |

Exemples :

```http
GET /api/tarification/?page=1&page_size=50
GET /api/tarification/?q=café&prix_manquant=true
GET /api/tarification/?type_article_id=3
```

---

## 3. Réponse

```json
{
  "rapport": "tarification",
  "count": 120,
  "next": "http://…/api/tarification/?page=2",
  "previous": null,
  "results": [ { "...": "voir §3.1" } ],
  "resume": {
    "nombre_articles": 25,
    "avec_prix": 18,
    "sans_prix": 7,
    "placeholder_prix": "....."
  },
  "instructions_frontend": {
    "afficher_placeholder_prix": ".....",
    "prix_null_si_jamais_approvisionne": true,
    "conditionnements_inclus": true
  }
}
```

`resume` porte sur **la page courante** (pas forcément le total global).

### 3.1 Élément `results[]`

| Champ | Type | Description |
|-------|------|-------------|
| `article_id` | string | Code article (PK) |
| `nom_scientifique` | string | — |
| `nom_commercial` | string | — |
| `designation` | string | Commercial sinon scientifique sinon code |
| `categorie` | string \| null | `Type / Sous-type` |
| `unite` | object \| null | `{ id, libelle }` unité de stock |
| `unite_stock_base` | string | Libellé unité |
| `succursale_id` | int \| null | — |
| `stock_actuel` | string \| null | Quantité stock |
| `seuil_alerte` | string \| null | — |
| `prix_vente_unitaire_base` | string \| **null** | Dernier PU vente (unité de base) |
| `prix_vente_affiche` | string | Valeur ou `"....."` |
| `prix_manquant` | boolean | `true` si jamais de prix |
| `date_dernier_prix` | ISO \| null | Date du dernier approvisionnement source |
| `source_prix` | `"ligne_entree"` \| null | — |
| `devise` | object \| null | `{ id, sigle, symbole, nom }` — devise de la `LigneEntree` source |
| `devise_sigle` | string \| null | Raccourci (`sigle` ou `symbole`) pour affichage à côté du prix |
| `conditionnements` | array | Prix par packing (§3.2) |

Exemple sans prix :

```json
{
  "article_id": "BOEA0001",
  "designation": "Eau 50cl",
  "prix_vente_unitaire_base": null,
  "prix_vente_affiche": ".....",
  "prix_manquant": true,
  "date_dernier_prix": null,
  "source_prix": null,
  "conditionnements": [
    {
      "id": 12,
      "nom": "Pièce",
      "multiplicateur_base": "1.00000",
      "est_defaut": true,
      "prix_vente_conditionnement": null,
      "prix_vente_affiche": ".....",
      "prix_manquant": true,
      "date_dernier_prix": null,
      "source_prix": null
    }
  ]
}
```

Exemple avec prix :

```json
{
  "article_id": "BOEA0002",
  "designation": "Jus mangue",
  "unite_stock_base": "pcs",
  "prix_vente_unitaire_base": "1.50000",
  "prix_vente_affiche": "1.50000",
  "prix_manquant": false,
  "date_dernier_prix": "2026-09-01T10:00:00Z",
  "source_prix": "ligne_entree",
  "devise": { "id": 2, "sigle": "USD", "symbole": "$", "nom": "Dollar US" },
  "devise_sigle": "USD",
  "conditionnements": [
    {
      "id": 20,
      "nom": "Pièce",
      "multiplicateur_base": "1.00000",
      "est_defaut": true,
      "prix_vente_conditionnement": "1.50000",
      "prix_vente_affiche": "1.50000",
      "prix_manquant": false,
      "source_prix": "ligne_entree",
      "devise": { "id": 2, "sigle": "USD", "symbole": "$", "nom": "Dollar US" },
      "devise_sigle": "USD"
    },
    {
      "id": 21,
      "nom": "Carton 24",
      "multiplicateur_base": "24.00000",
      "est_defaut": false,
      "prix_vente_conditionnement": "36.00000",
      "prix_vente_affiche": "36.00000",
      "prix_manquant": false,
      "source_prix": "derive_unitaire_base",
      "devise": { "id": 2, "sigle": "USD", "symbole": "$", "nom": "Dollar US" },
      "devise_sigle": "USD"
    }
  ]
}
```

### 3.2 `conditionnements[]`

| Champ | Description |
|-------|-------------|
| `prix_vente_conditionnement` | Dernier prix packing, ou `null` |
| `source_prix` | `ligne_entree` (packing déjà entré) **ou** `derive_unitaire_base` (calculé : PU base × multiplicateur) |
| `prix_manquant` | `true` si aucun PU base ni packing |
| `devise` | Devise de la ligne d'approvisionnement source (ou héritée du PU base si dérivé) |
| `devise_sigle` | Sigle prêt à afficher à côté du montant |

---

## 4. Affichage UI recommandé

```ts
function afficherPrix(row: { prix_vente_affiche: string; prix_manquant: boolean }) {
  if (row.prix_manquant) {
    return { text: '.....', className: 'text-muted' }; // jamais tarifé
  }
  return { text: formatMoney(row.prix_vente_affiche), className: '' };
}
```

- Colonne principale : `designation` + `article_id`
- Colonne prix : `prix_vente_affiche` (unité de base)
- Ligne expandable / sous-tableau : `conditionnements` (pièce, carton…)
- Badge / filtre : « Sans prix » → `?prix_manquant=true`
- Compteurs page : `resume.avec_prix` / `resume.sans_prix`

---

## 5. Types TypeScript suggérés

```ts
export interface TarificationDevise {
  id: number;
  sigle: string;
  symbole: string;
  nom: string;
}

export interface TarificationConditionnement {
  id: number;
  nom: string;
  multiplicateur_base: string;
  est_defaut: boolean;
  prix_vente_conditionnement: string | null;
  prix_vente_affiche: string; // "....." ou montant
  prix_manquant: boolean;
  date_dernier_prix: string | null;
  source_prix: 'ligne_entree' | 'derive_unitaire_base' | null;
  devise?: TarificationDevise | null;
  devise_sigle?: string | null;
}

export interface TarificationArticle {
  article_id: string;
  nom_scientifique: string;
  nom_commercial: string;
  designation: string;
  categorie: string | null;
  unite: { id: number; libelle: string } | null;
  unite_stock_base: string;
  succursale_id: number | null;
  stock_actuel: string | null;
  seuil_alerte: string | null;
  prix_vente_unitaire_base: string | null;
  prix_vente_affiche: string;
  prix_manquant: boolean;
  date_dernier_prix: string | null;
  source_prix: 'ligne_entree' | null;
  devise?: TarificationDevise | null;
  devise_sigle?: string | null;
  conditionnements: TarificationConditionnement[];
}

export interface TarificationResponse {
  rapport: 'tarification';
  count: number;
  next: string | null;
  previous: string | null;
  results: TarificationArticle[];
  resume: {
    nombre_articles: number;
    avec_prix: number;
    sans_prix: number;
    placeholder_prix: string;
  };
  instructions_frontend: {
    afficher_placeholder_prix: string;
    prix_null_si_jamais_approvisionne: boolean;
    conditionnements_inclus: boolean;
  };
}
```

---

## 6. Checklist FE

- [ ] Page `/tarification` (ou équivalent) branchée sur `GET /api/tarification/`
- [ ] Afficher **tous** les articles (pagination)
- [ ] Afficher `.....` quand `prix_manquant === true`
- [ ] Filtre « Sans prix » / recherche
- [ ] Afficher conditionnements (prix packing)
- [ ] Ne pas planter si `prix_vente_unitaire_base === null`
- [ ] Headers JWT + `Accept-Language` comme le reste de l’app

---

## 7. Notes

- Endpoint **lecture seule** : pas encore de PATCH pour modifier un prix hors approvisionnement.
- Plan SaaS : rattaché à la fonctionnalité `articles` (lecture autorisée si plan articles actif).
- Les montants sont des **strings décimales** (5 décimales), comme le reste de l’API stock.
