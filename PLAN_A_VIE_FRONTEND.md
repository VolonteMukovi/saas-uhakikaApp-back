# Plan « À vie » — Guide d’intégration Frontend

> **Date** : septembre 2026  
> **Backend** : formule `a_vie` + période `a_vie` + `date_fin = null`  
> **Objectif** : accès **permanent** à **toutes** les fonctionnalités UHAKIKAAPP (paiement unique)

---

## 1. Résumé pour l’équipe

| Élément | Valeur |
|---------|--------|
| Code formule | `a_vie` |
| Nom commercial | **À vie** |
| Période | `a_vie` (uniquement pour cette formule) |
| Prix | `prix_a_vie` (paiement **unique**, défaut seed **1999 USD**) |
| Expiration | **Aucune** (`date_fin: null`, `jours_restants: null`) |
| Fonctionnalités | **Toutes** (équivalent essai / Premium) |
| Quotas | Illimités (`utilisateurs_max` / `succursales_max` = `null`) |
| Essai 60 jours | **Inchangé** — le plan À vie est une offre séparée |

**Règle métier** : tant que `est_a_vie === true` et `est_actif === true`, l’utilisateur a **tous les droits métier** et **ne doit jamais** voir de bannière d’expiration / renouvellement.

---

## 2. Catalogue — nouveaux champs

### Endpoint

`GET /api/abonnements/formules/` (public, `AllowAny`)

### Champs formule (ajout)

| Champ | Type | Usage UI |
|-------|------|----------|
| `prix_mensuel` | number | Plans récurrents |
| `prix_annuel` | number | Plans récurrents |
| **`prix_a_vie`** | number | **À afficher pour `code === "a_vie"`** |
| `fonctionnalites` | object | Matrice features |
| `limites` | object | Quotas |

Exemple (extrait) :

```json
{
  "id": 5,
  "code": "a_vie",
  "nom": "À vie",
  "description": "Accès permanent à toutes les fonctionnalités UHAKIKAAPP, sans date d'expiration — un seul paiement.",
  "prix_mensuel": "0.00",
  "prix_annuel": "0.00",
  "prix_a_vie": "1999.00",
  "devise": "USD",
  "fonctionnalites": { "articles": true, "stock": true, "chatbot": true, "...": true },
  "limites": { "utilisateurs_max": null, "succursales_max": null },
  "ordre_affichage": 4
}
```

### Affichage carte catalogue (recommandé)

```ts
if (formule.code === 'a_vie') {
  // Afficher : prix_a_vie + devise + libellé « Paiement unique »
  // Masquer le toggle mensuel / annuel
  // Badge : « Accès permanent » / « Sans expiration »
} else {
  // Afficher prix_mensuel / prix_annuel selon le toggle période
}
```

---

## 3. État licence — nouveaux champs

### Endpoints

| Méthode | URL | Rôle |
|---------|-----|------|
| `GET` | `/api/abonnements/mon-abonnement/` | État licence courant |
| `GET` | `/api/inscription/flow/` (ou équivalent bootstrap/flow) | Guard + `statut_licence_frontend` |

### Champs importants dans `etat_licence`

| Champ | Type | Signification |
|-------|------|----------------|
| `est_actif` | boolean | Licence utilisable |
| `est_essai` | boolean | Essai 60 j |
| **`est_a_vie`** | boolean | **Licence permanente** |
| `statut` | string | `actif` \| `essai` \| `expire` \| … |
| `periode` | string | `a_vie` \| `mensuel` \| `annuel` \| `essai` |
| `formule_code` | string | ex. `a_vie` |
| `formule_nom` | string | ex. `À vie` |
| `date_fin` | ISO \| **`null`** | `null` = jamais |
| `jours_restants` | number \| **`null`** | `null` = illimité |
| `fonctionnalites` | object | Toutes à `true` si à vie actif |
| `limites` | object | Quotas `null` = illimité |
| `message` | string | Ex. « Licence à vie active — accès permanent… » |

