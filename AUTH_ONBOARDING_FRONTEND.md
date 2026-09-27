# Guide frontend — Auth, Google OAuth, e-mail & onboarding

Document de référence pour aligner le **frontend** sur le backend après les correctifs d’inscription / connexion / Google / vérification e-mail.

> Objectif : **un seul système de comptes**. Entrée classique **ou** Google → même onboarding → même entreprise.

---

## 1. Variables d’environnement frontend

Obligatoire (dev + build Coolify) :

```env
VITE_API_DEV_BASE=http://127.0.0.1:8000
VITE_API_PROD_BASE=https://api.uhakikaapp.store
VITE_GOOGLE_OAUTH_CLIENT_ID=109588295121-jta9olbec2fo7s3pf4os55pfp6c48nbj.apps.googleusercontent.com
```

Règles :

| Variable | Rôle |
|----------|------|
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | Même **Client ID Web** que `GOOGLE_OAUTH_CLIENT_ID` côté API |
| `VITE_API_*_BASE` | Base API (sans `/api` trailing slash selon votre `API_CONFIG`) |

Après modification Coolify front → **rebuild / redéploiement** (Vite injecte les `VITE_*` au build).

Le bouton Google lit aussi `GET /api/inscription/google/config/` ; l’env sert de fallback.

---

## 2. Console Google (cause du `gis_transform : 400`)

