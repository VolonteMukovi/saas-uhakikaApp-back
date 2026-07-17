# Valorisation financière du stock — Module Inventaire

> Référence frontend pour l’intégration de la valorisation du capital stock.  
> La logique de comptage (quantités, écarts, validation/ajustements) **n’est pas modifiée**.

---

## 1. Objectif

À partir d’un inventaire physique, le système calcule automatiquement :

| Notion | Signification |
|--------|----------------|
| **Valeur théorique (logiciel)** | Capital stock selon les quantités enregistrées dans le logiciel |
| **Valeur physique** | Capital stock selon le comptage réel |
| **Écart financier** | Différence entre les deux |
| **Capital réel du stock** | = valeur physique = marchandises réellement présentes |

La valorisation repose **uniquement** sur le **dernier prix unitaire d’achat** (coût d’acquisition), jamais sur le prix de vente.

---

## 2. Source du prix unitaire

```text
Article
  → dernier approvisionnement (LigneEntree)
  → prix_unitaire d'achat
```

- Si aucun approvisionnement : `dernier_prix_unitaire = 0` (pas d’erreur).
- Le prix est **figé** à la génération des lignes (`POST .../demarrer/` ou `demarrer: true` à la création).
- Un approvisionnement ultérieur **ne change pas** le PU de l’inventaire déjà démarré (photographie à date).

---

## 3. Nouvelles colonnes de ligne (lecture seule)

Toutes calculées / figées côté backend. **Ne jamais** les rendre éditables.

| Colonne API | Formule / origine | Exemple |
|-------------|-------------------|---------|
| `dernier_prix_unitaire` | PU figé au démarrage | `"0.33000"` |
| `montant_logiciel` | `stock_theorique × dernier_prix_unitaire` | `152 × 0.33 = 50.16` |
| `montant_physique` | `stock_physique × dernier_prix_unitaire` | `150 × 0.33 = 49.50` |
| `ecart_montant` | `ecart × dernier_prix_unitaire` | `-2 × 0.33 = -0.66` |

Notes :

- `montant_physique` vaut `null` tant que `stock_physique` n’est pas saisi.
- Format : chaînes décimales à 5 décimales (comme le reste du module).
- Affichage monétaire : utiliser la **devise principale** de l’entreprise (symbole / sigle), ex. `0.33 USD`.

### Exemple de ligne API

```json
{
  "article_id": "PRTO0001",
  "stock_theorique": "152.00000",
  "stock_physique": "150.00000",
  "ecart": "-2.00000",
  "dernier_prix_unitaire": "0.33000",
  "montant_logiciel": "50.16000",
  "montant_physique": "49.50000",
  "ecart_montant": "-0.66000"
}
```

---

## 4. Résumé financier (`resume`)

En plus des compteurs existants (`total_lignes`, `lignes_comptees`, écarts…), l’API expose :

| Champ | Calcul |
|-------|--------|
| `capital_logiciel` | Σ `montant_logiciel` |
| `capital_physique` | Σ `montant_physique` (lignes comptées uniquement) |
| `ecart_financier` | `capital_physique − capital_logiciel` |
| `capital_reel_stock` | Alias de `capital_physique` (**à mettre en évidence**) |
| `total_montant_logiciel` / `total_montant_physique` | Alias des totaux |
| `total_ecart_positif` | Σ `ecart_montant > 0` (surplus) |
| `total_ecart_negatif` | Σ \|`ecart_montant < 0`\| (manques, valeur ≥ 0) |
| `total_ecart_montant` | Σ tous les `ecart_montant` (net) |

> Guide d’affichage frontend détaillé : **`INVENTAIRE_FRONTEND.md`**.

### Exemple

```json
{
  "resume": {
    "total_lignes": 405,
    "lignes_comptees": 392,
    "lignes_non_comptees": 13,
    "ecarts_positifs": 8,
    "ecarts_negatifs": 15,
    "ecarts_nuls": 369,
    "capital_logiciel": "25680.45000",
    "capital_physique": "25490.10000",
    "ecart_financier": "-190.35000",
    "capital_reel_stock": "25490.10000"
  }
}
```

Endpoints concernés :

- `GET /api/inventaires/` (liste : `resume`)
- `GET /api/inventaires/{id}/` (détail : `resume` + lignes enrichies)
- `GET /api/rapports/inventaire/?session_id=` → `statistiques` + `totaux_financiers`

---

## 5. Rapport / PDF (côté frontend)

Le backend renvoie du **JSON** ; le frontend compose le PDF.

### Colonnes tableau recommandées

| Article | Qté logiciel | Qté physique | Écart | Dernier PU | Montant logiciel | Montant physique |
|---------|-------------:|-------------:|------:|-----------:|-----------------:|-----------------:|

Sources :

- Qté logiciel → `stock_theorique`
- Qté physique → `stock_physique`
- Écart → `ecart`
- Dernier PU → `dernier_prix_unitaire`
- Montants → `montant_logiciel` / `montant_physique`

### Pied de rapport (à mettre en avant)

```text
Total logiciel …………… 25 680.45 USD
Total physique …………… 25 490.10 USD
Écart financier ………… -190.35 USD

★ Capital réel du stock … 25 490.10 USD
```

Le **Capital réel du stock** (= `capital_physique` / `capital_reel_stock`) doit être graphiquement mis en évidence (encadré, gras, couleur d’accent).

Pour les sessions, préférer :

`GET /api/rapports/inventaire/?session_id={id}&complet=true`

qui inclut déjà :

```json
"totaux_financiers": {
  "total_logiciel": "...",
  "total_physique": "...",
  "ecart_financier": "...",
  "capital_reel_stock": "..."
}
```

---

## 6. Recommandations d’affichage UI

1. **Colonnes financières en lecture seule** (badge « auto » ou fond légèrement grisé).
2. **Format monétaire** selon devise principale (`resume` + symbole « USD », « CDF », etc.).
3. **Écart financier** :
   - négatif → danger / rouge (manquant),
   - positif → info / vert (excédent),
   - zéro → neutre.
4. **Capital réel** : KPI en tête de fiche inventaire + footer rapport + futur dashboard.
5. Lignes non comptées : afficher `—` pour montant physique (pas `0.00` forcé).
6. Mobile : garder PU + montants accessibles (carte dépliable) ; ne pas les supprimer.

---

## 7. Tableaux de bord (évolution)

Réutiliser `capital_reel_stock` / `capital_physique` des inventaires validés pour :

- widget « Capital immobilisé en stock »
- historique d’évolution après chaque inventaire validé
- écart financier moyen

Ne pas recalculer côté FE à partir des ventes : le backend est la source de vérité du snapshot.

---

## 8. Pourquoi le prix d’achat ?

| Prix | Rôle |
|------|------|
| Achat (coût) | Capital immobilisé — **utilisé** |
| Vente | Marge / CA — **non utilisé** pour le capital stock |

Pratique comptable standard des logiciels de gestion (valorisation au coût d’acquisition).

---

## 9. Checklist intégration frontend

- [ ] Ajouter colonnes PU / montant logiciel / montant physique (readonly)
- [ ] Afficher `resume.capital_*` et `ecart_financier` en bas de tableau
- [ ] Mettre en évidence `capital_reel_stock`
- [ ] Adapter le PDF/rapport (colonnes + totaux)
- [ ] Format monétaire devise principale
- [ ] Gérer `montant_physique = null` (non compté)
- [ ] Brancher les KPI dashboard sur inventaires `VALIDE`

---

*Document de référence — valorisation financière inventaire UHAKIKA.*