Exemple réponse À vie active :

```json
{
  "a_licence": true,
  "abonnement_id": 42,
  "statut": "actif",
  "est_actif": true,
  "est_essai": false,
  "est_a_vie": true,
  "formule_code": "a_vie",
  "formule_nom": "À vie",
  "periode": "a_vie",
  "date_debut": "2026-09-07T13:00:00Z",
  "date_fin": null,
  "jours_restants": null,
  "fonctionnalites": { "vente_credit": true, "chatbot": true, "multi_succursales": true },
  "limites": { "utilisateurs_max": null, "succursales_max": null },
  "message": "Licence à vie active — accès permanent à toutes les fonctionnalités."
}
```

### Abonnement sérialisé (`POST /api/abonnements/demander/` réponse)

Nouveau champ read-only : **`est_a_vie`** (boolean).

---

## 4. Flow SaaS / guards

### Nouveau statut frontend

`statut_licence_frontend` peut valoir :

| Valeur | Signification |
|--------|----------------|
| `essai_actif` | Essai en cours |
| `actif` | Plan payant périodique actif |
| **`a_vie`** | **Plan à vie actif** |
| `licence_expiree` | Expiré → lecture seule + CTA renouveler |
| `pending_manual_activation` | Demande en attente |
| `suspendu` | Suspendu |
| `sans_abonnement` | Aucun abonnement |

### Règles UI recommandées

```ts
const estAVie =
  flow.statut_licence_frontend === 'a_vie' ||
  flow.etat_licence?.est_a_vie === true;

if (estAVie) {
  // ✅ Accès dashboard + opérations métier
  // ❌ Ne pas afficher countdown / jours restants
  // ❌ Ne pas afficher bannière « expire bientôt » / « renouveler »
  // ✅ Afficher badge « Licence à vie » (optionnel)
}

if (flow.etat_licence?.jours_restants == null && flow.etat_licence?.est_actif) {
  labelDuree = 'Illimité'; // ou 'À vie'
} else {
  labelDuree = `${flow.etat_licence.jours_restants} jours restants`;
}
```

`operations_metier_autorisees` et `licence_active` restent `true` pour un plan à vie actif (même logique que plan payant actif).

---

## 5. Souscription — API

### A) Demande manuelle (activation plateforme)

```http
POST /api/abonnements/demander/
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "formule_code": "a_vie",
  "periode": "a_vie"
}
```

- Si `formule_code = "a_vie"`, le backend **force** `periode = "a_vie"`.
- Montant du paiement créé = `prix_a_vie`.
- Statut initial : `en_attente` jusqu’à activation admin / confirmation paiement.
- Cet endpoint reste **autorisé même si la licence est expirée** (chemin exempté).

### B) Paiement en ligne

```http
POST /api/abonnements/paiements/initier/
Authorization: Bearer <jwt>

{
  "formule_code": "a_vie",
  "periode": "a_vie",
  "fournisseur": "maishapay"   // ou flexpay | serdi
}
```

`periode` accepte maintenant : `mensuel` | `annuel` | **`a_vie`**.

Après webhook confirmé → `statut: actif`, `date_fin: null`, `est_a_vie: true`.

### C) Toggle période UI

```ts
type PeriodeAbonnement = 'mensuel' | 'annuel' | 'a_vie';

function periodesDisponibles(formule: Formule): PeriodeAbonnement[] {
  if (formule.code === 'a_vie') return ['a_vie'];
  return ['mensuel', 'annuel'];
}

function prixAffiche(formule: Formule, periode: PeriodeAbonnement): number {
  if (periode === 'a_vie') return Number(formule.prix_a_vie);
  if (periode === 'annuel') return Number(formule.prix_annuel);
  return Number(formule.prix_mensuel);
}
```

---

