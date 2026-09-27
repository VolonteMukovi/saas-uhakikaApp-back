# Plan à vie (formule `a_vie`) — Guide frontend

Le backend expose la formule **À vie** dans le catalogue.  
Parcours attendu : **essai gratuit 2 mois d’abord**, puis éventuellement demande / activation **À vie**.

Le tarif n’est **pas** publié par défaut (`prix_a_vie = 0`, `prix_sur_demande: true`) — il est fixé avec l’équipe technique.

---

## 1. Identité de la formule

| Champ | Valeur |
|-------|--------|
| `code` | `a_vie` |
| `nom` | `À vie` |
| `periode` à envoyer | **toujours** `a_vie` |
| Prix | `prix_a_vie` (0 = sur devis) — `prix_mensuel` / `prix_annuel` = `0` |
| `prix_sur_demande` | `true` tant que `prix_a_vie <= 0` |
| Quotas | `limites.utilisateurs_max: null`, `succursales_max: null` |
| Features | toutes à `true` |

Exemple API (prix pas encore fixé) :

```json
{
  "code": "a_vie",
  "nom": "À vie",
  "prix_a_vie": "0.00",
  "prix_mensuel": "0.00",
  "prix_annuel": "0.00",
  "devise": "USD",
  "est_a_vie": true,
  "periodes_disponibles": ["a_vie"],
  "acces_illimite": true,
  "prix_sur_demande": true
}
```

Quand l’équipe technique publie un tarif : `FORMULE_A_VIE_PRIX_USD` ou admin Django → `prix_sur_demande: false`.

---

## 2. Parcours métier (important)

```
Inscription / création entreprise
        ↓
Essai gratuit 2 mois (auto, statut=essai, accès complet)
        ↓
(optionnel) Demande plan À vie  →  en_attente
        ↓  l’essai RESTE actif
Validation équipe / paiement      →  licence à vie (date_fin=null)
```

- Ne pas proposer « À vie » comme **premier** choix obligatoire à l’inscription.
- Pendant l’essai, l’utilisateur peut déjà demander `a_vie` : le backend **ne coupe pas** l’essai tant que la demande n’est pas activée.
- Après activation : `est_a_vie: true`, plus de timer d’expiration.

---

## 3. Endpoints

| Action | Méthode | URL |
|--------|---------|-----|
| Liste formules | `GET` | `/api/abonnements/formules/` |
| Demande (manuel / devis) | `POST` | `/api/abonnements/demander/` |
| Paiement en ligne | `POST` | `/api/abonnements/paiements/initier/` |
| Mon abonnement | `GET` | `/api/abonnements/mon-abonnement/` |
| Flow SaaS | `GET` | `/api/inscription/flow/` |

### Demande manuelle (recommandé tant que prix sur devis)

```http
POST /api/abonnements/demander/
Authorization: Bearer …
Content-Type: application/json

{
  "formule_code": "a_vie",
  "periode": "a_vie"
}
```

### Paiement en ligne

Uniquement si `prix_sur_demande === false` et `prix_a_vie > 0`.  
Sinon le backend répond `prix_non_defini` — orienter vers demande manuelle / contact équipe.

```http
POST /api/abonnements/paiements/initier/
{
  "formule_code": "a_vie",
  "periode": "a_vie",
  "fournisseur": "maisha_pay"
}
```

---

## 4. Affichage frontend

### Catalogue / pricing

1. Charger `GET /api/abonnements/formules/`.
2. Carte **À vie** distincte.
3. Si `prix_sur_demande` → libellé **« Sur devis »** / **« Contactez l’équipe »** (ne pas afficher `0 USD`).
4. Pas de toggle mensuel/annuel (`periodes_disponibles: ["a_vie"]`).
5. CTA principal onboarding : **Essai gratuit 2 mois** ; CTA secondaire / upgrade : **Passer à vie**.

### Sélection

```ts
saveSelectedPlan(
  buildPlanFromFormule(formuleAVie, 'a_vie', 'manuel')
);
```

### UI licence

| État | Affichage |
|------|-----------|
| `est_essai` | badge Essai + jours restants |
| demande `a_vie` en cours + essai actif | essai inchangé + banner « Demande À vie en attente » |
| `est_a_vie` | badge Accès permanent ; **pas** de jours restants / renouveler |

---

## 5. Checklist QA

- [ ] Catalogue : `a_vie` avec `prix_sur_demande: true` (ou prix > 0 si publié)
- [ ] Nouvelle entreprise → essai 60 j automatique
- [ ] Pendant essai, `POST .../demander/` `a_vie` → essai toujours `est_actif`
- [ ] Après activation manuelle → `est_a_vie: true`, `date_fin: null`
- [ ] Paiement en ligne bloqué si prix non défini

---

## 6. Ops backend

```bash
python manage.py seed_formules_abonnement
```

```env
# Laisser vide tant que le tarif n'est pas validé
FORMULE_A_VIE_PRIX_USD=
```

Activation manuelle VIP :

```bash
python manage.py activer_acces_a_vie --entreprise-id=<ID>
```
