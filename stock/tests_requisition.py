from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import (
    Article,
    Devise,
    Entree,
    Entreprise,
    LigneEntree,
    Requisition,
    Stock,
    SousTypeArticle,
    TypeArticle,
    Unite,
)
from users.models import Membership


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class RequisitionModuleTests(APITestCase):
    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom='E-REQ',
            secteur='s',
            pays='CD',
            adresse='a',
            telephone='t',
            email='req@example.com',
            nif='n-req',
            responsable='resp',
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            username='admin_req',
            email='req@example.com',
            password='secretpass123',
        )
        Membership.objects.create(
            user=self.user,
            entreprise=self.entreprise,
            role='admin',
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)

        Devise.objects.create(
            sigle='USD', nom='Dollar', symbole='$',
            est_principal=True, entreprise=self.entreprise,
        )
        self.unite = Unite.objects.create(libelle='pcs', entreprise=self.entreprise)
        self.type_art = TypeArticle.objects.create(libelle='Consommable', entreprise=self.entreprise)
        self.sous = SousTypeArticle.objects.create(
            libelle='Divers', type_article=self.type_art, entreprise=self.entreprise,
        )
        self.article = Article.objects.create(
            nom_scientifique='Café Premium Stock',
            nom_commercial='Café Premium',
            sous_type_article=self.sous,
            unite=self.unite,
            entreprise=self.entreprise,
        )
        Stock.objects.create(article=self.article, Qte=Decimal('0'), seuilAlert=Decimal('10'))
        entree = Entree.objects.create(libele='Appro test', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            quantite=Decimal('50'),
            quantite_restante=Decimal('0'),
            prix_unitaire=Decimal('2.50000'),
            prix_vente=Decimal('3.50000'),
        )

        self.article_sans_appro = Article.objects.create(
            nom_scientifique='Nouveau Produit',
            nom_commercial='Nouveau',
            sous_type_article=self.sous,
            unite=self.unite,
            entreprise=self.entreprise,
        )
        Stock.objects.create(
            article=self.article_sans_appro, Qte=Decimal('0'), seuilAlert=Decimal('5'),
        )

    def test_create_with_suggestions_and_price_rules(self):
        response = self.client.post(
            '/api/requisitions/',
            {
                'titre': 'Réassort café',
                'avec_suggestions': True,
                'sources': ['rupture'],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertTrue(data['numero'].startswith('REQ-'))
        self.assertEqual(data['statut'], 'BROUILLON')
        self.assertGreaterEqual(data['resume']['nombre_lignes'], 1)

        ligne_cafe = next(
            (l for l in data['lignes'] if l['article_id'] == self.article.article_id),
            None,
        )
        self.assertIsNotNone(ligne_cafe)
        self.assertEqual(ligne_cafe['prix_estime'], '2.50000')
        self.assertFalse(ligne_cafe['prix_manquant'])

        ligne_new = next(
            (l for l in data['lignes'] if l['article_id'] == self.article_sans_appro.article_id),
            None,
        )
        self.assertIsNotNone(ligne_new)
        self.assertIsNone(ligne_new['prix_estime'])
        self.assertEqual(ligne_new['prix_estime_affiche'], '.....')
        self.assertTrue(ligne_new['prix_manquant'])

    def test_ligne_libre_workflow_document_json(self):
        create = self.client.post(
            '/api/requisitions/',
            {'titre': 'Nouveau rayon', 'avec_suggestions': False},
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.content)
        req_id = create.json()['id']

        add = self.client.post(
            f'/api/requisitions/{req_id}/lignes/',
            {
                'type_ligne': 'LIBRE',
                'designation': 'Café Premium Edition Limitée',
                'quantite': '24',
                'unite': 'boîtes',
                'prix_estime': '......',
            },
            format='json',
        )
        self.assertEqual(add.status_code, 200, add.content)
        ligne = add.json()['lignes'][0]
        self.assertEqual(ligne['type_ligne'], 'LIBRE')
        self.assertTrue(ligne['prix_manquant'])

        patch = self.client.patch(
            f'/api/requisitions/{req_id}/lignes/{ligne["id"]}/',
            {'prix_estime': '3.75'},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.content)
        self.assertEqual(patch.json()['lignes'][0]['prix_estime'], '3.75000')

        soumettre = self.client.post(f'/api/requisitions/{req_id}/soumettre/', {}, format='json')
        self.assertEqual(soumettre.status_code, 200, soumettre.content)
        self.assertEqual(soumettre.json()['statut'], 'EN_ATTENTE_VALIDATION')

        valider = self.client.post(f'/api/requisitions/{req_id}/valider/', {}, format='json')
        self.assertEqual(valider.status_code, 200, valider.content)
        self.assertEqual(valider.json()['statut'], 'VALIDEE')
        self.assertFalse(valider.json()['est_modifiable'])

        # Plus de modification après validation
        blocked = self.client.post(
            f'/api/requisitions/{req_id}/lignes/',
            {'type_ligne': 'LIBRE', 'designation': 'X', 'quantite': '1'},
            format='json',
        )
        self.assertEqual(blocked.status_code, 400)

        doc = self.client.get(f'/api/requisitions/{req_id}/document/')
        self.assertEqual(doc.status_code, 200)
        payload = doc.json()
        self.assertEqual(payload['rapport'], 'requisition')
        self.assertEqual(payload['format'], 'json')
        self.assertEqual(payload['rendu'], 'frontend')
        self.assertIn('entreprise', payload)
        self.assertIn('lignes', payload)
        self.assertIn('resume', payload)
        self.assertIn('historique', payload)
        self.assertIn('sections_impression', payload)
        self.assertTrue(payload['instructions_frontend']['backend_ne_genere_pas_pdf'])
        self.assertEqual(len(payload['lignes']), 1)
        self.assertEqual(payload['lignes'][0]['designation'], 'Café Premium Edition Limitée')

        # Alias rétrocompatible : /pdf/ renvoie le même JSON (plus de binaire)
        alias = self.client.get(f'/api/requisitions/{req_id}/pdf/')
        self.assertEqual(alias.status_code, 200)
        self.assertEqual(alias.json()['rapport'], 'requisition')

    def test_list_filters(self):
        self.client.post('/api/requisitions/', {'titre': 'A'}, format='json')
        self.client.post(
            '/api/requisitions/',
            {'titre': 'B urgent', 'priorite': 'URGENTE'},
            format='json',
        )
        listing = self.client.get('/api/requisitions/?priorite=URGENTE&search=urgent')
        self.assertEqual(listing.status_code, 200)
        body = listing.json()
        results = body.get('results', body)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['priorite'], 'URGENTE')
