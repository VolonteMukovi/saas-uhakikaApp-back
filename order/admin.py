from django.contrib import admin

from .models import Commande, CommandeItem, CommandeResponse, Fournisseur, Lot, FraisLot, LotItem


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "nom", "entreprise", "is_active", "created_at")
    list_filter = ("is_active", "entreprise")
    search_fields = ("code", "nom", "telephone", "email", "nif")


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "statut", "entreprise", "fournisseur", "date_expedition", "date_arrivee_prevue", "created_at")
    list_filter = ("statut", "entreprise", "date_expedition")
    search_fields = ("reference",)


@admin.register(FraisLot)
class FraisLotAdmin(admin.ModelAdmin):
    list_display = ("id", "lot", "type_frais", "montant", "devise", "entreprise", "created_at")
    list_filter = ("type_frais", "entreprise", "created_at")
    search_fields = ("lot__reference",)


@admin.register(LotItem)
class LotItemAdmin(admin.ModelAdmin):
    list_display = ("id", "lot", "article", "quantite", "prix_achat_unitaire", "entreprise", "created_at")
    list_filter = ("entreprise", "created_at")
    search_fields = ("lot__reference", "article__nom_scientifique")


class CommandeItemInline(admin.TabularInline):
    model = CommandeItem
    extra = 0
    raw_id_fields = ("article",)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ("id", "reference", "statut", "client", "entreprise", "succursale", "created_at")
    list_filter = ("statut", "entreprise")
    search_fields = ("reference", "client__nom", "note_client")
    raw_id_fields = ("client", "entreprise", "succursale")
    inlines = [CommandeItemInline]


@admin.register(CommandeResponse)
class CommandeResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "commande", "auteur", "created_at")
    list_filter = ("commande__entreprise",)
    raw_id_fields = ("commande", "auteur")