Dans [Google Cloud Console](https://console.cloud.google.com/) → Identifiants → **ID client OAuth Web** :

**Origines JavaScript autorisées** (exactes) :

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `https://uhakikaapp.store`

Sans ces origines, GIS affiche `accounts.google.com/gis_transform : 400` **avant** tout appel API.

Type de client : **Application Web** (pas Android / iOS seul).

---

## 3. Flux métier attendus

### 3.1 Inscription manuelle

```
Register → POST /api/inscription/compte/
       → email_envoye ? toast succès / erreur
       → /verify-email?email=…
       → clic lien → POST /api/inscription/verifier-email/
       → tokens + onboarding → /onboarding/…
```

**FE** (`RegisterPage`) :

- Si `isEmailVerificationPending(data)` → page verify (pas de dashboard).
- Si `data.email_envoye === false` → **toast erreur** (pas de faux succès) + quand même page verify pour « Renvoyer ».
- Si `data.tokens?.access` → session + `completeStaffOnboardingAfterAuth`.

### 3.2 Connexion manuelle

```
Login → POST /api/login/  { username: identifier, password }
```

L’identifiant peut être **e-mail**, username ou téléphone (résolu côté backend).

| Réponse | Code | Action FE |
|---------|------|-----------|
| 200 + tokens | — | Session + onboarding |
| 400 | `email_not_verified` | → `/verify-email?email=…` |
| 400 | `compte_inexistant` + `suggest_register: true` | Toast + → `/register?email=…` |
| 400 | `identifiants_invalides` | Erreur « Identifiants incorrects » |

**Ne pas** créer un compte automatiquement depuis la page login.

### 3.3 Google — compte existant

```
Bouton Google → credential JWT → POST /api/inscription/google/
             → 200 + tokens → session + onboarding / dashboard
```

Même e-mail qu’un compte manuel → **liaison** Google, **pas** de 2ᵉ compte.

### 3.4 Google — nouveau compte

Si Google envoie `email_verified: true` (cas normal Gmail) :

```
POST /api/inscription/google/
→ 201 + tokens + email_verifie: true
→ session immédiate → onboarding (création entreprise)
→ PAS d’attente e-mail SMTP
```

Si `email_verifie: false` (rare) :

```
→ statut_verification: EN_ATTENTE → /verify-email
```

**FE** (`LoginPage` / `RegisterPage` Google) :

1. Valider le credential avec `isValidGoogleCredential` (JWT `eyJ…`, 3 parties).
2. Appeler `registerGoogle(credential)` → body `{ credential }` (alias `id_token` accepté).
3. Si pending verify → verify page ; sinon `applyStaffLogin` / `finishSignup`.

---

## 4. Endpoints à utiliser

| Action | Méthode | URL |
|--------|---------|-----|
| Config bouton Google | `GET` | `/api/inscription/google/config/` |
| Google login/signup | `POST` | `/api/inscription/google/` |
| Inscription manuelle | `POST` | `/api/inscription/compte/` |
| Connexion | `POST` | `/api/login/` |
| Vérifier e-mail | `POST` | `/api/inscription/verifier-email/` `{ token }` |
| Renvoyer e-mail | `POST` | `/api/inscription/renvoyer-verification/` `{ email }` |
| Statut onboarding | `GET` | `/api/onboarding/status/` |
| Flow SaaS | `GET` | `/api/inscription/flow/` |

---

## 5. Contrats JSON importants

### 5.1 Attente vérification e-mail

```json
{
  "statut_verification": "EN_ATTENTE",
  "email_verifie": false,
  "email": "user@exemple.com",
  "email_envoye": true,
  "email_erreur": null,
  "message": "…",
  "delai_renvoi_secondes": 60,
  "validite_lien_heures": 24,
  "connexion_google": false,
  "est_nouveau_compte": true
}
```

- `email_envoye: false` → afficher `message` en **erreur / warning**, jamais en succès.
- `email_erreur` possible : `smtp_auth_failed`, `domaine_non_verifie`, `erreur_envoi`, …

### 5.2 Renvoi e-mail

Succès `200` :

```json
{ "message": "…", "email_envoye": true, "delai_renvoi_secondes": 60 }
```

Échec SMTP `503` :

```json
{
  "message": "Authentification SMTP refusée (Brevo). …",
  "email_envoye": false,
  "code": "smtp_auth_failed"
}
```

Cooldown `429` : `code: cooldown` + `delai_renvoi_secondes`.

**FE** : sur 503 / codes SMTP → toast **warning** avec `message` API (pas un toast générique « serveur off »).

### 5.3 Compte inexistant au login

```json
{
  "detail": "Aucun compte trouvé pour cet identifiant. Créez un compte pour continuer.",
  "code": "compte_inexistant",
  "email": "user@exemple.com",
  "suggest_register": true
}
```

→ naviguer vers `/register?email=…` (préremplir le champ e-mail).

### 5.4 Google succès (nouveau, e-mail déjà vérifié par Google)

```json
{
  "est_nouveau_compte": true,
  "connexion_google": true,
  "email_verifie": true,
  "tokens": { "access": "…", "refresh": "…" },
  "user": { … },
  "prochaine_etape": "creer_entreprise",
  "message": "Compte créé via Google. Poursuivez la configuration…"
}
```

Helper FE : `isEmailVerificationPending(data)` doit être **false** dès que `tokens.access` est présent.

---

## 6. Composant Google (`GoogleAuthButton`)

Déjà adapté côté front :

- Init GIS **une seule fois** par `client_id` (évite `gis_transform` au remount Strict Mode).
- **Ne pas** appeler `google.accounts.id.cancel()` au cleanup.
- Callback uniquement avec `response.credential` (JWT), jamais le HTML de l’iframe.
- `use_fedcm_for_prompt: false` pour limiter les 400 locaux.
- Modes : `signin` (login) / `signup` (register).

Checklist si le bouton reste cassé :

1. `VITE_GOOGLE_OAUTH_CLIENT_ID` présent au build.
2. `GET /api/inscription/google/config/` → `{ "actif": true, "client_ids": ["…"] }`.
3. Origines Google Console = URL exacte de la barre d’adresse.
4. Hard refresh / rebuild après changement d’env.

---

## 7. Onboarding après auth

Après tokens (manuel vérifié **ou** Google) :

1. `login(access, user, refresh)`
2. `completeStaffOnboardingAfterAuth(…)`
3. Suivre `redirection` / `next_step` (`/onboarding/profile`, `/onboarding/company/…`, dashboard)

Ne pas forcer `/dashboard` si l’entreprise n’existe pas.

Sources d’arrivée dans l’onboarding :

- inscription manuelle (après verify) ;
- Google nouveau ;
- login d’un compte sans entreprise.

---

## 8. Checklist QA frontend

### Inscription manuelle

- [ ] Compte créé → page verify
- [ ] Si SMTP OK → toast succès + e-mail reçu
- [ ] Si SMTP KO → toast **erreur** + bouton Renvoyer visible
- [ ] Renvoyer → succès ou message SMTP explicite (pas faux succès)
- [ ] Lien verify → tokens → onboarding

### Connexion manuelle

- [ ] Compte OK → app / onboarding
- [ ] Mauvais mot de passe → `identifiants_invalides`
- [ ] E-mail inconnu → redirect register prérempli
- [ ] E-mail non vérifié → verify-email

### Google

- [ ] Bouton visible (config actif)
- [ ] Pas d’erreur `gis_transform 400` (origines OK)
- [ ] Nouveau Google → tokens + onboarding (sans verify e-mail)
- [ ] Google existant → connexion
- [ ] Même e-mail qu’un compte manuel → un seul user

### Régression

- [ ] LoadingSpinner importé sur le bouton Renvoyer
- [ ] Pas de double toast succès/erreur

---

## 9. Ce que le frontend a déjà (état actuel du repo)

| Point | Fichier | Statut |
|-------|---------|--------|
| Google button robuste | `GoogleAuthButton.tsx` | OK |
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | `.env` + Coolify | OK (rebuild front requis) |
| Login → `compte_inexistant` | `LoginPage.tsx` | OK |
| Register prérempli `?email=` | `RegisterPage.tsx` | OK |
| `email_envoye: false` → toast erreur | `RegisterPage.tsx` | OK |
| Renvoi SMTP / 503 | `VerifyEmailPage.tsx` | OK (codes smtp inclus) |
| Google → tokens / pending | Login + Register | OK |
| Helper pending | `emailVerificationFlow.ts` | OK |

---

## 10. Ce qui reste côté ops (hors code FE)

Sans ça, les e-mails **réels** ne partent toujours pas :

1. **Coolify API** — ajouter les vraies variables Brevo :
   - `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
   - `EMAIL_HOST=smtp-relay.brevo.com`
   - `EMAIL_PORT=587`
   - `EMAIL_USE_TLS=True`
   - `EMAIL_HOST_USER=` *(login SMTP Brevo réel)*
   - `EMAIL_HOST_PASSWORD=` *(clé `xsmtpsib_…` réelle)*
   - `DEFAULT_FROM_EMAIL=UhakikaApp <noreply@uhakikaapp.store>`
2. Redémarrer l’API après ajout.
3. Domaine `uhakikaapp.store` authentifié dans Brevo (DKIM / DMARC).

En **DEBUG local**, si les placeholders `.env` sont encore là, le backend bascule sur le backend **console** (e-mails dans le terminal `runserver`, plus de 503). Pour tester un vrai envoi local, coller la vraie clé Brevo dans `.env`.

---

## 11. Schéma résumé

```text
              ┌──────────────┐
              │  Utilisateur │
              └──────┬───────┘
         ┌───────────┴───────────┐
         │                       │
   Login / Register           Google GIS
         │                       │
         ▼                       ▼
   Compte existe ?         Compte (email/sub) ?
      /        \              /            \
    Oui        Non          Oui            Non
     │          │            │              │
  Connexion  Inscription  Connexion    Inscription
  (+ verify (+ e-mail       (+ link)     (email Google
   verify     verify si                  déjà OK →
   si besoin) manuel)                    tokens)
         │          │            │              │
         └──────────┴─────┬──────┴──────────────┘
                          ▼
                     Onboarding
                          ▼
                 Création entreprise
                          ▼
                    UhakikaApp
```

---

## 12. Contacts techniques utiles

- Backend guide SMTP / Google : `.env.example` (section e-mail + Google).
- Types TS : `src/types/saas.ts` (`InscriptionCompteResponse`, `ResendVerificationResponse`).
- API helpers : `src/lib/saas/saasApi.ts`.
