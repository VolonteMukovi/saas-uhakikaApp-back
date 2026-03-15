from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

User = get_user_model()

# Désinscrire le modèle User standard si il est déjà enregistré
if admin.site.is_registered(User):
    admin.site.unregister(User)


class UserAdmin(BaseUserAdmin):
    """
    Administration personnalisée pour le modèle User
    """
    list_display = ('username', 'email', 'role', 'entreprise', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'entreprise')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    
    # Champs à afficher dans le formulaire d'édition
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations Supplémentaires', {
            'fields': ('role', 'entreprise')
        }),
    )
    
    # Champs à afficher lors de la création d'un utilisateur
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informations Supplémentaires', {
            'fields': ('role', 'entreprise', 'email', 'first_name', 'last_name')
        }),
    )


# Enregistrer le modèle avec notre admin personnalisé
admin.site.register(User, UserAdmin)
