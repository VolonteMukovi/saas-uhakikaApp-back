# Uhakika — Plateforme de gestion d’entreprise, stock et caisse

**Uhakika** est une solution logicielle **SaaS multi-tenant** conçue pour les commerces, dépôts, cantines et PME qui doivent **piloter le stock en temps réel**, **encaisser sur plusieurs devises et canaux de caisse**, **gérer la vente à crédit**, **suivre les approvisionnements** (y compris depuis l’import Excel ou les lots en transit) et **offrir un portail client** (commandes, historique, dettes).

Ce dépôt contient le **backend API** (Django 5 + Django REST Framework). Il expose une API REST documentée (**Swagger** / **ReDoc**, schéma OpenAPI) et sert de socle à des applications web ou mobiles « front ».

---

## Table des matières

1. [Vision produit](#1-vision-produit)
2. [Architecture technique](#2-architecture-technique)
3. [Multi-tenant, contexte et sécurité](#3-multi-tenant-contexte-et-sécurité)
4. [Acteurs et rôles](#4-acteurs-et-rôles)
5. [Modules applicatifs](#5-modules-applicatifs)
6. [Processus métier (de bout en bout)](#6-processus-métier-de-bout-en-bout)
7. [Fonctionnalités détaillées par domaine](#7-fonctionnalités-détaillées-par-domaine)
8. [API, internationalisation et rapports](#8-api-internationalisation-et-rapports)
9. [Pour aller plus loin](#9-pour-aller-plus-loin)

---

## 1. Vision produit

### 1.1 Ce que Uhakika résout

| Besoin | Réponse dans la plateforme |
|--------|----------------------------|
| Savoir **ce qu’il reste** en rayon ou en réserve | Stock global par article + **lots d’entrée** avec **FIFO** (premier entré, premier sorti) |
| **Acheter** et **vendre** en traçant les marges | Entrées / sorties, **coût d’achat** et **prix de vente** par lot, **bénéfices par lot** |
| **Encaisser** et suivre la **caisse** | Mouvements **ENTREE** / **SORTIE**, multi-devises, **types de caisse** (multicaisse), pièces justificatives |
| Vendre **à crédit** et **recouvrer** | **Dettes client**, statuts, **paiements** liés à la caisse |
| **Commandes** avant livraison | **Commandes** (statuts), passage à **livrée** → **sortie de stock automatique** (même logique qu’une vente) |
| **Marchandise en route** | **Lots** fournisseur (transit → arrivée → **clôture** avec **entrée stock** sans double débit caisse) |
| **Décisionnel** | **Rapports** (inventaire, ventes, dettes, bons PDF), **tableaux de bord** caisse, **bénéfices** par période |
| **Clients autonomes** | **Portail client** (JWT dédié) : catalogue recherchable, **commandes**, **dettes**, **ventes** |

### 1.2 Positionnement SaaS

- Une **entreprise** = un **tenant** : les données sont **isolées** (articles, stock, ventes, caisse, etc.).
- Les **succursales** (optionnelles) permettent de **scinder** catalogue, stock et périmètre des **agents**.
- **Plusieurs utilisateurs** peuvent travailler sur la même entreprise avec des **rôles** différents (admin / agent).
- Les **clients finaux** peuvent disposer d’un **compte portail** lié à une ou plusieurs entreprises (liaison `ClientEntreprise`).

---

## 2. Architecture technique

| Couche | Technologie |
|--------|-------------|
| Framework | **Django 5.2** |
| API | **Django REST Framework** (viewsets, serializers, pagination) |
| Auth staff | **JWT** (`djangorestframework-simplejwt`) avec **claims** `entreprise_id`, `succursale_id`, `membership_id` |
| Auth portail client | **JWT client** dédié (`ClientJWTAuthentication`) |
| Documentation API | **drf-yasg** — `/swagger/`, `/redoc/`, `swagger.json` |
| Base de données | **MySQL** ou **MariaDB** (via **PyMySQL** en mode MySQLdb) |
| Configuration | **python-decouple** (`.env`), option **`DATABASE_URL`**, charset **utf8mb4** |
| Fichiers / médias | Logos entreprise, images types de caisse (stockage `MEDIA`) |
| Import masse | **openpyxl** — feuilles Excel pour **approvisionnement** |

Le projet est organisé en **applications Django** : `config`, `users`, `stock`, `order`, `rapports`, `import_excel`.

---

## 3. Multi-tenant, contexte et sécurité

### 3.1 Entreprise et succursale

- Chaque enregistrement métier majeur est rattaché à une **`Entreprise`**.
- Si `has_branches` est activé, des **`Succursale`** précisent le site (magasin, dépôt).
- Les **articles**, **entrées**, **sorties**, **mouvements de caisse**, etc. respectent ce **périmètre** selon les filtres du code (tenant + branche dans le JWT ou paramètres).

### 3.2 JWT staff et sélection de contexte

1. **Connexion** : `POST /api/auth/` → tokens + premier **membership** actif injecté dans le refresh.
2. **Changement d’entreprise / succursale** : `POST /api/auth/select-context/` → nouveaux tokens avec le **contexte** voulu.

Sans contexte entreprise valide, la plupart des endpoints métier répondent **400** ou **403** avec un message explicite.

### 3.3 Membership et branches agents

- **`Membership`** : lien `(utilisateur, entreprise)` + **`role`** `admin` ou `user` (agent).
- **`UserBranch`** : pour un agent, liste des **succursales autorisées** ; l’**admin** voit en général toute l’entreprise.

### 3.4 Portail client

- Authentification séparée : **`/api/client-auth/login/`**, refresh, **`select-context`** (entreprise + membership client).
- Le serveur pose **`request.client`** et **`request.client_membership`** pour filtrer **commandes**, **dettes**, **ventes** et **recherche articles** au périmètre du client.

---

## 4. Acteurs et rôles

### 4.1 Super administrateur plateforme

- Compte **`is_superuser`** (créé via `createsuperuser`).
- Gestion transverse : utilisateurs, rattachements entreprises, supervision.

### 4.2 Administrateur d’entreprise (`Membership.role = admin`)

- Paramètre l’**entreprise** (logo, slogan, succursales, devises, types de caisse, etc.).
- Gère les **utilisateurs** et **agents**, le **catalogue**, les **clients**, les **entrées/sorties**, les **dettes**, les **commandes** (dont passage **livrée** / **rejetée**), les **lots** et la **clôture**.
- Peut **supprimer** des commandes (selon règles) et accède à tous les **rapports** du tenant.

### 4.3 Agent / employé (`Membership.role = user`)

- Opère dans le **périmètre succursale** (branches autorisées + contexte JWT).
- Peut **consulter** et **mettre à jour le statut** des **commandes** (livrée / rejetée), mais **pas** les supprimer (sauf règles spécifiques documentées dans l’API).
- Utilise les écrans de **vente**, **stock**, **caisse** selon les permissions des viewsets.

### 4.4 Client final (portail)

- Compte **`Client`** avec **mot de passe** optionnel pour le portail et lien **`ClientEntreprise`** (entreprise + succursale + flag **client spécial** pour certains rapports dettes).
- **Crée** et **modifie** ses **commandes** tant qu’elles sont **en attente**.
- Consulte **ses dettes**, **ses ventes** (sorties), **recherche** le catalogue autorisé.
- **Ne passe pas** par le même JWT que le staff.

---

## 5. Modules applicatifs

### 5.1 `users` — Comptes, memberships, contexte

- Inscription utilisateur, profil, **assignation** à une entreprise, gestion **succursales** par utilisateur.
- **Tokens** enrichis (session, `session_start`, claims tenant).
- Endpoints clés documentés dans **Swagger** : `users`, `login`, `auth`, `select-context`.

### 5.2 `stock` — Cœur métier (référentiel, stock, ventes, caisse, crédit)

| Ressource | Rôle |
|-----------|------|
| **Entreprise**, **Succursale** | Tenant et sites |
| **Unité**, **TypeArticle**, **SousTypeArticle**, **Article** | Catalogue (code article auto `XXXX####` par préfixe type/sous-type) |
| **Stock** | Quantité agrégée par article (alertes seuil) |
| **Entree** / **LigneEntree** | Approvisionnements par **lot** (`quantite_restante` pour FIFO) |
| **Sortie** / **LigneSortie** | Ventes ; traçabilité **LigneSortieLot** ; **BeneficeLot** |
| **Devise** | Multi-devises par entreprise (dont devise **principale**) |
| **MouvementCaisse** | Toute entrée/sortie d’argent (ventes, achats, ajustements, paiements dettes…) |
| **TypeCaisse**, **DetailMouvementCaisse** | Multicaisse (ventilation par canal) |
| **Client**, **ClientEntreprise** | Contacts et rattachement multi-entreprises / succursales |
| **DetteClient**, **PaiementDette** (logique migrée vers MouvementCaisse) | Crédit client et recouvrement |

**Actions personnalisées** (exemples) : recherche **articles** / **clients**, **stats** articles, **lots par article**, **bénéfices totaux** (période + pagination), **produits les plus vendus**, **soldes caisse**, **tableau de bord**, **mouvements par devise**, **bons POS / factures PDF**, etc.

### 5.3 `order` — Fournisseurs, lots en transit, commandes client, portail

| Ressource | Rôle |
|-----------|------|
| **Fournisseur** | Référentiel achats |
| **Lot** + **LotItem** | Expedition, articles, quantités, coûts ; statuts **EN_TRANSIT**, **ARRIVE**, **CLOTURE** |
| **FraisLot** | Frais de transport, douane, manutention (par devise) |
| **Commande** + **CommandeItem** | Pré-commande client (article catalogue **ou** nom libre) |
| **CommandeResponse** | Fil de discussion / validation interne |

**Clôture de lot** : création d’une **Entrée** + lignes (prix vente, seuil, expiration) **sans** débit caisse (coût déjà engagé « hors caisse » en transit).

**Livraison commande** : passage au statut **LIVREE** → **sortie automatique** (FIFO, stock, bénéfices, **mouvement caisse** comme une vente), lien **`sortie_livraison`** sur la commande.

**Portail** : routes sous `/api/client-auth/…`, `/api/client-portal/…`.

### 5.4 `rapports` — PDF et JSON métier

- **Inventaire** (JSON / PDF)
- **Bon d’entrée**, **bon d’achat**, **clients & dettes** (variantes générales / synthèse)
- **Rapport des ventes** (période obligatoire, **pagination SQL** sur les lignes, totaux agrégés sur la période)
- **Fiche stock** par article (PDF)

En-têtes avec **logo**, **slogan**, **téléphone** entreprise.

### 5.5 `import_excel` — Approvisionnement par fichier

- Téléchargement d’un **modèle Excel** (colonnes article, quantités, prix, devise, seuil, expiration).
- Upload : validation, création d’**Entrée** / **LigneEntree**, mise à jour **Stock**, règles de caisse selon implémentation (voir endpoints dans `import_excel`).

### 5.6 `config` — Paramètres globaux

- **`settings`** : apps installées, CORS, JWT, **DATABASES** (utf8mb4, pooling optionnel), **i18n** (fr/en), middleware **langue** (`Accept-Language`).

---

## 6. Processus métier (de bout en bout)

### 6.1 Cycle de vie d’un article

1. Création des **taxonomies** (unité, type, sous-type) si besoin.
2. Création de l’**Article** (code généré automatiquement).
3. Création éventuelle de la fiche **Stock** (souvent à la première entrée).

### 6.2 Approvisionnement classique (entrée magasin)

1. **POST** entrée avec **lignes** : quantité, **prix d’achat**, **prix de vente**, devise, seuil, date d’expiration.
2. Création des **LigneEntree** (`quantite_restante` = quantité initiale).
3. **Augmentation** de `Stock.Qte`.
4. **Sortie de caisse** (si le montant est dû immédiatement) selon règles métier de l’endpoint (solde vérifié le cas échéant).

### 6.3 Vente au comptant (ou payée)

1. **POST** sortie avec lignes : article, quantité, **prix unitaire encaissé** (optionnel ; sinon moyenne pondérée des **prix de vente des lots** consommés en FIFO).
2. Consommation **FIFO** sur `LigneEntree`, création **LigneSortieLot** et **BeneficeLot**.
3. **Diminution** `Stock.Qte`.
4. **Mouvement caisse ENTREE** par devise (sauf vente **EN_CREDIT** : montant caisse 0 mais sortie enregistrée).

### 6.4 Vente à crédit

1. Sortie avec statut **EN_CREDIT** : traçabilité stock / FIFO / bénéfices comme une vente ; **pas** d’encaissement immédiat.
2. **DetteClient** associée (montant, devise, lien sortie / client / entreprise).
3. **Paiements** : via API **paiements-dettes** → **MouvementCaisse** lié à la dette (**ENTREE**).

### 6.5 Lot fournisseur (transit → stock)

1. Création **Lot** + **LotItem** (articles, quantités, **prix d’achat**).
2. Enregistrement des **FraisLot** (transport, douane…).
3. Changement de statut jusqu’à **CLOTURE** avec payload **approvisionnement** (prix vente, seuil, expiration par ligne).
4. Service **`apply_stock_on_lot_closure`** : **Entrée** dédiée, **Stock** mis à jour, **Lot.entree_stock** renseigné ; **pas** de mouvement caisse pour ce flux (règle métier « déjà engagé »).

### 6.6 Commande client → livraison

1. **Client** ou **admin** crée une **Commande** avec **items** (quantités).
2. Statuts : **EN_ATTENTE** → **ACCEPTEE** (selon workflow) → **LIVREE** ou **REJETEE**.
3. Au passage **LIVREE** (première fois) :
   - Vérification : **toutes** les lignes ont un **article catalogue** ; stock suffisant.
   - Création **Sortie** + lignes + FIFO + **sortie_livraison** sur la commande + **caisse**.
4. Les lignes **nom libre** sans article **bloquent** la livraison automatique (message API explicite).

### 6.7 Ajustement ou annulation d’entrée

- Mise à jour d’entrée : recalcul **FIFO** / lots / stock (logique dans **EntreeViewSet** — attention aux cohérences `Stock` si ventes déjà passées).
- Annulation : **restitution** stock et mouvements de caisse associés selon implémentation.

---

## 7. Fonctionnalités détaillées par domaine

### 7.1 Stock et FIFO

- Chaque **ligne d’entrée** est un **lot** avec **quantité restante**.
- Les **sorties** consomment les lots du **plus ancien** au plus récent (`date_entree`, `id`).
- **Rapports** et **fiches** utilisent ces données pour **marge**, **bénéfice**, **valorisation**.

### 7.2 Caisse multidevise et multicanal

- **Types de caisse** : espèces, mobile money, etc. (par entreprise / succursale).
- **Mouvements** : montant, devise, type ENTREE/SORTIE, **motif**, **moyen**, **référence pièce**, lien ** générique** (`content_type` / `object_id`) vers sortie, entrée, dette…
- **Détails** historiques ou ventilation sur plusieurs types pour les anciens enregistrements.

### 7.3 Clients et recherche

- **Recherche full-text** (selon migrations MySQL) sur articles et clients (`/api/articles/search/`, `/api/clients/search/`) avec `q`, `limit`, `offset`.
- **Clients spéciaux** (`is_special`) : filtrage dédié sur certains **rapports dettes**.

### 7.4 Tableaux de bord et indicateurs

- Soldes de caisse, **comparaison devises**, **bénéfices totaux** avec **évaluation de performance** (statuts type EXCELLENTE, NEUTRE, A_SURVEILLER selon résultat net période).
- **Top produits** vendus (par **nombre de ventes** ou métriques dédiées).

### 7.5 Internationalisation

- Langues **fr** / **en** ; middleware et **gettext** sur messages d’erreur et libellés métiers.
- Endpoint de test : `/api/i18n-test/`.

---

## 8. API, internationalisation et rapports

### 8.1 Préfixe API

Toutes les routes métier sont sous **`/api/`** (voir `config/urls.py`).

Exemples :

- `/api/entreprises/`, `/api/articles/`, `/api/entrees/`, `/api/sorties/`
- `/api/mouvements-caisse/`, `/api/types-caisse/`, `/api/dettes/`
- `/api/commandes/`, `/api/lots/`, `/api/fournisseurs/`
- `/api/rapports/rapports/...` (inventaire, ventes, dettes, PDF…)
- `/api/import-excel/...`

### 8.2 Documentation interactive

| URL | Usage |
|-----|--------|
| `/swagger/` | Tester les endpoints, bouton **Authorize** |
| `/redoc/` | Lecture linéaire du schéma |
| `/swagger.json` | Export Postman, génération client |

La description générale (auth, tenant, caisse, clients) est centralisée dans **`config/openapi_description.py`**.

### 8.3 Pagination

- Liste standard : **`page`**, **`page_size`** (plafond configurable, ex. 200).
- Rapport ventes : pagination **côté SQL** + totaux période en **agrégats**.

---

## 9. Pour aller plus loin

### 9.1 Guide d’intégration frontend (détaillé)

Un guide pas à pas (inscription, login, création entreprise, `select-context`, payloads) a été conservé ici :

**[`docs/GUIDE_INTEGRATION_FRONTEND.md`](docs/GUIDE_INTEGRATION_FRONTEND.md)**

### 9.2 Configuration locale

- Copier les variables d’environnement (voir `.env` / `config/.env`) : `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_*` ou `DATABASE_URL`.
- Installer les dépendances : `pip install -r requirements.txt`
- Migrations : `python manage.py migrate`
- Serveur : `python manage.py runserver`

### 9.3 Base de données

- Prévoir **utf8mb4** pour éviter les problèmes de caractères et aligner les migrations Django.
- En cas de déploiement **MySQL/MariaDB** hébergé, vérifier les types de clés étrangères (INT/BIGINT) si bases anciennes — des migrations utilitaires peuvent être présentes dans `stock/migration_utils/`.

---

## Synthèse pour communication commerciale (Uhakika)

**Uhakika** aide les organisations à **centraliser** la gestion opérationnelle : **catalogue** structuré, **stock** fiable par **lot** et **FIFO**, **ventes** et **caisse** multi-devises, **crédit client** avec **recouvrement** tracé, **commandes** et **livraisons** qui **impactent automatiquement le stock**, **achats fournisseurs** avec **transit** et **clôture** propre, **rapports PDF** pour le pilotage, et un **portail client** pour réduire les appels et les erreurs de saisie.

Le tout dans une architecture **multi-entreprise**, **multi-succursale**, **sécurisée par JWT** et **documentée** pour une intégration rapide des équipes produit et IT.

---

*Document généré à partir du code du dépôt — à actualiser lors de nouvelles fonctionnalités.*
