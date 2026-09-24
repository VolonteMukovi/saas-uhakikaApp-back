# Impression vente — Facture (crédit) vs Reçu (comptant)

## Règle métier

Après création / consultation d’une **sortie (vente)**, le document à afficher ou imprimer dépend uniquement de `sortie.statut` :

| `statut` | Mode | Document | Endpoints |
|----------|------|----------|-----------|
| `EN_CREDIT` | Vente à crédit | **FACTURE** (modèle inchangé) | PDF + print facture |
| `PAYEE` | Vente au comptant | **REÇU** | PDF + print reçu (`bon-pos`) |

Ne plus imprimer systématiquement la facture pour toutes les ventes.

---

## Endpoints

Base : `/api/sorties/{id}/`

### Aide au routage (recommandé)

```http
GET /api/sorties/{id}/document-vente/
```

Exemple réponse crédit :

```json
{
  "sortie_id": 42,
  "statut": "EN_CREDIT",
  "type_document": "FACTURE",
  "mode_paiement": "CREDIT",
  "pdf_url": "/api/sorties/42/facture-pos/",
  "print_url": "/api/sorties/42/facture-pos-print/"
}
```

Exemple réponse comptant :

```json
{
  "sortie_id": 43,
  "statut": "PAYEE",
  "type_document": "RECU",
  "mode_paiement": "COMPTANT",
  "pdf_url": "/api/sorties/43/bon-pos/",
  "print_url": "/api/sorties/43/bon-pos-print/"
}
```

### Documents

| Action | Méthode | URL | Usage |
|--------|---------|-----|--------|
| Aperçu PDF facture | `GET` | `/api/sorties/{id}/facture-pos/` | Crédit uniquement |
| Impression ESC/POS facture | `POST` | `/api/sorties/{id}/facture-pos-print/` | Crédit uniquement |
| Aperçu PDF reçu | `GET` | `/api/sorties/{id}/bon-pos/` | Comptant uniquement |
| Impression ESC/POS reçu | `POST` | `/api/sorties/{id}/bon-pos-print/` | Comptant uniquement |

Alias PDF reçu (inchangé) : `GET /api/sorties/{id}/bon-sortie-pos/` → même contenu que `bon-pos`.

---

## Adaptation UI (checklist)

1. Après vente (ou bouton « Imprimer » / « Voir ticket ») :
   - lire `statut` de la sortie **ou** appeler `GET …/document-vente/` ;
   - ouvrir / imprimer l’URL renvoyée (`pdf_url` ou `print_url`).
2. Libellés boutons suggérés :
   - crédit → « Voir facture » / « Imprimer facture » ;
   - comptant → « Voir reçu » / « Imprimer reçu ».
3. Ne pas forcer `facture-pos` sur une vente `PAYEE`.
4. Ne pas forcer `bon-pos` sur une vente `EN_CREDIT`.
5. PDF : ouvrir en nouvel onglet / viewer (`Content-Type: application/pdf`).
6. Print : `POST` → succès `{ "status": "impression lancée" }` ; gérer `501` (imprimante non configurée) et `500`.

### Pseudo-code

```ts
async function printVente(sortieId: number) {
  const doc = await api.get(`/api/sorties/${sortieId}/document-vente/`);
  // Aperçu PDF
  window.open(doc.pdf_url, '_blank');
  // Ou impression directe POS :
  // await api.post(doc.print_url);
}
```

Variante sans `document-vente` (si `statut` déjà connu) :

```ts
const isCredit = sortie.statut === 'EN_CREDIT';
const pdf = isCredit
  ? `/api/sorties/${id}/facture-pos/`
  : `/api/sorties/${id}/bon-pos/`;
const print = isCredit
  ? `/api/sorties/${id}/facture-pos-print/`
  : `/api/sorties/${id}/bon-pos-print/`;
```

---

## Contenu des tickets (info FE)

Les deux tickets partagent la **même source de données** (entreprise, client, lignes, devises, totaux, imprimé par).

Différences de libellés uniquement :

| Élément | Facture | Reçu |
|---------|---------|------|
| Titre | `FACTURE DE VENTE` | `RECU DE VENTE` |
| Numéro | `FACT-000042` | `REC-000042` |
| Mode | *(absent)* | `Mode: COMPTANT` |
| Total | `TOTAL DU` | `TOTAL RECU` |

Format : ticket 58 mm, monospace (identique à l’actuelle facture POS). **Ne pas** redessiner le layout côté front : afficher le PDF backend tel quel.

---

## Hors scope

- Reçus de **paiement de dette** (`caisse`) : inchangés.
- Bons d’**entrée** stock : inchangés.
- Aucun changement de modèle / dimensions de la facture crédit.
