"""Inscription publique portail client : POST /api/client-auth/register/."""
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import Client, ClientEntreprise, Entreprise, Succursale


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class ClientRegisterTests(APITestCase):
    URL = '/api/client-auth/register/'

    def setUp(self):
        cache.clear()  # compteur du throttle
        self.entreprise = Entreprise.objects.create(
            nom='Boutique', secteur='s', pays='CD', adresse='a', telephone='t',
            email='boutique@example.com', nif='n-reg', responsable='resp',
        )

    def _body(self, **over):
        body = {
            'nom': 'Jean Client',
            'telephone': '0999',
            'adresse': 'Kinshasa',
            'email': 'jean.client@example.com',
            'password': 'Mot2PasseSolide!',
            'liens': [{'entreprise': self.entreprise.pk, 'is_special': False}],
        }
        body.update(over)
        return body

    def test_inscription_puis_connexion(self):
        resp = self.client.post(self.URL, self._body(), format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        client = Client.objects.get(email='jean.client@example.com')
        self.assertTrue(client.has_portal_password())
        self.assertTrue(ClientEntreprise.objects.filter(client=client, entreprise=self.entreprise).exists())

        login = self.client.post(
            '/api/client-auth/login/',
            {'email': 'jean.client@example.com', 'password': 'Mot2PasseSolide!'},
            format='json',
        )
        self.assertEqual(login.status_code, 200, login.content)
        self.assertIn('access', login.json())

    def test_email_existant_ne_divulgue_rien(self):
        self.client.post(self.URL, self._body(), format='json')
        resp = self.client.post(self.URL, self._body(nom='Autre'), format='json')
        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertEqual(body.get('code'), 'email_deja_utilise')
        self.assertNotIn('existing_client', body)
        self.assertNotIn('entreprises_disponibles', body)

    def test_entreprise_inconnue(self):
        resp = self.client.post(self.URL, self._body(liens=[{'entreprise': 999999}]), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Client.objects.exists())

    def test_succursale_d_une_autre_entreprise_refusee(self):
        autre = Entreprise.objects.create(
            nom='Autre', secteur='s', pays='CD', adresse='a', telephone='t',
            email='autre@example.com', nif='n-autre', responsable='resp',
        )
        succ = Succursale.objects.create(nom='S1', entreprise=autre)
        resp = self.client.post(
            self.URL,
            self._body(liens=[{'entreprise': self.entreprise.pk, 'succursale': succ.pk}]),
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_mot_de_passe_faible_refuse(self):
        resp = self.client.post(self.URL, self._body(password='123'), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('password', resp.json())

    def test_email_obligatoire(self):
        resp = self.client.post(self.URL, self._body(email=''), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email', resp.json())
