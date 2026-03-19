from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from stock.serializers import EntrepriseSerializer


class UserSerializer(serializers.ModelSerializer):
    """Serializer de base pour les utilisateurs (entreprise via Membership)."""
    entreprise_nom = serializers.SerializerMethodField()
    entreprise_id = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role',
                  'entreprise_id', 'entreprise_nom', 'is_active', 'date_joined']
        read_only_fields = ['role', 'date_joined']

    def get_entreprise_nom(self, obj):
        ent = obj.get_entreprise()
        return ent.nom if ent else None

    def get_entreprise_id(self, obj):
        return obj.get_entreprise_id()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer pour l'inscription des nouveaux admins"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(_("Les mots de passe ne correspondent pas"))
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Créer l'utilisateur comme admin par défaut
        user = get_user_model().objects.create_user(
            role='admin',
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'Admin : gestion des utilisateurs de son entreprise.
    """
    entreprise_nom = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role',
                  'entreprise_nom', 'is_active', 'date_joined', 'password']
        read_only_fields = ['date_joined', 'entreprise_nom']

    def get_entreprise_nom(self, obj):
        ent = obj.get_entreprise()
        return ent.nom if ent else None

    def validate_role(self, value):
        if value and value not in ('admin', 'user'):
            raise serializers.ValidationError(_("Le rôle doit être 'admin' ou 'user' pour les utilisateurs de votre entreprise."))
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SuperAdminUserSerializer(serializers.ModelSerializer):
    """Serializer pour les actions du superadmin sur les utilisateurs (entreprise via Membership)."""
    entreprise_nom = serializers.SerializerMethodField()
    entreprise = EntrepriseSerializer(required=False, write_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role',
                  'entreprise', 'entreprise_nom', 'is_active', 'date_joined', 'password']
        read_only_fields = ['date_joined']

    def get_entreprise_nom(self, obj):
        ent = obj.get_entreprise()
        return ent.nom if ent else None

    def create(self, validated_data):
        """Créer un utilisateur puis un Membership si entreprise fournie (context ou nested)."""
        from .models import Membership
        entreprise_data = validated_data.pop('entreprise', None)
        password = validated_data.pop('password', None)
        role = validated_data.get('role', 'admin')
        entreprise = self.context.get('entreprise')
        if not entreprise and entreprise_data:
            if isinstance(entreprise_data, dict):
                entreprise_serializer = EntrepriseSerializer(data=entreprise_data)
                if entreprise_serializer.is_valid():
                    entreprise = entreprise_serializer.save()
                else:
                    raise serializers.ValidationError(entreprise_serializer.errors)
            else:
                entreprise = entreprise_data
        if 'role' not in validated_data:
            validated_data['role'] = role
        user = get_user_model().objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        if entreprise:
            Membership.objects.get_or_create(
                user=user,
                entreprise=entreprise,
                defaults={'role': 'admin' if role == 'admin' else 'user', 'is_active': True},
            )
        return user

    def update(self, instance, validated_data):
        """Mise à jour utilisateur ; entreprise gérée via Membership (création si fournie)."""
        from .models import Membership
        password = validated_data.pop('password', None)
        entreprise_data = validated_data.pop('entreprise', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if entreprise_data is not None:
            if isinstance(entreprise_data, dict):
                entreprise_serializer = EntrepriseSerializer(data=entreprise_data)
                if entreprise_serializer.is_valid():
                    entreprise = entreprise_serializer.save()
                else:
                    raise serializers.ValidationError(entreprise_serializer.errors)
            else:
                entreprise = entreprise_data
            Membership.objects.get_or_create(
                user=instance,
                entreprise=entreprise,
                defaults={'role': 'admin', 'is_active': True},
            )
        return instance