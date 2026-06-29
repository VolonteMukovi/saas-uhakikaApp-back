from django.contrib import admin

from inscription.models import ProfilConnexionGoogle


@admin.register(ProfilConnexionGoogle)
class ProfilConnexionGoogleAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'google_sub', 'email_google', 'created_at')
    search_fields = ('google_sub', 'email_google', 'utilisateur__username')
