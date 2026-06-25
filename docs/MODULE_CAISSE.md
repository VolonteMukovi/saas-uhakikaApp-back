# Module Caisse — Documentation complète

Guide de référence unique pour l’application Django **`caisse`** : architecture, règles métier, API, scénarios, erreurs, rapports et intégration frontend.

**Base URL API :** `/api/` (préfixe commun avec `stock`, `order`, etc.)

**Authentification :** JWT + contexte entreprise / agence (`tenant_id`, `branch_id` sur la requête).

---

## Table des matières

1. [Vue d’ensemble](#1-vue-densemble)
2. [Architecture technique](#2-architecture-technique)
3. [Modèles de données](#3-modèles-de-données)
4. [Règles métier fondamentales](#4-règles-métier-fondamentales)
5. [Caisses (`TypeCaisse`)](#5-caisses-typecaisse)
6. [Sessions de caisse](#6-sessions-de-caisse)
7. [Mouvements de caisse](#7-mouvements-de-caisse)
8. [Paiements de dettes clients](#8-paiements-de-dettes-clients)
9. [Écarts et ajustements](#9-écarts-et-ajustements)
10. [Intégration avec les autres modules](#10-intégration-avec-les-autres-modules)
11. [Rapports et tableaux de bord](#11-rapports-et-tableaux-de-bord)
12. [Catalogue des erreurs](#12-catalogue-des-erreurs)
13. [Scénarios pas à pas](#13-scénarios-pas-à-pas)
14. [Migration et données historiques](#14-migration-et-données-historiques)
15. [Checklist frontend](#15-checklist-frontend)
16. [Référence rapide des endpoints](#16-référence-rapide-des-endpoints)

---

## 1. Vue d’ensemble

Le module **caisse** centralise tout ce qui touche à l’**argent réel** dans Uhakika :

- **Caisse** : canal physique ou virtuel (cash, banque, Airtel Money, M-Pesa, etc.)
- **Session de caisse** : période d’activité entre ouverture et clôture pour **une** caisse précise
- **Mouvement de caisse** : entrée ou sortie d’argent, toujours rattachée à une caisse et (pour les nouvelles opérations) à une session ouverte

### Principe directeur

> **Toute opération qui implique de l’argent doit sélectionner une caisse active et passer par une session ouverte pour cette caisse.**

Le backend **refuse** l’opération si le frontend oublie d’envoyer la caisse ou si aucune session n’est ouverte.

### Historique préservé

L’application a démarré sans multi-caisse. Les migrations ont :

- créé une **Caisse principale** (`CASH`) par entreprise / agence ;
- rattaché les anciens mouvements à cette caisse ;
- créé des sessions `LEGACY-*` clôturées pour l’historique (`est_legacy=true`).

**Aucune donnée existante n’a été supprimée.**

---

## 2. Architecture technique

### Application Django `caisse`

| Fichier / dossier | Rôle |
|-------------------|------|
| `caisse/models.py` | `TypeCaisse`, `SessionCaisse`, `MouvementCaisse`, `DetailMouvementCaisse`, `EcartCaisse` |
| `caisse/services/caisse.py` | `creer_mouvement_caisse()` — point d’entrée unique des mouvements |
| `caisse/services/session_caisse.py` | Ouverture, clôture, écarts, rapports session, `get_session_ouverte_for_caisse()` |
| `caisse/services/caisse_defaut.py` | Caisse cash par défaut, validation caisse |
| `caisse/services/operation_helpers.py` | Extraction `type_caisse_id` depuis les payloads |
| `caisse/views.py` | API caisses, mouvements, paiements dettes |
| `caisse/session_views.py` | API sessions de caisse |
| `caisse/serializers.py` | Sérialisation REST |
| `caisse/signals.py` | Caisse auto à la création entreprise/succursale ; statut dette après paiement |
| `caisse/urls.py` | Routes sous `/api/` |

### Tables en base

Les modèles utilisent `db_table = 'stock_*'` pour **conserver les tables existantes** (`stock_typecaisse`, `stock_mouvementcaisse`, etc.) après extraction de l’app `stock`.

### Compatibilité imports

Pour le code legacy :

```python
from stock.models import MouvementCaisse, TypeCaisse  # réexporte depuis caisse
from stock.services.caisse import creer_mouvement_caisse
```

---

## 3. Modèles de données

### 3.1 `TypeCaisse` (la caisse)

Représente un **canal d’argent** de l’entreprise.

| Champ | Type | Description |
|-------|------|-------------|
| `id` | int | Identifiant (utilisé comme `type_caisse_id` dans l’API) |
| `nom` | string | Nom affiché (ex. « Caisse principale ») |
| `libelle` | string | Libellé court (ex. « Caisse cash physique ») |
| `code_type` | enum | `CASH`, `BANQUE`, `AIRTEL_MONEY`, `MPESA`, `ORANGE_MONEY`, `MOBILE_MONEY`, `AUTRE` |
| `description` | text | Optionnel |
| `image` | fichier | Optionnel |
| `entreprise` | FK | Entreprise propriétaire |
| `succursale` | FK | Agence (nullable) |
| `devise` | FK | Devise principale de la caisse |
| `is_active` | bool | Caisse utilisable ou non |
| `est_defaut` | bool | Caisse cash par défaut (créée automatiquement) |
| `created_at` | datetime | Date de création |

**Note :** le nom technique du modèle reste `TypeCaisse` pour compatibilité ; dans l’UI, parlez de **« Caisse »**.

### 3.2 `SessionCaisse`

| Champ | Description |
|-------|-------------|
| `numero` | Unique, auto (`SESS-0001-000001`) |
| `type_caisse` | Caisse concernée |
| `devise` | Devise de la session |
| `entreprise`, `succursale` | Contexte tenant |
| `ouvert_par`, `cloture_par` | Utilisateurs |
| `ouvert_le`, `cloture_le` | Horodatage serveur |
| `solde_ouverture` | Fond de caisse initial |
| `total_entrees`, `total_sorties` | Calculés à la clôture |
| `solde_theorique` | `solde_ouverture + entrées − sorties` |
| `montant_physique` | Comptage réel à la clôture |
| `ecart_montant` | `montant_physique − solde_theorique` |
| `statut` | Voir ci-dessous |
| `est_legacy` | Session historique migrée |

**Statuts de session :**

| Code | Signification |
|------|----------------|
| `OUVERTE` | Opérations financières autorisées |
| `CLOTUREE_EN_ATTENTE_VALIDATION` | Écart constaté, validation admin requise |
| `CLOTUREE` | Terminée, lecture seule |
| `ANNULEE` | Annulée (rare) |

### 3.3 `MouvementCaisse`

| Champ | Description |
|-------|-------------|
| `date` | Auto à la création |
| `montant` | Toujours positif |
| `devise` | Devise du mouvement |
| `type` | `ENTREE` ou `SORTIE` |
| `motif` | Libellé |
| `moyen` | Cash, Mobile Money, etc. (optionnel) |
| `type_caisse` | **Caisse** (obligatoire pour nouvelles ops avec montant > 0) |
| `session_caisse` | Session (résolue automatiquement) |
| `categorie` | Origine métier (voir tableau) |
| `sortie`, `entree` | Liens stock si applicable |
| `content_type` + `object_id` | Lien générique (ex. dette client) |
| `utilisateur` | Qui a effectué l’opération |
| `reference_piece` | Référence métier (`VENT-123-USD`, etc.) |

**Catégories (`categorie`) :**

| Code | Déclenché par |
|------|----------------|
| `VENTE` | Vente comptant (`Sortie` PAYEE) |
| `PAIEMENT_DETTE` | Paiement client sur dette |
| `APPROVISIONNEMENT` | Entrée stock payée cash |
| `DEPENSE` | Dépense manuelle |
| `ENTREE_MANUELLE` | Entrée caisse manuelle |
| `SORTIE_MANUELLE` | Sortie caisse manuelle |
| `AJUSTEMENT_SURPLUS_CAISSE` | Écart surplus validé |
| `AJUSTEMENT_PERTE_CAISSE` | Écart perte validé |
| `AUTRE` | Défaut |

### 3.4 `EcartCaisse`

Lié 1–1 à une session en attente de validation.

| Champ | Description |
|-------|-------------|
| `type_ecart` | `SURPLUS` ou `PERTE` |
| `montant` | Valeur absolue |
| `statut` | `EN_ATTENTE_VALIDATION`, `VALIDE`, `REJETE`, `ANNULE` |
| `mouvement_ajustement` | Mouvement créé après validation admin |

### 3.5 `DetailMouvementCaisse` (legacy)

Ancien format « multicaisse » (plusieurs lignes par mouvement). Les **nouveaux** mouvements n’en créent plus ; l’historique reste lisible via `motif_affiche()`.

---

## 4. Règles métier fondamentales

### 4.1 Double verrou : caisse + session

Pour chaque opération avec **montant > 0** :

```
1. type_caisse_id fourni (ou caisse_id / caisse)
2. Caisse existe, active, bonne entreprise/agence
3. Devise compatible avec la caisse (si devise caisse définie)
4. Session OUVERTE pour (caisse + agence + devise)
5. Pour SORTIE : solde session suffisant
```

Fonction centrale : **`get_session_ouverte_for_caisse(type_caisse, succursale_id, devise_id)`**  
Fichier : `caisse/services/session_caisse.py`

Création mouvement : **`creer_mouvement_caisse(...)`**  
Fichier : `caisse/services/caisse.py`

### 4.2 Exceptions (pas de caisse requise)

| Cas | Raison |
|-----|--------|
| Vente `EN_CREDIT` avec montant caisse = 0 | Pas d’encaissement immédiat |
| `skip_session_check=True` | Ajustements système internes (validation écart) |

### 4.3 Une session par caisse × agence × devise

On ne peut pas ouvrir deux sessions `OUVERTE` pour le même triplet `(type_caisse_id, succursale_id, devise_id)`.

### 4.4 Caisse par défaut automatique

| Événement | Action |
|-----------|--------|
| Création `Entreprise` | Signal → `Caisse principale` / `CASH` / `est_defaut=true` |
| Création `Succursale` | Signal → caisse par défaut pour l’agence |
| Migration données | Anciens mouvements sans caisse → caisse par défaut |

### 4.5 Interdictions

- Supprimer un mouvement (`DELETE /api/mouvements-caisse/{id}/` → **403/400**)
- Désactiver la caisse `est_defaut=true`
- Clôturer sans être en statut `OUVERTE`
- Valider un écart sans être **admin**

---

## 5. Caisses (`TypeCaisse`)

### 5.1 Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/types-caisse/` | Liste |
| `POST` | `/api/types-caisse/` | Créer |
| `GET` | `/api/types-caisse/{id}/` | Détail |
| `PUT/PATCH` | `/api/types-caisse/{id}/` | Modifier |
| `DELETE` | `/api/types-caisse/{id}/` | Supprimer |
| `GET` | `/api/types-caisse/actives/` | Caisses actives (UI) |
| `GET` | `/api/types-caisse/{id}/rapport-general/` | Synthèse caisse |
| `GET` | `/api/types-caisse/{id}/rapport-detaille/` | Détail caisse |

### 5.2 Filtres liste

```
GET /api/types-caisse/?actives_only=true
GET /api/types-caisse/?code_type=AIRTEL_MONEY
GET /api/types-caisse/?succursale_id=2
```

### 5.3 Créer une caisse

**Requête :**

```http
POST /api/types-caisse/
Content-Type: application/json
Authorization: Bearer <token>
```

```json
{
  "nom": "Airtel Money boutique",
  "libelle": "Airtel Money",
  "code_type": "AIRTEL_MONEY",
  "description": "Compte Airtel agence centre-ville",
  "devise_id": 1,
  "succursale": 2,
  "is_active": true
}
```

**Réponse 201 (exemple) :**

```json
{
  "id": 5,
  "nom": "Airtel Money boutique",
  "libelle": "Airtel Money",
  "code_type": "AIRTEL_MONEY",
  "code_type_display": "Airtel Money",
  "description": "Compte Airtel agence centre-ville",
  "entreprise": 1,
  "succursale": 2,
  "devise": { "id": 1, "sigle": "USD", "symbole": "$", "est_principal": true },
  "is_active": true,
  "est_defaut": false,
  "created_at": "2026-06-24T10:00:00Z"
}
```

### 5.4 Alias API pour l’identifiant caisse

Dans tous les payloads, ces clés sont équivalentes :

| Clé acceptée | Exemple |
|--------------|---------|
| `type_caisse_id` | `3` |
| `caisse_id` | `3` |
| `caisse` | `3` |

---

## 6. Sessions de caisse

### 6.1 Endpoints

| Action | Méthode | URL |
|--------|---------|-----|
| Lister | `GET` | `/api/sessions-caisse/` |
| Détail | `GET` | `/api/sessions-caisse/{id}/` |
| Session(s) active(s) | `GET` | `/api/sessions-caisse/active/` |
| **État caisse (source de vérité UI)** | `GET` | `/api/caisse/session-active/` |
| Ouvrir | `POST` | `/api/sessions-caisse/ouvrir/` |
| Clôturer | `POST` | `/api/sessions-caisse/{id}/cloturer/` |
| Valider écart | `POST` | `/api/sessions-caisse/{id}/valider-ecart/` |
| Rapport général | `GET` | `/api/sessions-caisse/{id}/rapport-general/` |
| Rapport détaillé | `GET` | `/api/sessions-caisse/{id}/rapport-detaille/` |
| Procès-verbal | `GET` | `/api/sessions-caisse/{id}/proces-verbal/` |

Filtres liste : `?statut=OUVERTE`, `?devise_id=`, `?type_caisse_id=`

### 6.2 Ouvrir une session

**Toujours pour une caisse précise** (pas de session « globale »).

```http
POST /api/sessions-caisse/ouvrir/
```

```json
{
  "type_caisse_id": 1,
  "devise_id": 1,
  "solde_ouverture": "150.00000"
}
```

**Réponse 201 :**

```json
{
  "id": 42,
  "numero": "SESS-0001-000042",
  "type_caisse": { "id": 1, "nom": "Caisse principale", "libelle": "Caisse cash physique", "code_type": "CASH" },
  "devise": { "id": 1, "sigle": "USD" },
  "statut": "OUVERTE",
  "ouvert_le": "2026-06-24T08:00:00Z",
  "solde_ouverture": "150.00000",
  "totaux_courants": {
    "total_entrees": "0.00000",
    "total_sorties": "0.00000",
    "solde_theorique": "150.00000",
    "nombre_mouvements": 0
  }
}
```

### 6.3 Vérifier session active (frontend — source de vérité)

**Endpoint recommandé :**

```http
GET /api/caisse/session-active/?devise_id=1&type_caisse_id=1
```

Alias acceptés : `caisse_id` à la place de `type_caisse_id`.

**Session ouverte :**

```json
{
  "is_open": true,
  "ouverte": true,
  "session": {
    "id": 42,
    "numero": "SESS-0001-000042",
    "statut": "OUVERTE",
    "type_caisse_id": 1,
    "devise_id": 1,
    "caisse_id": 1,
    "caisse": "Caisse principale",
    "devise": "USD",
    "date_ouverture": "2026-06-24T08:00:00Z",
    "solde_ouverture": "150.00000",
    "solde_actuel": "150.00000",
    "type_caisse": { "id": 1, "nom": "Caisse principale", "code_type": "CASH" },
    "totaux_courants": { "solde_theorique": "150.00000", ... }
  },
  "sessions": [ ... ]
}
```

**Aucune session :**

```json
{
  "is_open": false,
  "ouverte": false,
  "session": null,
  "sessions": []
}
```

**Compatibilité :** `GET /api/sessions-caisse/active/` renvoie le **même format canonique** (`is_open`, `session` normalisée avec `type_caisse_id` / `devise_id` plats).

Sans filtre devise :

```http
GET /api/caisse/session-active/
```

Retourne toutes les sessions ouvertes du contexte ; `session` = la plus récente, `sessions` = liste complète.

### 6.3.1 Double ouverture (409)

Si une session est déjà ouverte pour la même caisse / agence / devise :

```http
POST /api/sessions-caisse/ouvrir/
```

**Réponse 409 :**

```json
{
  "code": "SESSION_ALREADY_OPEN",
  "detail": "Une session de caisse est déjà ouverte pour cette caisse, cette agence et cette devise.",
  "is_open": true,
  "ouverte": true,
  "session": { ... },
  "sessions": [ ... ]
}
```

Le frontend doit recharger l'état (`is_open: true`) au lieu d'afficher « Caisse fermée ».

### 6.4 Clôturer une session

```http
POST /api/sessions-caisse/42/cloturer/
```

```json
{
  "montant_physique": "487.50000",
  "commentaire": "Comptage fin de journée — 2 pièces de 1 USD manquantes"
}
```

**Calcul serveur :**

```text
solde_theorique = solde_ouverture + Σ entrées − Σ sorties
ecart           = montant_physique − solde_theorique
```

| Écart | Statut session | Suite |
|-------|----------------|-------|
| `0` | `CLOTUREE` | Fin |
| `> 0` (surplus) | `CLOTUREE_EN_ATTENTE_VALIDATION` | `EcartCaisse` type `SURPLUS` |
| `< 0` (perte) | `CLOTUREE_EN_ATTENTE_VALIDATION` | `EcartCaisse` type `PERTE` |

### 6.5 Valider un écart (admin)

```http
POST /api/sessions-caisse/42/valider-ecart/
```

**Accepter l’écart :**

```json
{
  "valider": true,
  "commentaire": "Écart confirmé après recomptage superviseur"
}
```

→ Crée un mouvement `AJUSTEMENT_SURPLUS_CAISSE` (entrée) ou `AJUSTEMENT_PERTE_CAISSE` (sortie)  
→ Session passe à `CLOTUREE`

**Rejeter l’écart :**

```json
{
  "valider": false,
  "commentaire": "Recomptage nécessaire"
}
```

→ Session repasse à `OUVERTE` (clôture annulée)

---

## 7. Mouvements de caisse

### 7.1 Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/mouvements-caisse/` | Liste |
| `POST` | `/api/mouvements-caisse/` | Créer (entrée/sortie manuelle) |
| `GET` | `/api/mouvements-caisse/{id}/` | Détail |
| `GET` | `/api/mouvements-caisse/resume/` | Stats par devise |
| `GET` | `/api/mouvements-caisse/solde/` | État de caisse |
| `GET` | `/api/mouvements-caisse/tableau-bord/` | Dashboard multi-devises |
| `GET` | `/api/mouvements-caisse/soldes-simples/` | Widget soldes |
| `GET` | `/api/mouvements-caisse/mouvements-par-devise/` | Filtre par devise |
| `GET` | `/api/mouvements-caisse/comparaison-devises/` | Comparaison devises |
| `GET` | `/api/mouvements-caisse/export/` | Export CSV |
| `GET` | `/api/mouvements-caisse/{id}/bon-pos/` | Ticket PDF POS |

**Pas de `DELETE`** — historique financier protégé.

### 7.2 Filtres liste

```
GET /api/mouvements-caisse/?type=ENTREE
GET /api/mouvements-caisse/?date_min=2026-06-01&date_max=2026-06-30
GET /api/mouvements-caisse/?type_caisse_id=1
GET /api/mouvements-caisse/?caisse_id=1
GET /api/mouvements-caisse/?session_caisse_id=42
```

### 7.3 Créer un mouvement manuel

```http
POST /api/mouvements-caisse/
```

```json
{
  "type": "SORTIE",
  "montant": "25.00000",
  "devise_id": 1,
  "type_caisse_id": 1,
  "motif": "Transport marchandises",
  "moyen": "Cash",
  "reference_piece": "DEP-2026-061"
}
```

Le backend :

1. valide la caisse ;
2. trouve la session ouverte ;
3. vérifie le solde (pour `SORTIE`) ;
4. enregistre le mouvement avec `categorie=ENTREE_MANUELLE` ou `SORTIE_MANUELLE`.

**Réponse 201 :** objet mouvement avec `session_caisse`, `type_caisse`, `categorie`, `resume`, etc.

---

## 8. Paiements de dettes clients

Les paiements passent par **`MouvementCaisse`** de type `ENTREE` lié à `DetteClient` (content_type).

### 8.1 Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/api/paiements-dettes/` | Liste paiements |
| `POST` | `/api/paiements-dettes/` | Enregistrer paiement |
| `GET` | `/api/paiements-dettes/{id}/` | Détail |
| `GET` | `/api/paiements-dettes/{id}/recu-json/` | Reçu JSON (impression frontend) |
| `GET` | `/api/paiements-dettes/{id}/recu-paiement/` | Reçu PDF POS |

Liste des paiements d’une dette : `GET /api/dettes/{id}/paiements/`

### 8.2 Enregistrer un paiement

```http
POST /api/paiements-dettes/
```

```json
{
  "dette_id": 12,
  "montant_paye": "50.00000",
  "type_caisse_id": 1,
  "devise_id": 1,
  "moyen": "Cash",
  "reference": "RECU-CLIENT-45"
}
```

**Réponse 201 :**

```json
{
  "id": 891,
  "dette": { "id": 12, "client_nom": "Jean Mukendi" },
  "montant_paye": "50.00000",
  "date_paiement": "2026-06-24T14:30:00Z",
  "moyen": "Cash",
  "type_caisse": { "id": 1, "nom": "Caisse principale", "code_type": "CASH" },
  "session_caisse": 42,
  "mouvement_caisse_id": 891
}
```

Le signal `sync_dette_apres_mouvement_caisse` recalcule automatiquement le **statut** de la dette (`EN_COURS`, `PAYEE`, `RETARD`).

---

## 9. Écarts et ajustements

### Flux complet

```text
Session OUVERTE
    ↓ opérations (ventes, dépenses, …)
Clôture avec montant_physique
    ↓
écart = 0 ?  → CLOTUREE
écart ≠ 0 ?  → CLOTUREE_EN_ATTENTE_VALIDATION + EcartCaisse
    ↓
Admin valide (valider=true)
    ↓
Mouvement ajustement sur LA MÊME caisse
    ↓
Session CLOTUREE
```

### Exemple chiffré

| Étape | Valeur |
|-------|--------|
| Solde ouverture | 100 USD |
| Entrées (ventes) | +400 USD |
| Sorties (dépenses) | −50 USD |
| Solde théorique | 450 USD |
| Montant physique compté | 455 USD |
| Écart | +5 USD (SURPLUS) |

Après validation admin → entrée `AJUSTEMENT_SURPLUS_CAISSE` de 5 USD sur la caisse cash.

---

## 10. Intégration avec les autres modules

Les modules **stock** et **order** appellent `creer_mouvement_caisse()` et exigent `type_caisse_id` dans le body.

### 10.1 Tableau des flux

| Opération métier | Endpoint | Champ caisse | Type mouvement |
|----------------|----------|--------------|----------------|
| Vente comptant | `POST /api/sorties/` | `type_caisse_id` | `ENTREE` |
| Vente crédit | `POST /api/sorties/` (`EN_CREDIT`) | Non requis (montant 0) | `ENTREE` 0 |
| Annulation vente | `DELETE /api/sorties/{id}/` | `type_caisse_id` | `SORTIE` |
| Ajustement vente | `PATCH /api/sorties/{id}/` | `type_caisse_id` | `ENTREE` ou `SORTIE` |
| Approvisionnement cash | `POST /api/entrees/` | `type_caisse_id` | `SORTIE` |
| Annulation entrée | `DELETE /api/entrees/{id}/` | `type_caisse_id` | `ENTREE` |
| Ajustement entrée | `PATCH /api/entrees/{id}/` | `type_caisse_id` | `ENTREE` ou `SORTIE` |
| Livraison commande | `PATCH /api/commandes/{id}/` (`LIVREE`) | `type_caisse_id` | `ENTREE` |
| Import Excel appro | `POST /api/import-excel/...` | `type_caisse_id` (form) | `SORTIE` |
| Mouvement manuel | `POST /api/mouvements-caisse/` | `type_caisse_id` | selon `type` |
| Paiement dette | `POST /api/paiements-dettes/` | `type_caisse_id` | `ENTREE` |

### 10.2 Exemple vente comptant

```http
POST /api/sorties/
```

```json
{
  "statut": "PAYEE",
  "type_caisse_id": 1,
  "client": 5,
  "lignes": [
    {
      "article_id": "CAPE0001",
      "quantite": 2,
      "prix_unitaire": 12.5,
      "devise_id": 1
    }
  ]
}
```

### 10.3 Exemple approvisionnement

```http
POST /api/entrees/
```

```json
{
  "libele": "Réappro juin",
  "type_caisse_id": 1,
  "lignes": [
    {
      "article": "CAPE0001",
      "quantite": 50,
      "prix_unitaire": 8,
      "prix_vente": 12,
      "devise_id": 1
    }
  ]
}
```

---

## 11. Rapports et tableaux de bord

### 11.1 Par session (période de travail)

| Rapport | URL | Contenu |
|---------|-----|---------|
| Général | `GET /api/sessions-caisse/{id}/rapport-general/` | Entrées, sorties, solde, nb mouvements |
| Détaillé | `GET /api/sessions-caisse/{id}/rapport-detaille/` | Lignes chronologiques + solde progressif |
| Procès-verbal | `GET /api/sessions-caisse/{id}/proces-verbal/` | JSON structuré pour PDF clôture |

**Exemple rapport général session :**

```json
{
  "session_id": 42,
  "numero": "SESS-0001-000042",
  "caisse": "Caisse cash physique",
  "caisse_id": 1,
  "caisse_nom": "Caisse principale",
  "caisse_code_type": "CASH",
  "devise": "USD",
  "total_entrees": "1250.00000",
  "total_sorties": "75.00000",
  "solde": "1325.00000",
  "nombre_mouvements": 38,
  "statut": "CLOTUREE"
}
```

**Exemple ligne rapport détaillé :**

```json
{
  "datetime": "2026-06-24T10:15:00Z",
  "reference": "VENT-156-USD",
  "type": "ENTREE",
  "categorie": "VENTE",
  "source": "VENTE",
  "description": "Vente sortie #156 — 25.00000",
  "montant_entree": "25.00000",
  "montant_sortie": "",
  "solde_progressif": "175.00000",
  "caisse": "Caisse cash physique",
  "session_numero": "SESS-0001-000042",
  "utilisateur": "agent1"
}
```

### 11.2 Par caisse (toutes sessions)

| Rapport | URL | Filtres optionnels |
|---------|-----|-------------------|
| Général | `GET /api/types-caisse/{id}/rapport-general/` | `?date_min=&date_max=` |
| Détaillé | `GET /api/types-caisse/{id}/rapport-detaille/` | `?date_min=&date_max=` |

Utile pour voir l’activité globale d’« Airtel Money » sur le mois, indépendamment des sessions.

### 11.3 Tableaux de bord mouvements

| Endpoint | Usage |
|----------|-------|
| `/api/mouvements-caisse/solde/` | État caisse par devise (enveloppe rapport) |
| `/api/mouvements-caisse/resume/` | Stats détaillées par devise |
| `/api/mouvements-caisse/tableau-bord/` | Dashboard avec mouvements récents |
| `/api/mouvements-caisse/soldes-simples/` | Widget léger |
| `/api/mouvements-caisse/comparaison-devises/` | Volumes par devise |
| `/api/mouvements-caisse/export/` | Export CSV |

Combiner avec `?type_caisse_id=1` sur le queryset pour filtrer par caisse.

### 11.4 Tickets et reçus

| Document | URL | Format |
|----------|-----|--------|
| Bon POS mouvement | `/api/mouvements-caisse/{id}/bon-pos/` | PDF |
| Reçu paiement dette | `/api/paiements-dettes/{id}/recu-paiement/` | PDF |
| Reçu JSON | `/api/paiements-dettes/{id}/recu-json/` | JSON (impression custom) |

---

## 12. Catalogue des erreurs

### 12.1 Caisse

| Message | HTTP | Cause | Action utilisateur |
|---------|------|-------|-------------------|
| `Veuillez sélectionner une caisse avant de valider cette opération.` | 400 | `type_caisse_id` absent | Choisir une caisse |
| `Cette opération financière exige une caisse active.` | 400 | Caisse désactivée | Choisir une autre caisse ou réactiver (admin) |
| `Caisse introuvable pour cette entreprise.` | 400 | ID invalide ou mauvaise agence | Vérifier la liste `/types-caisse/actives/` |
| `La devise de l'opération ne correspond pas à la devise de la caisse sélectionnée.` | 400 | Devise incompatible | Aligner devise opération / caisse |
| `Identifiant de caisse invalide.` | 400 | `caisse_id` non numérique | Corriger le payload |
| `Type de caisse invalide.` | 400 | `code_type` inconnu à la création | Utiliser CASH, BANQUE, etc. |
| `La caisse principale par défaut ne peut pas être désactivée.` | 400 | PATCH `is_active=false` sur défaut | Interdit |

### 12.2 Session

| Message | HTTP | Cause | Action |
|---------|------|-------|--------|
| `Aucune session ouverte pour cette caisse. Veuillez ouvrir la caisse avant d'effectuer cette opération.` | 400 | Pas de session pour cette caisse | Ouvrir session |
| `Aucune session de caisse n'est ouverte. Veuillez ouvrir une session de caisse avant d'effectuer cette opération.` | 400 | Aucune session (sans caisse précisée) | Ouvrir session |
| `Plusieurs sessions de caisse ouvertes pour cette devise. Précisez le type de caisse.` | 400 | Ambiguïté multi-caisses | Envoyer `type_caisse_id` |
| `Une session de caisse est déjà ouverte pour cette caisse, cette agence et cette devise.` | 400 | Double ouverture | Utiliser la session existante |
| `Le solde d'ouverture ne peut pas être négatif.` | 400 | `solde_ouverture < 0` | Corriger |
| `Seule une session ouverte peut être clôturée.` | 400 | Clôture sur session fermée | Vérifier statut |
| `Seul un administrateur peut valider un écart de caisse.` | 403 | Agent non admin | Appeler un admin |
| `Aucun écart en attente pour cette session.` | 400 | Pas d’écart à valider | — |

### 12.3 Mouvements et soldes

| Message | HTTP | Cause |
|---------|------|-------|
| `Solde insuffisant en {devise} pour la session ouverte. Solde disponible: X, Montant demandé: Y.` | 400 | Sortie > solde session |
| `Le montant ne peut pas être négatif.` | 400 | Montant < 0 |
| `Le champ devise est obligatoire pour le mouvement de caisse.` | 400 | `devise_id` manquant |
| `La suppression des mouvements financiers historiques est interdite.` | 400 | DELETE mouvement |
| `Devise requise pour un mouvement de caisse.` | 400 | Service interne |
| `Contexte entreprise manquant.` | 400/403 | JWT sans tenant |

### 12.4 Paiements dettes

| Message | HTTP | Cause |
|---------|------|-------|
| `Cette dette est déjà entièrement payée.` | 400 | Dette `PAYEE` |
| `Le montant (X) dépasse le solde restant (Y).` | 400 | Surpaiement |
| `Le montant doit être positif.` | 400 | `montant_paye <= 0` |

### 12.5 Format réponse erreur (DRF)

```json
{
  "type_caisse_id": [
    "Veuillez sélectionner une caisse avant de valider cette opération."
  ]
}
```

ou

```json
{
  "detail": "Aucune session ouverte pour cette caisse. Veuillez ouvrir la caisse avant d'effectuer cette opération."
}
```

---

## 13. Scénarios pas à pas

### Scénario A — Journée standard (une caisse cash)

```text
08:00  GET  /api/types-caisse/actives/           → Caisse principale id=1
08:00  GET  /api/sessions-caisse/active/?type_caisse_id=1&devise_id=1
       → ouverte: false
08:01  POST /api/sessions-caisse/ouvrir/        → solde_ouverture=200
08:30  POST /api/sorties/                       → type_caisse_id=1, vente 25 USD
10:00  POST /api/mouvements-caisse/             → sortie dépense 10 USD
14:00  POST /api/paiements-dettes/              → encaissement dette 50 USD
18:00  POST /api/sessions-caisse/42/cloturer/   → montant_physique compté
18:05  POST /api/sessions-caisse/42/valider-ecart/ (admin, si écart)
18:10  GET  /api/sessions-caisse/42/proces-verbal/
```

### Scénario B — Multi-caisses (cash + Airtel Money)

```text
Caisse 1 : Caisse principale CASH     → session OUVERTE USD
Caisse 5 : Airtel Money               → session FERMÉE

Vente payée Airtel :
  → type_caisse_id=5
  → ERREUR : aucune session ouverte pour cette caisse
  → POST /api/sessions-caisse/ouvrir/ avec type_caisse_id=5
  → retenter la vente

Vente cash :
  → type_caisse_id=1
  → OK (session cash déjà ouverte)
```

### Scénario C — Vente à crédit puis paiement

```text
1. POST /api/sorties/  statut=EN_CREDIT, sans type_caisse_id
   → mouvement caisse montant=0 (pas de session requise)

2. GET  /api/dettes/   → solde_restant > 0

3. Ouvrir session caisse si besoin

4. POST /api/paiements-dettes/
   { dette_id, montant_paye, type_caisse_id }
   → ENTREE + mise à jour statut dette
```

### Scénario D — Clôture avec surplus

```text
Solde théorique : 450.00 USD
Comptage réel   : 455.00 USD
→ écart +5 USD (SURPLUS)
→ statut session : CLOTUREE_EN_ATTENTE_VALIDATION
→ Admin POST valider-ecart { "valider": true }
→ Mouvement ENTREE +5 USD catégorie AJUSTEMENT_SURPLUS_CAISSE
→ Session CLOTUREE
```

### Scénario E — Nouvelle entreprise

```text
1. POST /api/entreprises/  (création)
   → Signal auto : Caisse principale CASH créée

2. POST /api/devises/      (devise principale USD)

3. Mettre à jour caisse avec devise_id si besoin

4. POST /api/sessions-caisse/ouvrir/
   → Première session de travail
```

### Scénario F — Consultation historique legacy

```text
GET /api/sessions-caisse/?statut=CLOTUREE
→ Sessions LEGACY-0001-00001 (est_legacy=true)

GET /api/mouvements-caisse/?type_caisse_id=1
→ Tous les mouvements rattachés à la caisse principale,
  y compris ceux d'avant le multi-caisse
```

---

## 14. Migration et données historiques

### Ce qui a été fait (migrations `0028`, `0029`, `0002`)

| Étape | Action |
|-------|--------|
| Sessions legacy | Groupes historiques par entreprise/agence/devise → sessions `LEGACY-*` clôturées |
| Extraction app | Modèles déplacés `stock` → `caisse` (tables inchangées) |
| Multi-caisse | Champs `nom`, `code_type`, `devise`, `est_defaut` sur `TypeCaisse` |
| Rattachement | Mouvements sans `type_caisse_id` → Caisse principale CASH |
| Caisses manquantes | Création auto par entreprise / succursale |

### Ce qui n’a **pas** été fait (volontairement)

- Suppression de mouvements
- Remise à zéro des soldes
- Modification des montants ou dates historiques

---

## 15. Checklist frontend

### Au chargement de l’application

- [ ] `GET /api/types-caisse/actives/` — remplir le sélecteur **Caisse \***
- [ ] `GET /api/sessions-caisse/active/` — afficher bannière « Caisse ouverte / fermée »
- [ ] Si une seule caisse : pré-sélectionner mais **toujours envoyer** `type_caisse_id`

### Avant chaque opération financière

- [ ] Caisse sélectionnée dans le formulaire
- [ ] Session ouverte pour `(caisse, devise, agence)`
- [ ] Si session fermée : proposer **Ouvrir la caisse** (bloquer vente/paiement/dépense)

### Formulaires à modifier

- [ ] Vente (`POST /api/sorties/`)
- [ ] Approvisionnement (`POST /api/entrees/`)
- [ ] Mouvement manuel
- [ ] Paiement dette
- [ ] Livraison commande (`PATCH` + `type_caisse_id`)
- [ ] Import Excel (champ form `type_caisse_id`)
- [ ] Ouverture / clôture session (sélection caisse explicite)

### Écrans admin

- [ ] Liste sessions + filtres statut
- [ ] Clôture : saisie **montant physique** uniquement (pas de date manuelle)
- [ ] Notification écarts en attente → écran validation admin
- [ ] Rapports session + caisse + export CSV

### Gestion des erreurs UI

| Erreur API | Comportement UI suggéré |
|------------|-------------------------|
| Caisse requise | Focus sur champ Caisse, message rouge |
| Session fermée | Modal « Ouvrir la caisse » avec raccourci |
| Solde insuffisant | Afficher solde disponible session |
| Écart en attente | Badge admin + lien validation |

---

## 16. Référence rapide des endpoints

### Caisses

```
GET    /api/types-caisse/
POST   /api/types-caisse/
GET    /api/types-caisse/actives/
GET    /api/types-caisse/{id}/
PATCH  /api/types-caisse/{id}/
DELETE /api/types-caisse/{id}/
GET    /api/types-caisse/{id}/rapport-general/
GET    /api/types-caisse/{id}/rapport-detaille/
```

### Sessions

```
GET    /api/sessions-caisse/
GET    /api/sessions-caisse/active/
POST   /api/sessions-caisse/ouvrir/
GET    /api/sessions-caisse/{id}/
POST   /api/sessions-caisse/{id}/cloturer/
POST   /api/sessions-caisse/{id}/valider-ecart/
GET    /api/sessions-caisse/{id}/rapport-general/
GET    /api/sessions-caisse/{id}/rapport-detaille/
GET    /api/sessions-caisse/{id}/proces-verbal/
```

### Mouvements

```
GET    /api/mouvements-caisse/
POST   /api/mouvements-caisse/
GET    /api/mouvements-caisse/{id}/
GET    /api/mouvements-caisse/resume/
GET    /api/mouvements-caisse/solde/
GET    /api/mouvements-caisse/tableau-bord/
GET    /api/mouvements-caisse/soldes-simples/
GET    /api/mouvements-caisse/export/
GET    /api/mouvements-caisse/{id}/bon-pos/
```

### Paiements dettes

```
GET    /api/paiements-dettes/
POST   /api/paiements-dettes/
GET    /api/paiements-dettes/{id}/
GET    /api/paiements-dettes/{id}/recu-json/
GET    /api/paiements-dettes/{id}/recu-paiement/
```

---

## Annexe — Schéma relationnel simplifié

```text
Entreprise
    │
    ├── TypeCaisse (caisse) ──────┬── SessionCaisse ── EcartCaisse
    │         │                   │         │
    │         └───────────────────┴── MouvementCaisse
    │                                    │
    ├── Sortie / Entree / DetteClient ◄──┘ (liens optionnels)
    └── Devise
```

---

## Annexe — Services clés (développeurs)

| Fonction | Fichier | Rôle |
|----------|---------|------|
| `creer_mouvement_caisse()` | `caisse/services/caisse.py` | Création mouvement + contrôles |
| `get_session_ouverte_for_caisse()` | `caisse/services/session_caisse.py` | Validation caisse + session |
| `ouvrir_session_caisse()` | idem | Ouverture |
| `cloturer_session_caisse()` | idem | Clôture + écart |
| `valider_ecart_caisse()` | idem | Validation admin |
| `get_or_create_caisse_defaut()` | `caisse/services/caisse_defaut.py` | Caisse CASH auto |
| `valider_caisse_pour_operation()` | idem | Contrôle caisse active |
| `parse_type_caisse_id_from_payload()` | idem | Parse API aliases |
| `extract_type_caisse_id()` | `caisse/services/operation_helpers.py` | Helper stock/order |

---

*Document unique module caisse — Uhakika Backend — juin 2026*
