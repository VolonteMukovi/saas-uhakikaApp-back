from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager personnalisé pour créer des superadmins automatiquement"""
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Créer un superutilisateur avec le rôle superadmin automatiquement"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')  # Force le rôle superadmin
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')
            
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Modèle utilisateur avec 3 rôles : SuperAdmin, Admin, User (Agent).
    - superadmin : créé via createsuperuser, R+D sur Entreprise uniquement, peut modifier son compte.
    - admin : propriétaire entreprise, CRUD complet sur les données de son entreprise et ses utilisateurs.
    - user : employé, CRUD métier, peut modifier uniquement son profil.
    """
    ROLE_CHOICES = (
        ('superadmin', 'Super Administrateur'),
        ('admin', 'Administrateur'),
        ('user', 'Agent / Employé'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="admin")
    entreprise = models.ForeignKey(
        'stock.Entreprise',
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )

    objects = UserManager()

    def __str__(self):
        if self.role == 'superadmin':
            return f"{self.username} (Super Admin)"
        if self.role == 'admin':
            return f"{self.username} (Admin) - {self.entreprise.nom if self.entreprise else 'Aucune entreprise'}"
        return f"{self.username} (Agent) - {self.entreprise.nom if self.entreprise else 'Aucune entreprise'}"

    def is_superadmin(self):
        return self.role == 'superadmin' or self.is_superuser

    def is_admin(self):
        return self.role == 'admin'

    def is_agent(self):
        """Vérifie si l'utilisateur est un agent / employé."""
        return self.role == 'user'
