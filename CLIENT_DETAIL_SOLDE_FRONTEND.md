# Détail client — Solde restant vs Écart période

## Changement (sept. 2026)

Le KPI **« Solde restant »** ne doit plus être `total_credit − total_paye` sur la période (ça donnait des soldes négatifs absurdes).

### Nouveaux champs `resume`

| Champ | Sens | Dépend de la période ? |
|-------|------|------------------------|
| `du_actuel` / `solde_restant` | Ce que le client **doit encore** (Σ soldes des dettes ouvertes) | **Non** |
| `ecart_periode` | Crédits **nés** dans la période − payé **sur ces mêmes crédits** | **Oui** (souvent ≈ 0 si soldés) |
| `total_credit` / `total_dettes` | Dettes créées dans la période | Oui |
| `total_paye` | Montant payé **sur les dettes nées dans la période** | Oui |
| `total_comptant` | Ventes comptant de la période | Oui |

`solde_restant` === `du_actuel` (alias pour compatibilité).

### Total payé (important)

`total_paye` suit le **même périmètre** que `total_dettes` :

- filtre = dettes dont `date_creation` est dans `[date_debut, date_fin]` ;
- somme des paiements (mouvements caisse) **liés à ces dettes**.

Il **n’inclut pas** les encaissements d’anciennes créances hors fenêtre (ex. dette d’août payée en septembre → comptée avec le filtre qui inclut la dette d’août, pas comme gonflement du mois de septembre au-delà des dettes du mois).

Exemple Pr AITA :

| Filtre | Total dettes | Total payé (attendu) |
|--------|--------------|----------------------|
| Ce mois (sept.) | ~11,60 | ~11,60 |
| 13/08 — 22/09 | ~104,41 | ~104,41 |

### UI recommandée

```
Solde restant     → resume.solde_restant   (ou du_actuel)
Écart période     → resume.ecart_periode
Total crédit      → resume.total_credit
Total payé        → resume.total_paye
```

- Carte principale **Solde restant** = `du_actuel` (jamais afficher `ecart_periode` comme dû).
- Carte secondaire optionnelle **Écart période** pour l’analyse d’activité sur les crédits de la fenêtre.
- `repartition.dettes_en_cours` / `dettes_en_retard` / `dettes_payees` = **globaux** (alignés sur le dû).
- Variantes `dettes_periode_*` = comptes des dettes **créées** dans la fenêtre.
