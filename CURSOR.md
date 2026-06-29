# Manifeste d'Architecture : Ne pas réinventer HTTP

Ce document définit les règles de développement absolues pour la conception des APIs et la consommation des ressources. Il est interdit de réinventer les mécanismes de transport, de cache ou de sécurité : le protocole HTTP natif doit être exploité à 100 % de son potentiel.

---

## 1. Optimisation du Cache Applicatif & Réduction des Transferts

### Backend (API)
- **Règle :** Tout endpoint retournant des données de consultation (lectures lourdes, listes, profils) doit implémenter la validation par jeton d'entité (`ETag`).
- **Implémentation :** Générer un hash cryptographique basé sur le contenu ou le timestamp de mise à jour de la ressource. Le renvoyer dans l'en-tête `ETag`. Si le client fournit un en-tête `If-None-Match` correspondant au hash actuel, stopper immédiatement le traitement et renvoyer un statut **`304 Not Modified`** avec un corps vide.

### Frontend (React TS)
- **Règle :** Respecter scrupuleusement les en-têtes de cache serveur et optimiser les requêtes réseau.
- **Implémentation :** Configurer le client HTTP (Axios) pour stocker et transmettre automatiquement l'en-tête `If-None-Match` contenant l' `ETag` reçu lors de la précédente lecture réussie. Intercepter le statut `304` pour réutiliser instantanément la donnée du cache local sans altérer l'expérience utilisateur.

---

## 2. Prévention de l'Écrasement Concurrent (Lost Update)

### Backend (API)
- **Règle :** Interdiction d'appliquer aveuglément des requêtes de modification (`PUT`, `PATCH`) sans validation de l'état initial.
- **Implémentation :** Exiger la présence de l'en-tête `If-Match` pour toutes les écritures sur des ressources partagées ou critiques. Comparer la valeur reçue avec l' `ETag` ou le jeton de version de la base de données. En cas de désalignement, rejeter la transaction avec un statut **`412 Precondition Failed`**.

### Frontend (React TS)
- **Règle :** Toute modification de formulaire doit être conditionnée par l'état exact de la ressource au moment de sa lecture.
- **Implémentation :** Lors du chargement d'une ressource, capturer l' `ETag` fourni par l'API. Lors de la soumission de la modification, injecter obligatoirement cet identifiant dans l'en-tête `If-Match`. En cas d'erreur `412`, bloquer l'interface, avertir l'utilisateur que la donnée a été modifiée ailleurs, et proposer un rafraîchissement.

---

## 3. Garantie d'Idempotence sur les Écritures Critiques

### Backend (API)
- **Règle :** Protéger les routes non idempotentes (`POST`) contre les effets de bord des défaillances réseau (timeouts, clics répétés).
- **Implémentation :** Intercepter l'en-tête standardisé `Idempotency-Key`. Vérifier la présence de cette clé dans un stockage temporaire rapide (ex: cache mémoire/Redis). Si la clé est en cours de traitement, retourner **`409 Conflict`**. Si le traitement est terminé, renvoyer immédiatement la réponse historisée en cache sans réexécuter la logique métier ni altérer la base de données.

### Frontend (React TS)
- **Règle :** Sécuriser l'envoi de chaque action critique (création de compte, transaction financière, validation de stock).
- **Implémentation :** Utiliser un intercepteur Axios pour générer un UUID unique (`v4`) inséré dans l'en-tête `Idempotency-Key` à chaque soumission de formulaire de mutation (`POST`). Ce jeton doit rester identique si l'application React réessaye automatiquement la requête après un timeout réseau.

---

## 4. Streaming & Reprise de Téléchargement

### Backend (API)
- **Règle :** Interdiction de charger des fichiers volumineux ou des flux de données intégralement en mémoire RAM avant envoi.
- **Implémentation :** Envoyer les fichiers sous forme de flux binaires (*streaming*) en incluant l'en-tête `Accept-Ranges: bytes`. Prendre en compte l'en-tête `Range` envoyé par le client pour segmenter la lecture du fichier et renvoyer uniquement les octets demandés avec un statut **`206 Partial Content`** et l'en-tête `Content-Range`.

### Frontend (React TS)
- **Règle :** Optimiser la lecture de contenus médias et gérer la résilience des téléchargements lourds.
- **Implémentation :** Pour l'affichage de vidéos ou le téléchargement de fichiers massifs, formater les requêtes en découpant les besoins via l'en-tête `Range: bytes=X-Y`. En cas de déconnexion, lire la taille du fichier partiellement récupérée et initier la requête de reprise à partir de l'octet exact d'interruption.

---

## 5. Standardisation Absolue des Erreurs

