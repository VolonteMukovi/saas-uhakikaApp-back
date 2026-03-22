# API Gestion de Stock — Guide frontend (Cursor AI)

Ce document décrit le flux chronologique des scénarios utilisateur (création de compte, entreprise, liaison user–entreprise, succursales) et donne tous les endpoints, méthodes HTTP, payloads et réponses attendus pour que le frontend (ou un agent Cursor AI) puisse implémenter les écrans dans le bon ordre.

**Base URL de l’API :** `http://127.0.0.1:8000/api/` (à adapter en production).

**Authentification :** JWT. Après login, envoyer le header :
`Authorization: Bearer <access>`

### Documentation interactive (Swagger & ReDoc)

- **Swagger UI :** `http://127.0.0.1:8000/swagger/` — tester les endpoints, bouton **Authorize** pour coller `Bearer <access_token>`.
- **ReDoc :** `http://127.0.0.1:8000/redoc/` — même schéma, lecture plus linéaire.
- **Schéma OpenAPI brut :** `http://127.0.0.1:8000/swagger.json` ou `http://127.0.0.1:8000/swagger.yaml` (import Postman, génération client).

La description générale (flux multi-tenant, auth, rôles) est dans la page d’accueil du schéma ; les actions personnalisées (`select-context`, `assign_entreprise`, `succursales`, `my_entreprise`, `users` sur entreprise, etc.) ont des résumés et corps de requête documentés via **drf-yasg**.

---

## 1. Ordre chronologique des scénarios

L’ordre logique côté utilisateur est le suivant :

1. **Création de compte** (inscription) — pas d’auth  
2. **Connexion** (login) — obtention des tokens + infos user / entreprises  
3. **Création d’une entreprise** — utilisateur connecté, sans entreprise encore (ou admin)  
4. **Liaison user ↔ entreprise** (Membership) — associer son compte à l’entreprise (avec rôle admin/user)  
5. **Sélection du contexte** (optionnel) — choisir l’entreprise (et la succursale) pour les prochains appels  
6. **Création de succursales** (optionnel) — si l’entreprise a `has_branches: true`

En pratique, les étapes 3 et 4 peuvent être proposées juste après le login pour un nouvel utilisateur : il crée son entreprise puis s’y associe en un flux guidé.

---

## 2. Création de compte (inscription)

- **Endpoint :** `POST /api/users/`  
- **Auth :** Aucune (`AllowAny`)  
- **Content-Type :** `application/json`

**Payload :**

```json
{
  "username": "string",
  "email": "user@example.com",
  "first_name": "string",
  "last_name": "string",
  "password": "string",
  "password_confirm": "string"
}
```

**Contraintes :**  
- `password` et `password_confirm` doivent être identiques.  
- Longueur minimale du mot de passe : 8 caractères.

**Réponse succès (201) :**

```json
{
  "message": "Compte créé avec succès. Contactez le superadmin pour associer votre entreprise.",
  "user_id": 1,
  "username": "johndoe",
  "email": "user@example.com"
}
```

**Réponse erreur (400) :** body avec champs d’erreur (ex. `password`, `password_confirm`, `username`).

---

## 3. Connexion (login)

- **Endpoint :** `POST /api/auth/`  
- **Auth :** Aucune  
- **Content-Type :** `application/json`

**Payload :**

```json
{
  "username": "johndoe",
  "password": "votremotdepasse"
}
```

