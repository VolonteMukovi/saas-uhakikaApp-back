from django.contrib import admin

from abonnements.models import (
    AbonnementEntreprise,
    DemandeInstallationPrivee,
    FormuleAbonnement,
    JournalActivationLicence,
    JournalWebhookPaiement,
    PaiementAbonnement,
)


@admin.register(FormuleAbonnement)
class FormuleAbonnementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code', 'prix_mensuel', 'prix_annuel', 'est_active', 'ordre_affichage')
    list_filter = ('est_active', 'est_visible_catalogue')
    search_fields = ('nom', 'code')


@admin.register(AbonnementEntreprise)
class AbonnementEntrepriseAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'formule', 'statut', 'periode', 'date_fin', 'est_courant')
    list_filter = ('statut', 'periode', 'est_courant')
    raw_id_fields = ('entreprise', 'formule', 'active_par')


@admin.register(PaiementAbonnement)
class PaiementAbonnementAdmin(admin.ModelAdmin):
    list_display = ('id', 'reference_interne', 'abonnement', 'montant', 'devise', 'statut', 'fournisseur', 'created_at')
    list_filter = ('statut', 'fournisseur')
    search_fields = ('reference_interne', 'reference_externe')


@admin.register(JournalWebhookPaiement)
class JournalWebhookPaiementAdmin(admin.ModelAdmin):
    list_display = ('id', 'fournisseur', 'reference_interne', 'statut_traitement', 'created_at')
    list_filter = ('fournisseur', 'statut_traitement')
    readonly_fields = ('payload', 'created_at')


@admin.register(JournalActivationLicence)
class JournalActivationLicenceAdmin(admin.ModelAdmin):
    list_display = ('entreprise', 'action', 'effectue_par', 'created_at')
    list_filter = ('action',)


@admin.register(DemandeInstallationPrivee)
class DemandeInstallationPriveeAdmin(admin.ModelAdmin):
    list_display = ('nom_contact', 'email_contact', 'statut', 'created_at')
    list_filter = ('statut',)
