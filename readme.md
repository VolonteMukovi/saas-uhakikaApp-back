# d-vd-api-cantine - Documentation Backend (Multi-tenant) pour Frontend React/TS

## 1) Objectif
Ce document decrit:
- le flux d'authentification JWT multi-tenant (entreprise + succursale)
- comment le backend isole strictement les donnees entre tenants
- les payloads (structure) pour creer: compte (user), entreprise, succursale
- les principaux payloads `POST` utiles pour tester de A a Z la fonctionnalite mise en place

## 2) Base URL
Tous les endpoints commencent par:
- `https://<host>/api/`

Routes:
- Auth / Users: `d:\vd\api_cantine\users\urls.py`
- Metier stock/ventes/dettes/caisse: `d:\vd\api_cantine\stock\urls.py`
- Rapports: `d:\vd\api_cantine\rapports\urls.py`
- Import Excel: `d:\vd\api_cantine\import_excel\urls.py`

## 3) Multi-tenant: comment le backend reconnait "votre entreprise"

### 3.1 JWT claims
Apres authentification, le backend injecte sur la requete:
- `request.tenant_id` (claim `entreprise_id`)
- `request.branch_id` (claim `succursale_id`)

### 3.2 Selection du contexte tenant (obligatoire si user a plusieurs entreprises)
Endpoint:
- `POST /api/auth/select-context/`

Body:
```json
{
  "entreprise_id": 10,
  "succursale_id": 55
}
```

Regles:
- `entreprise_id` est obligatoire
- `succursale_id`:
  - optionnel
  - si absent, le backend utilise la succursale par defaut du membership

### 3.3 Filtrage automatique des donnees metier
Pour les ViewSets metier (stock/ventes/dettes/caisse), le filtrage est automatique via `TenantFilterMixin`:
- si le modele porte `entreprise_id`, alors `entreprise_id` est filtre
- si le modele porte aussi `succursale_id` et que `branch_id` est defini, alors `succursale_id` est filtre
- a la creation, le backend force aussi les champs tenant/scursurcale si le modele les supporte

## 4) Creation compte (users) - Payloads

### 4.1 S'inscrire publiquement (creer un compte public)
Endpoint:
- `POST /api/users/` (action `create`, permission AllowAny)

But:
- cree un utilisateur avec `role=admin`
- ne cree PAS directement de membership entreprise
- le frontend doit ensuite demander l'association entreprise via le superadmin

Body (payload):
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string (min 8)",
  "password_confirm": "string"
}
```

Remarque:
- la validation impose `password == password_confirm`
- le backend renvoie un message demandant l'association a une entreprise par le superadmin

### 4.2 Cree un user par un ADMIN d'entreprise (auth requise)
Endpoint:
- `POST /api/users/` (action `create`)

Condition:
- vous devez etre authentifie en tant que `admin` (meme tenant)

Body:
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "role": "admin | user",
  "password": "string (min 8, optionnel selon UI)"
}
```

Points importants:
- si `role` n'est pas `admin` ou `user`, le backend force a `user`
- le backend cree directement le `Membership` dans l'entreprise du tenant courant (via context)

### 4.3 ASSOCIER un user a une entreprise (superadmin seulement)
Endpoint:
- `POST /api/users/{user_id}/assign_entreprise/`

Permission:
- `IsSuperAdmin`

Body:
```json
{
  "entreprise_id": 10
}
```

Effet:
- cree (ou reactiver) `Membership(user, entreprise)`
- defaults: `role='admin'`, `is_active=true`

### 4.4 RETIRER l'association entreprise (superadmin seulement)
Endpoint:
- `POST /api/users/{user_id}/remove_entreprise/`

Body:
```json
{
  "entreprise_id": 10
}
```

Effet:
- supprime le membership correspondant

### 4.5 Profil: consulter / modifier le compte (action `me`)
Endpoint:
- `GET /api/users/me/` (lire profil)
- `PATCH /api/users/me/` (modifier profil)
- `PUT /api/users/me/` (modifier profil)

Payload pour `PATCH/PUT`:
- selon le role:
  - admin: `AdminUserSerializer` (role editable)
  - agent/user: `UserSerializer` (role read only)

Champs typiques (admin):
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "role": "admin | user",
  "password": "string (min 8, optionnel)"
}
```

Champs typiques (agent/user):
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string (min 8, optionnel)"
}
```

## 5) Creation entreprise (Entreprise)

### 5.1 Creer une entreprise (ADMIN)
Endpoint:
- `POST /api/entreprises/`

Permission:
- seul `admin` peut creer
- un `superadmin` ne peut pas creer via ce route

Important:
- apres creation, le backend cree automatiquement un `Membership` pour l'admin createur

