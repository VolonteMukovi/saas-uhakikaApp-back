import time
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers as drf_serializers
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext as _

from .serializers import UserSerializer, UserRegistrationSerializer, SuperAdminUserSerializer, AdminUserSerializer
from .permissions import IsSuperAdmin, IsSuperAdminOrAdmin, IsAdminFullEnterpriseAndUsers
from stock.models import Entreprise, Succursale
from .models import Membership

# Durée max de la session (24 h) en secondes ; au-delà, l'utilisateur doit se reconnecter
SESSION_MAX_AGE_SECONDS = 24 * 3600


def _add_context_to_token(refresh, membership):
    """Ajoute le contexte multi-tenant aux claims JWT (entreprise_id, succursale_id, membership_id)."""
    if not membership:
        refresh["entreprise_id"] = None
        refresh["succursale_id"] = None
        refresh["membership_id"] = None
        return
    refresh["entreprise_id"] = membership.entreprise_id
    refresh["succursale_id"] = membership.default_succursale_id
    refresh["membership_id"] = membership.id


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Connexion : tokens + infos user ; claims session_start + contexte tenant (entreprise/succursale)."""

    def validate(self, attrs):
        super(TokenObtainPairSerializer, self).validate(attrs)
        refresh = self.get_token(self.user)
        refresh["session_start"] = int(time.time())

        # Contexte multi-tenant : premier membership actif (entreprise + succursale par défaut)
        first_m = (
            Membership.objects
            .select_related('entreprise', 'default_succursale')
            .filter(user_id=self.user.id, is_active=True)
            .order_by('entreprise_id', 'id')
            .first()
        )
        _add_context_to_token(refresh, first_m)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        user_data = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
        }
        memberships = (
            Membership.objects
            .select_related('entreprise', 'default_succursale')
            .filter(user_id=self.user.id, is_active=True)
            .order_by('entreprise_id', 'id')
        )
        entreprises = []
        for m in memberships:
            e = m.entreprise
            entreprises.append({
                "membership_id": m.id,
                "entreprise": {
                    "id": e.id,
                    "nom": e.nom,
                    "secteur": e.secteur,
                    "adresse": e.adresse,
                    "telephone": e.telephone,
                    "email": e.email,
                    "responsable": e.responsable,
                    "has_branches": getattr(e, "has_branches", False),
                },
                "role": m.role,
                "default_branch_id": m.default_succursale_id,
            })

        primary_entreprise = entreprises[0]["entreprise"] if entreprises else None
        user_data["entreprise"] = primary_entreprise
        user_data["enterprises"] = entreprises
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


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def select_context(request):
    """
    Étape 2/3 du login multi-tenant : choisir l'entreprise (et optionnellement la succursale).
    Body: { "entreprise_id": int, "succursale_id": int | null }
    Retourne de nouveaux access + refresh avec le contexte dans les claims.
    """
    user = request.user
    entreprise_id = request.data.get('entreprise_id')
    if not entreprise_id:
        return Response(
            {'error': _('entreprise_id est requis.')},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        entreprise_id = int(entreprise_id)
    except (TypeError, ValueError):
        return Response(
            {'error': _('entreprise_id doit être un entier.')},
            status=status.HTTP_400_BAD_REQUEST
        )

    membership = (
        Membership.objects
        .select_related('entreprise', 'default_succursale')
        .filter(user=user, entreprise_id=entreprise_id, is_active=True)
        .first()
    )
    if not membership:
        return Response(
            {'error': _("Vous n'avez pas accès à cette entreprise.")},
            status=status.HTTP_403_FORBIDDEN
        )

    succursale_id = request.data.get('succursale_id')
    if succursale_id is not None and succursale_id != '':
        try:
            succursale_id = int(succursale_id)
        except (TypeError, ValueError):
            succursale_id = None
        if succursale_id is not None:
            if not Succursale.objects.filter(id=succursale_id, entreprise_id=entreprise_id).exists():
                return Response(
                    {'error': _("Cette succursale n'appartient pas à l'entreprise choisie.")},
                    status=status.HTTP_400_BAD_REQUEST
                )
    else:
        succursale_id = membership.default_succursale_id

    # Nouveaux tokens avec contexte
    refresh = RefreshToken.for_user(user)
    refresh["session_start"] = int(time.time())
    # Construire un "contexte" pour le token (même membership, succursale choisie ou défaut)
    refresh["entreprise_id"] = entreprise_id
    refresh["succursale_id"] = succursale_id
    refresh["membership_id"] = membership.id

    data = {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'entreprise_id': entreprise_id,
            'succursale_id': succursale_id,
            'membership_id': membership.id,
            'entreprise': {
                'id': membership.entreprise.id,
                'nom': membership.entreprise.nom,
                'has_branches': getattr(membership.entreprise, 'has_branches', False),
            },
        },
    }
    return Response(data, status=status.HTTP_200_OK)


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
            if self.request.user.is_admin(self.request):
                return SuperAdminUserSerializer
            return UserSerializer
        if self.action in ('update', 'partial_update') and self.request.user.is_authenticated and self.request.user.is_admin(self.request):
            return AdminUserSerializer
        if self.request.user.is_authenticated and self.request.user.is_superadmin():
            return SuperAdminUserSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ('remove_entreprise', 'without_entreprise'):
            return [IsSuperAdmin()]
        # assign_entreprise : auto-association par l'utilisateur lui-même (ou par superadmin)
        if self.action == 'assign_entreprise':
            return [permissions.IsAuthenticated()]
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
        if user.is_admin(self.request):
            eid = getattr(self.request, 'tenant_id', None) or user.get_entreprise_id(self.request)
            if eid:
                return base.filter(memberships__entreprise_id=eid, memberships__is_active=True).distinct()
            return get_user_model().objects.none()
        if user.is_agent(self.request):
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
        if request.user.is_agent(request) and obj.pk != request.user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Vous ne pouvez modifier que votre propre profil."))
        if request.user.is_admin(request):
            eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
            if obj.get_entreprise_id() != eid:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied(_("Vous ne pouvez gérer que les utilisateurs de votre entreprise."))
    
    def create(self, request, *args, **kwargs):
        """Inscription publique (admin sans entreprise) ou création par un Admin (admin/user de son entreprise)."""
        if request.user.is_authenticated and request.user.is_admin(request):
            entreprise = getattr(request, 'tenant_id', None) and Entreprise.objects.filter(id=request.tenant_id).first() or request.user.get_entreprise(request)
            if not entreprise:
                return Response(
                    {'error': _("Vous devez être associé à une entreprise pour créer des utilisateurs.")},
                    status=status.HTTP_403_FORBIDDEN
                )
            data = request.data.copy()
            role = (data.get('role') or 'user').lower()
            data['role'] = 'user' if role not in ('admin', 'user') else role
            serializer = SuperAdminUserSerializer(data=data, context={'request': request, 'entreprise': entreprise})
            if serializer.is_valid():
                user = serializer.save()
                m = user.get_current_membership(request)
                return Response({
                    'message': _('Utilisateur créé avec succès.'),
                    'user_id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': m.role if m else role,
                    'entreprise': m.entreprise.nom if m else (entreprise.nom if entreprise else None),
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
    
    @action(detail=True, methods=['post'])
    def assign_entreprise(self, request, pk=None):
        """
        Associer un utilisateur à une entreprise via Membership.

        - Superadmin : peut associer n'importe quel utilisateur.
        - Utilisateur simple : ne peut associer que son propre compte.

        Body attendu :
        {
            "entreprise_id": int,          # obligatoire
            "role": "admin" | "user"       # optionnel, défaut = "admin"
        }
        """
        target_user = self.get_object()

        # Si ce n'est pas un superadmin, il ne peut agir que sur lui-même
        if not request.user.is_superadmin() and target_user.id != request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(_("Vous ne pouvez associer qu'à partir de votre propre compte."))

        entreprise_id = request.data.get('entreprise_id')
        if not entreprise_id:
            return Response({'error': _('entreprise_id est requis')}, status=status.HTTP_400_BAD_REQUEST)

        role = (request.data.get('role') or 'admin').lower()
        if role not in ('admin', 'user'):
            return Response(
                {'error': _("Le rôle doit être 'admin' ou 'user'.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            entreprise = Entreprise.objects.get(id=entreprise_id)
        except Entreprise.DoesNotExist:
            return Response({'error': _('Entreprise introuvable')}, status=status.HTTP_400_BAD_REQUEST)

        membership, created = Membership.objects.get_or_create(
            user=target_user,
            entreprise=entreprise,
            defaults={'role': role, 'is_active': True},
        )
        if not created:
            membership.role = role
            membership.is_active = True
            membership.save()

        return Response({
            'message': _('Utilisateur %(user)s associé à %(ent)s avec le rôle %(role)s') % {
                'user': target_user.username,
                'ent': entreprise.nom,
                'role': role,
            },
            'user_id': target_user.id,
            'entreprise_id': entreprise.id,
            'entreprise_nom': entreprise.nom,
            'role': membership.role,
        })

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def remove_entreprise(self, request, pk=None):
        """Retirer l'association entreprise d'un utilisateur (entreprise_id dans le body)."""
        user = self.get_object()
        entreprise_id = request.data.get('entreprise_id')
        if not entreprise_id:
            return Response({'error': _('entreprise_id est requis')}, status=400)
        deleted, _ = Membership.objects.filter(user=user, entreprise_id=entreprise_id).delete()
        return Response({
            'message': _('Association entreprise retirée pour %(user)s') % {'user': user.username},
            'user_id': user.id,
            'deleted': deleted,
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
        serializer_class = AdminUserSerializer if user.is_admin(request) else UserSerializer
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
        """Lister les utilisateurs sans aucune entreprise (aucun membership actif), pour superadmin."""
        with_membership = Membership.objects.filter(is_active=True).values_list('user_id', flat=True)
        users = get_user_model().objects.exclude(id__in=with_membership).order_by('-date_joined', '-id')
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
