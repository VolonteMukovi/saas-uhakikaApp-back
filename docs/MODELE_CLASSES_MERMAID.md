# Modèle de classes UHAKIKAAPP (Mermaid)

## Comment afficher le diagramme (important)

Sur [mermaid.live](https://mermaid.live), **ne collez pas ce fichier Markdown**.

1. Ouvrez **`docs/modele-classes.mmd`**
2. Copiez **tout** son contenu (la première ligne doit être `classDiagram`)
3. Collez dans l’éditeur mermaid.live

**Ne pas coller :**
- le titre `# Modèle de classes...`
- les lignes ` ```mermaid ` / ` ``` `
- le tableau Django en bas de ce fichier

---

## Fichier source du diagramme

**Code Mermaid pur :** [`modele-classes.mmd`](modele-classes.mmd)

---

## Aperçu (GitHub / VS Code)

Si votre lecteur Markdown supporte Mermaid, le bloc ci-dessous s’affiche directement ici :

```mermaid
classDiagram
    direction TB
    namespace Gestion_Entreprises_Succursales_Utilisateurs {
        class Entreprise
        class Succursale
        class Utilisateur
    }
    namespace Gestion_Articles_Stocks {
        class Article
        class Stock
        class Unite
        class TypeArticle
        class SousTypeArticle
    }
    namespace Flux_Entrees_Ventes {
        class Entree
        class LigneEntree
        class Sortie
        class LigneSortie
    }
    namespace Tracabilite_FIFO_Marges {
        class LigneSortieLot
        class BeneficeLot
    }
    namespace Finances_Caisse_Clients {
        class Client
        class ClientEntreprise
        class DetteClient
        class MouvementCaisse
        class DetailMouvementCaisse
        class TypeCaisse
        class Devise
    }
    Entreprise "1" *-- "0..*" Succursale
    Article "1" -- "1" Stock
    Entree "1" *-- "1..*" LigneEntree
    Sortie "1" *-- "1..*" LigneSortie
```

> Le diagramme complet (attributs + toutes les relations) est dans **`modele-classes.mmd`**.

---

## Correspondance avec le code Django

| Classe diagramme | Fichier modèle |
|------------------|----------------|
| Entreprise, Succursale, Article, Stock, Entree, Sortie, Client, DetteClient, MouvementCaisse, Devise, … | `stock/models.py` |
| Utilisateur | `users/models.py` (`User`) |
| LigneSortieLot, BeneficeLot | `stock/models.py` |
| Lot, Fournisseur (non représentés ici) | `order/models.py` |
| InventaireSession, InventaireLigne | `stock/models.py` |
