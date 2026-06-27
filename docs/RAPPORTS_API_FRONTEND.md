# API Rapports — Guide complet frontend

Documentation de **tous les endpoints de rapports et statistiques** de UHAKIKAAPP.  
Le backend retourne des **données JSON** ; le frontend gère l’affichage, l’impression et l’export PDF/Excel.

**Base URL :** `http://127.0.0.1:8000/api/`  
**Swagger :** `/swagger/` · Schéma : `/swagger.json`

---

## 1. État de la migration (réponse courte)

| Question | Réponse |
|----------|---------|
| Tous les rapports métier sont-ils en JSON ? | **Oui** |
| Les anciens endpoints `.../pdf/` des rapports existent-ils encore ? | **Non — supprimés** |
| Le frontend doit-il appeler un PDF serveur pour les rapports ? | **Non** |
| Y a-t-il encore du PDF côté serveur ? | **Oui**, uniquement pour les **tickets POS** (factures, bons, reçus) — voir section 6 |

---

## 2. Tableau de migration : ancien → nouveau

### 2.1 Rapports métier (anciennement JSON + PDF)

| Rapport | Ancien JSON | Ancien PDF (supprimé) | **Nouveau endpoint** | Type réponse |
|---------|-------------|----------------------|----------------------|--------------|
| Inventaire | `GET /api/rapports/inventaire/` | `.../inventaire/pdf/` | **Même URL JSON** | `application/json` |
| Bon d'entrée (réquisition) | `GET /api/rapports/bon-entree/` | `.../bon-entree/pdf/` | **Même URL JSON** | `application/json` |
| Bon d'achat | `GET /api/rapports/bon-achat/` | `.../bon-achat/pdf/` | **Même URL JSON** | `application/json` |
| Dettes client (détail) | `GET /api/rapports/clients-dettes/` | `.../clients-dettes/pdf/` | **Même URL JSON** | `application/json` |
| Dettes générales | `GET /api/rapports/clients-dettes-general/` | `.../clients-dettes-general/pdf/` | **Même URL JSON** | `application/json` |
| Ventes | `GET /api/rapports/ventes/` | `.../ventes/pdf/` | **Même URL JSON** | `application/json` |
| Fiche stock | `GET .../fiche-stock/json/` | `GET .../fiche-stock/` (**retournait un PDF**) | **`GET .../fiche-stock/` → JSON** | `application/json` |
| Journal complet | *(n'existait pas)* | `GET /api/rapports/journal/` (**PDF uniquement**) | **`GET /api/rapports/journal/` → JSON** | `application/json` |
| État de caisse | `GET /api/mouvements-caisse/solde/` | `GET .../solde/pdf/` (**supprimé**) | **Même URL JSON** (enrichie) | `application/json` |

### 2.2 Rapports complémentaires (déjà JSON — inchangés)

Ces endpoints **n'ont jamais eu de PDF** ; ils restent identiques :

| Rapport | Endpoint | Rôle |
|---------|----------|------|
| Stats stock | `GET /api/stocks/stats/` | Agrégats rupture / alerte / expiration |
| Bénéfices totaux | `GET /api/entrees/benefices-totaux/` | Performance FIFO, top articles |
| Produits plus vendus | `GET /api/sorties/produits-plus-vendus/` | Classement best-sellers |
| Tableau de bord caisse | `GET /api/mouvements-caisse/tableau-bord/` | Dashboard multi-devises |
| Soldes simples | `GET /api/mouvements-caisse/soldes-simples/` | Widget soldes rapides |
| Mouvements par devise | `GET /api/mouvements-caisse/mouvements-par-devise/` | Derniers mouvements filtrés |
| Comparaison devises | `GET /api/mouvements-caisse/comparaison-devises/` | Métriques comparatives |
| Stats entreprise | `GET /api/entreprises/{id}/stats/` | Compteurs globaux |

### 2.3 Reçus, rapports et opérations — ne pas confondre

| Catégorie | Exemple | Type réponse | Usage frontend |
|-----------|---------|--------------|----------------|
| **Rapport métier** | `GET /api/rapports/clients-dettes/?client_id=CLI0001&is_special=all` | JSON enveloppé (`rapport`, `entreprise`, `details`…) | Écran rapport, export PDF/Excel **côté client** avec `?complet=true` |
| **Reçu JSON** | `GET /api/paiements-dettes/{id}/recu-json/` | JSON document (`document`, `client`, `paiement`, `dette`, `pdf_url`) | Impression personnalisée, aperçu avant impression |
| **Reçu / ticket PDF** | `GET /api/paiements-dettes/{id}/recu-paiement/` | `application/pdf` (blob) | Impression directe POS / ouverture nouvel onglet |
| **Opération métier** | `POST /api/paiements-dettes/` | JSON (`201`) — enregistrement du paiement | Formulaire « payer une dette » ; puis appeler `recu-json` ou `recu-paiement` |
| **Liste paiements d'une dette** | `GET /api/dettes/{id}/paiements/` | JSON paginé | Historique des paiements sur une dette |

> **`is_special`** : attribut du lien **`ClientEntreprise`**, pas du modèle `Client` seul. Dans les rapports dettes, utiliser `?is_special=all` pour consulter n'importe quel client du tenant.

### 2.4 Documents POS (PDF serveur — hors rapports métier)

| Document | Endpoint | Type | Action frontend |
|----------|----------|------|-----------------|
| Facture POS | `GET /api/sorties/{id}/facture-pos/` | PDF | Afficher / imprimer le blob PDF |
| Bon sortie POS | `GET /api/sorties/{id}/bon-pos/` | PDF | Idem |
| Bon sortie (alt.) | `GET /api/sorties/{id}/bon-sortie-pos/` | PDF | Idem |
| Bon entrée POS | `GET /api/entrees/{id}/bon-pos/` | PDF | Idem |
| Bon caisse POS | `GET /api/mouvements-caisse/{id}/bon-pos/` | PDF | Idem |
| Reçu paiement dette (PDF) | `GET /api/paiements-dettes/{id}/recu-paiement/` | PDF | Idem |
| Reçu paiement dette (JSON) | `GET /api/paiements-dettes/{id}/recu-json/` | JSON | Même contenu métier, rendu côté front |
| Export CSV caisse | `GET /api/mouvements-caisse/export/` | CSV | Téléchargement fichier |

---

## 3. Changements globaux à connaître (tous rapports métier)

### 3.1 Avant (ancien fonctionnement)

```
GET /api/rapports/ventes/?...
  → Option A : JSON brut (données partielles, pas d'en-tête unifié)
  → Option B : GET .../ventes/pdf/ → fichier PDF généré serveur (ReportLab)
```

- En-tête entreprise : clé `entete.entreprise.logo_path` (chemin disque serveur — **inutilisable** côté navigateur)
- Métadonnées : `meta_generation.printed_at`, `printed_by` (parfois absentes du JSON)
- Pas de bloc `agence` / `session` structuré
- Le frontend ouvrait souvent le PDF dans un nouvel onglet ou téléchargeait le fichier

### 3.2 Maintenant (nouveau fonctionnement)

```
GET /api/rapports/ventes/?...
  → JSON complet avec enveloppe standard
  → Le frontend construit le tableau, les cartes KPI, et génère le PDF localement si besoin
```

| Ancien champ | Nouveau champ | Note |
|--------------|---------------|------|
| `entete.entreprise.nom` | `entreprise.nom` | Objet enrichi (adresse, NIF, email…) |
| `entete.entreprise.logo_path` | `entreprise.logo_url` | **URL HTTP absolue** utilisable dans `<img>` |
| `meta_generation` | `metadata` | ISO 8601 + objet `generated_by` + `session` |
| `statistiques` / `resume_global` | `resume` | Normalisé en tête d'enveloppe |
| `totaux_globaux` / `totaux_encours` | `totaux` | Normalisé en tête d'enveloppe |
| *(absent)* | `rapport` | Identifiant technique (`ventes`, `inventaire`…) |
| *(absent)* | `agence` | Succursale courante |
| *(absent)* | `devise` | Devise principale structurée |
| *(absent)* | `filtres` | Paramètres réellement appliqués |
| Lignes (`articles`, `lignes_ventes`…) | + `details` | **Alias unifié** pour les tableaux |

### 3.3 Paramètre `complet` (remplace le mode PDF)

| Avant | Maintenant |
|-------|------------|
| Appeler `.../pdf/` pour avoir **toutes** les lignes | `?complet=true` sur l'endpoint JSON |
| JSON paginé pour l'écran | `?page=1&page_size=25` (défaut) |

### 3.4 Structure URL `/api/rapports/`

Les rapports métier et le journal partagent le préfixe **`/api/rapports/`** (deux routers Django fusionnés) :

```
/api/rapports/inventaire/          ← module rapports (RapportsViewSet)
/api/rapports/clients-dettes/      ← idem
/api/rapports/journal/             ← module stock (RapportViewSet)
/api/rapports/{article_id}/fiche-stock/
```

> Ancienne doc erronée : `/api/rapports/rapports/...` — **n'existe pas**.

---

## 4. Authentification et contexte

```http
Authorization: Bearer <access_token>
```

```http
POST /api/auth/select-context/
Content-Type: application/json

{ "entreprise_id": 1, "succursale_id": 2 }
```

- **Admin** et **Agent** : accès aux rapports métier
- **SuperAdmin** : pas d'accès aux rapports métier
- Scoping automatique : entreprise JWT + succursale agent

---

## 5. Enveloppe JSON standard

Tous les rapports de la section 2.1 retournent cette structure racine :

```json
{
  "rapport": "ventes",
  "titre": "RAPPORT DES VENTES (Période)",
  "periode": { "date_debut": "2026-01-01", "date_fin": "2026-01-31" },
  "entreprise": {
    "id": 1,
    "nom": "Uhakika App",
    "logo_url": "http://localhost:8000/media/logos/logo.png",
    "telephone": "+243...",
    "slogan": "...",
    "has_branches": true
  },
  "agence": { "id": 2, "nom": "Uhakika Bunia" },
  "devise": { "id": 1, "sigle": "USD", "est_principal": true },
  "filtres": {},
  "resume": {},
  "totaux": {},
  "metadata": {
    "generated_at": "2026-06-21T14:30:00+00:00",
    "generated_at_display": "21/06/2026 14:30",
    "generated_by": {
      "id": 5,
      "username": "admin",
      "full_name": "Jean Dupont",
      "display_name": "Jean Dupont"
    },
    "session": {
      "entreprise_id": 1,
      "succursale_id": 2,
      "membership_id": 3,
      "language": "fr"
    }
  },
  "details": []
}
```

**Recommandation :** lire `details` pour les tableaux ; conserver les clés historiques (`lignes_ventes`, `articles`…) en repli.

---

## 6. Détail rapport par rapport (ancien → nouveau)

> **Inventaire physique (opérationnel) :** [docs/INVENTAIRE_API.md](INVENTAIRE_API.md) — sessions, comptage, validation, ajustements tracés.

---

### 6.1 Rapport d'inventaire

| | |
|---|---|
| **Avant JSON** | `GET /api/rapports/inventaire/` — JSON avec `entete`, `articles`, `statistiques` |
| **Avant PDF** | `GET .../inventaire/pdf/` — fichier A4 téléchargé |
| **Maintenant** | `GET /api/rapports/inventaire/` — **Rapport d'inventaire** JSON enveloppé, **PDF supprimé** |
| **Changement endpoint** | URL JSON **inchangée** ; supprimer tout appel à `/pdf/` |

**Deux modes :**

| Mode | Paramètre | Contenu |
|------|-----------|---------|
| **catalogue** | *(défaut)* | Fiche préparatoire : `stock_theorique` = stock actuel, `stock_physique` / `ecart` = `null` |
| **session** | `session_id={id}` | Session opérationnelle : comptage, écarts, statuts ligne complets |

**Paramètres :**

| Param | Défaut | Description |
|-------|--------|-------------|
| `session_id` | — | Rapport lié à une session `/api/inventaires/` (statut ≠ `BROUILLON`) |
| `date_debut`, `date_fin` | Exercice courant | `YYYY-MM-DD` (mode catalogue) |
| `filtrer_mouvements` | `false` | `true` = articles avec mouvements dans la période |
| `type_article` | — | Filtre libellé type |
| `statut` | — | Filtre stock : `NORMAL`, `ALERTE`, `RUPTURE` |
| `statut_ligne` | — | Filtre comptage (mode session) : `NON_COMPTÉ`, `CONFORME`, `ECART_POSITIF`, `ECART_NEGATIF` |
| `seulement_en_stock` | `false` | `true` = exclure quantité 0 (mode catalogue) |
| `complet` | `true` | `false` → pagination (`page_size` max 5000) |

**Statuts de référence (`statuts` dans la réponse) :**

| Famille | Codes |
|---------|--------|
| **Stock** (`statut_stock_code`) | `NORMAL`, `ALERTE`, `RUPTURE` |
| **Ligne inventaire** (`statut_ligne_code`) | `NON_APPLICABLE` (catalogue), `NON_COMPTÉ`, `CONFORME`, `ECART_POSITIF`, `ECART_NEGATIF` |
| **Session** (`session.statut`) | `BROUILLON`, `EN_COURS`, `VALIDE`, `ANNULE` |

**Lignes (`details` / `articles`) — colonnes rapport d'inventaire :**

| Colonne UI | Champs JSON |
|------------|-------------|
| Stock logiciel | `stock_theorique`, `quantite`, `quantite_stock`, `Qte` |
| Stock physique | `stock_physique` (`null` en mode catalogue) |
| Écart | `ecart` (`null` en mode catalogue) |
| Statut stock | `statut_stock_code`, `statut_stock` (alias `statut_code`, `statut`) |
| Statut ligne | `statut_ligne_code`, `statut_ligne` |
| P.U. / Total | `pu`, `prix_unitaire`, `total`, `prix_total` |
| Motif | `motif_ligne` (mode session) |

**`resume` / `statistiques` :**

| Champ | Description |
|-------|-------------|
| `total_articles`, `normaux`, `en_alerte`, `en_rupture` | Synthèse statuts stock |
| `lignes_comptees`, `lignes_non_comptees` | Progression comptage (session) |
| `ecarts_positifs`, `ecarts_negatifs`, `ecarts_nuls`, `conformes` | Synthèse écarts (session) |

**Exemples :**

```http
GET /api/rapports/inventaire/?seulement_en_stock=true
GET /api/rapports/inventaire/?session_id=1
GET /api/rapports/inventaire/?session_id=1&statut_ligne=ECART_NEGATIF
```

---

### 6.2 Bon d'entrée (réquisition)

| | |
|---|---|
| **Avant JSON** | `GET .../bon-entree/` — liste paginée, `entete` |
| **Avant PDF** | `GET .../bon-entree/pdf/` — PDF avec colonnes vides à remplir ; param `extra_articles`, `lang` |
| **Maintenant** | `GET .../bon-entree/` — JSON enveloppé avec **calculs automatiques** |
| **Changement endpoint** | URL JSON **inchangée** ; stock, PU et montants calculés par l'API |

**Paramètres :**

| Param | Description |
|-------|-------------|
| `inclure_normaux` | `true` = inclure stock normal |
| `extra_articles` | IDs virgule (`PRLI0007,ID2`) — force liste complète |
| `complet` | `true` = sans pagination |
| `page`, `page_size` | Pagination standard |

**Lignes (`details` / `articles`) — colonnes calculées :**

| Colonne UI | Champs JSON | Calcul |
|------------|-------------|--------|
| Stock actuel | `stock_actuel`, `quantite_en_stock`, `quantite_stock`, `quantite`, `Qte` | `Stock.Qte` |
| Qté à commander | `quantite_a_commander` | Jusqu'au seuil : `seuil − stock` si stock &lt; seuil |
| Dernier P.U. achat | `dernier_prix`, `pu`, `prix_unitaire` | Dernière `LigneEntree` |
| Montant estimé | `montant_estime`, `prix_total`, `total` | `quantite_a_commander × dernier_prix` |
| Statut | `statut_code`, `statut_stock` | `NORMAL` / `ALERTE` / `RUPTURE` |

**`totaux` :** `montant_estime_total`, `quantite_a_commander_total`  
**`statistiques` :** `total_articles`, `en_rupture`, `en_alerte`, + totaux ci-dessus

---

### 6.3 Bon d'achat

| | |
|---|---|
| **Avant JSON** | `GET .../bon-achat/` — paginé ; `for_pdf=true` côté serveur pour le PDF |
| **Avant PDF** | `GET .../bon-achat/pdf/` — toutes les lignes en PDF |
| **Maintenant** | `GET .../bon-achat/?complet=true` — toutes les lignes en JSON |
| **Changement endpoint** | URL JSON **inchangée** ; utiliser `complet=true` au lieu de `/pdf/` |

**Paramètres :**

| Param | Obligatoire | Description |
|-------|-------------|-------------|
| `entree_id` | Non* | Filtre par N° entrée |
| `date_debut` | Oui** | `YYYY-MM-DD` |
| `date_fin` | Non | Fin période |
| `article_id` | Non | Filtre article |
| `complet` | Non | Liste intégrale |

\* Si `entree_id` fourni, dates non requises.

**Lignes (`details` / `achats`) :**

| Colonne UI | Champs JSON |
|------------|-------------|
| Qté achetée | `quantite` |
| P.U. achat | `prix_unitaire`, `pu` |
| Total ligne | `prix_total`, `total`, `montant_ligne` |
| Devise | `devise_sigle` (si ≠ devise principale) |

Autres champs : `numero_entree`, `date_entree`, `libelle_entree`, `article_id`, `designation`, `unite`, `date_expiration`

**`recapitulatif` :** totaux par devise — `nombre_lignes` (nombre de lignes), `total_montant` (chaîne formatée)

**`totaux` / `statistiques` :** `montant_total` (global), `total_lignes`, `nombre_entrees`

**Extras :** `entree_details` (si `entree_id`)

---

### 6.4 Dettes client (détail)

| | |
|---|---|
| **Avant JSON** | `GET .../clients-dettes/?client_id=CLI0001` — `entete`, `clients`, `totaux_encours` |
| **Avant PDF** | `GET .../clients-dettes/pdf/?client_id=...` — même données en PDF |
| **Maintenant** | `GET .../clients-dettes/?client_id=CLI0001` — JSON enveloppé |
| **Changement endpoint** | URL **inchangée** ; `client_id` toujours **obligatoire** |

**Filtre `is_special` :** absent = spéciaux uniquement ; `true` / `false` / `all`

**Structure :** un client dans `details` / `clients`, chaque dette avec `sortie.produits[]`, montants, `devise`, dates, `statut`.

**`totaux` :** `montant_total`, `montant_paye`, `solde_restant`

---

### 6.5 Dettes générales (synthèse)

| | |
|---|---|
| **Avant JSON** | `GET .../clients-dettes-general/` — liste clients + totaux (pagination) |
| **Avant PDF** | `GET .../clients-dettes-general/pdf/` |
| **Maintenant** | `GET .../clients-dettes-general/` — JSON enveloppé |
| **Changement important** | `totaux` / `totaux_globaux` = agrégat **toute la période**, pas seulement la page |

**Paramètres :** `date_debut`, `date_fin`, `is_special`, `page`, `page_size`

**Lignes :** `id`, `nom`, `telephone`, `totaux_encours` (sans détail dettes individuelles)

---

### 6.6 Rapport des ventes

| | |
|---|---|
| **Avant JSON** | `GET .../ventes/` - pilotage principal par dates |
| **Maintenant** | `GET .../ventes/` - **pilotage principal par session** |
| **Changement endpoint** | URL **inchang?e** ; logique m?tier d?plac?e vers la session |

**Param?tres principaux :**

- `session_id=12`
- `session_numero=SESS-2026-00012`

**Comportement par d?faut :**

- sans param?tre de session, le backend charge automatiquement la **session ouverte** du contexte courant ;
- si aucune session ouverte n'existe, l'API retourne une r?ponse JSON vide avec un message explicite ;
- une session s?lectionn?e manuellement est accept?e **quel que soit son statut**.

**Filtres compl?mentaires :**

- `client_id`, `client_nom`, `reference`
- `statut_paiement` (`COMPTANT`|`CREDIT`)
- `montant_min`, `montant_max`
- `agence_id` / `succursale_id`
- `page`, `page_size`
- `complet=true`

**Lignes (`details` / `lignes_ventes`) :** `sortie_id`, `ligne_id`, `date`, `client`, `client_id`, `statut_paiement`, `article`, `article_id`, `pu_achat`, `pu_vente`, `quantite`, `montant_ligne`, `benefice`, `reference`

**Nouveaux blocs m?tier :**

- `session` : session utilis?e pour le rapport
- `ventes` : ventes group?es par sortie, avec leurs lignes
- `totaux` : `total_comptant`, `total_credit`, `total_general`, `total_quantite`, `total_benefice`

**`resume` :** `nombre_ventes`, `total_clients`, `sorties_comptant`, `sorties_credit`, `total_comptant`, `total_credit`, `total_general`, `total_quantite`, `total_benefice`

**Exemples :**

```http
GET /api/rapports/ventes/
GET /api/rapports/ventes/?session_id=12&page=1&page_size=25
GET /api/rapports/ventes/?session_numero=SESS-2026-00012&statut_paiement=CREDIT
```

Voir aussi : **`docs/RAPPORT_VENTES_PAR_SESSION.md`**

---

### 6.7 Fiche de stock (article)

| | |
|---|---|
| **Avant JSON** | `GET .../{article_id}/fiche-stock/json/` |
| **Avant PDF** | `GET .../{article_id}/fiche-stock/` → **PDF** (c'était l'URL principale) |
| **Maintenant** | `GET .../{article_id}/fiche-stock/` → **JSON** |
| **Changement endpoint** | **URL principale = JSON** ; `/json/` conservé comme alias rétrocompatibilité |

**Paramètres :** `date_min`, `date_max`

**`article_details` :** identité article, stock, seuil, `prix_vente_reference`

**Lignes (`details` / `mouvements`) :** `datetime`, `designation`, `entree` / `sortie` / `stock` (quantité, PU, PT)

**`solde_final` :** `quantite`, `valeur`

---

### 6.8 Journal complet des opérations

| | |
|---|---|
| **Avant** | `GET /api/rapports/journal/` → **PDF uniquement** (pas de JSON) |
| **Maintenant** | `GET /api/rapports/journal/` → **JSON** |
| **Changement endpoint** | **Même URL**, `Content-Type` passé de `application/pdf` à `application/json` |

**Paramètres :**

| Param | Description |
|-------|-------------|
| `month`, `year` | Mois calendaire (défaut : courant) |
| `date_min`, `date_max` | Plage personnalisée |
| `complet` | `true` = toutes les opérations |
| `page`, `page_size` | Pagination (défaut si pas `complet`) |

**Types d'opérations :** `APPROVISIONNEMENT`, `VENTE`, `CAISSE_ENTREE`, `CAISSE_SORTIE`, `PAIEMENT_DETTE`

**Lignes (`details` / `operations`) :** `date`, `date_display`, `type`, `type_display`, `designation`, `montant_texte`, `montants_par_devise`, `ref`, `source_id`, `client`…

**`resume` :** compteurs par type + `total_operations`

---

### 6.9 État de caisse

| | |
|---|---|
| **Avant JSON** | `GET /api/mouvements-caisse/solde/` — soldes par devise (minimal) |
| **Avant PDF** | `GET .../solde/pdf/` — PDF état caisse |
| **Maintenant** | `GET /api/mouvements-caisse/solde/` — JSON enrichi (enveloppe partielle) |
| **Changement endpoint** | URL JSON **inchangée** ; `/solde/pdf/` **supprimé** |

**Paramètres (filtres mouvements) :** `type`, `date_min`, `date_max`

**Réponse :** `rapport: "etat-caisse"`, `entreprise`, `agence`, `metadata`, `resume`, `details` / `soldes_par_devise`

**Chaque devise :** `devise_sigle`, `solde`, `total_entrees`, `total_sorties`, `nb_mouvements`, `est_principale`

---

## 7. Rapports complémentaires (JSON — détail)

Ces endpoints étaient **déjà en JSON** avant la migration. Ils n'utilisent pas l'enveloppe `rapport` / `metadata` standard (sauf état caisse ci-dessus).

### 7.1 Stats stock — `GET /api/stocks/stats/`

```json
{
  "total": 150,
  "normal": 120,
  "alerte": 20,
  "faible": 5,
  "rupture": 5,
  "sum_statuts": 150,
  "by_code": { "NORMAL": 120, "ALERTE": 20, ... },
  "expiration_sous_30_jours": 3,
  "expiration_periode_30_jours": { ... },
  "expiration_sous_3_mois": 8,
  "expiration_periode": { ... }
}
```

### 7.2 Bénéfices totaux — `GET /api/entrees/benefices-totaux/`

**Params :** `month`, `year` (défaut : mois courant)

```json
{
  "resume": {
    "benefice_total": "1500.00",
    "total_gain": "2000.00",
    "total_perte": "500.00",
    "nombre_lots_gagnants": 45,
    "nombre_lots_perdants": 5,
    "taux_reussite": "90.00000%"
  },
  "performance": {
    "statut": "EXCELLENTE",
    "message": "..."
  },
  "benefices_par_article": [ { "article_id", "nom", "benefice_total", "nombre_lots" } ],
  "details": { "entreprise_id", "succursale_id", "mois", "annee", "periode" }
}
```

### 7.3 Produits plus vendus — `GET /api/sorties/produits-plus-vendus/`

**Params :** `date_debut`, `date_fin`, `mois`, `annee`, `limit` (défaut 10), `general=true`

```json
{
  "periode": { "type": "mois", "description": "Janvier 2026" },
  "statistiques": {
    "nombre_produits": 10,
    "total_quantite_vendue": 500,
    "total_chiffre_affaires": "12000.00"
  },
  "produits": [
    {
      "rang": 1,
      "article_id": "ART001",
      "nom_scientifique": "...",
      "nombre_ventes": 85,
      "quantite_vendue": 120,
      "chiffre_affaires": "3600.00"
    }
  ]
}
```

> Classement par **nombre de ventes** (fois vendu), pas par quantité totale.

### 7.4 Tableau de bord caisse — `GET /api/mouvements-caisse/tableau-bord/`

Dashboard riche : `resume_global`, `devises[]` avec soldes, mouvements récents, ratios, `statut_solde`.

### 7.5 Soldes simples — `GET /api/mouvements-caisse/soldes-simples/`

Widget léger : `{ "soldes": [{ "sigle", "solde", "statut" }], "devise_principale" }`

### 7.6 Mouvements par devise — `GET /api/mouvements-caisse/mouvements-par-devise/`

**Params :** `devise=USD`, `limit=20`

### 7.7 Comparaison devises — `GET /api/mouvements-caisse/comparaison-devises/`

Métriques comparatives entre devises actives.

### 7.8 Stats entreprise — `GET /api/entreprises/{id}/stats/`

```json
{
  "nombre_utilisateurs": 5,
  "nombre_articles": 200,
  "nombre_sorties": 1500,
  "nombre_entrees": 80,
  "valeur_stock": 45000
}
```

---

## 7.9 Paiements de dettes (opérations + reçus)

Ce bloc n'est **pas** un rapport métier : ce sont des **écritures** et des **documents de paiement**.

| Action | Méthode | Endpoint | Réponse |
|--------|---------|----------|---------|
| Lister / créer paiements | `GET` / `POST` | `/api/paiements-dettes/` | JSON (liste paginée / `201` création) |
| Paiements d'une dette | `GET` | `/api/dettes/{id}/paiements/` | JSON paginé |
| Reçu structuré | `GET` | `/api/paiements-dettes/{id}/recu-json/` | JSON document |
| Reçu ticket POS | `GET` | `/api/paiements-dettes/{id}/recu-paiement/` | PDF blob |

**Flux après paiement :**

```
POST /api/paiements-dettes/  →  { "id": 42, ... }
GET  /api/paiements-dettes/42/recu-json/     → impression personnalisée
GET  /api/paiements-dettes/42/recu-paiement/ → PDF serveur (POS)
```

**Exemple `recu-json` (extrait) :**

```json
{
  "document": "recu_paiement_dette",
  "titre": "REÇU DE PAIEMENT",
  "format": "json",
  "entreprise": { "nom": "...", "logo_url": "..." },
  "agence": { "id": 1, "nom": "..." },
  "client": { "id": "CLI0001", "nom": "...", "is_special": false },
  "dette": { "montant_total": "100.00000", "solde_restant": "50.00000", "statut": "EN_COURS" },
  "paiement": { "id": 42, "montant": "50.00000", "date": "..." },
  "pdf_url": "http://127.0.0.1:8000/api/paiements-dettes/42/recu-paiement/"
}
```

---

## 8. Documents POS (PDF serveur — inchangés)

Le frontend **continue** d'appeler ces URLs pour obtenir un blob PDF (ou `recu-json` pour le reçu dette) :

| Document | Endpoint PDF | Endpoint JSON (si dispo) |
|----------|--------------|--------------------------|
| Facture client | `GET /api/sorties/{id}/facture-pos/` | — |
| Bon de sortie | `GET /api/sorties/{id}/bon-pos/` | — |
| Bon sortie (variante) | `GET /api/sorties/{id}/bon-sortie-pos/` | — |
| Bon d'entrée | `GET /api/entrees/{id}/bon-pos/` | — |
| Bon mouvement caisse | `GET /api/mouvements-caisse/{id}/bon-pos/` | — |
| Reçu paiement dette | `GET /api/paiements-dettes/{id}/recu-paiement/` | `GET .../recu-json/` |

```javascript
// Exemple affichage PDF POS
const res = await fetch(`/api/sorties/${id}/facture-pos/`, {
  headers: { Authorization: `Bearer ${token}` }
});
const blob = await res.blob();
const url = URL.createObjectURL(blob);
window.open(url);
```

---

## 9. Guide de migration frontend (checklist)

### À supprimer dans le code frontend

- [ ] Tous les appels `fetch('.../inventaire/pdf/')` et équivalents
- [ ] `fetch('.../solde/pdf/')`
- [ ] Ouverture directe du journal en PDF (`/api/rapports/journal/` attendait du PDF)
- [ ] Utilisation de `entete.entreprise.logo_path`
- [ ] Dépendance à `meta_generation` (utiliser `metadata`)

### À mettre à jour

- [ ] Fiche stock : pointer vers `/fiche-stock/` (plus le PDF sur cette URL)
- [ ] Journal : parser JSON au lieu d'un blob PDF
- [ ] En-têtes rapports : `entreprise.logo_url`, `agence.nom`, `metadata.generated_by`
- [ ] Tableaux : lire `details` (avec repli sur clé historique)
- [ ] Export / impression : `?complet=true` puis génération PDF client (jsPDF, react-pdf…)

### Flux type écran rapport

```
1. Utilisateur choisit filtres
2. GET /api/rapports/{rapport}/?params
3. Afficher entreprise + agence + titre + période (depuis enveloppe)
4. Cartes KPI depuis resume + totaux
5. Tableau depuis details (+ pagination)
6. Bouton Exporter → GET ?complet=true → export local
```

---

## 10. Erreurs courantes

| Code | Exemple | Cause |
|------|---------|-------|
| 400 | `{ "detail": "..." }` | Dates invalides, période ventes manquante |
| 400 | `{ "error": "client_id obligatoire" }` | Paramètre requis absent |
| 401 | — | Token absent / expiré |
| 403 | — | Rôle non autorisé |
| 404 | `{ "error": "Client non trouvé ou hors du périmètre..." }` | Rapport dettes : client standard sans `?is_special=all` |
| 404 | `POST /api/paiements-dettes/` | Route absente — vérifier que `stock/urls.py` enregistre `paiements-dettes` |

---

## 11. Récapitulatif URLs

### Rapports métier (enveloppe standard)

| Rapport | URL |
|---------|-----|
| Inventaire | `GET /api/rapports/inventaire/` |
| Réquisition | `GET /api/rapports/bon-entree/` |
| Bon d'achat | `GET /api/rapports/bon-achat/` |
| Dettes client | `GET /api/rapports/clients-dettes/` |
| Dettes générales | `GET /api/rapports/clients-dettes-general/` |
| Ventes | `GET /api/rapports/ventes/` |
| Fiche stock | `GET /api/rapports/{article_id}/fiche-stock/` |
| Journal | `GET /api/rapports/journal/` |
| État caisse | `GET /api/mouvements-caisse/solde/` |

### Statistiques complémentaires (JSON)

| Rapport | URL |
|---------|-----|
| Stats stock | `GET /api/stocks/stats/` |
| Bénéfices | `GET /api/entrees/benefices-totaux/` |
| Top ventes | `GET /api/sorties/produits-plus-vendus/` |
| Dashboard caisse | `GET /api/mouvements-caisse/tableau-bord/` |
| Soldes widgets | `GET /api/mouvements-caisse/soldes-simples/` |
| Mvts par devise | `GET /api/mouvements-caisse/mouvements-par-devise/` |
| Comparaison devises | `GET /api/mouvements-caisse/comparaison-devises/` |
| Stats entreprise | `GET /api/entreprises/{id}/stats/` |

### Paiements dettes (opérations + reçus)

| Action | URL |
|--------|-----|
| Lister / créer | `GET` / `POST /api/paiements-dettes/` |
| Par dette | `GET /api/dettes/{id}/paiements/` |
| Reçu JSON | `GET /api/paiements-dettes/{id}/recu-json/` |
| Reçu PDF | `GET /api/paiements-dettes/{id}/recu-paiement/` |

---

*Dernière mise à jour : juin 2026 — Migration rapports JSON-only terminée. URLs corrigées : `/api/rapports/...` (plus de double `rapports/`).*
