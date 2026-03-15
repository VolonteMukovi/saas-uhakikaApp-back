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
    Modèle utilisateur personnalisé avec système simplifié à 2 rôles.
    
    Rôles:
    - superadmin: Développeurs/techniciens (créés via createsuperuser)
    - admin: Utilisateurs d'entreprise (créés via API)
    """
    ROLE_CHOICES = (
        ('superadmin', 'Super Administrateur'),
        ('admin', 'Administrateur'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="admin")
    entreprise = models.ForeignKey(
        'stock.Entreprise', 
        on_delete=models.CASCADE, 
        related_name='users', 
        null=True, 
        blank=True
    )
    
    objects = UserManager()  # Utiliser notre manager personnalisé

    def __str__(self):
        if self.role == 'superadmin':
            return f"{self.username} (Super Admin)"
        return f"{self.username} (Admin) - {self.entreprise.nom if self.entreprise else 'Aucune entreprise'}"
    
    def is_superadmin(self):
        """Vérifie si l'utilisateur est un super administrateur"""
        return self.role == 'superadmin' or self.is_superuser
    
    def is_admin(self):
        """Vérifie si l'utilisateur est un administrateur d'entreprise"""
        return self.role == 'admin'
