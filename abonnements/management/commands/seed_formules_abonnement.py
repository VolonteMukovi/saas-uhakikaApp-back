"""Commande : initialiser les formules d'abonnement du catalogue SaaS."""
from django.core.management.base import BaseCommand

from abonnements.models import FormuleAbonnement
from abonnements.services.licence import _fonctionnalites_essai_complet, get_formule_essai


FORMULES = [
    {
        'code': FormuleAbonnement.CODE_ESSENTIEL,
        'nom': 'Essentiel',
        'description': (
            'Le plan idéal pour commencer à gérer simplement les articles, le stock, '
            'les ventes, les factures et la caisse.'
        ),
        'prix_mensuel': 30,
        'prix_annuel': 342,
        'ordre_affichage': 1,
        'fonctionnalites': {
            'articles': True,
            'stock': True,
            'approvisionnement': True,
            'vente_comptant': True,
            'vente_credit': True,
            'clients': True,
            'dettes': True,
            'caisse': True,
            'rapports_simples': False,
            'rapports_avances': False,
            'impression_factures': True,
            'lecteur_code_barres': False,
            'roles_permissions': False,
            'tableaux_bord': True,
            'statistiques': False,
            'exports': False,
            'impression_pos': True,
            'multi_succursales': False,
            'assistance_prioritaire': False,
            'portail_client_autonome': False,
            'chatbot': False,
            'accompagnement_personnalisation': False,
        },
        'limites': {'utilisateurs_max': 2, 'succursales_max': 1},
    },
    {
        'code': FormuleAbonnement.CODE_CROISSANCE,
        'nom': 'Croissance',
        'description': (
            'Un plan adapté aux entreprises qui grandissent et souhaitent être '
            'accompagnées dans l’utilisation de la plateforme.'
        ),
        'prix_mensuel': 60,
        'prix_annuel': 684,
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
            'rapports_simples': False,
            'rapports_avances': False,
            'impression_factures': True,
            'lecteur_code_barres': False,
            'roles_permissions': False,
            'tableaux_bord': True,
            'statistiques': True,
            'exports': False,
            'impression_pos': True,
            'multi_succursales': False,
            'assistance_prioritaire': True,
            'portail_client_autonome': False,
            'chatbot': True,
            'accompagnement_personnalisation': True,
        },
        'limites': {'utilisateurs_max': 4, 'succursales_max': 1},
    },
    {
        'code': FormuleAbonnement.CODE_PREMIUM_ENTREPRISE,
        'nom': 'Premium Entreprise',
        'description': (
            'La formule complète pour les entreprises qui veulent centraliser '
            'toute leur gestion commerciale sans restriction.'
        ),
        'prix_mensuel': 120,
        'prix_annuel': 1296,
        'ordre_affichage': 3,
        'fonctionnalites': _fonctionnalites_essai_complet(),
        'limites': {'utilisateurs_max': None, 'succursales_max': None},
    },
]


class Command(BaseCommand):
    help = 'Initialise ou met à jour les formules d\'abonnement SaaS.'

    def handle(self, *args, **options):
        # Migration douce des anciens codes vers les codes officiels.
        remap = {
            'essai_gratuit': FormuleAbonnement.CODE_ESSAI,
            'starter': FormuleAbonnement.CODE_ESSENTIEL,
            'standard': FormuleAbonnement.CODE_CROISSANCE,
            'professionnel': FormuleAbonnement.CODE_PREMIUM_ENTREPRISE,
            'entreprise': FormuleAbonnement.CODE_PREMIUM_ENTREPRISE,
        }
        for old_code, new_code in remap.items():
            if old_code == new_code:
                continue
            obj = FormuleAbonnement.objects.filter(code=old_code).first()
            if obj and not FormuleAbonnement.objects.filter(code=new_code).exists():
                obj.code = new_code
                obj.save(update_fields=['code'])
                self.stdout.write(f'  Code migré: {old_code} -> {new_code}')

        get_formule_essai()
        self.stdout.write(self.style.SUCCESS('Formule Découverte Pro OK'))

        for data in FORMULES:
            code = data.pop('code')
            obj, created = FormuleAbonnement.objects.update_or_create(
                code=code,
                defaults={**data, 'devise': 'USD', 'est_visible_catalogue': True, 'est_active': True},
            )
            action = 'Créée' if created else 'Mise à jour'
            self.stdout.write(f'  {action} : {obj.nom} ({obj.code})')

        self.stdout.write(self.style.SUCCESS('Catalogue formules terminé.'))
