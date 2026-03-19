from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

# Désinscrire le modèle User standard si il est déjà enregistré
if admin.site.is_registered(User):
    admin.site.unregister(User)


class UserAdmin(BaseUserAdmin):
    """
    Administration personnalisée pour le modèle User (entreprise via Membership).
    """
    list_display = ('username', 'email', 'role', 'admin_entreprise_display', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def admin_entreprise_display(self, obj):
        ent = obj.get_entreprise()
        return ent.nom if ent else '-'
    admin_entreprise_display.short_description = 'Entreprise'

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations Supplémentaires', {
            'fields': ('role',)
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations Supplémentaires', {
            'fields': ('role', 'email', 'first_name', 'last_name')
        }),
    )


# Enregistrer le modèle avec notre admin personnalisé
admin.site.register(User, UserAdmin)
