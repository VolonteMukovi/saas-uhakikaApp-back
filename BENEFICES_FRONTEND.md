# Bénéfices / Gains / Pertes / CA — Guide d’intégration Frontend

> **Date** : septembre 2026  
> **Objectif** : voir quels **produits** génèrent des **gains** ou des **pertes**, le **chiffre d’affaires**, et **expliquer** chaque mouvement pour un article.

---

## 1. Endpoints

Base : `/api/benefices/`  
Auth : JWT staff + contexte entreprise.  
Période par défaut : **mois / année courants**.

| Méthode | URL | Rôle |
|---------|-----|------|
| `GET` | `/api/benefices/resume/` | Tableau de bord période (CA, gain, perte, performance) |
| `GET` | `/api/benefices/articles/` | Liste **tous** les produits avec CA / marge / statut |
| `GET` | `/api/benefices/articles/{article_id}/` | **Détail** : comment le produit a gagné ou perdu |

Paramètres communs de période / périmètre :

| Param | Type | Description |
|-------|------|-------------|
| `month` | 1–12 | Mois (défaut = courant) |
| `year` | int | Année (défaut = courant) |
| `succursale_id` | int | Optionnel (sinon branche JWT) |

---

## 2. Formules (backend)

Pour chaque enregistrement `BeneficeLot` (FIFO) :

```text
CA ligne        = prix_vente × quantite_vendue
Coût ligne      = prix_achat × quantite_vendue
Bénéfice ligne  = (prix_vente − prix_achat) × quantite_vendue
                = CA − Coût
```

- **Gain** si bénéfice ≥ 0  
- **Perte** si bénéfice < 0  
- Les ventes **`EN_CREDIT`** déficitaires sont **exclues** du total « perte » (pas définitives), mais restent visibles dans le détail article.

Origines possibles d’un mouvement :

| `origine.type` | Signification |
|----------------|---------------|
| `VENTE` | Vente payée |
| `VENTE_CREDIT` | Vente à crédit |
| `INVENTAIRE` | Ajustement inventaire (souvent PV=0 → perte au coût) |
| `AUTRE` | Sans sortie liée |

---

## 3. `GET /api/benefices/resume/`

### Exemple réponse

```json
{
  "rapport": "benefices_resume",
  "periode": { "annee": 2026, "mois": 9, "libelle": "2026-09" },
  "contexte": { "entreprise_id": 1, "succursale_id": null },
  "resume": {
    "chiffre_affaires": "15000.00000",
    "cout_achat": "11000.00000",
    "benefice_net": "4000.00000",
    "total_gain": "5200.00000",
    "total_perte": "1200.00000",
    "quantite_totale": "800.00000",
    "nombre_mouvements": 120,
    "nombre_mouvements_gagnants": 95,
    "nombre_mouvements_perdants": 20,
    "nombre_articles": 40
  },
  "performance": {
    "statut": "EXCELLENTE",
    "message": "Période profitable : bénéfice net 4000.00000.",
    "benefice_net": "4000.00000"
  },
  "gains": {
    "montant": "5200.00000",
    "chiffre_affaires": "14000.00000",
    "nombre_mouvements": 95
  },
  "pertes": {
    "montant": "1200.00000",
    "chiffre_affaires": "1000.00000",
    "nombre_mouvements": 20,
    "note": "Les ventes à crédit déficitaires sont exclues des pertes (non définitives)."
  }
}
```

### UI recommandée

- KPI cards : **CA**, **Bénéfice net**, **Total gains**, **Total pertes**
- Badge performance (`EXCELLENTE` | `NEUTRE` | `A_SURVEILLER` | `PREOCCUPANTE` | `CRITIQUE`)
- Sélecteur mois / année

---

## 4. `GET /api/benefices/articles/`

### Query params

| Param | Valeurs | Description |
|-------|---------|-------------|
| `filtre` | `tous` (défaut) \| `gains` \| `pertes` | Onglets |
| `search` / `q` | string | Code / nom article |
| `page` | int | Défaut 1 |
| `page_size` | int | Défaut 25, max 200 |
| `month`, `year`, `succursale_id` | — | Période / scope |

### Élément `results[]`

| Champ | Description |
|-------|-------------|
| `article_id`, `designation`, `unite` | Identité produit |
| `chiffre_affaires` | CA période |
| `cout_achat` | Coût des lots consommés |
| `benefice_net` | CA − coût (peut être négatif) |
| `total_gain` | Somme des mouvements ≥ 0 |
| `total_perte` | \|somme\| des mouvements < 0 (hors crédit) |
| `quantite_vendue` | Quantité sortie (unité de base) |
| `nombre_mouvements` | Nb de `BeneficeLot` |
| `statut` | `GAIN` \| `PERTE` \| `NEUTRE` |
| `marge_pourcent` | `benefice_net / CA × 100` ou `null` |

