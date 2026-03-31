"""
Sérialiseurs lecture seule pour le portail client (JWT dédié).
Les ventes (sorties) exposées ici excluent les champs de marge / lots (bénéfices) réservés au back-office.
"""
from rest_framework import serializers

from stock.models import Article, Devise, LigneSortie, Sortie


class ClientPortalArticleLineSerializer(serializers.ModelSerializer):
    """Aperçu article pour une ligne de vente."""

    class Meta:
        model = Article
        fields = ("article_id", "nom_scientifique", "nom_commercial")


class ClientPortalDeviseMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Devise
        fields = ("id", "sigle", "symbole", "nom")


class ClientPortalLigneSortieReadSerializer(serializers.ModelSerializer):
    article = ClientPortalArticleLineSerializer(read_only=True)
    devise = ClientPortalDeviseMiniSerializer(read_only=True)

    class Meta:
        model = LigneSortie
        fields = ("id", "article", "quantite", "prix_unitaire", "devise", "date_sortie")


class ClientPortalSortieReadSerializer(serializers.ModelSerializer):
    """Vente (sortie) — consultation uniquement."""

    lignes = ClientPortalLigneSortieReadSerializer(many=True, read_only=True)

    class Meta:
        model = Sortie
        fields = ("id", "motif", "statut", "date_creation", "lignes")
