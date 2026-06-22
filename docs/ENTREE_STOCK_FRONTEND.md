# Entrée en stock / Approvisionnement — Guide frontend

Spécification d’intégration pour la page **Entrée en stock** et la vue **Gestion des approvisionnements**.

> **Contexte dépôt :** ce fichier documente l’UI attendue et les appels API. Le code React/Vue/Angular vit dans le **projet frontend** ; ouvrez ce dépôt dans Cursor pour implémenter les composants.

---

## 1. Principes UX

| Règle | Détail |
|-------|--------|
| **Header principal** | Toujours visible (entreprise, agence, utilisateur, session, notifications). L’utilisateur ne doit pas avoir l’impression de quitter l’app. |
| **Sidebar** | Masquée **uniquement** sur la route « Entrée en stock » pour libérer l’espace horizontal. |
| **Chargement paresseux** | Sur la page saisie, **aucun** appel liste/stats/graphiques tant que l’utilisateur n’a pas cliqué sur **Voir les approvisionnements**. |

---

## 2. Structure visuelle

```text
┌─────────────────────────────────────────────────────────────┐
│ HEADER PRINCIPAL (toujours visible — ne pas masquer)        │
├─────────────────────────────────────────────────────────────┤
│ [sans sidebar]                                              │
│                                                             │
│ Entrée en stock                                             │
│ Sélectionnez des articles à gauche, complétez le panier.    │
│                                    [Voir les approvisionnements] │
│                                                             │
│ Informations générales (1 ligne, compacte)                  │
│ [Date opération] [Libellé] [Description] [Devise]           │
│                                                             │
│ ┌──────────────────────────┬──────────────────────────────┐ │
│ │ Produits / Recherche     │ Panier d’approvisionnement   │ │
│ │ (scroll indépendant)     │ (scroll indépendant)         │ │
│ │ Rechercher ou scanner…   │ Produit │ Qté │ P.Achat │ …  │ │
│ │ Liste produits           │ …                            │ │
│ └──────────────────────────┴──────────────────────────────┘ │
│                                                             │
│ Total général          [Enregistrer]  [Annuler]             │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 Informations générales (une seule ligne)

**Afficher :**

| Champ UI | Obligatoire | Notes |
|----------|-------------|-------|
| Date d’opération | Oui | Défaut : maintenant. Envoyée en `date_op` (ISO 8601). |
| Libellé | Oui | `libele` |
| Description | Non | `description` (texte court) |
| Devise | Oui | Sélection globale ; appliquée à **toutes** les lignes du panier (`devise_id`) |

**Ne pas afficher :**

| Champ | Raison |
|-------|--------|
| Référence | Générée par le serveur à l’enregistrement → `id` de l’entrée (afficher après succès, ex. « Réf. #42 »). |
| Attribuée à l’enregistrement | Non requis métier |
| Agence (select) | Provient du **contexte JWT** (`POST /api/auth/select-context/`) ; le backend pose `succursale_id` automatiquement |

### 2.2 Panier (zone principale droite)

Colonnes recommandées :

| Colonne | Comportement |
|---------|--------------|
| Produit | Nom + code article |
| Quantité | Éditable ; incrément si clic sur produit déjà présent |
| Prix d’achat | `prix_unitaire` — éditable |
| Prix de vente | `prix_vente` — éditable, > 0 |
| Seuil d’alerte | `seuil_alerte` |
| Lot | Avant enregistrement : n° de ligne client ; après enregistrement : `lignes[].id` (lot FIFO) |
| Date expiration | `date_expiration` (optionnel, `YYYY-MM-DD`) |
| Total ligne | `quantite × prix_unitaire` — recalcul auto |
| Supprimer | Retire la ligne du panier |

**Règles panier :**

- Clic produit (gauche) → ajoute ou `quantite + 1` si déjà présent
- Totaux ligne et **total général** recalculés côté client à chaque modification
- La devise du header est propagée sur chaque ligne au `POST`

### 2.3 Scrolls

| Zone | CSS suggéré |
|------|-------------|
| Liste produits | `overflow-y: auto`, hauteur = viewport − header − bandeau infos − footer actions |
| Panier | Idem, colonne droite |
| Infos générales + actions | `flex-shrink: 0` (fixes en haut / bas) |

---

## 3. Routing et layout

### Route saisie (page principale)

Exemple : `/stock/entree` ou `/approvisionnements/nouveau`

```tsx
// Pseudo-code layout
<AppShell showSidebar={false} showHeader={true}>
  <EntreeStockPage />