### UI recommandée

```
[ Tous ] [ Produits en gain ] [ Produits en perte ]
Tableau : Produit | CA | Coût | Bénéfice net | Marge % | Statut
Clic ligne → /benefices/articles/{article_id}
```

- `filtre=gains` → tri bénéfice décroissant  
- `filtre=pertes` → tri bénéfice croissant (pires pertes en premier)

---

## 5. `GET /api/benefices/articles/{article_id}/`

### En-tête `article` + `resume`

Même logique CA / coût / bénéfice net / statut pour **un** produit.

### `mouvements[]` — pourquoi gain ou perte

| Champ | Description |
|-------|-------------|
| `date` | Date calcul bénéfice |
| `quantite` | Qté sortie de ce lot |
| `prix_achat_unitaire` | Coût FIFO du lot |
| `prix_vente_unitaire` | Prix réellement encaissé (ou 0 inventaire) |
| `chiffre_affaires` | PV × qté |
| `cout_achat` | PA × qté |
| `benefice_unitaire` | PV − PA |
| `benefice_total` | (PV − PA) × qté |
| `statut` | `GAIN` \| `PERTE` \| `NEUTRE` |
| `explication` | Texte prêt à afficher (FR) |
| `origine` | `{ type, type_libelle, sortie_id, statut_sortie, motif, client_nom, date_sortie }` |

### Exemple d’explication (perte vente)

> « Vendu à 1.00000 sous le coût d'achat 1.50000 (écart -0.50000 / unité) — remise, sous-tarification ou lot cher. »

### Exemple d’explication (perte inventaire)

> « Ajustement inventaire : stock manquant valorisé au coût d'achat 1.50000 (perte 15.00000). »

### UI recommandée

1. En-tête produit + KPI (CA, bénéfice net, badge Gain/Perte)  
2. Timeline / tableau des mouvements  
3. Couleur verte / rouge selon `statut`  
4. Afficher `explication` sous chaque ligne (tooltip ou sous-texte)  
5. Lien éventuel vers la sortie : `origine.sortie_id`

---

## 6. Types TypeScript suggérés

```ts
export type BeneficeStatut = 'GAIN' | 'PERTE' | 'NEUTRE';
export type OrigineType = 'VENTE' | 'VENTE_CREDIT' | 'INVENTAIRE' | 'AUTRE';

export interface BeneficeResumeResponse {
  rapport: 'benefices_resume';
  periode: { annee: number; mois: number; libelle: string };
  resume: {
    chiffre_affaires: string;
    cout_achat: string;
    benefice_net: string;
    total_gain: string;
    total_perte: string;
    nombre_articles: number;
    // ...
  };
  performance: { statut: string; message: string; benefice_net: string };
  gains: { montant: string; chiffre_affaires: string; nombre_mouvements: number };
  pertes: { montant: string; chiffre_affaires: string; nombre_mouvements: number; note: string };
}

export interface BeneficeArticleRow {
  article_id: string;
  designation: string;
  chiffre_affaires: string;
  cout_achat: string;
  benefice_net: string;
  total_gain: string;
  total_perte: string;
  quantite_vendue: string;
  nombre_mouvements: number;
  statut: BeneficeStatut;
  statut_libelle: string;
  marge_pourcent: string | null;
}

export interface BeneficeMouvement {
  id: number;
  date: string | null;
  quantite: string;
  prix_achat_unitaire: string;
  prix_vente_unitaire: string;
  chiffre_affaires: string;
  cout_achat: string;
  benefice_unitaire: string;
  benefice_total: string;
  statut: BeneficeStatut;
  explication: string;
  origine: {
    type: OrigineType;
    type_libelle: string;
    sortie_id: number | null;
    statut_sortie: string | null;
    motif: string;
    client_nom?: string | null;
    date_sortie?: string | null;
  };
}
```

---

## 7. Checklist FE

- [ ] Page dashboard période → `GET /api/benefices/resume/`
- [ ] Onglets Tous / Gains / Pertes → `GET /api/benefices/articles/?filtre=…`
- [ ] Recherche produit
- [ ] Clic article → détail `GET /api/benefices/articles/{id}/`
- [ ] Afficher CA + bénéfice net + explication par mouvement
- [ ] Couleurs Gain (vert) / Perte (rouge)
- [ ] Sélecteur mois/année
- [ ] Montants en **string** décimale (ne pas parser en float naïf)

---

## 8. Compatibilité

L’ancien endpoint reste disponible :

`GET /api/entrees/benefices-totaux/?month=&year=`

Préférer la nouvelle API `/api/benefices/*` pour l’écran « produits qui gagnent / perdent ».

---

## 9. Plan SaaS

Lecture rattachée à la fonctionnalité **`statistiques`**.  
Si 403 `fonctionnalite_non_autorisee`, proposer un upgrade de formule.
