"""Commande : initialiser les formules d'abonnement du catalogue SaaS."""
from django.core.management.base import BaseCommand

from abonnements.models import FormuleAbonnement
from abonnements.services.licence import _fonctionnalites_essai_complet, get_formule_essai


FORMULES = [
    {
        'code': FormuleAbonnement.CODE_STARTER,
        'nom': 'Starter',
        'description': 'Petites boutiques — gestion essentielle : articles, stock simple, ventes et rapports de base.',
        'prix_mensuel': 15,
        'prix_annuel': 150,
        'ordre_affichage': 1,
        'fonctionnalites': {
            'articles': True,
            'stock': True,
            'approvisionnement': False,
            'vente_comptant': True,
            'vente_credit': False,
            'clients': True,
            'dettes': False,
            'caisse': True,
            'rapports_simples': True,
            'rapports_avances': False,
            'impression_factures': True,
            'lecteur_code_barres': False,
            'roles_permissions': False,
            'tableaux_bord': True,
            'statistiques': False,
            'exports': False,
            'impression_pos': False,
            'multi_succursales': False,
            'assistance_prioritaire': False,
        },
        'limites': {'utilisateurs_max': 2, 'succursales_max': 1},
    },
    {
        'code': FormuleAbonnement.CODE_STANDARD,
        'nom': 'Standard',
        'description': 'Entreprises en croissance — gestion complète ventes, crédit, clients, dettes et caisse.',
        'prix_mensuel': 35,
        'prix_annuel': 350,
        'ordre_affichage': 2,
        'fonctionnalites': {
            'articles': True,
            'stock': True,
            'approvisionnement': True,
            'vente_comptant': True,
            'vente_credit': True,
            'clients': True,
            'dettes': True,
            'caisse': True,
            'rapports_simples': True,
            'rapports_avances': False,
            'impression_factures': True,
            'lecteur_code_barres': True,
            'roles_permissions': False,
            'tableaux_bord': True,
            'statistiques': True,
            'exports': False,
            'impression_pos': False,
            'multi_succursales': False,
            'assistance_prioritaire': False,
        },
        'limites': {'utilisateurs_max': 5, 'succursales_max': 1},
    },
    {
        'code': FormuleAbonnement.CODE_PROFESSIONNEL,
        'nom': 'Professionnelle',
        'description': 'PME structurées — rôles, rapports avancés, POS, exports et assistance prioritaire.',
        'prix_mensuel': 65,
        'prix_annuel': 650,
        'ordre_affichage': 3,
        'fonctionnalites': {
            'articles': True,
            'stock': True,
            'approvisionnement': True,
            'vente_comptant': True,
            'vente_credit': True,
            'clients': True,
            'dettes': True,
            'caisse': True,
            'rapports_simples': True,
            'rapports_avances': True,
            'impression_factures': True,
            'lecteur_code_barres': True,
            'roles_permissions': True,
            'tableaux_bord': True,
            'statistiques': True,
            'exports': True,
            'impression_pos': True,
            'multi_succursales': False,
            'assistance_prioritaire': True,
        },
        'limites': {'utilisateurs_max': 15, 'succursales_max': 3},
    },
    {
        'code': FormuleAbonnement.CODE_ENTREPRISE,
        'nom': 'Entreprise',
        'description': 'Grandes structures — multi-succursales, permissions avancées, rapports globaux.',
        'prix_mensuel': 120,
        'prix_annuel': 1200,
        'ordre_affichage': 4,
        'fonctionnalites': _fonctionnalites_essai_complet(),
        'limites': {'utilisateurs_max': None, 'succursales_max': None},
    },
]


class Command(BaseCommand):
    help = 'Initialise ou met à jour les formules d\'abonnement SaaS.'

    def handle(self, *args, **options):
        get_formule_essai()
        self.stdout.write(self.style.SUCCESS('Formule essai gratuit OK'))

        for data in FORMULES:
            code = data.pop('code')
            obj, created = FormuleAbonnement.objects.update_or_create(
                code=code,
                defaults={**data, 'devise': 'USD', 'est_visible_catalogue': True, 'est_active': True},
            )
            action = 'Créée' if created else 'Mise à jour'
            self.stdout.write(f'  {action} : {obj.nom} ({obj.code})')

        self.stdout.write(self.style.SUCCESS('Catalogue formules terminé.'))