</AppShell>
```

- `showSidebar={false}` **uniquement** sur cette route
- `showHeader={true}` **obligatoire** (ne jamais utiliser un layout « fullscreen » qui cache le header)

### Route liste (lazy)

Exemple : `/stock/approvisionnements`

Ouverture **uniquement** au clic sur **Voir les approvisionnements**.

Titre : **Gestion des Approvisionnements**  
Sous-titre : *Gérez vos entrées de stock manuellement ou via import Excel*

À charger **à l’ouverture** de cette vue :

| Donnée | Endpoint |
|--------|----------|
| Liste entrées | `GET /api/entrees/?page=1&page_size=25` |
| Stats / graphiques | Endpoints déjà utilisés par votre dashboard stock (si existants) |
| Import Excel | `GET /api/import-excel/modele-approvisionnement/`, `POST /api/import-excel/import-approvisionnement/` |

**Ne pas** précharger ces endpoints sur la page saisie.

---

## 4. Appels API — page saisie

### 4.1 Au montage de la page saisie

| Appel | Quand | Endpoint |
|-------|-------|----------|
| Devises | Montage | `GET /api/devises/?page_size=200` |
| Recherche produits | Saisie utilisateur (debounce) | `GET /api/articles/search/?q={terme}&limit=50` |

**Ne pas** appeler : `GET /api/entrees/`, stats, graphiques.

### 4.2 Enregistrement

`POST /api/entrees/`

```json
{
  "libele": "Approvisionnement mars",
  "description": "Livraison fournisseur X",
  "date_op": "2026-06-21T14:30:00+02:00",
  "lignes": [
    {
      "article_id": "CAPE0001",
      "quantite": "10.00000",
      "prix_unitaire": "2.50000",
      "prix_vente": "3.50000",
      "seuil_alerte": "5.00000",
      "date_expiration": "2027-01-15",
      "devise_id": 1
    }
  ]
}
```

| Champ | Source UI |
|-------|-----------|
| `entreprise_id` / `succursale_id` | **Ne pas envoyer** — injectés par le backend depuis le JWT |
| `id` (référence) | Réponse `201` → afficher à l’utilisateur |
| `devise_id` | Même valeur sur toutes les lignes = devise sélectionnée dans le header |

**Réponse succès (`201`) :**

```json
{
  "id": 42,
  "libele": "Approvisionnement mars",
  "description": "Livraison fournisseur X",
  "date_op": "2026-06-21T12:30:00Z",
  "lignes": [ "..." ],
  "messages": [ "Ajout au stock existant de ..." ],
  "articles_traites": 3
}
```

**Erreurs fréquentes :**

| Code | Clé | Action UI |
|------|-----|-----------|
| 400 | `soldes_insuffisants` | Toast : solde caisse insuffisant pour la devise |
| 400 | `prix_vente` | Mettre en évidence la ligne concernée |
| 403 | `Contexte entreprise manquant` | Rediriger vers sélection de contexte |

### 4.3 Dernier prix d’achat (préremplissage)

Lors de l’ajout au panier, optionnel :

`GET /api/entrees/lots-par-article/{article_id}/`

Utiliser le dernier lot pour préremplir `prix_unitaire`, `prix_vente`, `seuil_alerte` (modifiables ensuite).

---

## 5. État React suggéré

```ts
type LignePanier = {
  key: string;              // uuid client
  article_id: string;
  designation: string;
  quantite: number;
  prix_unitaire: number;
  prix_vente: number;
  seuil_alerte: number;
  date_expiration?: string;
};

type EntreeForm = {
  date_op: string;
  libele: string;
  description: string;
  devise_id: number;
  lignes: LignePanier[];
};

// totalLigne = quantite * prix_unitaire
// totalGeneral = sum(totalLigne) — une devise à la fois si multi-devises interdites en UI
```

**Ajout produit :**

```ts
function addToCart(article: Article, cart: LignePanier[]) {
  const existing = cart.find(l => l.article_id === article.article_id);
  if (existing) {
    return cart.map(l =>
      l.article_id === article.article_id
        ? { ...l, quantite: l.quantite + 1 }
        : l
    );
  }
  return [...cart, {
    key: crypto.randomUUID(),
    article_id: article.article_id,
    designation: article.nom_commercial || article.nom_scientifique,
    quantite: 1,
    prix_unitaire: article.dernier_prix_achat ?? 0,
    prix_vente: article.dernier_prix_vente ?? 0,
    seuil_alerte: article.seuilAlert ?? 0,
  }];
}
```

---

## 6. Checklist implémentation frontend

- [ ] Header global toujours visible sur `/stock/entree`
- [ ] Sidebar masquée uniquement sur cette route
- [ ] Bandeau « Informations générales » sur **une ligne** (4 champs max)
- [ ] Pas de champs Référence / Agence / Attribuée à
- [ ] Grille 2 colonnes : produits (gauche) + panier (droite)
- [ ] Scrolls indépendants gauche / droite
- [ ] Panier : ajout, incrément, édition qté/prix, total ligne, total général, suppression
- [ ] `POST /api/entrees/` au clic Enregistrer ; afficher `id` comme référence
- [ ] Bouton « Voir les approvisionnements » → navigation lazy vers liste
- [ ] Aucun `GET /api/entrees/` au montage de la page saisie

---

## 7. Cohérence backend

| Besoin UI | Backend |
|-----------|---------|
| Référence auto | `Entree.id` (PK auto) |
| Agence implicite | `perform_create` → `succursale_id` depuis JWT |
| Date opération modifiable | `date_op` accepté au `POST` (ISO 8601) ; défaut serveur si absent |
| Devise par ligne | `lignes[].devise_id` ; le front duplique la devise du header |
| Impact stock + caisse | Automatique côté serveur après `POST` |

---

*Dernière mise à jour : juin 2026*
