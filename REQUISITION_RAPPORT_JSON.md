# Mise à jour — Rapports de réquisition en JSON (PDF côté frontend)

> **Date** : juillet 2026  
> **Périmètre** : génération des documents d’impression / export  
> **Inchangé** : toute la logique métier CRUD, workflow, suggestions, prix estimés

---

## 1. Décision d’architecture

| Couche | Responsabilité |
|--------|----------------|
| **Backend** | Données, calculs, totaux, historique → **JSON structuré** |
| **Frontend** | Mise en page, design, PDF, impression, thèmes, responsive |

Le backend **ne produit plus** :

- fichiers PDF
- HTML ReportLab
- styles, polices, marges, couleurs, tableaux graphiques

Le frontend est le **seul** responsable du rendu documentaire.

---

## 2. Endpoints

| Méthode | URL | Réponse |
|---------|-----|---------|
| `GET` | `/api/requisitions/{id}/document/` | **Endpoint principal** — JSON d’impression |
| `GET` | `/api/requisitions/{id}/pdf/` | **Alias** — même JSON (rétrocompatibilité, plus de binaire) |

`Content-Type` : `application/json`

Le détail métier (`GET /api/requisitions/{id}/`) reste inchangé pour l’écran d’édition.  
Le document d’impression ajoute l’enveloppe entreprise, les sections signatures et les instructions FE.

---

## 3. Structure du JSON

```json
{
  "rapport": "requisition",
  "titre": "Réquisition d'approvisionnement",
  "format": "json",
  "rendu": "frontend",
  "entreprise": { "...": "voir §3.1" },
  "agence": { "...": "succursale ou null" },
  "devise": { "sigle": "USD", "symbole": "$", "...": "..." },
  "requisition": { "...": "voir §3.2" },
  "lignes": [ { "...": "voir §3.3" } ],
  "resume": { "...": "voir §3.4" },
  "historique": [ { "...": "voir §3.5" } ],
  "sections_impression": { "...": "voir §3.6" },
  "instructions_frontend": {
    "generer_pdf": true,
    "generer_html": true,
    "backend_ne_genere_pas_pdf": true,
    "afficher_placeholder_prix": ".....",
    "sections_signatures_obligatoires": ["prepare_par", "valide_par", "reception"]
  },
  "metadata": {
    "generated_at": "ISO-8601",
    "generated_by": { "display_name": "..." },
    "session": { "entreprise_id": 1, "succursale_id": null }
  }
}
```

### 3.1 Entreprise (`entreprise`)

| Champ | Description |
|-------|-------------|
| `id`, `nom` | Identité |
| `logo_url` | URL absolue du logo (si présent) |
| `adresse`, `telephone`, `email` | Coordonnées |
| `slogan`, `nif` | En-tête rapports |
| `pays`, `secteur`, `responsable` | Infos complémentaires |
| `has_branches` | Booléen |

`agence` : succursale liée (`id`, `nom`, `adresse`, `telephone`, `email`) ou `null`.

### 3.2 Réquisition (`requisition`)

| Champ | Description |
|-------|-------------|
| `id`, `numero`, `reference` | `reference` = `numero` |
| `titre`, `description`, `observations`, `commentaires` | Textes |
| `priorite`, `priorite_libelle` | Ex. `HAUTE` / `Haute` |
| `statut`, `statut_libelle` | Ex. `VALIDEE` / `Validée` |
| `auteur` / `cree_par` | `{ id, username, full_name, display_name }` |
| `valide_par`, `rejete_par` | Idem |
| `motif_rejet`, `archived`, `succursale_id` | — |
| `dates.*` | ISO : `creation`, `modification`, `preparation`, `validation`, `rejet`, `cloture` |
| `dates_affichees.*` | Formats `dd/mm/YYYY HH:MM` pour affichage |

### 3.3 Lignes (`lignes[]`)

| Champ | Description |
|-------|-------------|
| `id`, `ordre`, `type_ligne`, `type_ligne_libelle` | `ARTICLE` ou `LIBRE` |
| `article` | `{ code, nom, nom_scientifique, nom_commercial }` |
| `code_article`, `designation`, `categorie`, `unite` | Catalogue / libre |
| `quantite_demandee`, `quantite_validee`, `quantite` | Validée remplie si statut `VALIDEE` / `CLOTUREE` |
| `prix_estimatif`, `prix_estimatif_affiche` | `null` → afficher `.....` |
| `prix_manquant`, `prix_source` | `DERNIER_ACHAT` \| `MANUEL` |
| `montant_estimatif`, `montant_estimatif_affiche` | Calculés backend |
| `commentaire` / `remarque` | — |
| `origine_suggestion` | `RUPTURE`, `ALERTE`, `CATALOGUE`, `MANUEL` |
| `statut_ligne` / `statut_stock` | Snapshot stock |
| `stock_actuel`, `seuil_alerte` | Contexte |

