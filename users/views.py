import time
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework import serializers as drf_serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext as _

from .serializers import UserSerializer, UserRegistrationSerializer, SuperAdminUserSerializer, AdminUserSerializer
from .permissions import IsSuperAdmin, IsSuperAdminOrAdmin, IsAdminFullEnterpriseAndUsers
from stock.models import Entreprise

# Durée max de la session (24 h) en secondes ; au-delà, l'utilisateur doit se reconnecter
SESSION_MAX_AGE_SECONDS = 24 * 3600


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Connexion : tokens + infos user ; ajout du claim session_start pour limite 24 h."""

    def validate(self, attrs):
        # Authentification uniquement (TokenObtainPairSerializer met déjà refresh/access, on les reconstruit avec session_start)
        super(TokenObtainPairSerializer, self).validate(attrs)
        refresh = self.get_token(self.user)
        refresh["session_start"] = int(time.time())
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        user_data = {
            "id": self.user.id,
            "username": self.user.username,
            "role": self.user.role,
            "email": self.user.email,
        }
        if self.user.entreprise:
            user_data["entreprise"] = {
                "id": self.user.entreprise.id,
                "nom": self.user.entreprise.nom,
                "secteur": self.user.entreprise.secteur,
                "adresse": self.user.entreprise.adresse,
                "telephone": self.user.entreprise.telephone,
                "email": self.user.entreprise.email,
                "responsable": self.user.entreprise.responsable,
            }
        else:
            user_data["entreprise"] = None
        data["user"] = user_data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vue personnalisée pour la connexion avec informations utilisateur"""
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Refresh avec limite de session 24 h : même en rafraîchissant,
    après 24 h depuis la première connexion il faut se reconnecter.
    """
    default_error_messages = {
        **TokenRefreshSerializer.default_error_messages,
        "session_expired": _("Session expirée (durée max 24 h). Veuillez vous reconnecter."),
    }

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        session_start = refresh.get("session_start") or refresh.get("iat")
        if session_start is not None:
            now = int(time.time())
            if (now - session_start) > SESSION_MAX_AGE_SECONDS:
                raise drf_serializers.ValidationError(
                    {"detail": self.error_messages["session_expired"]}
                )
        return super().validate(attrs)


class CustomTokenRefreshView(TokenRefreshView):
    """Vue de rafraîchissement du token avec durée max de session 24 h."""
    serializer_class = CustomTokenRefreshSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    Gestion des utilisateurs selon le rôle :
    - SuperAdmin : liste/voir tous, modifier/supprimer uniquement son propre compte ; assign_entreprise, remove_entreprise.
    - Admin : CRUD complet sur les utilisateurs de son entreprise (créer, lire, modifier nom/username/email/mot de passe/rôle, supprimer).
    - User (Agent) : accès uniquement à son profil (GET me, PATCH/PUT self).
    """
    queryset = get_user_model().objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            if not self.request.user.is_authenticated:
                return UserRegistrationSerializer
            if self.request.user.is_admin():
                return SuperAdminUserSerializer
            return UserSerializer
        if self.action in ('update', 'partial_update') and self.request.user.is_authenticated and self.request.user.is_admin():
            return AdminUserSerializer
        if self.request.user.is_authenticated and self.request.user.is_superadmin():
            return SuperAdminUserSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ('assign_entreprise', 'remove_entreprise', 'without_entreprise'):
            return [IsSuperAdmin()]
        # Admin gère entièrement les utilisateurs de son entreprise (séparation stricte entre entreprises)
        if self.action in ('me', 'list', 'retrieve', 'update', 'partial_update', 'destroy'):
            return [IsAdminFullEnterpriseAndUsers()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return get_user_model().objects.none()
        base = get_user_model().objects.all().order_by('-date_joined', '-id')
        if user.is_superadmin():
            return base
        if user.is_admin():
            if user.entreprise_id:
                return base.filter(entreprise_id=user.entreprise_id)
            return get_user_model().objects.none()
        if user.is_agent():
            return base.filter(pk=user.pk)
        return get_user_model().objects.none()

    def check_object_permissions(self, request, obj):
        """SuperAdmin : seulement son compte en écriture. Admin : même entreprise. User : seulement soi."""
        super().check_object_permissions(request, obj)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        if request.user.is_superadmin() and obj.pk != request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Le super administrateur ne peut modifier que son propre compte."))
        if request.user.is_agent() and obj.pk != request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Vous ne pouvez modifier que votre propre profil."))
        if request.user.is_admin() and obj.entreprise_id != request.user.entreprise_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Vous ne pouvez gérer que les utilisateurs de votre entreprise."))
    
    def create(self, request, *args, **kwargs):
        """Inscription publique (admin sans entreprise) ou création par un Admin (admin/user de son entreprise)."""
        if request.user.is_authenticated and request.user.is_admin():
            if not request.user.entreprise_id:
                return Response(
                    {'error': _("Vous devez être associé à une entreprise pour créer des utilisateurs.")},
                    status=status.HTTP_403_FORBIDDEN
                )
            data = request.data.copy()
            role = (data.get('role') or 'user').lower()
            data['role'] = 'user' if role not in ('admin', 'user') else role
            serializer = SuperAdminUserSerializer(data=data, context={'request': request, 'entreprise': request.user.entreprise})
            if serializer.is_valid():
                user = serializer.save()
                return Response({
                    'message': _('Utilisateur créé avec succès.'),
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'entreprise': user.entreprise.nom if user.entreprise else None,
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': _('Compte créé avec succès. Contactez le superadmin pour associer votre entreprise.'),
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def assign_entreprise(self, request, pk=None):
        """Associer un utilisateur à une entreprise (superadmin seulement)"""
        user = self.get_object()
        entreprise_id = request.data.get('entreprise_id')
        
        if not entreprise_id:
            return Response({'error': _('entreprise_id est requis')}, status=400)
        
        try:
            entreprise = Entreprise.objects.get(id=entreprise_id)
            user.entreprise = entreprise
            user.save()
            return Response({
                'message': f'Utilisateur {user.username} associé à {entreprise.nom}',
                'user_id': user.id,
                'entreprise_id': entreprise.id,
                'entreprise_nom': entreprise.nom
            })
        except Entreprise.DoesNotExist:
            return Response({'error': _('Entreprise introuvable')}, status=400)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def remove_entreprise(self, request, pk=None):
        """Retirer l'association entreprise d'un utilisateur"""
        user = self.get_object()
        user.entreprise = None
        user.save()
        return Response({
            'message': f'Association entreprise retirée pour {user.username}',
            'user_id': user.id
        })
    
    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[IsSuperAdminOrAdmin])
    def me(self, request):
        """
        Récupérer ou modifier les informations de l'utilisateur connecté (profil).
        SuperAdmin et Admin : GET (voir profil + entreprise), PATCH/PUT (modifier profil).
        Permission IsSuperAdminOrAdmin conservée pour que l'Admin garde l'accès à son entreprise et aux utilisateurs.
        """
        user = request.user
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        # PUT / PATCH : mise à jour du profil
        serializer_class = AdminUserSerializer if user.is_admin() else UserSerializer
        serializer = serializer_class(user, data=request.data, partial=(request.method == 'PATCH'))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsSuperAdmin])
    def register_admin(self, request):
        """Désactivé : le super administrateur ne peut pas créer d'utilisateurs (règles de sécurité)."""
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied(
            _("Le super administrateur ne peut pas créer d'utilisateurs. Les comptes sont créés par les Admins de chaque entreprise.")
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdmin])
    def without_entreprise(self, request):
        """Lister les utilisateurs sans entreprise (paginated, pour superadmin)"""
        users = get_user_model().objects.filter(entreprise__isnull=True, role='admin').order_by('-date_joined', '-id')
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