Body (EntrepriseSerializer fields='__all__'; en pratique utilisez les champs du modele):
```json
{
  "nom": "string",
  "secteur": "string",
  "pays": "string",
  "adresse": "string",
  "telephone": "string",
  "email": "string",
  "nif": "string",
  "responsable": "string",
  "has_branches": true,
  "slogan": "string (optionnel)",
  "logo": "file (optionnel: multipart/form-data)"
}
```

### 5.2 Update entreprise / Delete entreprise
Les payloads sont les memes que la creation (champ par champ).
Le delete est autorise selon permission RBAC (voir `EntreprisePermission`).

## 6) Creation succursale (Succursale)

### 6.1 Creer une succursale (ADMIN)
Endpoint:
- `POST /api/succursales/`

Permission:
- admin uniquement (superadmin et user agent ne peuvent pas)

Important:
- vous NE devez pas envoyer `entreprise` dans le payload:
  - le backend fixe `entreprise` depuis le tenant courant (`request.tenant_id` ou `user.get_entreprise_id()`)

Body:
```json
{
  "nom": "string",
  "adresse": "string (optionnel)",
  "telephone": "string (optionnel)",
  "email": "string (optionnel)",
  "is_active": true
}
```

### 6.2 Update / Delete succursale
Meme logique: update autorise uniquement admin; delete passe a `is_active=false`.

## 7) Payloads metier (POST) - pour tester A a Z
Cette section donne les structures des bodies `POST` les plus importantes.

### 7.1 Devises (Devise)
Endpoint:
- `POST /api/devises/`

Body:
```json
{
  "sigle": "string",
  "nom": "string",
  "symbole": "string",
  "est_principal": true
}
```

Notes:
- `entreprise` est fixe par le tenant (via `perform_create`)
- si `est_principal=true`, le backend desactive les autres devises principales de la meme entreprise

### 7.2 Types d'articles (TypeArticle)
Endpoint:
- `POST /api/typearticles/`

Body:
```json
{
  "libelle": "string",
  "description": "string (optionnel)"
}
```

### 7.3 Sous-types (SousTypeArticle)
Endpoint:
- `POST /api/soustypearticles/`

Body:
```json
{
  "libelle": "string",
  "description": "string (optionnel)",
  "type_article_id": 1
}
```

### 7.4 Unites (Unite)
Endpoint:
- `POST /api/unites/`

Body:
```json
{
  "libelle": "string",
  "description": "string (optionnel)"
}
```

### 7.5 Articles (Article)
Endpoint:
- `POST /api/articles/`

Body (ArticleSerializer):
```json
{
  "nom_scientifique": "string",
  "nom_commercial": "string (optionnel, peut etre null/empty)",
  "sous_type_article_id": 1,
  "unite_id": 1,
  "emplacement": "string (optionnel)"
}
```

Notes:
- `article_id` est genere si absent
- le backend cree aussi automatiquement un `Stock` a Qte=0 et seuilAlert=0

### 7.6 Client (Client)
Endpoint:
- `POST /api/clients/`

Body:
```json
{
  "nom": "string",
  "telephone": "string (optionnel)",
  "adresse": "string (optionnel)",
  "email": "string (optionnel)"
}
```

Notes:
- `id` du client est genere lors de create via `ClientSerializer`

### 7.7 Entree (approvisionnement) - creation custom
Endpoint:
- `POST /api/entrees/`

Body:
```json
{
  "libele": "string (optionnel)",
  "description": "string (optionnel)",
  "lignes": [
    {
      "article_id": "string (article_id code)",
      "quantite": 10,
      "prix_unitaire": 500.00,
      "prix_vente": 1200.00,
      "seuil_alerte": 0,
      "devise_id": 1,
      "date_expiration": "YYYY-MM-DD (optionnel)"
    }
  ]
}
```

Regles importantes:
- `lignes` doit contenir au moins 1 element
- `prix_vente` est obligatoire et doit etre > 0
- `quantite` doit etre > 0
- `seuil_alerte` est obligatoire (a fournir meme a 0) car le serializer le valide
- `devise_id` est optionnel; si absent, le backend utilise la devise principale de l'entreprise du tenant

Effets backend:
- cree `Entree` + `LigneEntree` (avec quantite_restante initialisee)
- met a jour `Stock.Qte`
- cree `MouvementCaisse` de type `SORTIE` (depense) par devise si total > 0
- refuse si solde caisse insuffisant par devise (tenant scope)

### 7.8 Sortie (vente) - creation custom
Endpoint:
- `POST /api/sorties/`

Body:
```json
{
  "motif": "string (optionnel)",
  "statut": "PAYEE | EN_CREDIT",
  "client_id": "CLI0001 (optionnel; requis si EN_CREDIT dans votre flux UI/Excel)",
  "lignes": [
    {
      "article_id": "string (article_id code)",
      "quantite": 3,
      "prix_unitaire": 1200.00,
      "devise_id": 1
    }
  ]
}
```

