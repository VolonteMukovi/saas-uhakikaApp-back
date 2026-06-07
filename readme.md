<p align="center">
  <strong>UHAKIKAAPP</strong><br>
  <em>Certitude. Fiabilité. Assurance.</em><br>
  Solution professionnelle de gestion commerciale, stock, caisse et pilotage d'entreprise
</p>

---

# UHAKIKAAPP — Documentation officielle et commerciale

> **UHAKIKAAPP** est une plateforme moderne de gestion d'entreprise conçue pour offrir **certitude**, **fiabilité** et **contrôle** sur l'ensemble des activités commerciales. Le nom vient du mot swahili **« Uhakika »**, qui signifie en français **certitude**, **fiabilité**, **assurance** ou **garantie** — valeurs au cœur de notre solution.

Ce document constitue la **documentation officielle et commerciale** de l'application. Il présente l'ensemble des fonctionnalités disponibles dans le backend API, de la création d'une entreprise jusqu'à l'exploitation complète du système. Il est destiné aux **clients potentiels**, **partenaires**, **équipes commerciales** et **intégrateurs techniques** souhaitant déployer UHAKIKAAPP via une interface web, mobile ou un système tiers.

---

## Table des matières

1. [Présentation générale de UHAKIKAAPP](#1-présentation-générale-de-uhakikaapp)
2. [À qui s'adresse l'application ?](#2-à-qui-sadresse-lapplication-)
3. [Problèmes que l'application résout](#3-problèmes-que-lapplication-résout)
4. [Fonctionnalités principales](#4-fonctionnalités-principales)
5. [Lecture de code-barres *(module prévu)*](#5-lecture-de-code-barres--module-prévu)
6. [Système d'abonnement *(module prévu)*](#6-système-dabonnement--module-prévu)
7. [Présentation de l'API](#7-présentation-de-lapi)
8. [Avantages de UHAKIKAAPP](#8-avantages-de-uhakikaapp)
9. [Cas d'utilisation concrets](#9-cas-dutilisation-concrets)
10. [Architecture technique](#10-architecture-technique)
11. [Démarrage rapide](#11-démarrage-rapide)
12. [Conclusion](#12-conclusion)

---

## 1. Présentation générale de UHAKIKAAPP

### 1.1 Vision et mission

**UHAKIKAAPP** est une solution **SaaS multi-entreprise** (multi-tenant) qui centralise la gestion opérationnelle et financière des structures commerciales. Elle permet de piloter en temps réel :

- le **catalogue produits** ;
- les **stocks** par lots avec méthode **FIFO** (premier entré, premier sorti) ;
- les **ventes** au comptant et **à crédit** ;
- la **caisse multi-devises** ;
- les **approvisionnements** et **achats fournisseurs** ;
- les **commandes clients** avec livraison automatique ;
- les **dettes** et **recouvrements** ;
- les **rapports PDF** professionnels ;
- un **portail client** autonome.

### 1.2 Ce que signifie « Uhakika »

| Terme swahili | Signification | Impact dans l'application |
|---------------|---------------|-------------------------|
| **Uhakika** | Certitude, fiabilité | Données fiables, calculs traçables, décisions éclairées |
| **Assurance** | Garantie de qualité | Sécurité des accès, isolation des données par entreprise |
| **Contrôle** | Maîtrise totale | Suivi stock, caisse, dettes et bénéfices en temps réel |

### 1.3 Valeurs portées par la solution

| Valeur | Description |
|--------|-------------|
| **Fiabilité** | Stock calculé automatiquement à chaque entrée et sortie ; marges tracées lot par lot |
| **Contrôle** | Rôles admin/agent, périmètre par succursale, vérification des soldes caisse |
| **Transparence** | Rapports PDF, journal des opérations, historique des paiements et dettes |
| **Rapidité** | Recherche full-text articles/clients, tableaux de bord, impression POS |
| **Sécurité** | Authentification JWT, isolation multi-tenant, sessions contextualisées |
| **Simplicité** | API REST documentée (Swagger/ReDoc), import Excel, workflows guidés |

### 1.4 Positionnement

UHAKIKAAPP n'est pas un simple carnet de ventes : c'est une **plateforme de gestion intégrée** qui relie chaque opération commerciale à son impact sur le **stock**, la **caisse** et la **rentabilité**. Chaque entreprise dispose de son propre espace isolé, avec ses articles, utilisateurs, ventes, rapports et paramètres.

---

## 2. À qui s'adresse l'application ?

UHAKIKAAPP s'adresse à toute structure qui gère des **produits**, des **ventes**, des **clients** et des **flux financiers**.

| Type de structure | Usage typique |
|-------------------|---------------|
| **Boutiques** | Catalogue, ventes, factures, dettes clients |
| **Magasins** | Stock multi-rayons, caisse, rapports journaliers |
| **Cantines** | Approvisionnements, ventes quotidiennes, suivi des sorties |
| **Supermarchés** | Gestion volumineuse du stock, alertes rupture, expiration |
| **PME** | Multi-utilisateurs, permissions, pilotage financier |
| **Dépôts** | Entrées/sorties, lots fournisseurs, valorisation stock |
| **Pharmacies** | Suivi des dates d'expiration, alertes DLC |
| **Librairies** | Classification par types/sous-types, recherche rapide |
| **Organisations** | Multi-succursales, rapports consolidés par site |
| **Commerces de détail** | Vente à crédit, recouvrement, portail client |

> **En résumé** : si votre activité implique d'**acheter**, de **stocker**, de **vendre** et d'**encaisser**, UHAKIKAAPP est conçue pour vous.

---

## 3. Problèmes que l'application résout

Les entreprises locales rencontrent souvent les mêmes difficultés. UHAKIKAAPP y répond de manière structurée.

| Problème rencontré | Conséquence | Solution UHAKIKAAPP |
|--------------------|-----------|---------------------|
| Mauvaise gestion des stocks | Ruptures, surstock, pertes | Stock temps réel, seuils d'alerte, statuts NORMAL / ALERTE / RUPTURE |
| Absence de suivi entrées/sorties | Inventaires erronés | Entrées et sorties tracées, lots FIFO, fiche stock par article |
| Pertes non contrôlées | Marges inconnues | Bénéfices par lot (`BeneficeLot`), rapport ventes avec marges |
| Confusion dans les ventes | Erreurs de caisse | Ventes structurées, lien automatique stock + caisse |
| Absence de rapports fiables | Décisions à l'aveugle | 8+ rapports PDF + journal complet + tableaux de bord |
| Mauvaise gestion des dettes | Impayés oubliés | Dettes client, statuts EN_COURS / PAYEE / RETARD, paiements tracés |
| Erreurs dans la caisse | Écarts financiers | Mouvements ENTREE/SORTIE par devise, contrôle des soldes |
| Absence de traçabilité | Responsabilité floue | Contexte JWT (utilisateur, entreprise, succursale), liens mouvements ↔ opérations |
| Bénéfice réel inconnu | Pilotage approximatif | Endpoint bénéfices totaux avec évaluation de performance |
| Manque d'historique | Difficulté d'audit | Journal PDF, historique paiements dettes, fil de discussion commandes |
| Suivi utilisateurs difficile | Risques de fraude | Rôles admin/agent, périmètre succursale (`UserBranch`) |

---

## 4. Fonctionnalités principales

Cette section décrit **toutes les fonctionnalités implémentées** dans le backend UHAKIKAAPP, dans l'ordre logique d'utilisation : de la création de l'entreprise jusqu'au pilotage avancé.

---

### 4.1 Gestion des entreprises

#### Objectif

Chaque client UHAKIKAAPP opère dans le cadre d'une **entreprise** (tenant). C'est l'unité fondamentale d'isolation des données.

#### Informations enregistrées

| Champ | Description |
|-------|-------------|
| **Nom** | Raison sociale ou nom commercial |
| **Secteur d'activité** | Domaine d'activité de l'entreprise |
| **Adresse** | Localisation physique |
| **Pays** | Pays d'exploitation |
| **Téléphone** | Contact principal |
| **Email** | Adresse de contact officielle |
| **NIF** | Numéro d'identification fiscale |
| **Responsable** | Personne responsable de l'entreprise |
| **Logo** | Image affichée sur factures et rapports PDF |
| **Slogan** | Devise ou slogan (en-tête des documents) |
| **Succursales** | Option `has_branches` pour activer le multi-sites |

#### Création et gestion

1. L'utilisateur s'inscrit (`POST /api/users/`).
2. Il se connecte (`POST /api/auth/`).
3. Il crée son entreprise (`POST /api/entreprises/`) — un **membership admin** est créé automatiquement.
4. Il peut activer les **succursales** et créer des points de vente (`POST /api/succursales/`).

#### Avantages

- Chaque entreprise possède **ses propres** articles, utilisateurs, stocks, ventes, achats, rapports et paramètres.
- Les données d'une entreprise sont **totalement isolées** des autres.
- Le branding (logo, slogan) professionnalise les documents commerciaux.

#### Endpoints clés

| Action | Endpoint |
|--------|----------|
| Créer une entreprise | `POST /api/entreprises/` |
| Mon entreprise (contexte) | `GET /api/entreprises/my_entreprise/` |
| Statistiques entreprise | `GET /api/entreprises/{id}/stats/` |
| Utilisateurs de l'entreprise | `GET /api/entreprises/{id}/users/` |

---

### 4.2 Gestion des succursales (multi-sites)

#### Objectif

Pour les entreprises disposant de plusieurs points de vente, UHAKIKAAPP permet de gérer des **succursales** indépendantes au sein du même tenant.

#### Fonctionnement

- Activation via `has_branches` sur l'entreprise.
- Chaque succursale a : nom, adresse, téléphone, email, statut actif/inactif.
- Les articles, stocks, ventes et mouvements peuvent être **scindés par succursale**.
- Les agents peuvent être limités à certaines succursales via `UserBranch`.

#### Cas d'utilisation

- Chaîne de magasins avec stocks séparés par site.
- Dépôt central + points de vente.
- Cantine avec plusieurs emplacements.

---

### 4.3 Gestion des utilisateurs, rôles et permissions

#### Objectif

UHAKIKAAPP permet à plusieurs personnes de travailler sur la même entreprise, chacune avec un **périmètre d'action défini**.

#### Rôles implémentés dans le système

| Rôle technique | Équivalent métier courant | Périmètre |
|----------------|---------------------------|-----------|
| **Super administrateur** (`is_superuser`) | Administrateur plateforme | Supervision globale, gestion utilisateurs transverse |
| **Administrateur** (`Membership.role = admin`) | Directeur, gérant, propriétaire | Contrôle total sur **son** entreprise |
| **Agent / Employé** (`Membership.role = user`) | Caissier, guichetier, agent stock, agent vente | Opérations métier selon succursales autorisées |
| **Client portail** (`Client` + JWT dédié) | Client final | Consultation commandes, dettes, ventes ; création commandes |

> **Note** : Les intitulés métier (Directeur Général, Gérant, Caissier, etc.) sont des **fonctions organisationnelles** que vous attribuez en pratique aux rôles **admin** ou **agent** selon les responsabilités de chaque collaborateur.

#### Permissions par ressource

| Ressource | Admin | Agent | Superadmin |
|-----------|-------|-------|------------|
| Entreprise (paramétrage) | CRUD | Lecture seule | Supervision |
| Succursales | CRUD | Lecture | — |
| Utilisateurs | CRUD son entreprise | Profil `me` | Limité |
| Catalogue / stock / ventes / caisse | Oui | Oui (tenant/branch) | Exclu du CRUD métier |
| Fournisseurs / lots transit | Oui | Non | — |
| Commandes | Oui (+ suppression) | Statut LIVREE/REJETEE | — |
| Rapports | Oui | Oui | — |
| Portail client | — | — | — |

#### Gestion des succursales par utilisateur

- `GET/POST /api/users/{id}/succursales/` : définit les succursales autorisées et la succursale par défaut.
- Un agent ne voit que les données de **ses succursales** dans le contexte JWT.

#### Avantages

- **Sécurisation** des opérations sensibles (paramétrage, fournisseurs, suppression).
- **Responsabilisation** : chaque action est liée à l'utilisateur connecté.
- **Flexibilité** : un même utilisateur peut appartenir à plusieurs entreprises avec des rôles différents.

---

### 4.4 Authentification et sécurité

#### Système de connexion staff

| Étape | Endpoint | Description |
|-------|----------|-------------|
| Connexion | `POST /api/auth/` | Username + password → tokens JWT |
| Rafraîchissement | `POST /api/auth/refresh/` | Renouvellement avec rotation et blacklist |
| Changement de contexte | `POST /api/auth/select-context/` | Sélection entreprise/succursale → nouveaux tokens |

#### Claims JWT injectés

- `entreprise_id` — entreprise active
- `succursale_id` — succursale active (si applicable)
- `membership_id` — membership courant
- `session_start` — horodatage de session

#### Authentification portail client

| Endpoint | Description |
|----------|-------------|
| `POST /api/client-auth/login/` | Connexion email + mot de passe client |
| `POST /api/client-auth/refresh/` | Rafraîchissement token client |
| `POST /api/client-auth/select-context/` | Choix entreprise/succursale client |

#### Mesures de sécurité

| Mesure | Bénéfice |
|--------|----------|
| JWT avec expiration (48 h) | Sessions limitées dans le temps |
| Isolation multi-tenant | Impossible d'accéder aux données d'une autre entreprise |
| Permissions par rôle | Accès restreint aux fonctions sensibles |
| Contexte obligatoire | Sans entreprise valide, les endpoints métier répondent 400/403 |
| Mots de passe hashés | Stockage sécurisé (utilisateurs et clients portail) |
| Traçabilité des mouvements | Chaque mouvement caisse peut être lié à son opération source |

---

### 4.5 Gestion des articles et produits

#### Objectif

Le catalogue est le fondement de toute l'activité commerciale : ventes, stocks, rapports et commandes s'appuient sur les articles.

#### Informations d'un article

| Champ | Description |
|-------|-------------|
| **Code article** | Généré automatiquement : `XXXX####` (2 lettres type + 2 lettres sous-type + 4 chiffres) |
| **Nom scientifique** | Désignation principale du produit |
| **Nom commercial** | Nom d'usage (optionnel) |
| **Type d'article** | Catégorie principale |
| **Sous-type** | Sous-catégorie |
| **Unité de mesure** | Pièce, kg, litre, carton, etc. |
| **Emplacement** | Localisation physique en magasin/dépôt |
| **Entreprise / Succursale** | Périmètre du produit |

#### Prix et stock

Les **prix d'achat** et **prix de vente** sont définis au niveau des **lignes d'entrée** (lots), pas directement sur l'article. Cela permet une gestion fine des marges par lot d'approvisionnement.

#### Recherche avancée

- `GET /api/articles/search/?q=` — recherche full-text rapide, bornée au tenant.
- Idéale pour l'autocomplétion en caisse ou en saisie de vente.

#### Avantages

- Code article **unique et automatique** : zéro erreur de saisie manuelle.
- Classification structurée facilitant rapports et inventaires.
- Recherche instantanée pour accélérer les opérations.

---

### 4.6 Gestion des catégories, types et unités

#### Structure hiérarchique

```
Unité de mesure
Type d'article
  └── Sous-type d'article
        └── Article
```

#### Ressources

| Ressource | Endpoint | Rôle |
|-----------|----------|------|
| **Unités** | `/api/unites/` | Pièce, kg, litre, carton… |
| **Types** | `/api/typearticles/` | Catégories principales (Boissons, Alimentaire…) |
| **Sous-types** | `/api/soustypearticles/` | Sous-catégories (Sodas, Eau…) |
| **Par type** | `/api/soustypearticles/par_type/` | Liste groupée par type |

#### Avantages

- **Classement** logique du catalogue.
- **Recherche** et filtrage facilités dans les rapports.
- **Cohérence** des codes articles via le préfixe type/sous-type.

---

### 4.7 Gestion du stock

#### Objectif

Connaître en **temps réel** ce qui est disponible, ce qui manque et ce qui approche de la rupture.

#### Modèle de stock

| Élément | Description |
|---------|-------------|
| **Stock** | Quantité agrégée `Qte` par article + seuil d'alerte `seuilAlert` |
| **LigneEntree** | Lot individuel avec `quantite_restante` pour la méthode FIFO |
| **Statuts** | NORMAL (stock suffisant), ALERTE (stock faible), RUPTURE (stock nul) |

#### Méthode FIFO (Premier Entré, Premier Sorti)

Chaque approvisionnement crée un **lot**. Lors d'une vente, les lots les plus anciens sont consommés en premier. Cela garantit :

- une **valorisation correcte** du stock ;
- un calcul **fiable des marges** ;
- une **traçabilité** lot par lot.

#### Suivi des expirations

UHAKIKAAPP gère les **dates d'expiration** au niveau des lots d'entrée :

| Indicateur | Description |
|------------|-------------|
| `date_expiration` | Saisie optionnelle à chaque entrée de stock |
| Alertes 30 jours | Articles avec lot expirant dans les 30 prochains jours |
| Alertes 3 mois | Articles avec lot expirant dans les 3 prochains mois |
| Champs article | `date_expiration_proche`, `jours_avant_expiration` |

#### Statistiques stock

`GET /api/stocks/stats/` retourne :

- total articles ;
- compteurs NORMAL / ALERTE / RUPTURE ;
- articles proches expiration (30 jours et 3 mois).

#### Avantages

- **Visibilité immédiate** sur l'état du stock.
- **Anticipation** des ruptures et des expirations.
- **Valorisation** fiable pour la comptabilité de gestion.

---

### 4.8 Gestion des entrées de stock (approvisionnements)

#### Objectif

Enregistrer tout approvisionnement et **augmenter automatiquement** le stock disponible.

#### Informations d'une entrée

| Champ | Description |
|-------|-------------|
| **Libellé** | Nom de l'opération d'entrée |
| **Description** | Détails complémentaires |
| **Date** | Horodatage automatique |
| **Lignes** | Articles approvisionnés |

#### Informations d'une ligne d'entrée

| Champ | Description |
|-------|-------------|
| **Article** | Produit approvisionné |
| **Quantité** | Quantité entrée |
| **Prix d'achat unitaire** | Coût d'acquisition |
| **Prix de vente unitaire** | Prix de vente fixé pour ce lot |
| **Devise** | Monnaie de l'opération |
| **Seuil d'alerte** | Niveau d'alerte pour cet article |
| **Date d'expiration** | DLC/DLUO si applicable |

#### Impact automatique

1. Création du lot (`LigneEntree` avec `quantite_restante = quantite`).
2. **Augmentation** de `Stock.Qte`.
3. Mise à jour du `seuilAlert` de l'article.
4. **Sortie de caisse** (`MouvementCaisse SORTIE`) si le paiement est immédiat — avec vérification du solde disponible.

#### Import Excel

UHAKIKAAPP permet l'import massif d'approvisionnements via Excel :

| Action | Endpoint |
|--------|----------|
| Télécharger le modèle | `GET /api/import-excel/modele-approvisionnement/` |
| Importer le fichier | `POST /api/import-excel/import-approvisionnement/` |

#### Documents générés

- `GET /api/entrees/{id}/bon-pos/` — Bon d'entrée PDF format POS.

---

### 4.9 Gestion des sorties de stock (ventes et mouvements sortants)

#### Objectif

Enregistrer toute sortie de produits et **diminuer automatiquement** le stock.

#### Types de sorties

| Type | Statut | Description |
|------|--------|-------------|
| **Vente au comptant** | `PAYEE` | Vente encaissée immédiatement |
| **Vente à crédit** | `EN_CREDIT` | Vente avec création de dette client |
| **Livraison commande** | `PAYEE` | Sortie automatique lors du passage commande à LIVREE |
| **Sortie avec motif** | Variable | Champ `motif` pour commenter la sortie |

#### Informations d'une sortie

| Champ | Description |
|-------|-------------|
| **Client** | Client associé (optionnel) |
| **Devise** | Monnaie de la transaction |
| **Statut** | PAYEE ou EN_CREDIT |
| **Motif** | Commentaire libre |
| **Lignes** | Articles, quantités, prix unitaires encaissés |

#### Impact automatique

1. Consommation **FIFO** des lots (`LigneSortieLot`).
2. Calcul des **bénéfices par lot** (`BeneficeLot`).
3. **Diminution** de `Stock.Qte`.
4. **Entrée caisse** (`MouvementCaisse ENTREE`) — montant 0 si vente à crédit.

#### Import Excel des sorties

| Action | Endpoint |
|--------|----------|
| Modèle | `GET /api/import-excel/modele-sortie/` |
| Import | `POST /api/import-excel/import-sortie/` |

#### Documents générés

| Document | Endpoint |
|----------|----------|
| Facture PDF | `GET /api/sorties/{id}/facture-pos/` |
| Facture impression POS | `POST /api/sorties/{id}/facture-pos-print/` |
| Bon de sortie PDF | `GET /api/sorties/{id}/bon-pos/` |
| Bon de sortie impression | `POST /api/sorties/{id}/bon-pos/` |

---

### 4.10 Gestion des ventes

#### Processus complet de vente

```
1. Sélection du client (optionnel)
2. Ajout des articles et quantités
3. Définition du prix unitaire (ou prix moyen des lots FIFO)
4. Choix de la devise
5. Choix du mode : PAYEE ou EN_CREDIT
6. Validation → stock + caisse + documents mis à jour
```

#### Modes de paiement

Le champ **`moyen`** sur les mouvements de caisse accepte une valeur libre : espèces, Mobile Money, chèque, virement, etc. Un référentiel **`TypeCaisse`** permet de définir les canaux de paiement de l'entreprise.

#### Produits les plus vendus

`GET /api/sorties/produits-plus-vendus/` — classement des articles par fréquence de vente, filtrable par période (jour, mois, année, plage de dates).

#### Avantages

- Vente **rapide** et **fiable**.
- Impact **immédiat** sur stock et caisse.
- **Facture professionnelle** générée automatiquement.

---

### 4.11 Gestion des ventes à crédit et dettes clients

#### Objectif

Permettre la vente à crédit tout en **maîtrisant le recouvrement**.

#### Fonctionnement

1. Création d'une sortie avec statut **`EN_CREDIT`**.
2. Création automatique d'une **`DetteClient`** liée à la sortie.
3. Échéance par défaut : **30 jours** après la création.
4. Statuts : **EN_COURS**, **PAYEE**, **RETARD**.

#### Paiements

| Action | Endpoint |
|--------|----------|
| Enregistrer un paiement | `POST /api/paiements-dettes/` |
| Historique paiements | `GET /api/dettes/{id}/paiements/` |
| Reçu PDF | `GET /api/paiements-dettes/{id}/recu-paiement/` |

Chaque paiement crée un **`MouvementCaisse ENTREE`** lié à la dette. Le statut est recalculé automatiquement :

- **PAYEE** si solde ≤ 0 ;
- **RETARD** si échéance dépassée et solde > 0.

#### Filtres dettes

| Filtre | Endpoint |
|--------|----------|
| Dettes en cours | `GET /api/dettes/en_cours/` |
| Dettes en retard | `GET /api/dettes/en_retard/` |
| Dettes payées | `GET /api/dettes/payees/` |
| Total dettes client | `GET /api/clients/{id}/total_dettes/` |

#### Avantages

- **Fidélisation** des clients par le crédit contrôlé.
- **Suivi rigoureux** des impayés.
- **Recouvrement tracé** avec reçus PDF.

---

### 4.12 Gestion des clients

#### Objectif

Centraliser les informations clients et suivre l'historique de leurs opérations.

#### Informations client

| Champ | Description |
|-------|-------------|
| **ID** | Code auto `CLI0001`, `CLI0002`… |
| **Nom** | Nom complet ou raison sociale |
| **Téléphone** | Contact téléphonique |
| **Adresse** | Adresse physique |
| **Email** | Adresse email (connexion portail) |
| **Mot de passe** | Accès portail client (optionnel, hashé) |

#### Multi-entreprises

Un même client peut être lié à **plusieurs entreprises** via `ClientEntreprise` :

- entreprise de rattachement ;
- succursale préférée ;
- flag **`is_special`** (priorité dans les rapports dettes).

#### Création et association

| Action | Endpoint |
|--------|----------|
| Créer un client | `POST /api/clients/` (avec ou sans authentification) |
| Rechercher | `GET /api/clients/search/?q=` |
| Associer à une entreprise | `POST /api/clients/associate-entreprise/` |
| Voir les dettes | `GET /api/clients/{id}/dettes/` |

#### Portail client

Les clients disposent d'un **espace autonome** :

| Fonctionnalité | Endpoint |
|----------------|----------|
| Tableau de bord | `GET /api/client-portal/dashboard/` |
| Recherche catalogue | `GET /api/client-portal/articles/search/` |
| Mes dettes | `GET /api/client-portal/dettes/` |
| Historique paiements | `GET /api/client-portal/dettes/{id}/paiements/` |
| Mes ventes | `GET /api/client-portal/ventes/` |

---

### 4.13 Gestion des fournisseurs et achats

#### Objectif

Gérer les relations d'approvisionnement et le suivi des marchandises en transit.

#### Fournisseurs

| Champ | Description |
|-------|-------------|
| **Code** | Auto `FOU000001`… |
| **Nom** | Raison sociale |
| **Contacts** | Téléphone, email, adresse |
| **NIF** | Identification fiscale |
| **Notes** | Informations complémentaires |
| **Statut** | Actif / inactif |

Endpoint : CRUD `/api/fournisseurs/` (accès **admin** uniquement).

#### Lots en transit (achats fournisseurs)

UHAKIKAAPP gère un workflow complet d'**achat fournisseur** via les lots :

| Statut | Description |
|--------|-------------|
| **EN_TRANSIT** | Marchandise commandée, en route |
| **ARRIVE** | Marchandise arrivée au dépôt |
| **CLOTURE** | Lot intégré au stock |

**Composition d'un lot** :
- Référence et fournisseur ;
- **LotItem** : articles, quantités, prix d'achat unitaire ;
- **FraisLot** : transport, douane, manutention.

**Clôture du lot** :
- Création automatique d'une **Entrée** + lignes (prix vente, seuil, expiration) ;
- Mise à jour du **Stock** ;
- **Pas de débit caisse** (coût déjà engagé hors caisse lors du transit).

#### Avantages

- Suivi des **achats internationaux** ou longue distance.
- Intégration **propre** au stock sans double comptabilisation.
- **Traçabilité** des coûts (achat + frais).

---

### 4.14 Gestion des commandes clients

#### Objectif

Permettre aux clients de **passer commande** avant livraison, avec impact automatique sur le stock.

#### Statuts de commande

| Statut | Description |
|--------|-------------|
| **EN_ATTENTE** | Commande créée, modifiable par le client |
| **ACCEPTEE** | Commande acceptée par le staff |
| **LIVREE** | Livrée → sortie de stock automatique |
| **REJETEE** | Commande refusée |

#### Workflow

1. Le client ou l'admin crée une commande avec des lignes (article catalogue ou nom libre).
2. Le staff valide ou rejette la commande.
3. Au passage à **LIVREE** (première fois) :
   - Vérification du stock suffisant ;
   - Création automatique d'une **Sortie** (FIFO, bénéfices, caisse) ;
   - Lien `sortie_livraison` sur la commande.

#### Fil de discussion

`POST /api/commandes/{id}/reponses/` — échanges staff/client sur la commande.

#### Avantages

- **Réduction des appels** et des erreurs de saisie.
- **Traçabilité** complète commande → livraison → stock.
- **Portail client** pour l'autonomie des clients.

---

### 4.15 Gestion de la caisse

#### Objectif

Suivre **tous les flux financiers** de l'entreprise en temps réel.

#### Types de mouvements

| Type | Exemples |
|------|----------|
| **ENTREE** | Ventes encaissées, paiements dettes, dépôts |
| **SORTIE** | Achats/approvisionnements, dépenses, retraits |

#### Informations d'un mouvement

| Champ | Description |
|-------|-------------|
| **Montant** | Montant de l'opération |
| **Devise** | Monnaie utilisée |
| **Type** | ENTREE ou SORTIE |
| **Motif** | Raison de l'opération |
| **Moyen** | Mode de paiement (Cash, Mobile Money…) |
| **Lien générique** | Référence vers sortie, entrée ou dette source |

#### Tableau de bord caisse

| Endpoint | Description |
|----------|-------------|
| `GET /api/mouvements-caisse/tableau-bord/` | Soldes multi-devises + 10 derniers mouvements |
| `GET /api/mouvements-caisse/solde/` | Soldes par devise |
| `GET /api/mouvements-caisse/resume/` | Statistiques détaillées |
| `GET /api/mouvements-caisse/comparaison-devises/` | Volumes et pourcentages par devise |
| `GET /api/mouvements-caisse/mouvements-par-devise/` | Mouvements filtrés par devise |
| `GET /api/mouvements-caisse/solde/pdf/` | État de caisse PDF |
| `GET /api/mouvements-caisse/export/` | Export CSV |

#### Règles métier

- **Sortie manuelle** : vérification du solde disponible par devise.
- **Vente à crédit** : mouvement caisse avec montant 0.
- **Approvisionnement** : sortie caisse si paiement immédiat ; erreur si solde insuffisant.

#### Avantages

- **Vision claire** de la trésorerie par devise.
- **Contrôle** des dépenses et encaissements.
- **Documents PDF** pour la comptabilité.

---

### 4.16 Gestion des devises

#### Objectif

Supporter les entreprises opérant avec **plusieurs monnaies**.

#### Fonctionnement

| Élément | Description |
|---------|-------------|
| **Devise principale** | Une seule devise `est_principal = true` par entreprise |
| **Devises secondaires** | Autres monnaies acceptées |
| **Champs** | Sigle, nom, symbole |
| **Soldes caisse** | Calculés **séparément par devise** (pas de fusion automatique) |

#### Limitation actuelle

> **Important** : La gestion des **taux de change** et la **conversion automatique** entre devises ne sont pas encore pleinement opérationnelles dans cette version. Les montants sont enregistrés et suivis dans leur devise d'origine. La conversion inter-devises est prévue dans une évolution future.

#### Avantages

- Adaptation aux réalités des entreprises **multi-devises** (USD, CDF, EUR…).
- Suivi **distinct** de chaque monnaie en caisse.

---

### 4.17 Gestion des rapports

UHAKIKAAPP propose une suite complète de **rapports JSON** (pour tableaux de bord et intégrations) et **PDF** (pour impression et archivage).

#### Tableau des rapports disponibles

| Rapport | JSON | PDF | Rôle et utilité |
|---------|------|-----|-----------------|
| **Inventaire** | `/api/rapports/rapports/inventaire/` | `.../inventaire/pdf/` | État complet du stock : quantités, seuils, statuts. Filtres par type, période, statut. **Décision** : réapprovisionnement, inventaire physique. |
| **Bon d'entrée (réquisition)** | `/api/rapports/rapports/bon-entree/` | `.../bon-entree/pdf/` | Liste des articles en rupture ou alerte à commander. **Décision** : planifier les achats. |
| **Bon d'achat** | `/api/rapports/rapports/bon-achat/` | `.../bon-achat/pdf/` | Détail des approvisionnements par période ou par entrée. **Décision** : contrôler les achats. |
| **Dettes client (détail)** | `/api/rapports/rapports/clients-dettes/` | `.../clients-dettes/pdf/` | Toutes les dettes d'un client avec produits vendus. **Décision** : relance ciblée. |
| **Dettes générales** | `/api/rapports/rapports/clients-dettes-general/` | `.../clients-dettes-general/pdf/` | Synthèse de tous les clients avec solde > 0. Filtre clients spéciaux. **Décision** : vue globale du recouvrement. |
| **Rapport des ventes** | `/api/rapports/rapports/ventes/` | `.../ventes/pdf/` | Lignes de vente, FIFO, bénéfices par période. **Décision** : analyser la performance commerciale. |
| **Fiche stock** | `/api/rapports/rapports/{id}/fiche-stock/json/` | `.../fiche-stock/` | Mouvements chronologiques FIFO d'un article. **Décision** : audit d'un produit spécifique. |
| **Journal complet** | — | `/api/rapports/journal/` | PDF unifié : entrées, ventes, caisse, paiements dettes. **Décision** : audit global de la période. |

#### Rapports complémentaires (endpoints dédiés)

| Rapport | Endpoint | Utilité |
|---------|----------|---------|
| **Statistiques stock** | `GET /api/stocks/stats/` | Ruptures, alertes, expirations |
| **Bénéfices totaux** | `GET /api/entrees/benefices-totaux/` | Gains/pertes, top 10 articles, évaluation performance |
| **Produits plus vendus** | `GET /api/sorties/produits-plus-vendus/` | Classement des best-sellers |
| **État caisse** | `GET /api/mouvements-caisse/solde/pdf/` | Situation financière |
| **Stats entreprise** | `GET /api/entreprises/{id}/stats/` | Compteurs globaux |

#### Évaluation de performance (bénéfices)

| Statut | Condition |
|--------|-----------|
| **EXCELLENTE** | Résultat net très positif |
| **NEUTRE** | Résultat équilibré |
| **A_SURVEILLER** | Pertes modérées |
| **PREOCCUPANTE** | Pertes significatives |
| **CRITIQUE** | Pertes critiques |

#### En-têtes professionnels

Tous les PDF incluent le **logo**, le **nom**, le **slogan** et le **téléphone** de l'entreprise.

---

### 4.18 Factures, reçus et impression POS

#### Objectif

Professionnaliser les transactions et fournir des **preuves** aux clients.

#### Documents disponibles

| Document | Format | Usage |
|----------|--------|-------|
| **Facture client** | PDF 80 mm | Preuve de vente détaillée |
| **Facture client** | ESC/POS (ticket) | Impression directe sur imprimante thermique |
| **Bon de sortie** | PDF / ESC/POS | Justificatif de sortie stock |
| **Bon d'entrée** | PDF | Justificatif d'approvisionnement |
| **Reçu de paiement** | PDF | Preuve de paiement d'une dette |
| **État de caisse** | PDF | Situation financière |

#### Configuration imprimante POS

Variables d'environnement : `POS_PRINTER_PORT`, `POS_PRINTER_BACKEND=serial`, etc.

#### Avantages

- Image **professionnelle** auprès des clients.
- **Conformité** et traçabilité des transactions.
- **Rapidité** en caisse grâce à l'impression thermique.

---

### 4.19 Tableau de bord et statistiques

#### Indicateurs disponibles

| Indicateur | Source |
|------------|--------|
| Chiffre d'affaires / ventes | Rapport ventes, sorties |
| Stock disponible | `/api/stocks/`, `/api/stocks/stats/` |
| Total entrées / sorties | Stats entreprise, journal |
| Dettes en cours | `/api/dettes/en_cours/` |
| Caisse par devise | `/api/mouvements-caisse/solde/` |
| Bénéfice | `/api/entrees/benefices-totaux/` |
| Produits les plus vendus | `/api/sorties/produits-plus-vendus/` |
| Alertes stock | NORMAL / ALERTE / RUPTURE |
| Expirations proches | Stats stock (30j / 3 mois) |
| Portail client | `/api/client-portal/dashboard/` |

#### Avantages

- **Décisions rapides** basées sur des données réelles.
- **Anticipation** des problèmes (ruptures, dettes, expirations).
- **Pilotage** quotidien, mensuel et annuel.

---

### 4.20 Historique, audit et traçabilité

#### Mécanismes de traçabilité

| Mécanisme | Description |
|-----------|-------------|
| **Contexte JWT** | Chaque requête est liée à un utilisateur, une entreprise et une succursale |
| **Horodatage** | Date et heure sur toutes les opérations (entrées, sorties, mouvements) |
| **Liens génériques** | Mouvements caisse liés à leur opération source (sortie, entrée, dette) |
| **FIFO lot par lot** | `LigneSortieLot` trace quel lot a été consommé |
| **Bénéfices par lot** | `BeneficeLot` enregistre la marge de chaque vente |
| **Journal PDF** | Document unifié de toutes les opérations |
| **Fil commandes** | `CommandeResponse` conserve les échanges |
| **Logs suppressions** | Fichier `logs/stock_suppressions.log` pour les articles supprimés |

#### Limitation actuelle

> Un **module d'audit complet** (historique de toutes les modifications par entité, versioning) n'est pas encore implémenté. La traçabilité actuelle repose sur les liens entre opérations, les horodatages et le journal PDF.

---

### 4.21 Import Excel (données en masse)

#### Objectif

Accélérer l'intégration initiale ou les opérations récurrentes de masse.

| Opération | Modèle | Import |
|-----------|--------|--------|
| **Articles** | `GET .../modele-articles/` | `POST .../import-articles/` |
| **Approvisionnements** | `GET .../modele-approvisionnement/` | `POST .../import-approvisionnement/` |
| **Sorties / ventes** | `GET .../modele-sortie/` | `POST .../import-sortie/` |

#### Avantages

- **Migration rapide** depuis un ancien système ou des fichiers Excel existants.
- **Gain de temps** pour les inventaires initiaux.
- **Réduction des erreurs** de saisie manuelle.

---

## 5. Lecture de code-barres *(module prévu)*

> **Statut** : Fonctionnalité **planifiée** pour une prochaine version. Les dépendances techniques (`qrcode`, `reportlab.graphics.barcode`) sont déjà présentes dans le projet, mais le scan et l'association code-barres ↔ article ne sont pas encore actifs.

### Objectif

Intégrer un **lecteur de code-barres** pour accélérer et fiabiliser les opérations quotidiennes en magasin.

### Bénéfices attendus

| Bénéfice | Description |
|----------|-------------|
| **Enregistrement rapide** | Scanner un produit pour le créer ou l'identifier instantanément |
| **Recherche instantanée** | Retrouver un article en scannant son code |
| **Vente accélérée** | Ajouter un produit au panier par scan en caisse |
| **Réduction des erreurs** | Fini les fautes de frappe sur les noms ou codes |
| **Identification automatique** | Chaque produit associé à un code-barres unique |
| **Gain de temps** | Les caissiers traitent plus de clients par heure |
| **Expérience moderne** | Interface comparable aux solutions des supermarchés et pharmacies |

### Fonctionnement prévu

1. Chaque article pourra être associé à un **code-barres unique** (EAN-13, Code 128, QR…).
2. Lors du scan, le système retrouvera automatiquement l'article correspondant.
3. Intégration dans : création d'articles, recherche, vente à la caisse, inventaire.

### Public cible

Boutiques, magasins, supermarchés, pharmacies, librairies — toute structure avec un volume de transactions élevé.

---

## 6. Système d'abonnement *(module prévu)*

> **Statut** : Fonctionnalité **planifiée** pour le modèle commercial SaaS. Le backend actuel ne contient pas encore de module de facturation ou de gestion d'abonnements. Les formules ci-dessous sont des **propositions commerciales** destinées à structurer l'offre.

### Objectif

Proposer des **abonnements mensuels et annuels** permettant aux entreprises d'accéder à UHAKIKAAPP selon leurs besoins et leur taille.

### Formules proposées

#### Formule Starter — Petites boutiques

| | Détail |
|---|--------|
| **Prix** | **10 USD/mois** ou **100 USD/an** |
| **Entreprises** | 1 |
| **Utilisateurs** | 2 maximum |
| **Inclus** | Articles simples, stock simple, ventes simples, rapports de base, factures simples |
| **Non inclus** | Multi-succursale, rapports avancés, statistiques avancées, code-barres, permissions avancées |

#### Formule Standard — Entreprises en croissance

| | Détail |
|---|--------|
| **Prix** | **25 USD/mois** ou **250 USD/an** |
| **Entreprises** | 1 |
| **Utilisateurs** | Jusqu'à 5 |
| **Inclus** | Gestion complète articles/stock, entrées/sorties, ventes, clients, dettes, caisse, rapports standards, factures PDF, impression POS, lecteur code-barres, tableau de bord standard |

#### Formule Professionnelle — PME structurées

| | Détail |
|---|--------|
| **Prix** | **50 USD/mois** ou **500 USD/an** |
| **Entreprises** | 1 |
| **Utilisateurs** | Jusqu'à 15 |
| **Inclus** | Rôles et permissions avancés, stock FIFO complet, multi-devises, rapports avancés, statistiques avancées, audit et traçabilité, code-barres, impression POS, gestion dettes, suivi caisse, exports PDF, assistance prioritaire |

#### Formule Entreprise — Grandes structures

| | Détail |
|---|--------|
| **Prix** | **100 USD/mois** ou **1 000 USD/an** |
| **Utilisateurs** | Illimité |
| **Inclus** | Multi-succursales, rapports globaux, statistiques consolidées, permissions avancées, audit complet, support prioritaire, personnalisation, accompagnement technique, intégrations spécifiques |

### Tableau comparatif

| Fonctionnalité | Starter | Standard | Pro | Entreprise |
|----------------|---------|----------|-----|------------|
| Utilisateurs | 2 | 5 | 15 | Illimité |
| Multi-succursale | — | — | — | ✓ |
| Stock FIFO | Basique | ✓ | ✓ | ✓ |
| Ventes à crédit | — | ✓ | ✓ | ✓ |
| Rapports PDF | Basique | Standard | Avancé | Complet |
| Code-barres | — | ✓ | ✓ | ✓ |
| Portail client | — | ✓ | ✓ | ✓ |
| Multi-devises | — | — | ✓ | ✓ |
| Import Excel | — | ✓ | ✓ | ✓ |
| Support | Email | Email | Prioritaire | Dédié |

> **Note** : Les prix sont **estimatifs** et peuvent être adaptés selon le pays, la taille de l'entreprise, le volume de données et les besoins spécifiques du client. Des remises annuelles et des tarifs locaux pourront être proposés.

---

## 7. Présentation de l'API

### Une API moderne et documentée

UHAKIKAAPP expose une **API REST** complète, conçue pour être consommée par :

- une **application web** (React, Vue, Angular…) ;
- une **application mobile** (Flutter, React Native…) ;
- un **système externe** (ERP, comptabilité, e-commerce…).

### Préfixe et documentation

| Élément | URL |
|---------|-----|
| Préfixe API | `/api/` |
| Swagger UI (test interactif) | `/swagger/` |
| ReDoc (lecture) | `/redoc/` |
| Schéma OpenAPI | `/swagger.json` |

### Domaines couverts par l'API

| Domaine | Endpoints principaux |
|---------|---------------------|
| **Authentification** | `/api/auth/`, `/api/auth/refresh/`, `/api/auth/select-context/` |
| **Entreprises** | `/api/entreprises/`, `/api/succursales/` |
| **Utilisateurs** | `/api/users/`, `/api/users/me/` |
| **Catalogue** | `/api/articles/`, `/api/unites/`, `/api/typearticles/` |
| **Stock** | `/api/stocks/`, `/api/entrees/`, `/api/sorties/` |
| **Caisse** | `/api/mouvements-caisse/`, `/api/types-caisse/` |
| **Clients & dettes** | `/api/clients/`, `/api/dettes/`, `/api/paiements-dettes/` |
| **Fournisseurs & achats** | `/api/fournisseurs/`, `/api/lots/` |
| **Commandes** | `/api/commandes/` |
| **Rapports** | `/api/rapports/rapports/...` |
| **Portail client** | `/api/client-auth/...`, `/api/client-portal/...` |
| **Import Excel** | `/api/import-excel/...` |

### Avantages d'une architecture API

| Avantage | Description |
|----------|-------------|
| **Flexibilité** | Frontend web, mobile ou desktop au choix |
| **Évolutivité** | Ajout de fonctionnalités sans refonte du frontend |
| **Intégration facile** | Connexion à des systèmes tiers via HTTP/JSON |
| **Séparation frontend/backend** | Équipes parallèles, maintenance simplifiée |
| **Application mobile** | Possibilité de créer une app mobile native plus tard |
| **Sécurité** | JWT, isolation tenant, permissions granulaires |
| **Documentation** | Swagger/ReDoc pour onboarding rapide des développeurs |

### Guide d'intégration

Un guide pas à pas pour les équipes frontend est disponible :

**[`docs/GUIDE_INTEGRATION_FRONTEND.md`](docs/GUIDE_INTEGRATION_FRONTEND.md)**

---

## 8. Avantages de UHAKIKAAPP

| Avantage | Impact pour votre entreprise |
|----------|------------------------------|
| **Solution complète** | Stock, ventes, caisse, dettes, achats, rapports — tout en un |
| **Interface moderne** | API REST prête pour un frontend responsive et intuitif |
| **Gestion fiable** | FIFO, calculs automatiques, contrôles de solde |
| **Gain de temps** | Recherche rapide, import Excel, impression POS, portail client |
| **Réduction des erreurs** | Codes auto, validation stock, liens automatiques stock ↔ caisse |
| **Suivi en temps réel** | Stock, caisse et dettes mis à jour à chaque opération |
| **Meilleure visibilité** | Tableaux de bord, statistiques, alertes rupture et expiration |
| **Rapports professionnels** | PDF avec logo et branding, prêts pour la direction |
| **Meilleure prise de décision** | Bénéfices, top produits, dettes, état caisse |
| **Sécurité des données** | Isolation multi-tenant, JWT, rôles et permissions |
| **Traçabilité** | Journal, liens mouvements, FIFO lot par lot |
| **Adaptation locale** | Multi-devises, Mobile Money, contexte africain et international |
| **Évolutivité** | Code-barres et abonnements prévus, API extensible |
| **Portail client** | Autonomie des clients, réduction de la charge du staff |
| **Multi-succursales** | Gestion de plusieurs points de vente dans un même tenant |

---

## 9. Cas d'utilisation concrets

### Exemple 1 : Boutique de quartier

**Contexte** : Une boutique de vêtements gère 200 articles, 50 clients réguliers et 2 vendeuses.

**Utilisation UHAKIKAAPP** :
1. Création de l'entreprise et du catalogue (types : Homme, Femme, Enfant).
2. Approvisionnements enregistrés avec prix d'achat et de vente.
3. Ventes quotidiennes avec factures PDF.
4. Ventes à crédit pour les clients fidèles → suivi des dettes et paiements partiels.
5. Rapport mensuel des ventes et produits les plus vendus.

**Résultat** : La propriétaire connaît son stock, ses impayés et son chiffre d'affaires en temps réel.

---

### Exemple 2 : Cantine scolaire

**Contexte** : Une cantine approvisionne des denrées alimentaires et sert 300 repas par jour.

**Utilisation UHAKIKAAPP** :
1. Articles classés par type (Viandes, Légumes, Boissons).
2. Entrées de stock avec dates d'expiration.
3. Sorties journalières liées aux ventes.
4. Alertes sur les produits proches de l'expiration (30 jours).
5. Rapport mensuel des approvisionnements et des ventes.

**Résultat** : Réduction du gaspillage alimentaire, maîtrise des coûts, rapports pour la direction.

---

### Exemple 3 : Magasin avec caisse rapide

**Contexte** : Un magasin d'électronique traite un flux élevé de ventes en caisse.

**Utilisation UHAKIKAAPP** :
1. Catalogue complet avec codes articles automatiques.
2. Ventes rapides via recherche full-text.
3. Impression de tickets POS sur imprimante thermique 58 mm.
4. *(Futur)* Scan code-barres pour identification instantanée des produits.
5. Tableau de bord caisse en fin de journée.

**Résultat** : File d'attente réduite, erreurs de saisie éliminées, traçabilité complète.

---

### Exemple 4 : PME multi-utilisateurs

**Contexte** : Une PME de distribution a un gérant, 3 agents de vente, 1 agent de stock et 2 succursales.

**Utilisation UHAKIKAAPP** :
1. Entreprise avec `has_branches` activé et 2 succursales.
2. Rôles : gérant (admin), agents (user) limités à leur succursale.
3. Lots fournisseurs en transit → clôture → stock mis à jour.
4. Ventes à crédit avec recouvrement et rapports dettes.
5. Bénéfices totaux avec évaluation de performance mensuelle.
6. Portail client pour les commandes en ligne.

**Résultat** : Pilotage stratégique, contrôle des permissions, vision consolidée de l'activité.

---

## 10. Architecture technique

| Composant | Technologie |
|-----------|-------------|
| Framework backend | **Django 5.2** |
| API REST | **Django REST Framework 3.16** |
| Authentification | **JWT** (SimpleJWT) — staff et client |
| Base de données | **MySQL / MariaDB** (PyMySQL, utf8mb4) |
| Documentation API | **drf-yasg** (Swagger / ReDoc) |
| PDF | **ReportLab** |
| Excel | **openpyxl** |
| Impression POS | **python-escpos** + pyserial |
| Configuration | **python-decouple** (`.env`) |
| CORS | **django-cors-headers** |
| Internationalisation | Français (défaut) + Anglais |

### Applications Django

| App | Responsabilité |
|-----|----------------|
| `config` | Configuration, URLs, middleware, pagination |
| `users` | Utilisateurs, memberships, JWT, succursales par user |
| `stock` | Cœur métier : catalogue, stock, ventes, caisse, clients, dettes |
| `order` | Fournisseurs, lots transit, commandes, portail client |
| `rapports` | Rapports JSON et PDF |
| `import_excel` | Import massif Excel |
| `pos` | Service d'impression ESC/POS |

---

## 11. Démarrage rapide

### Prérequis

- Python 3.10+
- MySQL ou MariaDB (utf8mb4)
- pip

### Installation

```bash
# Cloner le dépôt
git clone <url-du-depot>
cd saas-uhakikaApp-back

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou : venv\Scripts\activate  # Windows

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env : SECRET_KEY, DATABASE_*, ALLOWED_HOSTS

# Base de données
python manage.py migrate

# Super administrateur
python manage.py createsuperuser

# Lancer le serveur
python manage.py runserver
```

### Accès

| Service | URL |
|---------|-----|
| API | `http://localhost:8000/api/` |
| Swagger | `http://localhost:8000/swagger/` |
| ReDoc | `http://localhost:8000/redoc/` |
| Admin Django | `http://localhost:8000/admin/` |

### Flux d'intégration type

```
1. POST /api/users/          → Inscription
2. POST /api/auth/           → Connexion
3. POST /api/entreprises/    → Création entreprise
4. POST /api/auth/select-context/  → Sélection contexte
5. POST /api/articles/       → Création articles
6. POST /api/entrees/        → Approvisionnement
7. POST /api/sorties/        → Vente
8. GET  /api/rapports/rapports/inventaire/pdf/  → Rapport
```

---

## 12. Conclusion

**UHAKIKAAPP** incarne la **certitude** dans la gestion d'entreprise. Du mot swahili « Uhakika » à chaque fonctionnalité de la plateforme, la promesse est la même : offrir aux commerces, PME et organisations une solution **fiable**, **sécurisée** et **professionnelle** pour maîtriser leurs activités quotidiennes.

### Ce que UHAKIKAAPP vous apporte dès aujourd'hui

- Un **catalogue structuré** avec codes automatiques et recherche instantanée.
- Un **stock fiable** géré par lots FIFO, avec alertes rupture et expiration.
- Des **ventes traçables** au comptant et à crédit, liées automatiquement à la caisse.
- Une **caisse multi-devises** avec tableaux de bord et exports PDF.
- Des **dettes maîtrisées** avec recouvrement, statuts et reçus.
- Des **achats fournisseurs** avec suivi en transit et clôture propre.
- Des **commandes clients** avec livraison automatique et portail dédié.
- Des **rapports PDF professionnels** pour piloter votre activité.
- Une **API REST documentée** prête pour vos interfaces web et mobiles.

### Ce que UHAKIKAAPP prépare pour demain

- La **lecture de code-barres** pour des opérations de caisse ultra-rapides.
- Un **système d'abonnement** flexible adapté à chaque taille d'entreprise.
- L'**évolution continue** vers une plateforme de gestion commerciale de référence.

---

<p align="center">
  <strong>UHAKIKAAPP</strong> — Parce que votre entreprise mérite la certitude.<br>
  <em>Documentation officielle — Backend API</em><br>
  <em>Dernière mise à jour : juin 2026</em>
</p>

---

*Ce document est basé sur le code source du dépôt `saas-uhakikaApp-back`. Les fonctionnalités marquées « module prévu » sont planifiées et seront intégrées dans les prochaines versions.*
