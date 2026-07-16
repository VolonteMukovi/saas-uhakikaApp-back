# Refonte Workflow Réquisition → Approvisionnement

Ce document formalise l'évolution du module `Réquisitions` vers un workflow d'achat complet, en conservant la logique métier existante et en évitant toute régression sur les modules `Approvisionnements`, `Stock`, `Inventaire`, `Ventes` et `Rapports`.

## Objectif métier

Transformer la réquisition en point d'entrée du cycle d'achat :

1. Analyse du stock
2. Création de la réquisition
3. Validation de la réquisition
4. Transformation en approvisionnement
5. Réception réelle fournisseur
6. Entrée en stock (workflow approvisionnement existant)

La réquisition reste une intention d'achat, l'approvisionnement représente la réalité de livraison.

## Principes non négociables

- Ne pas dupliquer la logique d'approvisionnement existante.
- Une réquisition transformée doit devenir un approvisionnement standard.
- Les validations, lots, conversions, dates d'expiration, calculs de coûts et impacts stock restent gérés par les services actuels d'approvisionnement.
- Le pré-remplissage doit être intelligent mais toujours éditable.

## 1) Conditionnement obligatoire dans les lignes de réquisition

### Nouveau besoin

Chaque ligne de réquisition doit porter un `conditionnement` explicite :

- article
- conditionnement choisi
- quantité demandée dans ce conditionnement

Exemple : `Coca` / `Carton 24` / `5`.

### Contrat métier

- La quantité demandée est exprimée dans le conditionnement sélectionné.
- Les lignes libres peuvent garder un mode texte si aucun article n'existe encore.
- Pour une ligne liée à un article existant, le conditionnement doit être sélectionnable parmi les conditionnements actifs de l'article.

## 2) Action "Transformer en approvisionnement"

### Règle d'affichage

Le bouton `Transformer en approvisionnement` apparaît uniquement quand :

- réquisition `VALIDEE`
- non encore transformée (ou partiellement transformée selon stratégie choisie)
- utilisateur autorisé à créer un approvisionnement

### Résultat attendu

L'action crée un brouillon d'approvisionnement pré-rempli avec :

- en-tête (entreprise, succursale, référence, commentaire)
- lignes issues de la réquisition
- conditionnement, quantités, prix suggérés

## 3) Gestion des écarts de livraison (réalité fournisseur)

Une fois le brouillon d'approvisionnement créé depuis réquisition, l'utilisateur peut :

- modifier les quantités reçues
- supprimer les lignes non livrées
- ajouter des lignes oubliées

Le document final d'approvisionnement reflète la livraison réelle.

## 4) Pré-remplissage intelligent des prix

### Prix d'achat

Par défaut, proposer le dernier prix d'achat du couple :

- article
- conditionnement

### Prix de vente

Par défaut, proposer le dernier prix de vente du même couple :

- article
- conditionnement

L'utilisateur peut modifier ces prix avant validation.

## 5) Historique de prix par conditionnement

Le système doit considérer chaque conditionnement comme une référence prix distincte :

- `Coca` + `Carton 24` != `Coca` + `Pack 6` != `Coca` + `Unité`

Les suggestions de prix doivent donc venir de l'historique au niveau conditionnement, pas uniquement article.

## 6) Héritage strict du workflow approvisionnement existant

Après transformation, l'approvisionnement suit exactement le flux manuel déjà en production :

- validations backend
- création / mise à jour lots
- gestion expirations
- valorisation coûts
- mouvements de stock
- historique et rapports

La réquisition ne remplace pas ce flux, elle l'initialise.

## 7) Traçabilité bidirectionnelle

### Lien de filiation

Chaque approvisionnement issu de réquisition doit conserver :

- `source_requisition_id`
- `source_requisition_numero`

Et chaque réquisition doit exposer :

- la/les références d'approvisionnement créées
- statut de transformation (`non_transformee`, `partiellement_transformee`, `transformee`)

### Exemples

- Réquisition `REQ-2026-00012`
- Approvisionnement `APP-2026-00035`
- relation : `APP-2026-00035` issu de `REQ-2026-00012`

## 8) Réutilisation composants/services existants

Le formulaire approvisionnement ouvert depuis réquisition réutilise :

- mêmes composants UI d'approvisionnement
- mêmes serializers/backend validations
- mêmes services métier de calcul

La différence : les champs arrivent pré-remplis.

## Architecture technique recommandée (backend)

### Endpoints

- `POST /api/requisitions/{id}/transform-to-approvisionnement/`
  - crée un approvisionnement brouillon pré-rempli
  - retourne l'identifiant + payload de redirection édition
- `GET /api/requisitions/{id}/transformation-preview/` (optionnel)
  - retourne le draft calculé sans persistance (validation amont UI)

### Modélisation minimale

- Ajouter sur approvisionnement :
  - `source_requisition` (FK nullable)
  - `source_requisition_numero` (copie lisible)
- Ajouter sur réquisition :
  - `transformation_status`
  - `transformed_at`
  - compteur ou relation vers approvisionnements générés

### Service métier

Créer un service unique, ex. `transform_requisition_to_approvisionnement(...)` :

1. vérifie statut réquisition
2. mappe les lignes réquisition vers lignes approvisionnement
3. résout conditionnement et prix par historique conditionnement
4. crée le brouillon approvisionnement
5. journalise l'action (historique réquisition + audit approvisionnement)

## Règles de sécurité et cohérence

- opération atomique (`transaction.atomic`)
- idempotence (éviter doublons si double clic)
- contrôle permissions tenant/succursale
- messages clairs en cas de conditionnement manquant

## Cas limites à traiter

- ligne article sans conditionnement valide
- ligne libre sans article réel (conserver en ligne libre approvisionnement ou ignorer avec avertissement selon règle)
- historique prix inexistant pour conditionnement (mettre 0 ou vide selon logique actuelle approvisionnement)
- réquisition déjà transformée

## Plan de tests (minimum)

1. Transformation d'une réquisition validée avec 3 lignes et conditionnements distincts.
2. Vérification pré-remplissage prix achat/vente par conditionnement.
3. Modification des quantités reçues avant validation approvisionnement.
4. Suppression d'une ligne non livrée.
5. Ajout d'une ligne oubliée.
6. Vérification impact stock identique au flux manuel.
7. Vérification traçabilité bidirectionnelle.
8. Vérification permissions et isolation multi-tenant.

## Résultat cible

`Réquisitions` devient le module d'expression du besoin d'achat, et `Approvisionnements` reste le module d'exécution réelle fournisseur, avec continuité complète et traçabilité native de bout en bout.

