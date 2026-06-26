# Gestion multi-caisse — spécification frontend

## Principe

Toute opération financière doit envoyer une **caisse** (`type_caisse_id`, alias `caisse_id` ou `caisse`) et une **session ouverte** pour cette caisse (résolue côté backend).

Les anciennes opérations ont été rattachées à la **Caisse principale** (type `CASH`) sans perte de données.

## Endpoints caisses

| Méthode | URL | Description |
|---------|-----|-------------|
| GET | `/api/types-caisse/` | Liste des caisses |
| GET | `/api/types-caisse/actives/` | Caisses actives (sélecteurs UI) |
| POST | `/api/types-caisse/` | Créer une caisse |
| GET | `/api/types-caisse/{id}/rapport-general/` | Synthèse par caisse |
| GET | `/api/types-caisse/{id}/rapport-detaille/` | Mouvements par caisse |

### Filtres liste

- `?actives_only=true`
- `?code_type=CASH|BANQUE|AIRTEL_MONEY|…`
- `?succursale_id=`

### Payload création caisse

```json
{
  "nom": "Airtel Money boutique",
  "libelle": "Airtel Money",
  "code_type": "AIRTEL_MONEY",
  "description": "Compte Airtel agence centre",
  "devise_id": 1,
  "succursale": 2,
  "is_active": true
}
```

Types recommandés : `CASH`, `BANQUE`, `AIRTEL_MONEY`, `MPESA`, `ORANGE_MONEY`, `MOBILE_MONEY`, `AUTRE`.

À la création d’une **entreprise**, une caisse `Caisse principale` / `CASH` est créée automatiquement.

## Sessions de caisse

Voir `docs/SESSIONS_CAISSE_API.md`. L’ouverture exige toujours `type_caisse_id` (une caisse précise).

Messages d’erreur backend :

- `Veuillez sélectionner une caisse avant de valider cette opération.`
- `Cette opération financière exige une caisse active.`
- `Aucune session ouverte pour cette caisse. Veuillez ouvrir la caisse avant d'effectuer cette opération.`

## Opérations à mettre à jour (champ obligatoire)

Ajouter **`type_caisse_id`** (ou `caisse_id`) dans le body :

| Flux | Endpoint |
|------|----------|
| Vente comptant | `POST /api/sorties/` |
| Annulation vente | `DELETE /api/sorties/{id}/` |
| Ajustement vente | `PATCH /api/sorties/{id}/` |
| Approvisionnement payé | `POST /api/entrees/` |
| Ajustement / annulation entrée | `PATCH` / `DELETE /api/entrees/{id}/` |
| Mouvement manuel | `POST /api/mouvements-caisse/` |
| Paiement dette | `POST /api/paiements-dettes/` |
| Livraison commande | `PATCH /api/commandes/{id}/` avec `statut: LIVREE` |
| Import Excel appro | `POST` import-excel (form `type_caisse_id`) |

**Exception** : vente à crédit (`EN_CREDIT`) avec montant caisse 0 — pas de caisse requise.

### Exemple vente comptant

```json
{
  "statut": "PAYEE",
  "type_caisse_id": 3,
  "lignes": [
    { "article_id": "ART001", "quantite": 2, "prix_unitaire": 10, "devise_id": 1 }
  ]
}
```

### Exemple paiement dette

```json
{
  "dette_id": 12,
  "montant_paye": 50,
  "type_caisse_id": 3,
  "devise_id": 1,
  "moyen": "Cash"
}
```

## UI — champ « Caisse * »

- Charger `/api/types-caisse/actives/` — chaque caisse expose `necessite_session` / `requires_session`
- Si une seule caisse : pré-sélectionner mais **toujours envoyer** `type_caisse_id`
- Filtrer par agence courante si applicable
- **Caisse cash par défaut** (`necessite_session: true`) : vérifier `GET /api/caisse/session-active/?devise_id=X&type_caisse_id=Y` avant opération cash
- **Autres caisses** (`necessite_session: false`) : pas de blocage session ; badge header cash indépendant

## Rapports

- Par session : `/api/sessions-caisse/{id}/rapport-general/` et `rapport-detaille/`
- Par caisse (toutes sessions) : `/api/types-caisse/{id}/rapport-general/` et `rapport-detaille/`
- Mouvements filtrés : `GET /api/mouvements-caisse/?type_caisse_id=3`
