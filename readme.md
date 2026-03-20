# API Gestion de Stock — Guide frontend (Cursor AI)

Ce document décrit le flux chronologique des scénarios utilisateur (création de compte, entreprise, liaison user–entreprise, succursales) et donne tous les endpoints, méthodes HTTP, payloads et réponses attendus pour que le frontend (ou un agent Cursor AI) puisse implémenter les écrans dans le bon ordre.

**Base URL de l’API :** `http://127.0.0.1:8000/api/` (à adapter en production).

**Authentification :** JWT. Après login, envoyer le header :
`Authorization: Bearer <access>`

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

**Utiles en complément :**

- `GET /api/users/me/` — profil de l’utilisateur connecté (GET/PATCH/PUT).  
- `GET /api/entreprises/my_entreprise/` — entreprise du contexte (pour un admin).  
- `GET /api/entreprises/` — liste des entreprises (selon droits : une pour admin, toutes pour superadmin).  
- `GET /api/succursales/` — liste des succursales de l’entreprise du contexte.

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
   - Après création, l’utilisateur peut choisir la succursale via `POST /api/auth/select-context/` avec `succursale_id`.

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
