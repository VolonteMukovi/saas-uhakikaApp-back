# Internationalisation (i18n) – Backend Django

Ce document décrit l’implémentation de l’internationalisation côté **backend** (API Django), alignée avec le frontend qui envoie la langue via l’en-tête **`Accept-Language`** (`fr` ou `en`).

## 1. Principe

- Le **frontend** envoie `Accept-Language: fr` ou `Accept-Language: en` sur chaque requête.
- Le **backend** lit cet en-tête, active la langue pour la requête, et renvoie tous les **messages système** (erreurs, validations, réponses API) dans cette langue.
- Les **données issues de la BDD** ne sont jamais traduites ; seuls les textes générés par le serveur le sont.

## 2. Ce qui a été mis en place

### 2.1 Configuration (`config/settings.py`)

- **`LANGUAGE_CODE`** : `"fr"` (langue par défaut).
- **`LANGUAGES`** : `[("fr", "Français"), ("en", "English")]`.
- **`LOCALE_PATHS`** : `[BASE_DIR / "locale"]` (fichiers `.po` / `.mo`).
- **`SUPPORTED_LANG_CODES`** : `["fr", "en"]`.
- **`DEFAULT_LANG_FOR_API`** : `"fr"` (si la langue demandée n’est pas supportée).

### 2.2 Middleware (`config/middleware.py`)

- **`AcceptLanguageMiddleware`** : lit `HTTP_ACCEPT_LANGUAGE`, en extrait un code supporté (`fr` ou `en`), puis appelle `translation.activate(lang)` pour la durée de la requête.
- Placé après `SessionMiddleware` dans `MIDDLEWARE`.

### 2.3 Messages marqués pour traduction

Les chaînes destinées à l’utilisateur sont passées par **`gettext`** (`from django.utils.translation import gettext as _`) dans :

- **`stock/permissions.py`** : messages `PermissionDenied`.
- **`stock/serializers.py`** : messages de `ValidationError` (devise, quantité, montant, dette, etc.).
- **`stock/views.py`** : messages d’erreur / réponses (entreprises, etc.).
- **`users/views.py`** : messages d’erreur (entreprise requise, entreprise introuvable).
- **`users/serializers.py`** : message de validation (mots de passe).
- **`import_excel/views.py`** : message « Aucun fichier envoyé ».

D’autres messages dans `stock/views.py` et `import_excel/views.py` peuvent être progressivement enveloppés avec `_()` au même endroit.

## 3. Génération et compilation des traductions

### 3.1 Créer / mettre à jour les catalogues

À la racine du projet :

```bash
python manage.py makemessages -l fr -l en --ignore=env
```

Les fichiers générés sont dans :  
`locale/fr/LC_MESSAGES/django.po` et `locale/en/LC_MESSAGES/django.po`.

### 3.2 Renseigner les traductions

Éditer les fichiers `.po` : pour chaque `msgid` (texte source, en général en français), renseigner `msgstr` pour l’anglais dans `locale/en/LC_MESSAGES/django.po`. Laisser `msgstr ""` pour le français si la source est déjà en français.

### 3.3 Compiler les catalogues

```bash
python manage.py compilemessages
```

Cela génère les `.mo` utilisés à l’exécution.

## 4. Bonnes pratiques

- **Nouveaux messages** : toujours utiliser `_("...")` pour tout message d’erreur, de validation ou de réponse API destiné à l’utilisateur.
- **Variables dans les messages** : utiliser des placeholders, par exemple  
  `_("Message avec %(variable)s") % {"variable": valeur}`.
- **Données métier** : ne pas traduire le contenu venant de la BDD (noms de clients, libellés saisis, etc.) ; les renvoyer tels quels.

## 5. Synchronisation avec le frontend

| Étape | Frontend | Backend |
|-------|----------|---------|
| 1. Langue choisie | Met à jour URL, localStorage, i18n (FR/EN) | — |
| 2. Requête API | Envoie `Accept-Language: fr` ou `en` | Reçoit l’en-tête |
| 3. Traitement | — | `AcceptLanguageMiddleware` active la langue |
| 4. Réponse | Affiche données + messages | Données BDD inchangées ; messages (erreurs, validation, etc.) dans la langue demandée |

Pour plus de détails sur le comportement du frontend et la règle « données BDD non traduites / messages système traduits », se référer au guide **Internationalisation (i18n) – Guide Frontend / Backend** fourni avec le projet.
