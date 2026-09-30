# Guide backend — Onboarding & reconnexion (Google)

Document pour l’équipe **API / Django** : éviter de renvoyer les utilisateurs **déjà onboardés** au wizard « création entreprise » à chaque connexion (notamment **Google**).

> **Règle métier :** le parcours entreprise (identité, adresse, contact, logo, review) ne se fait **qu’une fois**. Après `onboarding_complete=True`, ne plus proposer `next_step: company`.

---

## 1. Symptôme observé

- Utilisateur a déjà créé son entreprise et finalisé (ou quasi finalisé) l’onboarding.
- À **chaque** connexion Google (ou classique), le frontend reçoit :
  - `next_step: "company"`
  - `redirection: ".../onboarding/company"` (souvent `/onboarding/company/identity` côté UI)
- L’utilisateur revoit le formulaire **Identité de l’entreprise** en boucle.

Le frontend suivait `GET /api/inscription/flow/` → `redirection` / `next_step` (comportement attendu tant que l’API renvoie `company`).

---

## 2. Cause racine

Fichier : `inscription/services/onboarding_status.py` — fonction **`resoudre_next_step(user, request)`**.

**Ancienne logique (problématique) :**

1. Profil incomplet → `profile`
2. **`entreprise_est_configuree(ent)` false** → **`company`** ← sans tenir compte de `onboarding_complete`
3. `onboarding_complete` false → `review`
4. Puis activation / welcome / dashboard

Si l’entreprise n’est plus considérée configurée (champs vides, `À compléter`, sync uniquement via `PATCH /entreprises/` sans `PATCH /api/onboarding/company/`, `configuration_complete=False`, etc.) **mais** que `user.onboarding_complete=True`, le backend renvoyait quand même **`company`**.

Critère entreprise : `inscription/services/entreprise_saas.py` — `entreprise_est_configuree()` :

- `configuration_complete=True` **ou**
- Tous les champs de `CHAMPS_CONFIG_REQUIS` valides :  
  `nom`, `email`, `telephone`, `adresse`, `pays`, `responsable`, `secteur`  
  (pas de `nif` dans cette liste côté métier « configurée »).

Entreprise courante : `user.get_entreprise(request)` (membership / JWT).

---

## 3. Correctif obligatoire

### 3.1 Modifier `resoudre_next_step`

**Fichier :** `inscription/services/onboarding_status.py`

**Nouvelle règle :**

| Étape | Condition | `next_step` |
|-------|-----------|-------------|
| 1 | Profil incomplet | `profile` |
| 2 | Entreprise **non** configurée **et** onboarding **non** finalisé | `company` |
| 3 | Onboarding **non** finalisé | `review` |
| 4 | Workspace non activé | `activation` |
| 5 | Welcome non vu | `welcome` |
| 6 | Sinon | `dashboard` |

**Pseudo-code :**

```python
onboarding_ok = bool(getattr(user, 'onboarding_complete', False))

if not profile_ok:
    return NEXT_PROFILE
if not company_ok and not onboarding_ok:
    return NEXT_COMPANY
if not onboarding_ok:
    return NEXT_REVIEW
# ... workspace_activated, welcome_seen, dashboard
```

**Invariant à respecter :**

> Si `user.onboarding_complete is True`, **`next_step` ne doit jamais être `company`** (ni `profile` sauf profil réellement incomplet).

### 3.2 Cohérence des réponses API

Ces endpoints doivent utiliser **la même** `resoudre_next_step` (pas de logique dupliquée) :

| Endpoint | Fichier / fonction |
|----------|-------------------|
| `GET /api/onboarding/status/` | `build_onboarding_status()` |
| `GET /api/inscription/flow/` | `flow_saas.py` (construction du flow SaaS) |

Champs alignés :

- `next_step`
- `redirection` = `chemin_redirection_pour_etape(next_step)`  
  (`inscription/services/onboarding_status.py`)

Le frontend s’appuie sur `next_step` et `onboarding_completed` ; `redirection` doit rester **strictement cohérent** avec `next_step`.

### 3.3 Test automatisé

**Fichier :** `inscription/tests_onboarding.py`

Test ajouté (à conserver après merge) :

