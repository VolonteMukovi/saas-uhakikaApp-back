# Déploiement du multilingue (FR/EN) en production (cPanel)

Ce document décrit les **fichiers à déployer** et les **configurations nécessaires** pour que le système de traduction fonctionne correctement en ligne, comme en local.

---

## 1. Fichiers liés à la traduction à inclure dans le déploiement

### 1.1 Dossier des traductions (obligatoire)

À **uploader tel quel** à la racine du projet (à côté de `manage.py`) :

```
locale/
├── fr/
│   └── LC_MESSAGES/
│       ├── django.po    # sources des traductions FR
│       └── django.mo    # fichiers compilés (voir § 2.1)
└── en/
    └── LC_MESSAGES/
        ├── django.po    # sources des traductions EN
        └── django.mo    # fichiers compilés
```

- **`.po`** : fichiers sources (éditables). À déployer pour pouvoir recompiler plus tard.
- **`.mo`** : fichiers compilés utilisés par Django à l’exécution. **Indispensables en production** (sinon les chaînes ne seront pas traduites).

### 1.2 Fichiers de configuration et code i18n

Ces fichiers sont déjà dans le projet ; il suffit de les inclure dans l’upload habituel :

| Fichier | Rôle |
|--------|------|
| `config/settings.py` | `LANGUAGE_CODE`, `LANGUAGES`, `LOCALE_PATHS`, `USE_I18N`, `SUPPORTED_LANG_CODES`, `DEFAULT_LANG_FOR_API` |
| `config/middleware.py` | `AcceptLanguageMiddleware` (lit `Accept-Language` et `?lang=`) |
| `config/views_i18n.py` | Endpoint de test `/api/i18n-test/` |
| `config/urls.py` | Route `api/i18n-test/` |

Dans `settings.py`, vérifier que vous avez bien :

```python
LANGUAGE_CODE = "fr"
USE_I18N = True
LANGUAGES = [("fr", "Français"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
SUPPORTED_LANG_CODES = ["fr", "en"]
DEFAULT_LANG_FOR_API = "fr"
```

Et dans `MIDDLEWARE` que `AcceptLanguageMiddleware` est bien présent (idéalement juste après `CorsMiddleware`) :

```python
"config.middleware.AcceptLanguageMiddleware",
```

### 1.3 Applications qui utilisent les traductions

Aucun fichier supplémentaire “spécial” à uploader : il suffit de déployer **tout le projet** (y compris les apps qui utilisent `gettext` / `_()`), par exemple :

- `users` (serializers, views)
- `stock` (views, serializers, permissions)
- `rapports` (views, serializers, utils)
- `import_excel` (views)

Les chaînes traduites sont dans `locale/` ; le code appelle simplement `_("...")`.

---

## 2. Configurations spécifiques côté serveur

### 2.1 Compiler les fichiers de traduction (`.mo`)

Django utilise les **`.mo`** (fichiers compilés), pas uniquement les `.po`. En production il **faut** que les `.mo` existent.

**Option A – Compiler en local avant d’uploader (recommandé pour cPanel)**

Sur votre machine (environnement virtuel du projet) :

```bash
cd d:\vd\api_cantine
.venv\Scripts\activate
python manage.py compilemessages
```

