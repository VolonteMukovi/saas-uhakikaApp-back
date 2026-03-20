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
    Utilisateur : SuperAdmin (is_superuser) ou membre d'entreprises via Membership.
    - SuperAdmin : is_superuser (créé via createsuperuser).
    - Admin / User (Agent) : déterminé par Membership.role (par entreprise), plus par User.role.
    Le champ `role` reste en base pour rétrocompatibilité / affichage legacy ; la logique
    des permissions s'appuie sur is_superuser et sur Membership.role.
    """
    ROLE_CHOICES = (
        ('superadmin', 'Super Administrateur'),
        ('admin', 'Administrateur'),
        ('user', 'Agent / Employé'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")

    objects = UserManager()

    def get_current_membership(self, request=None):
        """
        Membership du contexte courant.
        Si request est fourni et a current_membership (défini par l'auth JWT), utilise celui-là
        pour cet utilisateur ; sinon premier membership actif.
        """
        if request is not None:
            m = getattr(request, 'current_membership', None)
            if m is not None and m.user_id == self.pk:
                return m
        return self.memberships.filter(is_active=True).select_related('entreprise', 'default_succursale').first()

    def get_entreprise(self, request=None):
        """Entreprise courante (contexte request ou premier membership actif)."""
        m = self.get_current_membership(request)
        return m.entreprise if m else None

    def get_entreprise_id(self, request=None):
        """ID de l'entreprise courante ou None."""
        m = self.get_current_membership(request)
        return m.entreprise_id if m else None

    def __str__(self):
        if self.is_superuser:
            return f"{self.username} (Super Admin)"
        m = self.get_current_membership()
        ent = m.entreprise if m else None
        nom = ent.nom if ent else 'Aucune entreprise'
        role_label = m.role if m else 'user'
        if role_label == 'admin':
            return f"{self.username} (Admin) - {nom}"
        return f"{self.username} (Agent) - {nom}"

    def is_superadmin(self):
        """Super administrateur plateforme (créé via createsuperuser)."""
        return bool(self.is_superuser)

    def is_admin(self, request=None):
        """True si l'utilisateur est admin dans le contexte courant (Membership.role)."""
        m = self.get_current_membership(request)
        return m is not None and m.role == 'admin'

    def is_agent(self, request=None):
        """True si l'utilisateur est agent dans le contexte courant (Membership.role)."""
        m = self.get_current_membership(request)
        return m is not None and m.role == 'user'


class Membership(models.Model):
    """
    Liaison SaaS entre un utilisateur et une entreprise (tenant).
    Un user peut appartenir à plusieurs entreprises avec un rôle différent par entreprise.
    """

    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('user', 'Agent / Employé'),
    )

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='memberships')
    entreprise = models.ForeignKey('stock.Entreprise', on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    default_succursale = models.ForeignKey(
        'stock.Succursale',
        on_delete=models.SET_NULL,
        related_name='default_for_memberships',
        null=True,
        blank=True,
        help_text="Succursale par défaut si l'entreprise a des succursales."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'entreprise')
        ordering = ['entreprise_id', 'user_id', 'id']

    def __str__(self):
        return f"{self.user.username} @ {self.entreprise.nom} ({self.role})"


class UserBranch(models.Model):
    """Autorisation d'un membership sur une ou plusieurs succursales."""
    membership = models.ForeignKey('users.Membership', on_delete=models.CASCADE, related_name='branches')
    succursale = models.ForeignKey('stock.Succursale', on_delete=models.CASCADE, related_name='user_branches')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('membership', 'succursale')
        ordering = ['succursale_id', 'membership_id', 'id']

    def __str__(self):
        return f"{self.membership.user.username} -> {self.succursale}"