## 6. Erreurs / licence expirée (rappel)

Si licence **expirée** (essai 60 j ou plan mensuel/annuel) :

- **GET** métier : OK (lecture seule)
- **POST/PUT/PATCH/DELETE** métier : `403` `application/problem+json`

```json
{
  "code": "licence_inactive",
  "detail": "Votre abonnement a expiré. Veuillez renouveler pour continuer.",
  "action_recommandee": "renouveler_abonnement",
  "url_renouvellement": "/api/abonnements/formules/"
}
```

Sur l’écran renouvellement, **proposer aussi la carte « À vie »** (paiement unique, fin des renouvellements).

Un plan **À vie actif** ne déclenche **jamais** ce 403 pour cause d’expiration.

---

## 7. Checklist intégration FE

- [ ] Lire `prix_a_vie` dans le catalogue
- [ ] Carte formule `code === "a_vie"` sans toggle mensuel/annuel
- [ ] CTA souscription : body `{ formule_code: "a_vie", periode: "a_vie" }`
- [ ] Paiement init : accepter `periode: "a_vie"`
- [ ] Gérer `est_a_vie` + `statut_licence_frontend === "a_vie"`
- [ ] Afficher « Illimité » / « À vie » si `jours_restants === null`
- [ ] Masquer bannières expiration / renouvellement si `est_a_vie`
- [ ] Page abonnement : badge « Accès permanent »
- [ ] Types TypeScript mis à jour (voir §8)

---

## 8. Types TypeScript suggérés

```ts
export type PeriodeAbonnement = 'essai' | 'mensuel' | 'annuel' | 'a_vie';

export type StatutLicenceFrontend =
  | 'sans_abonnement'
  | 'essai_actif'
  | 'actif'
  | 'a_vie'
  | 'licence_expiree'
  | 'pending_manual_activation'
  | 'suspendu'
  | string;

export interface FormuleAbonnement {
  id: number;
  code: string; // 'decouverte_pro' | 'essentiel' | 'croissance' | 'premium_entreprise' | 'a_vie'
  nom: string;
  description: string;
  prix_mensuel: string | number;
  prix_annuel: string | number;
  prix_a_vie: string | number; // nouveau
  devise: string;
  fonctionnalites: Record<string, boolean>;
  limites: {
    utilisateurs_max: number | null;
    succursales_max: number | null;
  };
  ordre_affichage: number;
}

export interface EtatLicence {
  a_licence: boolean;
  abonnement_id?: number | null;
  statut: string;
  est_actif: boolean;
  est_essai: boolean;
  est_a_vie?: boolean; // nouveau
  formule_code: string | null;
  formule_nom: string | null;
  periode?: PeriodeAbonnement | null;
  date_debut?: string | null;
  date_fin?: string | null; // null = permanent
  jours_restants?: number | null; // null = illimité
  fonctionnalites: Record<string, boolean>;
  limites: Record<string, number | null>;
  message: string;
}
```

---

## 9. Textes catalogue (référence)

| Ordre | Code | Nom | Modèle tarifaire |
|------:|------|-----|------------------|
| 0 | `decouverte_pro` | Découverte Pro | Essai 60 j (auto) |
| 1 | `essentiel` | Essentiel | Mensuel / annuel |
| 2 | `croissance` | Croissance | Mensuel / annuel |
| 3 | `premium_entreprise` | Premium Entreprise | Mensuel / annuel |
| 4 | **`a_vie`** | **À vie** | **Paiement unique** |

---

## 10. Contact backend

- Migration : `abonnements.0004_formule_a_vie_prix_periode`
- Seed : `python manage.py seed_formules_abonnement`
- Activation manuelle plateforme (ops) :  
  `python manage.py activer_acces_a_vie --entreprise-id=<ID>`

En cas de doute sur un champ, comparer avec `GET /api/abonnements/mon-abonnement/` après activation d’un compte de test À vie.
