# Sessions de caisse — Guide API frontend

Gestion professionnelle des **sessions de caisse** : toute opération financière doit être rattachée à une session **OUVERTE**.

> **Données existantes** : les mouvements historiques ont été rattachés à des sessions `LEGACY-*` clôturées (`est_legacy=true`). Aucune donnée n'a été supprimée.

---

## 1. Principe

| Règle | Détail |
|-------|--------|
| Session obligatoire | Vente, paiement dette, approvisionnement cash, mouvement manuel → **session OUVERTE** requise |
| Horodatage auto | `ouvert_le` / `cloture_le` = serveur (`timezone.now()`), jamais saisis manuellement |
| Une session active | Par **type de caisse + agence + devise** |
| Après clôture | Lecture seule ; nouvelles opérations → nouvelle session |

**Message d'erreur backend :**

```text
Aucune session de caisse n'est ouverte. Veuillez ouvrir une session de caisse avant d'effectuer cette opération.
```

---

## 2. Endpoints

| Action | Méthode | URL |
|--------|---------|-----|
| Lister sessions | `GET` | `/api/sessions-caisse/` |
| Détail session | `GET` | `/api/sessions-caisse/{id}/` |
| Session(s) active(s) | `GET` | `/api/sessions-caisse/active/?devise_id=1` |
| Ouvrir session | `POST` | `/api/sessions-caisse/ouvrir/` |
| Clôturer session | `POST` | `/api/sessions-caisse/{id}/cloturer/` |
| Valider écart (admin) | `POST` | `/api/sessions-caisse/{id}/valider-ecart/` |
| Rapport général | `GET` | `/api/sessions-caisse/{id}/rapport-general/` |
| Rapport détaillé | `GET` | `/api/sessions-caisse/{id}/rapport-detaille/` |
| Procès-verbal clôture | `GET` | `/api/sessions-caisse/{id}/proces-verbal/` |

Filtres liste : `?statut=OUVERTE`, `?devise_id=`, `?type_caisse_id=`

---

## 3. Ouvrir une session

`POST /api/sessions-caisse/ouvrir/`

```json
{
  "type_caisse_id": 1,
  "devise_id": 1,
  "solde_ouverture": "100.00000"
}
```

Réponse `201` : objet session avec `statut: "OUVERTE"`, `ouvert_le` auto, `numero` auto (`SESS-0001-000001`).

---

## 4. Clôturer une session

`POST /api/sessions-caisse/{id}/cloturer/`

```json
{
  "montant_physique": "495.00000",
  "commentaire": "Comptage fin de journée"
}
```

Le serveur calcule :

```text
solde_theorique = solde_ouverture + total_entrees - total_sorties
ecart = montant_physique - solde_theorique
```

| Écart | Statut session | Action |
|-------|----------------|--------|
| `0` | `CLOTUREE` | Fin |
| `≠ 0` | `CLOTUREE_EN_ATTENTE_VALIDATION` | Crée `EcartCaisse` (SURPLUS ou PERTE) |

---

## 5. Valider un écart (admin uniquement)

`POST /api/sessions-caisse/{id}/valider-ecart/`

```json
{ "valider": true, "commentaire": "Écart confirmé" }
```

Rejeter :

```json
{ "valider": false, "commentaire": "Recomptage nécessaire" }
```

Si validé : mouvement d'ajustement automatique (`AJUSTEMENT_SURPLUS_CAISSE` ou `AJUSTEMENT_PERTE_CAISSE`), puis session → `CLOTUREE`.

---

## 6. Rapports

### Général (synthétique)

`GET .../rapport-general/`

```json
{
  "caisse": "Caisse principale",
  "devise": "USD",
  "total_entrees": "1000.00000",
  "total_sorties": "300.00000",
  "solde": "700.00000",
  "nombre_mouvements": 25
}
```

### Détaillé (solde progressif)

`GET .../rapport-detaille/`

Chaque ligne : datetime, référence, type, catégorie, montant entrée/sortie, **solde_progressif**.

---

## 7. Frontend — checklist

- [ ] Au démarrage : `GET /api/sessions-caisse/active/`
- [ ] Si aucune session : alerte + bouton **Ouvrir la caisse** ; désactiver vente / paiement / mouvements
- [ ] Après ouverture : activer les opérations (le backend rattache automatiquement les mouvements)
- [ ] Clôture : formulaire montant physique uniquement (pas de date manuelle)
- [ ] Écart en attente : notifier l'admin pour validation
- [ ] Sessions clôturées : consultation seule + rapports + procès-verbal JSON

---

## 8. Modèles Django

| Modèle | Fichier |
|--------|---------|
| `SessionCaisse`, `EcartCaisse` | `stock/models.py` |
| Logique métier | `stock/services/session_caisse.py` |
| Intégration mouvements | `stock/services/caisse.py` → `creer_mouvement_caisse()` |

Champs ajoutés sur `MouvementCaisse` : `session_caisse`, `type_caisse`, `categorie`.

---

*Dernière mise à jour : juin 2026*