**Réponse succès (200) :**

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "user@example.com",
    "entreprise": { "id": 1, "nom": "...", "has_branches": false, ... },
    "enterprises": [
      {
        "membership_id": 1,
        "entreprise": { "id": 1, "nom": "...", "secteur": "...", "adresse": "...", "telephone": "...", "email": "...", "responsable": "...", "has_branches": false },
        "role": "admin",
        "default_branch_id": null
      }
    ]
  }
}
```

- Si l’utilisateur n’a **aucune entreprise** (pas encore de Membership), `user.enterprises` est `[]` et `user.entreprise` peut être `null`.  
- Conserver `access` pour le header `Authorization: Bearer <access>` et `refresh` pour renouveler le token (voir refresh ci‑dessous).

**Refresh du token :**  
`POST /api/auth/refresh/`  
Body : `{ "refresh": "<refresh_token>" }`  
Réponse : `{ "access": "..." }` (et éventuellement `refresh`).

---

## 4. Création d’une entreprise

- **Endpoint :** `POST /api/entreprises/`  
- **Auth :** Bearer token requis. L’utilisateur doit être considéré comme “admin” (en pratique : après liaison à une entreprise) **ou** le backend peut autoriser un utilisateur sans entreprise à en créer une (à confirmer selon les règles métier).  
- **Content-Type :** `application/json`

**Payload :**

```json
{
  "nom": "Ma Société",
  "secteur": "Commerce",
  "pays": "France",
  "adresse": "123 rue Example",
  "telephone": "+33600000000",
  "email": "contact@masociete.com",
  "nif": "NIF123456",
  "responsable": "Jean Dupont",
  "logo": null,
  "slogan": "Notre slogan",
  "has_branches": false
}
```

**Champs optionnels :** `logo` (fichier ou null), `slogan`, `has_branches` (défaut `false`). Si l’entreprise aura des succursales, mettre `has_branches: true`.

**Réponse succès (201) :** objet entreprise (tous les champs du modèle, ex. `id`, `nom`, `secteur`, `pays`, `adresse`, `telephone`, `email`, `nif`, `responsable`, `logo`, `slogan`, `has_branches`).

**Comportement backend :** À la création, le backend associe automatiquement l’utilisateur connecté à cette entreprise avec le rôle **admin** (Membership créé). Donc après cette étape, l’utilisateur a déjà une liaison avec l’entreprise créée.

**Note pour le flux “premier compte” :** Actuellement, seuls les utilisateurs déjà “admin” (ayant au moins un Membership avec rôle admin) peuvent créer une entreprise. Pour un **nouvel utilisateur sans aucune entreprise**, deux options côté produit : (1) Adapter le backend pour autoriser `POST /api/entreprises/` pour tout utilisateur authentifié sans membership (puis création auto du Membership admin), afin que le flux “Inscription → Login → Créer mon entreprise” fonctionne ; (2) Ou faire créer la première entreprise par un superadmin, puis l’utilisateur s’y associe via `assign_entreprise`.

---

## 5. Liaison user ↔ entreprise (Membership)

Utilisé quand l’utilisateur a déjà un compte et qu’une entreprise existe déjà (créée par lui ou par un superadmin). Il s’associe à cette entreprise avec un rôle.

- **Endpoint :** `POST /api/users/{user_id}/assign_entreprise/`  
- **Auth :** Bearer token requis.  
- **Règle :** Un utilisateur non superadmin ne peut associer **que son propre compte** (`user_id` = son `id`). Le superadmin peut associer n’importe quel `user_id`.

**Payload :**

```json
{
  "entreprise_id": 1,
  "role": "admin"
}
```

- `entreprise_id` : **obligatoire**, ID de l’entreprise existante.  
- `role` : **optionnel**, `"admin"` ou `"user"`. Défaut : `"admin"`.

**Réponse succès (200) :**

```json
{
  "message": "Utilisateur johndoe associé à Ma Société avec le rôle admin",
  "user_id": 1,
  "entreprise_id": 1,
  "entreprise_nom": "Ma Société",
  "role": "admin"
}
```

**Scénario typique après inscription :**  
1. Login (`POST /api/auth/`).  
2. Créer l’entreprise (`POST /api/entreprises/`) → l’utilisateur est déjà lié en admin.  
**OU** si l’entreprise a été créée autrement (ex. par un superadmin) :  
3. Associer son compte : `POST /api/users/<son_id>/assign_entreprise/` avec `entreprise_id` et `role` (souvent `"admin"`).

---

## 6. Sélection du contexte (entreprise / succursale)

Après login, les appels API sont “dans le contexte” d’une entreprise (et éventuellement d’une succursale). Par défaut, le premier Membership actif est utilisé. Pour **changer** d’entreprise ou de succursale, appeler :

- **Endpoint :** `POST /api/auth/select-context/`  
- **Auth :** Bearer token requis  
- **Content-Type :** `application/json`

**Payload :**

```json
{
  "entreprise_id": 1,
  "succursale_id": null
}
```

- `entreprise_id` : **obligatoire**. Doit être une entreprise à laquelle l’utilisateur est lié (Membership actif).  
- `succursale_id` : **optionnel**. Si l’entreprise a des succursales (`has_branches: true`), on peut passer l’ID d’une succursale de cette entreprise ; sinon `null`.

**Réponse succès (200) :** nouveaux tokens avec le contexte mis à jour :

```json
{
  "refresh": "...",
  "access": "...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": "user@example.com",
    "entreprise_id": 1,
    "succursale_id": null,
    "membership_id": 1,
    "entreprise": { "id": 1, "nom": "Ma Société", "has_branches": false }
  }
}
```

À utiliser pour mettre à jour le token côté frontend et afficher la bonne entreprise/succursale courante.

---

## 7. Création de succursale (si l’entreprise a des succursales)

Disponible seulement si l’entreprise a `has_branches: true`. Réservé à l’**admin** de l’entreprise (Membership avec rôle `admin`).

- **Endpoint :** `POST /api/succursales/`  
- **Auth :** Bearer token. L’utilisateur doit être admin de l’entreprise du contexte (contexte JWT = cette entreprise).  
- **Content-Type :** `application/json`

**Payload :**

```json
{
  "nom": "Succursale Centre",
  "adresse": "45 avenue Example",
  "telephone": "+33600000001",
  "email": "centre@masociete.com"
}
```

- `nom` : obligatoire.  
- `adresse`, `telephone`, `email` : optionnels.  
- L’**entreprise** est fixée côté backend par le contexte (token / membership) ; inutile de l’envoyer.

**Réponse succès (201) :** objet succursale avec `id`, `entreprise`, `entreprise_nom`, `nom`, `adresse`, `telephone`, `email`, `is_active`, `created_at`.

**Liste des succursales :** `GET /api/succursales/` — retourne les succursales de l’entreprise du contexte.

### CRUD succursale (complete côté API)

- **Lire une succursale (GET détail)** : `GET /api/succursales/{id}/`
- **Créer (POST)** : `POST /api/succursales/`
- **Mettre à jour (PATCH/PUT)** : `PATCH /api/succursales/{id}/` ou `PUT /api/succursales/{id}/`
- **Supprimer (DELETE)** : `DELETE /api/succursales/{id}/`
  - Implémenté comme une **désactivation** (`is_active = false`) via `perform_destroy`.

Règles d’accès :
- **Admin** de l’entreprise (Membership.role = `admin`) : peut créer/modifier/supprimer.
- **Agent** (Membership.role = `user`) : ne voit que sa succursale courante (filtrage côté backend), pas de CRUD.

---

## 7 bis. Associer un utilisateur aux succursales (Membership)

En base, cela repose sur :

- **`Membership.default_succursale`** : succursale par défaut pour le JWT / le filtrage (voir aussi `select-context`).
- **`UserBranch`** : liste des succursales auxquelles ce **membership** (user + entreprise) est autorisé.

Ce n’était **pas** documenté avant ; les endpoints suivants exposent cette logique.

### Lire les succursales liées à un user pour une entreprise

- **Endpoint :** `GET /api/users/{user_id}/succursales/?entreprise_id={entreprise_id}`  
- **Auth :** Bearer. **Superadmin** ou **admin** de l’entreprise (même règle que la gestion des utilisateurs).  
- **Query :** `entreprise_id` **obligatoire**.

**Réponse succès (200) :**

```json
{
  "user_id": 3,
  "entreprise_id": 1,
  "membership_id": 5,
  "default_succursale_id": 2,
  "succursales": [
    { "id": 2, "nom": "Centre", "adresse": "..." }
  ]
}
```

### Définir la succursale par défaut et/ou la liste des succursales autorisées

- **Endpoint :** `POST /api/users/{user_id}/succursales/`  
- **Auth :** Bearer. **Superadmin** ou **admin** de l’entreprise.  
- **Content-Type :** `application/json`

**Payload (exemple complet) :**

```json
{
  "entreprise_id": 1,
  "default_succursale_id": 2,
  "succursale_ids": [2, 7]
}
```

- **`entreprise_id`** : obligatoire. L’utilisateur cible doit avoir un **Membership actif** pour cette entreprise.  
- **`succursale_ids`** : optionnel. Si la clé est **présente**, elle **remplace** toutes les lignes `UserBranch` pour ce membership (liste vide = aucune succursale autorisée explicitement). Chaque id doit être une succursale **active** de cette entreprise.  
- **`default_succursale_id`** : optionnel (`null` pour effacer). Doit être une succursale de cette entreprise. Si vous envoyez **à la fois** `succursale_ids` et `default_succursale_id` non null, la valeur par défaut **doit** figurer dans `succursale_ids`. Avec `succursale_ids: []`, la valeur par défaut doit être `null` ou omise.

Vous pouvez aussi n’envoyer **que** `default_succursale_id` (sans clé `succursale_ids`) pour ne mettre à jour que la succursale par défaut, sans toucher aux `UserBranch`.

**Réponse succès (200) :** message + `membership_id`, `default_succursale_id`, liste `succursales` mise à jour.

**Ordre conseillé côté produit :** créer les succursales (`POST /api/succursales/`) → puis appeler ce `POST` pour chaque employé / admin qui doit être limité à certaines succursales.

### CRUD côté frontend : association User ↔ Succursales (UserBranch)

Cette association (User <-> Succursales) est gérée via :
- **`GET /api/users/{user_id}/succursales/?entreprise_id={entreprise_id}`** (lecture)
- **`POST /api/users/{user_id}/succursales/`** (création / mise à jour / suppression)

Il n’y a pas d’endpoint séparé “PUT/PATCH UserBranch par id” : le CRUD est fait via `POST`.

#### 1) Lire (GET)
- **Endpoint :** `GET /api/users/{user_id}/succursales/?entreprise_id=1`
- **Auth :** Bearer token (superadmin ou admin de l’entreprise)

Réponse (exemple) :
```json
{
  "user_id": 3,
  "entreprise_id": 1,
  "membership_id": 5,
  "default_succursale_id": 2,
  "succursales": [
    { "id": 2, "nom": "Centre", "adresse": "..." }
  ]
}
```

#### 2) Écrire (POST) : Create / Update / Delete
- **Endpoint :** `POST /api/users/{user_id}/succursales/`
- **Body :** au moins un des champs `succursale_ids` ou `default_succursale_id` doit être fourni.

##### Create / Update complet (remplacer la liste)
```json
{
  "entreprise_id": 1,
  "default_succursale_id": 2,
  "succursale_ids": [2, 7]
}
```
Effet :
- remplace toutes les lignes `UserBranch` de ce membership
- met à jour `Membership.default_succursale_id`

##### Update “default uniquement” (ne pas toucher aux UserBranch)
```json
{ "entreprise_id": 1, "default_succursale_id": 2 }
```

##### Delete (retirer l’accès à toutes les succursales)
```json
{
  "entreprise_id": 1,
  "succursale_ids": [],
  "default_succursale_id": null
}
```

#### 3) Cas critique : agent (`Membership.role == "user"`) sans succursale

Règle stricte backend :
- si un agent n’a **pas** de succursale courante déterminée (JWT / `membership.default_succursale_id`), les endpoints “métier stock/rapports” échouent avec **403 (succursale requise)**.

Guide frontend (côté UI) :
1. Quand tu affiches la fiche d’un agent, fais un `GET /api/users/{id}/succursales/?entreprise_id=...`.
2. Si `default_succursale_id == null` ou `succursales` est vide :
   - affiche : “Affecter des succursales à cet agent”
   - empêche d’accéder aux écrans stock/rapports pour cet agent tant que l’affectation n’est pas faite.
3. Pour corriger :
   - envoie un `POST /api/users/{id}/succursales/` avec `succursale_ids` + `default_succursale_id`
   - puis côté agent, déclenche `POST /api/auth/select-context/` :
     ```json
     { "entreprise_id": 1, "succursale_id": 2 }
     ```
     (ou laisse `succursale_id` à `null` si tu veux que le backend utilise le default)

Remarque sécurité :
- quand tu remplaces `succursale_ids`, le backend met aussi `default_succursale_id` à `null` si l’ancien default n’appartient plus à la nouvelle liste (pour éviter toute fuite d’accès).

---

## 8. Récapitulatif des endpoints (ordre chronologique)

| Étape | Méthode | Endpoint | Auth | Rôle |
|-------|--------|----------|------|------|
| 1. Inscription | `POST` | `/api/users/` | Non | - |
| 2. Connexion | `POST` | `/api/auth/` | Non | - |
| 3. Refresh token | `POST` | `/api/auth/refresh/` | Refresh token | - |
| 4. Créer entreprise | `POST` | `/api/entreprises/` | Bearer | Admin ou premier compte |
| 5. Lier user ↔ entreprise | `POST` | `/api/users/{id}/assign_entreprise/` | Bearer | Soi‑même ou superadmin |
| 6. Changer contexte | `POST` | `/api/auth/select-context/` | Bearer | Utilisateur avec Membership |
| 7. Créer succursale | `POST` | `/api/succursales/` | Bearer | Admin entreprise |
| 8. Lier user ↔ succursales | `GET` / `POST` | `/api/users/{id}/succursales/` | Bearer | Superadmin ou admin entreprise |

**Utiles en complément :**

- `GET /api/users/me/` — profil de l’utilisateur connecté (GET/PATCH/PUT).  
- `GET /api/entreprises/my_entreprise/` — entreprise du contexte (pour un admin).  
- `GET /api/entreprises/` — liste des entreprises (selon droits : une pour admin, toutes pour superadmin).  
- `GET /api/succursales/` — liste des succursales de l’entreprise du contexte.  
- `GET /api/entreprises/{id}/users/` — liste des utilisateurs d’une entreprise.

---

## 8 bis. Bénéfices totaux (`GET /api/entrees/benefices-totaux/`) — **obligatoirement contextualisé**

Cet endpoint agrège les enregistrements `BeneficeLot` **uniquement** pour :

- l’**`entreprise_id`** portée par le JWT (`login` / `select-context`) ;
- et, si le token contient une **`succursale_id`**, **uniquement** les lots dont l’**entrée** (`Entree`) est rattachée à cette succursale.

**Sans contexte entreprise** (pas de `entreprise_id` / membership utilisable) → **400** avec un message explicite.

### Appel frontend

1. S’assurer que l’utilisateur a un **access token** valide **après** `POST /api/auth/` et idéalement **`POST /api/auth/select-context/`** avec `entreprise_id` (et `succursale_id` si vous voulez un périmètre succursale).
2. Requête :

```http
GET /api/entrees/benefices-totaux/?year=2026&month=3
Authorization: Bearer <access>
```

3. Interpréter la réponse :
   - `resume` : totaux du mois **pour le tenant courant uniquement** ;
   - `benefices_par_article` : top 10 articles (déjà filtré) ;
   - `details.entreprise_id` / `details.succursale_id` : rappel du **périmètre** appliqué (le front peut l’afficher ou le logger pour debug).

**Important :** ne pas appeler cet URL sans token ni avec un utilisateur sans entreprise : vous obtiendrez **400**, pas des données “globales”.

---

## 9. Flux recommandé côté frontend (nouvel utilisateur)

1. **Inscription**  
   - Afficher formulaire (username, email, first_name, last_name, password, password_confirm).  
   - `POST /api/users/` → afficher message de succès.

2. **Connexion**  
   - Formulaire username + password.  
   - `POST /api/auth/` → stocker `access`, `refresh` et `user` (localStorage/session/cookie au choix).

3. **Si `user.enterprises` est vide** (pas encore d’entreprise) :  
   - Proposer “Créer mon entreprise” : formulaire avec les champs entreprise → `POST /api/entreprises/`.  
   - Le backend crée l’entreprise et associe l’utilisateur en admin.  
   - Puis appeler `POST /api/auth/select-context/` avec le nouvel `entreprise_id` pour mettre à jour le contexte (optionnel si le token est déjà mis à jour côté backend au prochain appel).

4. **Si l’utilisateur a déjà une entreprise** mais veut s’associer à une autre (ou se lier à une entreprise existante) :  
   - `POST /api/users/<current_user_id>/assign_entreprise/` avec `entreprise_id` et `role` (`"admin"` ou `"user"`).

5. **Si l’entreprise a `has_branches: true`** :  
   - Proposer “Ajouter une succursale” : formulaire nom, adresse, téléphone, email → `POST /api/succursales/`.  
   - Pour **attribuer** des succursales à un employé : `GET` / `POST /api/users/{id}/succursales/` (voir section **7 bis**).  
   - L’utilisateur peut choisir la succursale active dans le JWT via `POST /api/auth/select-context/` avec `succursale_id`.

6. **Tous les autres appels API** (stock, ventes, rapports, etc.) : envoyer le header `Authorization: Bearer <access>` ; le backend utilise le contexte (entreprise_id / succursale_id) présent dans le JWT ou dans la requête.

---

## 10. Gestion des erreurs

- **400** : payload invalide (champs manquants, format, contraintes). Body : `{ "champ": ["message d’erreur"], ... }` ou `{ "error": "message" }`.  
- **401** : non authentifié (pas de token ou token expiré).  
- **403** : authentifié mais pas le droit (ex. associer un autre user sans être superadmin, ou accès à une entreprise sans Membership).  
- **404** : ressource introuvable (ex. entreprise_id ou user_id inexistant).

Utiliser le champ `error` ou les clés par champ dans la réponse pour afficher les messages à l’utilisateur.

---

Ce README sert de **prompt / spec** pour un agent Cursor AI ou un développeur frontend : en suivant l’ordre des sections et les payloads ci‑dessus, les scénarios “création compte → création entreprise → liaison user–entreprise → création succursale” peuvent être implémentés dans le bon ordre chronologique avec les bons endpoints et formats.