### 3.4 Résumé (`resume`)

- `nombre_articles`, `nombre_lignes`
- `quantite_totale`
- `montant_estimatif` / `montant_estime`
- `lignes_prix_manquants`, `montant_estime_complet`
- `statistiques` : `lignes_article`, `lignes_libres`, `lignes_rupture`, `lignes_alerte`, `prix_manquants`

### 3.5 Historique (`historique[]`)

Pour chaque événement :

- `action` (`CREATION`, `CHANGEMENT_STATUT`, `AJOUT_LIGNE`, …)
- `ancien_statut`, `nouveau_statut`
- `commentaire` / `detail`
- `utilisateur` (`display_name`, …)
- `date` (ISO), `date_affichee`
- `metadata` (JSON libre)

### 3.6 Sections d’impression (`sections_impression`)

Le frontend doit réserver ces zones dans le PDF :

```json
"sections_impression": {
  "prepare_par": {
    "nom": "Jean Dupont",
    "signature": null,
    "signature_placeholder": true,
    "date": "14/07/2026 10:00",
    "date_placeholder": false,
    "libelle_zone_signature": "Signature",
    "libelle_zone_date": "Date"
  },
  "valide_par": { "...": "idem, prérempli si validation" },
  "reception": {
    "nom": "",
    "signature": null,
    "signature_placeholder": true,
    "date": null,
    "date_placeholder": true
  },
  "observations_finales": {
    "texte_prerempli": "...",
    "zone_manuscrite": true,
    "hauteur_suggeree": "large",
    "placeholder": "Zone réservée aux observations manuscrites après impression."
  }
}
```

---

## 4. Contrat frontend — génération PDF

1. Appeler `GET /api/requisitions/{id}/document/`.
2. Ne **jamais** attendre un `application/pdf` binaire de cet endpoint.
3. Composer le document (HTML print / jsPDF / pdfmake / autre).
4. Inclure obligatoirement :
   - en-tête entreprise (`logo_url`, nom, adresse, contacts, nif, slogan) ;
   - corps réquisition + tableau lignes ;
   - totaux `resume` ;
   - blocs `sections_impression` (signatures + observations) ;
   - historique si besoin d’une annexe.
5. Afficher `prix_estimatif_affiche` / `montant_estimatif_affiche` tels quels (`.....` si manquant).
6. Thèmes clair/sombre, responsive et styles : **100 % frontend**.

### Boutons UI

Utiliser `actions_disponibles` du détail :

- `imprimer` → ouvrir preview / fenête d’impression basée sur le JSON
- `exporter_document` → générer et télécharger le PDF côté client

---

## 5. Migration depuis l’ancien endpoint PDF

| Avant | Après |
|-------|-------|
| `GET .../pdf/` → binaire ReportLab | `GET .../document/` → JSON |
| `Content-Type: application/pdf` | `application/json` |
| Backend dessinait le PDF | Frontend génère le PDF |

**Action FE obligatoire** : remplacer tout `iframe` / `window.open` sur `/pdf/` qui attendait un blob PDF par un appel JSON + moteur de rendu local.

L’URL `/pdf/` reste vivante temporairement mais **renvoie le même JSON** — ne pas s’y fier pour un téléchargement binaire.

---

## 6. Fichiers backend touchés

| Fichier | Rôle |
|---------|------|
| `stock/services/requisition_document.py` | Construction du payload JSON |
| `stock/requisition_views.py` | Actions `document` + alias `pdf` |
| ~~`stock/services/requisition_pdf.py`~~ | **Supprimé** (plus de ReportLab réquisition) |
| `REQUISITION_FRONTEND.md` | Doc CRUD globale (à croiser avec ce fichier) |

Logique métier (`requisition.py`, modèles, workflow) : **inchangée**.

---

## 7. Exemple d’appel

```http
GET /api/requisitions/12/document/
Authorization: Bearer <token>
```

```js
const res = await api.get(`/api/requisitions/${id}/document/`);
const doc = res.data; // JSON complet
await generatePdfFromRequisitionDocument(doc); // responsabilité FE
```

---

## 8. Checklist frontend

- [ ] Remplacer le viewer PDF binaire par un rendu à partir de `/document/`
- [ ] En-tête entreprise + logo
- [ ] Tableau lignes (ARTICLE / LIBRE, placeholder prix)
- [ ] Totaux + statistiques
- [ ] Signatures Préparé / Validé / Réception
- [ ] Zone observations manuscrites
- [ ] Impression navigateur + export PDF
- [ ] Thème clair / sombre cohérent avec l’app
- [ ] Mobile : aperçu lisible avant export

---

*Document de mise à jour — architecture rapports réquisition JSON-first.*
