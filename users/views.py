from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from .serializers import UserSerializer, UserRegistrationSerializer, SuperAdminUserSerializer
from .permissions import IsSuperAdmin, IsSuperAdminOrAdmin
from stock.models import Entreprise


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer personnalisé pour inclure les informations utilisateur dans le token"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Ajouter les informations utilisateur à la réponse
        user_data = {
            'id': self.user.id,
            'username': self.user.username,
            'role': self.user.role,
            'email': self.user.email,
        }
        
        # Ajouter les infos entreprise si l'utilisateur en a une
        if self.user.entreprise:
            user_data['entreprise'] = {
                'id': self.user.entreprise.id,
                'nom': self.user.entreprise.nom,
                'secteur': self.user.entreprise.secteur,
                'adresse': self.user.entreprise.adresse,
                'telephone': self.user.entreprise.telephone,
                'email': self.user.entreprise.email,
                'responsable': self.user.entreprise.responsable,
            }
        else:
            user_data['entreprise'] = None
        
        data['user'] = user_data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vue personnalisée pour la connexion avec informations utilisateur"""
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des utilisateurs.
    Super admin : peut tout voir et modifier
    Admin : peut seulement voir et modifier son propre profil
    """
    queryset = get_user_model().objects.all()
    
    def get_serializer_class(self):
        """Utiliser le bon serializer selon l'action et l'utilisateur"""
        if self.action == 'create' and not self.request.user.is_authenticated:
            # Inscription libre pour nouveaux admins
            return UserRegistrationSerializer
        elif self.request.user.is_authenticated and self.request.user.is_superadmin():
            return SuperAdminUserSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Permissions dynamiques selon l'action."""
        if self.action == 'create':
            # Inscription ouverte pour nouveaux admins
            return [permissions.AllowAny()]
        elif self.action in ['update', 'partial_update', 'destroy', 'assign_entreprise', 'remove_entreprise']:
            # Seuls les super admin peuvent modifier/supprimer
            return [IsSuperAdmin()]
        elif self.action == 'list':
            # Liste pour super admin et admin (filtrée)
            return [IsSuperAdminOrAdmin()]
        elif self.action == 'retrieve':
            # Super admin ou admin (pour voir son propre profil)
            return [IsSuperAdminOrAdmin()]
        else:
            return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        """Filtrage selon le rôle. Ordre : plus récent en premier."""
        user = self.request.user
        base = get_user_model().objects.all().order_by('-date_joined', '-id')
        if user.is_superadmin():
            return base
        elif user.is_admin():
            # Admin peut voir les utilisateurs de son entreprise
            return base
        return get_user_model().objects.none()
    
    def create(self, request, *args, **kwargs):
        """Inscription d'un nouvel admin"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Compte créé avec succès. Contactez le superadmin pour associer votre entreprise.',
                'user_id': user.id,
                'username': user.username,
                'email': user.email
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdmin])
    def me(self, request):
        """Récupérer les informations de l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsSuperAdmin])
    def register_admin(self, request):
        """Créer un admin avec son entreprise (superadmin seulement)"""
        serializer = SuperAdminUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': 'Admin créé avec succès',
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'entreprise': user.entreprise.nom if user.entreprise else None
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