### Backend (API)
- **Règle :** Bannir les formats d'erreurs customisés, arbitraires ou textuels. L'API doit parler un langage universel.
- **Implémentation :** Formater toutes les exceptions applicatives et techniques selon la spécification **RFC 9457**. Renvoyer obligatoirement le Content-Type `application/problem+json` associé à un objet JSON contenant les clés : `type` (URI explicative), `title` (erreur générique), `status` (code HTTP), `detail` (contexte de l'erreur) et `instance` (URI de la requête).

### Frontend (React TS)
- **Règle :** Centraliser et automatiser le traitement des erreurs réseau pour éliminer la redondance de code dans l'UI.
- **Intercepteur global :** Configurer un intercepteur de réponse Axios qui détecte le Content-Type `application/problem+json`. Mapper cet objet standardisé vers un composant de notification global (Toast/Alert) pour afficher dynamiquement le message contenu dans la clé `detail` de la RFC 9457.

---

## 6. Versionnage par Négociation de Contenu

### Backend (API)
- **Règle :** Maintenir l'unicité des URIs pour respecter les contraintes REST fondamentales. Ne jamais inclure de version dans le chemin de l'URL (Ex: pas de `/api/v1/`).
- **Implémentation :** Utiliser la négociation de contenu via l'en-tête HTTP standard `Accept` (Ex: `Accept: application/json; version=2.0`). Router dynamiquement la logique vers le sérialiseur ou le contrôleur adéquat en fonction de la version extraite de l'en-tête.

### Frontend (React TS)
- **Règle :** Déclarer explicitement la version du modèle de données attendue lors des appels à l'API.
- **Implémentation :** Configurer l'instance Axios globale pour injecter la version cible du contrat d'interface dans l'en-tête `Accept` de chaque requête sortante, assurant une parfaite étanchéité face aux futures évolutions de l'API.

---

## 7. Pagination Scalable par Curseur

### Backend (API)
- **Règle :** Interdire la pagination par décalage (`Offset / Limit` ou par numéro de page) sur les tables à forte volumétrie afin de garantir des requêtes SQL s'exécutant en temps constant $O(1)$.
- **Implémentation :** Implémenter une pagination basée sur un curseur opaque (généralement un identifiant ou un timestamp encodé). Générer les liens de navigation `next` et `previous` contenant ce curseur et appliquer un filtrage SQL direct (`WHERE id < curseur LIMIT X`) sur des colonnes indexées.

### Frontend (React TS)
- **Règle :** Consommer les flux paginés de manière fluide sans perte de performance.
- **Implémentation :** Structurer les états des listes pour extraire les curseurs de pagination (`next_cursor`) fournis dans la réponse de l'API. Passer ce curseur de manière transparente comme paramètre d'URL lors des demandes de défilement infini ou de changement de page.

---

## 8. Observabilité Avancée (Correlation-ID)

### Backend (API)
- **Règle :** Rendre chaque cycle de traitement de requête traçable, de l'entrée dans le middleware jusqu'à l'accès en base de données.
- **Implémentation :** Extraire l'en-tête `X-Correlation-ID` de la requête entrante (ou en générer un si absent). Injecter cet identifiant unique (UUID) dans le contexte d'exécution local du thread afin qu'il apparaisse automatiquement dans **chaque ligne de log** générée. Renvoyer cet ID dans les en-têtes de la réponse HTTP.

### Frontend (React TS)
- **Règle :** Assurer la traçabilité des incidents de l'action utilisateur jusqu'au cœur du serveur.
- **Implémentation :** À chaque cycle de requête initié dans l'intercepteur Axios, générer un identifiant unique universel (`X-Correlation-ID`). En cas d'erreur HTTP majeure, capturer cet identifiant pour l'afficher explicitement à l'écran de l'utilisateur sous la forme d'un code de suivi de bug pour le support technique.

---

## Implémentation backend (état actuel)

| # | Règle | Module / middleware |
|---|--------|---------------------|
| 1 | ETag / 304 | `config.http.etag.ETagMiddleware` |
| 2 | If-Match / 412 / 428 | `config.http.preconditions` (patch global `ModelViewSet`) |
| 3 | Idempotency-Key | `config.http.idempotency.IdempotencyMiddleware` + `CACHES` |
| 4 | Range / 206 | `config.http.streaming` (+ ETag middleware sur PDF/CSV) |
| 5 | RFC 9457 | `config.http.problem_details.exception_handler` |
| 6 | Accept version | `config.http.versioning.ApiVersionMiddleware` → en-tête `API-Version` |
| 7 | Curseur | `config.pagination.UhakikaCursorPagination` (défaut DRF) |
| 8 | Correlation-ID | `config.http.correlation.CorrelationIdMiddleware` + logs |

En-têtes client : `If-None-Match`, `If-Match`, `Idempotency-Key`, `Accept: application/json; version=1.0`, `X-Correlation-ID`, `Range`, paramètre `?cursor=`.