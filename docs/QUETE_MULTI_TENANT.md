# Quête : Multi-tenant SaaS (Entreprise + Succursales)

## Objectif global
- **Tenant = Entreprise** : chaque entreprise est un monde isolé.
- Un **utilisateur** peut appartenir à **plusieurs entreprises** (via `Membership`).
- Une **entreprise** peut avoir **plusieurs succursales** (optionnel : `has_branches`).
- Les **données métier** sont scopées par **entreprise** (+ **succursale** si `has_branches`).

## Flow connexion (login)
1. **Étape 1** : À la connexion, on renvoie la **liste des entreprises** accessibles (via Membership).
2. **Étape 2** : L’utilisateur **choisit une entreprise** (ou une seule → auto).
3. **Étape 3** : Si `has_branches = true` → il **choisit une succursale** (ou utilise `default_branch`). Sinon → travail au niveau entreprise.

## Ce qui est fait
- [x] Modèles : `Entreprise.has_branches`, `Succursale`, `Membership`, `UserBranch`
- [x] Suppression de `User.entreprise` ; tout passe par **Membership**
- [x] Login renvoie `user.enterprises` (liste) + `user.entreprise` (première pour compat)
- [x] Assign/remove entreprise → création/suppression de **Membership**
- [x] Filtrage par entreprise via `user.get_entreprise()` (premier membership actif)

## Ce qui est fait (suite)
- [x] **Contexte dans le JWT** : `entreprise_id`, `succursale_id` (optionnel), `membership_id` (à la connexion + select-context)
- [x] **Endpoint** : `POST /api/auth/select-context/` (body: `entreprise_id`, `succursale_id` optionnel) → renvoie nouveaux access + refresh avec contexte
- [x] **Auth** : `JWTAuthenticationWithContext` pose `request.tenant_id`, `request.branch_id`, `request.membership_id` depuis le JWT
- [x] Utilisation du contexte dans les vues : si `request.tenant_id` est présent (token avec contexte), il est utilisé pour le scoping ; sinon fallback sur `user.get_entreprise_id()`

## Étape suivante (faite)
- [x] **API Succursales** : `GET/POST/PUT/PATCH/DELETE /api/succursales/` — liste filtrée par l’entreprise courante (tenant_id) ; création/modification/suppression réservées à l’Admin. Permet au frontend d’afficher la liste des succursales après choix de l’entreprise (pour `select-context`).

## Règle d’or données
Toute donnée métier doit avoir (ou être filtrée par) :
- **entreprise_id** (obligatoire)
- **succursale_id** (optionnel, obligatoire si `has_branches`)
