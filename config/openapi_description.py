"""
Description affichée en tête de Swagger UI et ReDoc (drf-yasg).
"""

API_DESCRIPTION = """
## API Gestion de Stock — Multi-tenant

### Authentification
- **JWT** : `POST /api/auth/` avec `username` et `password` → récupérer `access` et `refresh`.
- Header : `Authorization: Bearer <access>`
- **Rafraîchissement** : `POST /api/auth/refresh/` avec le body `{"refresh": "..."}`.
- **Contexte entreprise / succursale** : les claims JWT peuvent contenir `entreprise_id`, `succursale_id`, `membership_id`.
- **Changer de contexte** : `POST /api/auth/select-context/` (authentifié) avec `entreprise_id` et optionnellement `succursale_id`.

### Flux typique (nouvel utilisateur)
1. `POST /api/users/` — inscription (sans token).
2. `POST /api/auth/` — connexion.
3. `POST /api/entreprises/` — création entreprise (utilisateur connecté ; Membership admin créé automatiquement).
4. `POST /api/users/{id}/assign_entreprise/` — liaison à une entreprise existante si besoin (`entreprise_id`, `role`).
5. `POST /api/succursales/` — si `has_branches` sur l’entreprise.
6. `GET` / `POST /api/users/{id}/succursales/` — succursale par défaut + liste autorisée (`UserBranch`).

### Endpoints utiles
- `GET /api/users/me/` — profil connecté.
- `GET /api/entreprises/my_entreprise/` — entreprise du contexte.
- `GET /api/entreprises/{id}/users/` — utilisateurs d’une entreprise.

### Branding (logo, slogan) — une seule forme de lecture
Le payload entreprise est le même partout : **`EntrepriseSerializer`** (champ `logo` en URL absolue si requête HTTP, `slogan`, etc.) sur `POST /api/auth/`, `POST /api/auth/select-context/`, `GET /api/users/me/`, `GET /api/entreprises/{id}/` et `GET /api/entreprises/my_entreprise/`. Les **agents** (`Membership.role=user`) ont **lecture seule** sur leur entreprise (pas de PATCH entreprise).

### Rôles
- **Superadmin** : `is_superuser` (createsuperuser).
- **Admin / Agent** : via `Membership.role` (`admin` ou `user`) pour chaque entreprise.

---
*Pour plus de détail, voir le fichier `README.md` à la racine du projet.*
""".strip()