Cela génère/met à jour `locale/fr/LC_MESSAGES/django.mo` et `locale/en/LC_MESSAGES/django.mo`. Uploadez ensuite tout le dossier **locale/** (avec les `.mo`) sur le serveur.

**Option B – Compiler sur le serveur**

Si vous avez accès SSH à l’hébergement (ou un “Terminal” cPanel) et que Python + Django sont disponibles :

```bash
cd /chemin/vers/votre/projet
source venv/bin/activate   # ou selon votre setup
python manage.py compilemessages
```

Vérifier que le répertoire **locale** est bien au même niveau que `manage.py` et que `LOCALE_PATHS` dans `settings.py` pointe vers ce dossier (ce qui est le cas avec `BASE_DIR / "locale"`).

### 2.2 Droits sur les fichiers

- Le compte sous lequel tourne l’application (ex. `nobody`, `apache`, utilisateur cPanel) doit avoir les droits de **lecture** sur tout le dossier `locale/` (et en particulier sur les `.mo`).
- Pas besoin d’écriture sur `locale/` en production si vous ne lancez pas `makemessages`/`compilemessages` sur le serveur.

### 2.3 Pas de configuration Apache/Nginx spécifique pour l’i18n

La langue est gérée **dans Django** (middleware + paramètre `lang` + en-tête `Accept-Language`). Aucune règle particulière (type `RewriteRule` ou `location`) n’est nécessaire pour le multilingue. Votre configuration actuelle pour faire tourner l’app (Passenger, WSGI, reverse proxy, etc.) suffit.

---

## 3. S’assurer que le changement de langue fonctionne en production

### 3.1 Comportement côté backend

- La langue est choisie **par requête** via :
  1. Paramètre de requête **`?lang=en`** ou **`?lang=fr`** (prioritaire)
  2. Sinon en-tête HTTP **`Accept-Language: en`** ou **`Accept-Language: fr`**
  3. Sinon langue par défaut : **`fr`**

Le middleware `AcceptLanguageMiddleware` active cette langue pour la requête et renvoie `Content-Language` dans la réponse.

### 3.2 Frontend : envoyer la langue choisie

Pour que la production se comporte comme en local, le frontend doit envoyer la langue à chaque requête API :

- **Méthode recommandée** : envoyer l’en-tête **`Accept-Language`** sur toutes les requêtes (fetch, axios, etc.) selon la langue sélectionnée par l’utilisateur, par exemple :
  - `Accept-Language: fr`
  - `Accept-Language: en`
- **Alternative** : ajouter **`?lang=en`** ou **`?lang=fr`** à l’URL des appels API (si votre client HTTP le permet globalement).

Exemple (JavaScript) :

```javascript
const lang = localStorage.getItem('lang') || 'fr';  // ou état React/Vue
fetch('https://votre-domaine.com/api/...', {
  headers: {
    'Authorization': 'Bearer ...',
    'Accept-Language': lang,
  },
});
```

### 3.3 Vérification rapide en production

1. **Test direct de l’API**  
   - `https://votre-domaine.com/api/i18n-test/?lang=fr`  
     → doit retourner `"message": "Bonjour"`, `"language": "fr"`.  
   - `https://votre-domaine.com/api/i18n-test/?lang=en`  
     → doit retourner `"message": "Hello"`, `"language": "en"`.

2. **Sans paramètre**  
   - Appeler sans `?lang=` : la réponse doit utiliser la langue par défaut (`fr`) ou celle envoyée par `Accept-Language` si le navigateur ou le client l’envoie.

3. **Frontend**  
   - Changer la langue dans l’interface, recharger ou naviguer : les libellés renvoyés par l’API (erreurs, messages, rapports, etc.) doivent être dans la bonne langue.

---

## 4. Checklist déploiement cPanel

- [ ] Dossier **`locale/`** uploadé avec **`fr/LC_MESSAGES/`** et **`en/LC_MESSAGES/`**.
- [ ] Fichiers **`django.mo`** présents (générés par `compilemessages` en local ou sur le serveur).
- [ ] **`config/settings.py`** avec `LOCALE_PATHS`, `LANGUAGES`, `USE_I18N`, `SUPPORTED_LANG_CODES`, `DEFAULT_LANG_FOR_API`.
- [ ] **`AcceptLanguageMiddleware`** actif dans `MIDDLEWARE`.
- [ ] Droits de **lecture** sur `locale/` pour l’utilisateur du serveur.
- [ ] Frontend envoie **`Accept-Language`** (ou `?lang=`) sur les requêtes API.
- [ ] Test manuel : **`/api/i18n-test/?lang=fr`** et **`/api/i18n-test/?lang=en`** retournent les bonnes chaînes.

Si ces points sont respectés, la fonctionnalité multilingue reste pleinement opérationnelle en production comme en local.
