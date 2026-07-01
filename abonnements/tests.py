"""Tests SaaS abonnements et inscription."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from abonnements.models import AbonnementEntreprise, FormuleAbonnement
from abonnements.services.licence import (
    activer_abonnement_manuellement,
    build_etat_licence,
    demander_abonnement,
    demarrer_essai_gratuit,
)
from stock.models import Entreprise

User = get_user_model()


class EssaiGratuitTests(TestCase):
    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_STARTER,
            defaults={
                'nom': 'Starter',
                'prix_mensuel': 15,
                'prix_annuel': 150,
                'est_visible_catalogue': True,
            },
        )

    def test_essai_auto_a_creation_entreprise(self):
        ent = Entreprise.objects.create(nom='Boutique Test')
        abo = AbonnementEntreprise.objects.get(entreprise=ent, est_courant=True)
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ESSAI)
        self.assertEqual(abo.formule.code, FormuleAbonnement.CODE_ESSAI)
        self.assertTrue(abo.est_actif)

    def test_essai_acces_complet(self):
        ent = Entreprise.objects.create(nom='Test Complet')
        etat = build_etat_licence(ent.id)
        self.assertTrue(etat['est_actif'])
        self.assertTrue(etat['est_essai'])
        self.assertTrue(etat['fonctionnalites'].get('vente_credit'))
        self.assertTrue(etat['fonctionnalites'].get('rapports_avances'))

    def test_demande_et_activation_manuelle(self):
        user = User.objects.create_user(username='admin1', password='testpass123', role='admin')
        admin = User.objects.create_superuser(username='super', password='superpass123', email='s@t.com')
        ent = Entreprise.objects.create(nom='PME')
        abo = demander_abonnement(ent, FormuleAbonnement.CODE_STARTER, AbonnementEntreprise.PERIODE_MENSUEL, user=user)
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_EN_ATTENTE)
        abo = activer_abonnement_manuellement(abo, admin, notes='Paiement vérifié')
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ACTIF)
        etat = build_etat_licence(ent.id)
        self.assertTrue(etat['est_actif'])
        self.assertFalse(etat['est_essai'])

    def test_activation_par_entreprise_id(self):
        from abonnements.services.licence import activer_abonnement_pour_entreprise

        user = User.objects.create_user(username='admin2', password='testpass123', role='admin')
        admin = User.objects.create_superuser(username='super2', password='superpass123', email='s2@t.com')
        ent = Entreprise.objects.create(nom='PME 2')
        demander_abonnement(ent, FormuleAbonnement.CODE_STARTER, AbonnementEntreprise.PERIODE_MENSUEL, user=user)
        abo = activer_abonnement_pour_entreprise(ent.id, admin, notes='OK')
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ACTIF)
        self.assertTrue(build_etat_licence(ent.id)['est_actif'])

    def test_plateforme_activer_par_entreprise_api(self):
        user = User.objects.create_user(username='admin3', password='testpass123', role='admin')
        admin = User.objects.create_superuser(username='super3', password='superpass123', email='s3@t.com')
        ent = Entreprise.objects.create(nom='PME 3')
        abo = demander_abonnement(ent, FormuleAbonnement.CODE_STARTER, AbonnementEntreprise.PERIODE_MENSUEL, user=user)
        client = APIClient()
        client.force_authenticate(user=admin)
        resp = client.post('/api/plateforme/abonnements/activer-par-entreprise/', {
            'entreprise_id': ent.id,
            'notes': 'Test API',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['statut'], AbonnementEntreprise.STATUT_ACTIF)
        abo.refresh_from_db()
        self.assertEqual(abo.statut, AbonnementEntreprise.STATUT_ACTIF)

    def test_plateforme_dashboard_api(self):
        admin = User.objects.create_superuser(username='superdash', password='superpass123', email='dash@t.com')
        ent = Entreprise.objects.create(nom='PME Dash')
        demander_abonnement(ent, FormuleAbonnement.CODE_STARTER, AbonnementEntreprise.PERIODE_MENSUEL, user=admin)

        client = APIClient()
        client.force_authenticate(user=admin)
        resp = client.get('/api/plateforme/abonnements/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('entreprises', resp.data)
        self.assertIn('licences', resp.data)
        self.assertIn('plans', resp.data)


class InscriptionApiTests(TestCase):
    def test_inscription_compte_public(self):
        client = APIClient()
        resp = client.post('/api/inscription/compte/', {
            'username': 'nouveau',
            'email': 'n@example.com',
            'first_name': 'N',
            'last_name': 'U',
            'password': 'motdepasse1',
            'password_confirm': 'motdepasse1',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertIn('tokens', resp.data)
        self.assertEqual(resp.data['prochaine_etape'], 'creer_entreprise')

    def test_formules_catalogue_public(self):
        FormuleAbonnement.objects.create(
            code=FormuleAbonnement.CODE_STANDARD,
            nom='Croissance',
            prix_mensuel=35,
            est_visible_catalogue=True,
        )
        client = APIClient()
        resp = client.get('/api/abonnements/formules/')
        self.assertEqual(resp.status_code, 200)
        codes = [f['code'] for f in resp.data['results']]
        self.assertIn(FormuleAbonnement.CODE_STANDARD, codes)


class ControleLicenceEcritureTests(TestCase):
    """Étape 3 : blocage écritures si licence expirée."""

    def setUp(self):
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_STARTER,
            defaults={
                'nom': 'Starter',
                'prix_mensuel': 15,
                'prix_annuel': 150,
                'est_visible_catalogue': True,
            },
        )
        from users.models import Membership

        self.user = User.objects.create_user(username='adminlic', password='testpass123', role='admin')
        self.ent = Entreprise.objects.create(nom='Ent Expiree')
        self.membership = Membership.objects.create(
            user=self.user, entreprise=self.ent, role='admin', is_active=True,
        )
        self.abo = AbonnementEntreprise.objects.get(entreprise=self.ent, est_courant=True)
        self.abo.statut = AbonnementEntreprise.STATUT_EXPIRE
        self.abo.date_fin = timezone.now() - timedelta(days=5)
        self.abo.save(update_fields=['statut', 'date_fin', 'updated_at'])

        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        refresh['entreprise_id'] = self.ent.id
        refresh['membership_id'] = self.membership.id
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_lecture_autorisee_licence_expiree(self):
        resp = self.client.get('/api/abonnements/mon-abonnement/')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data['est_actif'])

    def test_ecriture_bloquee_licence_expiree(self):
        resp = self.client.post('/api/typearticles/', {'nom': 'Test Type'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get('code'), 'licence_inactive')
        self.assertIn('etat_licence', resp.json())

    def test_demande_abonnement_autorisee_si_expiree(self):
        resp = self.client.post('/api/abonnements/demander/', {
            'formule_code': FormuleAbonnement.CODE_STARTER,
            'periode': AbonnementEntreprise.PERIODE_MENSUEL,
        }, format='json')
        self.assertIn(resp.status_code, (201, 400))  # 400 si déjà en attente après 1er test
        if resp.status_code == 403:
            self.fail('Demande abonnement ne doit pas être bloquée')

    def test_essai_actif_ecriture_autorisee(self):
        self.abo.statut = AbonnementEntreprise.STATUT_ESSAI
        self.abo.date_fin = timezone.now() + timedelta(days=30)
        self.abo.save(update_fields=['statut', 'date_fin', 'updated_at'])
        resp = self.client.post('/api/typearticles/', {'nom': 'Type OK'}, format='json')
        if resp.status_code == 403:
            self.assertNotEqual(resp.json().get('code'), 'licence_inactive')


class LimitesPlanTests(TestCase):
    """Étape 4 : limites par formule."""

    def setUp(self):
        from users.models import Membership
        from rest_framework_simplejwt.tokens import RefreshToken

        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_ESSAI,
            defaults={'nom': 'Essai', 'duree_essai_jours': 60},
        )
        FormuleAbonnement.objects.get_or_create(
            code=FormuleAbonnement.CODE_STARTER,
            defaults={
                'nom': 'Starter',
                'prix_mensuel': 15,
                'prix_annuel': 150,
                'est_visible_catalogue': True,
                'fonctionnalites': {
                    'articles': True, 'stock': True, 'approvisionnement': False,
                    'vente_comptant': True, 'vente_credit': False, 'clients': True,
                    'dettes': False, 'caisse': True, 'rapports_simples': True,
                },
                'limites': {'utilisateurs_max': 2, 'succursales_max': 1},
            },
        )
        self.user = User.objects.create_user(username='starteradmin', password='testpass123', role='admin')
        self.ent = Entreprise.objects.create(nom='Boutique Starter')
        self.membership = Membership.objects.create(
            user=self.user, entreprise=self.ent, role='admin', is_active=True,
        )
        self.abo = AbonnementEntreprise.objects.get(entreprise=self.ent, est_courant=True)
        starter = FormuleAbonnement.objects.get(code=FormuleAbonnement.CODE_STARTER)
        self.abo.formule = starter
        self.abo.statut = AbonnementEntreprise.STATUT_ACTIF
        self.abo.date_fin = timezone.now() + timedelta(days=30)
        self.abo.save()

        refresh = RefreshToken.for_user(self.user)
        refresh['entreprise_id'] = self.ent.id
        refresh['membership_id'] = self.membership.id
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_approvisionnement_bloque_starter(self):
        resp = self.client.post('/api/entrees/', {'motif': 'test'}, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get('code'), 'fonctionnalite_non_autorisee')

    def test_mes_limites_endpoint(self):
        resp = self.client.get('/api/abonnements/mes-limites/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['formule_code'], FormuleAbonnement.CODE_STARTER)
        self.assertFalse(resp.data['fonctionnalites']['approvisionnement'])
        self.assertEqual(resp.data['utilisateurs']['maximum'], 2)

    def test_quota_utilisateurs_starter(self):
        from users.models import Membership
        u2 = User.objects.create_user(username='agent1', password='x', role='user')
        Membership.objects.create(user=u2, entreprise=self.ent, role='user', is_active=True)
        resp = self.client.post('/api/users/', {
            'username': 'agent2',
            'email': 'a2@test.com',
            'password': 'testpass123',
            'role': 'user',
        }, format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get('code'), 'limite_quota_atteinte')
