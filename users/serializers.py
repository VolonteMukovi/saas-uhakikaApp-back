from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from stock.serializers import EntrepriseSerializer


class UserSerializer(serializers.ModelSerializer):
    """Serializer de base pour les utilisateurs"""
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 
                 'entreprise', 'entreprise_nom', 'is_active', 'date_joined']
        read_only_fields = ['role', 'date_joined', 'entreprise']


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


class SuperAdminUserSerializer(serializers.ModelSerializer):
    """Serializer pour les actions du superadmin sur les utilisateurs"""
    entreprise_nom = serializers.CharField(source='entreprise.nom', read_only=True)
    entreprise = EntrepriseSerializer(required=False)
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 
                 'entreprise', 'entreprise_nom', 'is_active', 'date_joined', 'password']
        read_only_fields = ['date_joined']
    
    def create(self, validated_data):
        """Créer un utilisateur avec son entreprise"""
        entreprise_data = validated_data.pop('entreprise', None)
        password = validated_data.pop('password', None)
        
        # Créer l'entreprise si fournie
        if entreprise_data:
            entreprise_serializer = EntrepriseSerializer(data=entreprise_data)
            if entreprise_serializer.is_valid():
                entreprise = entreprise_serializer.save()
                validated_data['entreprise'] = entreprise
            else:
                raise serializers.ValidationError(entreprise_serializer.errors)
        
        # Définir le rôle par défaut comme admin si non spécifié
        if 'role' not in validated_data:
            validated_data['role'] = 'admin'
        
        # Créer l'utilisateur
        user = get_user_model().objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        
        return user
    
    def update(self, instance, validated_data):
        # Le superadmin peut modifier tous les champs, y compris le rôle et l'entreprise
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance