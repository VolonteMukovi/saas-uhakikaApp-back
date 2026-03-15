"""
Commande Django pour migrer les rôles d'utilisateurs
De: DG, Guichetier, Partenaire
Vers: superadmin, admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Migrer les rôles d\'utilisateurs vers le nouveau système (superadmin/admin)'

    def handle(self, *args, **options):
        self.stdout.write("🔄 Début de la migration des rôles utilisateurs...")
        
        # 1. Convertir tous les DG en admin
        dg_users = User.objects.filter(role='DG')
        dg_count = dg_users.count()
        for user in dg_users:
            user.role = 'admin'
            user.save()
            self.stdout.write(f"✅ {user.username}: DG → admin")
        
        # 2. Convertir tous les Guichetiers en admin  
        guichetier_users = User.objects.filter(role='Guichetier')
        guichetier_count = guichetier_users.count()
        for user in guichetier_users:
            user.role = 'admin'
            user.save()
            self.stdout.write(f"✅ {user.username}: Guichetier → admin")
        
        # 3. Convertir tous les Partenaires en admin
        partenaire_users = User.objects.filter(role='Partenaire')
        partenaire_count = partenaire_users.count()
        for user in partenaire_users:
            user.role = 'admin'
            user.save()
            self.stdout.write(f"✅ {user.username}: Partenaire → admin")
        
        # 4. S'assurer que tous les superusers sont des superadmin
        superusers = User.objects.filter(is_superuser=True)
        superuser_count = superusers.count()
        for user in superusers:
            user.role = 'superadmin'
            user.entreprise = None  # Superadmin n'appartient à aucune entreprise
            user.save()
            self.stdout.write(f"✅ {user.username}: configuré comme superadmin")
        
        # 5. Statistiques finales
        total_admin = User.objects.filter(role='admin').count()
        total_superadmin = User.objects.filter(role='superadmin').count()
        
        self.stdout.write(self.style.SUCCESS(f"\n📊 Migration terminée:"))
        self.stdout.write(f"   - DG convertis: {dg_count}")
        self.stdout.write(f"   - Guichetiers convertis: {guichetier_count}")
        self.stdout.write(f"   - Partenaires convertis: {partenaire_count}")
        self.stdout.write(f"   - Superusers configurés: {superuser_count}")
        self.stdout.write(f"   - Total admins: {total_admin}")
        self.stdout.write(f"   - Total superadmins: {total_superadmin}")
        self.stdout.write(f"   - Total utilisateurs: {total_admin + total_superadmin}")
        
        self.stdout.write(self.style.SUCCESS("🎉 Migration réussie !"))