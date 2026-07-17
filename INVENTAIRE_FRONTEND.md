# Inventaire — Intégration frontend (écarts financiers)

Tous les calculs métier sont faits **côté backend**. Le frontend affiche uniquement les valeurs reçues.

---

## 1. Nouveaux champs API

### Par ligne (`lignes[]`)

| Champ | Type | Signification |
|-------|------|----------------|
| `stock_theorique` | string decimal | Stock logiciel figé |
| `stock_physique` | string decimal \| `null` | Comptage réel |
| `ecart` | string decimal \| `null` | `physique − théorique` |
| `dernier_prix_unitaire` | string decimal | PU d’achat figé au démarrage |
| `montant_logiciel` | string decimal | `théorique × PU` |
| `montant_physique` | string decimal \| `null` | `physique × PU` (si compté) |
| **`ecart_montant`** | string decimal \| `null` | `ecart × PU` (= montant physique − montant logiciel) |

Formule :

```text
écart_quantité = stock_physique − stock_théorique
écart_montant  = écart_quantité × dernier_prix_unitaire
```

- `ecart_montant > 0` → **surplus** de stock  
- `ecart_montant < 0` → **manque** de stock  
- `null` → ligne pas encore comptée

### Dans le résumé (`resume`)

| Champ | Signification | Signe |
|-------|----------------|-------|
| **`total_ecart_positif`** | Σ des `ecart_montant > 0` (surplus) | ≥ 0 |
| **`total_ecart_negatif`** | Σ des \|`ecart_montant < 0`\| (manques) | ≥ 0 (valeur absolue) |
| **`total_ecart_montant`** | Σ de tous les `ecart_montant` (net) | peut être ± |

Aussi présents (inchangés) : `capital_logiciel`, `capital_physique`, `ecart_financier`, `capital_reel_stock`, compteurs d’écarts quantité, etc.

Endpoints concernés :

- `GET /api/inventaires/`
- `GET /api/inventaires/{id}/`
- `GET /api/inventaires/{id}/resume/`
- Rapport inventaire (`statistiques` + `totaux_financiers`)

---

## 2. Où les afficher

### Interface Inventaire — bandeau résumé

```text
Total des surplus
+45,00 USD          ← resume.total_ecart_positif

Total des manques
33,00 USD           ← resume.total_ecart_negatif  (déjà positif)

Écart financier net
+12,00 USD          ← resume.total_ecart_montant
```

Suggestions UI :

- Surplus : vert / `+` devant le montant  
- Manques : rouge / **sans** signe moins (le backend renvoie déjà l’absolu)  
- Net : vert si ≥ 0, rouge si < 0  

Devise : devise principale de l’entreprise (ex. `USD`, `CDF`).

### Rapport PDF — bloc « Résumé financier »

```text
Résumé financier

Total des surplus :          +45,00 USD
Total des manques :           33,00 USD
Écart financier net :        +12,00 USD
```

Sources rapport :

- `statistiques.total_ecart_positif`
- `statistiques.total_ecart_negatif`
- `statistiques.total_ecart_montant`

ou le miroir :

- `totaux_financiers.total_ecart_*`

### Tableau des lignes

Colonnes à afficher (aucune formule côté FE) :

| Colonne | Champ API |
|---------|-----------|
| Stock théorique | `stock_theorique` |
| Stock physique | `stock_physique` |
| Écart quantité | `ecart` |
| Prix unitaire | `dernier_prix_unitaire` |
| **Écart montant** | **`ecart_montant`** |

Couleur de `ecart_montant` : vert si > 0, rouge si < 0, neutre si 0 / `null`.

---

## 3. Exemple JSON

```json
{
  "id": 12,
  "libelle": "Inventaire mars",
  "resume": {
    "total_lignes": 2,
    "lignes_comptees": 2,
    "capital_logiciel": "80.16000",
    "capital_physique": "91.50000",
    "ecart_financier": "11.34000",
    "total_ecart_montant": "11.34000",
    "total_ecart_positif": "12.00000",
    "total_ecart_negatif": "0.66000"
  },
  "lignes": [
    {
      "article_id": "PRTO0001",
      "stock_theorique": "152.00000",
      "stock_physique": "150.00000",
      "ecart": "-2.00000",
      "dernier_prix_unitaire": "0.33000",
      "montant_logiciel": "50.16000",
      "montant_physique": "49.50000",
      "ecart_montant": "-0.66000"
    },
    {
      "article_id": "PRON0001",
      "stock_theorique": "10.00000",
      "stock_physique": "14.00000",
      "ecart": "4.00000",
      "dernier_prix_unitaire": "3.00000",
      "montant_logiciel": "30.00000",
      "montant_physique": "42.00000",
      "ecart_montant": "12.00000"
    }
  ]
}
```

Vérification :

```text
total_ecart_positif  = 12.00
total_ecart_negatif  = 0.66
total_ecart_montant  = 12.00 − 0.66 = 11.34
```

---

## 4. Règles d’intégration

1. **Ne jamais recalculer** surplus / manques / net côté frontend.  
2. Formater uniquement (locale, symbole devise, signe `+` pour surplus et net positif).  
3. `total_ecart_negatif` est une **magnitude** (≥ 0) : libeller « Manque de stock », pas « −33 ».  
4. Lignes non comptées : `ecart_montant = null` → afficher `—` ou vide.  
5. Les champs restent en **chaînes** à 5 décimales ; parser en nombre seulement pour le formatage d’affichage.

---

## 5. Checklist FE

- [ ] Colonne `ecart_montant` dans le tableau inventaire  
- [ ] Bandeau : surplus / manques / écart net  
- [ ] Même trio dans le PDF inventaire  
- [ ] Couleurs cohérentes (+ vert / − rouge)  
- [ ] Aucun calcul métier local