Regles importantes:
- `lignes` obligatoire (au moins une ligne dans la logique custom)
- chaque ligne doit fournir une devise (`devise_id` ou champ `devise` compatible)
- backend consomme le stock via FIFO sur `LigneEntree.quantite_restante`
- met a jour `Stock.Qte`
- cree `MouvementCaisse` de type `ENTREE`
  - si `statut=PAYEE`: montant = total
  - si `statut=EN_CREDIT`: montant = 0 (dans la creation sortie)

Dettes:
- la creation `DetteClient` est faite dans le workflow Excel `import-sortie` (selon votre flux)
- si vous gerez dettes via API, utilisez `POST /api/dettes/` + `POST /api/paiements-dettes/`

### 7.9 DetteClient
Endpoint:
- `POST /api/dettes/`

Body (DetteClientSerializer):
```json
{
  "client_id": "CLI0001",
  "sortie_id": 123,
  "montant_total": 5000.00,
  "montant_paye": 0.00,
  "devise_id": 1,
  "date_echeance": "YYYY-MM-DD (optionnel)",
  "commentaire": "string (optionnel)"
}
```

Regle:
- le backend impose que la sortie referencee ait `statut=EN_CREDIT` pour creer une dette

### 7.10 Paiement dette
Endpoint:
- `POST /api/paiements-dettes/`

Body (PaiementDetteSerializer):
```json
{
  "dette_id": 99,
  "montant_paye": 1500.00,
  "moyen": "Cash | Mobile Money | Cheque",
  "reference": "string (optionnel)",
  "devise_id": 1
}
```

Effets:
- le backend met a jour `DetteClient` (solde restant + statut)
- le backend cree automatiquement un `MouvementCaisse` de type `ENTREE` associe au tenant de la dette

### 7.11 MouvementCaisse (caisse manuelle)
Endpoint:
- `POST /api/mouvements-caisse/`

Body:
```json
{
  "type": "ENTREE | SORTIE",
  "montant": 100.00,
  "devise_id": 1,
  "motif": "string",
  "moyen": "Cash",
  "reference_piece": "string (optionnel)",
  "sortie_id": 123 (optionnel),
  "entree_id": 456 (optionnel)
}
```

Regles:
- si `type=SORTIE` et montant > 0: le backend verifie le solde caisse disponible (tenant + succursale) pour la devise
- si `devise_id` n'est pas fourni, la devise principale est utilisee (attention: le serializer a aussi des validations, donc envoyer `devise_id` est le plus sur)

### 7.12 Import Excel - payloads

#### A) Import approvisionnement
Endpoint:
- `POST /api/import-excel/import-approvisionnement/`

Content-Type:
- `multipart/form-data`

Form-data:
 - `file`: `xlsx` (obligatoire)

Colonnes attendues dans la feuille:
- `article_id`, `quantite`, `prix_unitaire`, `prix_vente`, `devise_id`, `seuil_alerte`, `date_expiration` (selection selon valeurs)

#### B) Import articles
Endpoint:
- `POST /api/import-excel/import-articles/`

Form-data:
 - `file`: `xlsx` (obligatoire)

Feuille obligatoire:
- `Articles`

#### C) Import sorties (ventes)
Endpoint:
- `POST /api/import-excel/import-sortie/`

Form-data:
- `file`: `xlsx` (obligatoire)
- `motif`: `string` (optionnel, default "Import Excel")

Feuille obligatoire:
- `Sortie`

Colonnes attendues (dans la feuille):
- `statut`, `motif`, `client_id`, `article_id`, `quantite`, `prix_unitaire` (optionnel), `devise_id` (optionnel)

## 8) Plan de test A a Z (backend + isolation)
1. Login + select-context: verifier que l'entreprise et la succursale sont bien prises en compte
2. Multi-tenant isolation:
   - creer article + stock entreprise A
   - creer/consulter liste stock en entreprise B: doit etre vide
3. Creation:
   - creer compte public
   - superadmin assign entreprise
   - admin cree entreprise
   - admin cree succursale
4. Metier:
   - creer devises principales + secondaires
   - creer articles + stock
   - importer approvisionnement (entree) -> stock + caisse
   - vendre (sortie) -> FIFO + caisse
   - vendre EN_CREDIT -> dette creee via import-sortie
   - payer dette -> mouvement caisse ENTREE
5. Rapports + PDFs:
   - generer inventaire, bon entree, clients dettes, bon achat, fiche stock
   - verifier que les donnees correspondent toujours au tenant courant

## 9) Remarque importante
Les schemas "read/write" peuvent evoluer si des serializers ou validations differentes s'appliquent selon endpoints. Pour un contrat 100% exact cote TypeScript, vous pouvez egalement exploiter `Swagger`:
- `GET /api/swagger/` ou `/swagger/` (selon configuration)