- `test_onboarding_complete_skips_company_wizard_even_if_ent_incomplete`  
  - Utilisateur avec `onboarding_complete=True`, entreprise avec nom `À compléter` (non configurée métier).  
  - **Attendu :** `next_step != "company"`.

Lancer :

```bash
python manage.py test inscription.tests_onboarding
```

---

## 4. Actions post-déploiement (QA backend)

1. Compte test avec **`onboarding_complete=True`** :
   - `GET /api/onboarding/status/` → `next_step` ∈ `{ review, activation, welcome, dashboard }`, **pas** `company`.
   - `GET /api/inscription/flow/` → idem + `redirection` sans `/onboarding/company`.
2. **Nouveau** compte (première inscription Google) :
   - Après profil OK, entreprise non configurée, **`onboarding_complete=False`** → `next_step` doit rester **`company`**.
3. Parcours complet : `PATCH profile` → `PATCH company` → `POST /api/onboarding/complete/` → `onboarding_complete=True` → plus de retour `company` même si un champ entreprise repasse invalide plus tard.

---

## 5. Comptes déjà bloqués en production

Deux cas distincts :

### A. `onboarding_complete=True` (correctif §3 suffit)

Après déploiement du patch `resoudre_next_step`, la reconnexion Google ne doit **plus** renvoyer au wizard entreprise.

### B. `onboarding_complete=False` (parcours jamais finalisé)

L’utilisateur **doit** encore passer par review + `POST /api/onboarding/complete/` si l’entreprise est configurée métier.

Actions possibles :

1. **Support / admin :** compléter les champs manquants sur `Entreprise`, puis l’utilisateur finalise depuis `/onboarding/review`.
2. **Correction données :** appeler `evaluer_et_marquer_configuration(ent)` après sync des champs requis.
3. **Exception manuelle** (à documenter en interne) : marquer `onboarding_complete=True` **uniquement** si l’entreprise est réellement configurée et le parcours métier validé.

---

## 6. Recommandations complémentaires (qualité données)

Pour limiter les faux « entreprise non configurée » :

1. **`PATCH /api/onboarding/company/`** (`mettre_a_jour_entreprise_onboarding`) appelle déjà `evaluer_et_marquer_configuration(ent)` — s’assurer que le frontend synchronise bien les étapes wizard vers cet endpoint (ou équivalent) et pas seulement `PATCH /entreprises/{id}/` partiel.
2. **`POST /api/onboarding/complete/`** (`finaliser_onboarding`) : continue d’exiger `entreprise_est_configuree(ent)` avant de poser `onboarding_complete=True` (comportement correct).
3. E-mails d’activation / bienvenue : URLs via `build_frontend_url_pour_prochaine_etape(user)` alignées sur `resoudre_next_step` (déjà prévu dans `onboarding_status.py`).

---

## 7. Contrat API rappel (champs utilisés par le frontend)

| Champ | Rôle |
|-------|------|
| `next_step` | Étape cible (`profile`, `company`, `review`, `activation`, `welcome`, `dashboard`, `verify-email`) |
| `onboarding_completed` / `onboarding_complete` (user / flow) | Parcours review+complete terminé |
| `configuration_entreprise_complete` | Entreprise remplit `entreprise_est_configuree` |
| `profil_complet` | Prénom / nom OK |
| `redirection` | Chemin front (avec préfixe locale si configuré) — **dérivé de `next_step`** |
| `acces_dashboard` | Dashboard autorisé (onboarding + workspace + welcome selon règles flow) |

---

## 8. Résumé une phrase

**Ne renvoyer au wizard entreprise (`company`) que si l’entreprise n’est pas configurée ET que `onboarding_complete` est false ; sinon enchaîner review / activation / welcome / dashboard.**

---

## 9. Fichiers touchés (référence PR)

| Fichier | Modification |
|---------|----------------|
| `inscription/services/onboarding_status.py` | `resoudre_next_step` — condition `not company_ok and not onboarding_ok` |
| `inscription/tests_onboarding.py` | Test reconnexion avec `onboarding_complete=True` |

Frontend (repo séparé) : ne plus suivre `flow.redirection` seule ; mapper via `next_step` + `onboarding_completed`. Voir `AUTH_ONBOARDING_FRONTEND.md` dans le repo front.
