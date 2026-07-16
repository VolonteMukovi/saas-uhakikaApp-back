from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import (
    Article,
    ConditionnementArticle,
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
        self.cond_defaut = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Unité',
            multiplicateur_base=Decimal('1'),
            est_defaut=True,
        )
        self.cond_carton = ConditionnementArticle.objects.create(
            article=self.article,
            nom='Carton 24',
            multiplicateur_base=Decimal('24'),
            est_defaut=False,
        )
        entree = Entree.objects.create(libele='Appro test', entreprise=self.entreprise)
        LigneEntree.objects.create(
            article=self.article,
            entree=entree,
            conditionnement=self.cond_carton,
            quantite=Decimal('50'),
            quantite_restante=Decimal('0'),
            quantite_saisie=Decimal('2'),
            quantite_base=Decimal('24'),
            prix_unitaire=Decimal('0.75000'),
            prix_vente=Decimal('1.00000'),
            prix_achat_conditionnement=Decimal('18.00000'),
            prix_vente_conditionnement=Decimal('24.00000'),
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
        self.assertIsNotNone(ligne_cafe.get('conditionnement_id'))
        # Suggestion utilise le packing défaut ; prix peut venir du fallback unitaire.
        self.assertIsNotNone(ligne_cafe['prix_estime'])
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

    def _create_validated_requisition_with_carton(self, quantite='5'):
        create = self.client.post(
            '/api/requisitions/',
            {'titre': 'Cmd Coca', 'avec_suggestions': False},
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.content)
        req_id = create.json()['id']
        add = self.client.post(
            f'/api/requisitions/{req_id}/lignes/',
            {
                'type_ligne': 'ARTICLE',
                'article_id': self.article.article_id,
                'conditionnement_id': self.cond_carton.pk,
                'quantite': quantite,
            },
            format='json',
        )
        self.assertEqual(add.status_code, 200, add.content)
        ligne = add.json()['lignes'][0]
        self.assertEqual(ligne['conditionnement_id'], self.cond_carton.pk)
        self.assertEqual(ligne['conditionnement_nom'], 'Carton 24')
        self.assertEqual(ligne['prix_estime'], '18.00000')

        self.client.post(f'/api/requisitions/{req_id}/soumettre/', {}, format='json')
        valider = self.client.post(f'/api/requisitions/{req_id}/valider/', {}, format='json')
        self.assertEqual(valider.status_code, 200, valider.content)
        self.assertEqual(valider.json()['statut'], 'VALIDEE')
        self.assertIn('transformer_approvisionnement', valider.json()['actions_disponibles'])
        return req_id, ligne

    def test_transformation_preview_and_create(self):
        req_id, _ligne = self._create_validated_requisition_with_carton('5')

        preview = self.client.get(f'/api/requisitions/{req_id}/transformation-preview/')
        self.assertEqual(preview.status_code, 200, preview.content)
        prefill = preview.json()['prefill']
        self.assertEqual(prefill['source_requisition_id'], req_id)
        self.assertEqual(len(prefill['lignes']), 1)
        self.assertEqual(prefill['lignes'][0]['conditionnement_id'], self.cond_carton.pk)
        self.assertEqual(prefill['lignes'][0]['quantite_saisie'], '5.00000')
        self.assertEqual(prefill['lignes'][0]['prix_achat_conditionnement'], '18.00000')
        self.assertEqual(prefill['lignes'][0]['prix_vente_conditionnement'], '24.00000')

        stock_before = Stock.objects.get(article=self.article).Qte
        transform = self.client.post(
            f'/api/requisitions/{req_id}/transform-to-approvisionnement/',
            {'creer': True},
            format='json',
        )
        self.assertEqual(transform.status_code, 201, transform.content)
        body = transform.json()
        self.assertTrue(body['cree'])
        entree_id = body['entree_id']
        entree = Entree.objects.get(pk=entree_id)
        self.assertEqual(entree.source_requisition_id, req_id)
        self.assertTrue(entree.source_requisition_numero.startswith('REQ-'))

        ligne_entree = LigneEntree.objects.get(entree=entree)
        self.assertEqual(ligne_entree.conditionnement_id, self.cond_carton.pk)
        self.assertEqual(ligne_entree.quantite_saisie, Decimal('5.00000'))
        self.assertEqual(ligne_entree.quantite, Decimal('120.00000'))  # 5 * 24
        self.assertEqual(ligne_entree.prix_achat_conditionnement, Decimal('18.00000'))

        stock_after = Stock.objects.get(article=self.article).Qte
        self.assertEqual(stock_after, stock_before + Decimal('120.00000'))

        detail = self.client.get(f'/api/requisitions/{req_id}/')
        self.assertEqual(detail.status_code, 200)
        data = detail.json()
        self.assertEqual(data['transformation_status'], 'TRANSFORMEE')
        self.assertEqual(len(data['approvisionnements']), 1)
        self.assertEqual(data['approvisionnements'][0]['id'], entree_id)

        # Idempotence : second appel sans force → 400
        again = self.client.post(
            f'/api/requisitions/{req_id}/transform-to-approvisionnement/',
            {'creer': True},
            format='json',
        )
        self.assertEqual(again.status_code, 400)

        # force=true autorise une nouvelle Entree liée
        forced = self.client.post(
            f'/api/requisitions/{req_id}/transform-to-approvisionnement/',
            {'creer': True, 'force': True},
            format='json',
        )
        self.assertEqual(forced.status_code, 201, forced.content)
        detail2 = self.client.get(f'/api/requisitions/{req_id}/').json()
        self.assertEqual(len(detail2['approvisionnements']), 2)

    def test_transform_creer_false_then_post_entree_with_link(self):
        """Flux FE : preview / creer=false puis POST /api/entrees/ avec source_requisition_id."""
        req_id, _ = self._create_validated_requisition_with_carton('3')
        soft = self.client.post(
            f'/api/requisitions/{req_id}/transform-to-approvisionnement/',
            {'creer': False},
            format='json',
        )
        self.assertEqual(soft.status_code, 200, soft.content)
        self.assertFalse(soft.json()['cree'])
        prefill = soft.json()['prefill']
        self.assertEqual(Requisition.objects.get(pk=req_id).transformation_status, 'NON_TRANSFORMEE')

        ligne = prefill['lignes'][0]
        # Réalité fournisseur : 2 cartons seulement
        payload = {
            'libele': prefill['libele'],
            'description': prefill['description'],
            'source_requisition_id': req_id,
            'lignes': [
                {
                    'article_id': self.article.pk,
                    'conditionnement_id': ligne['conditionnement_id'],
                    'quantite_saisie': '2',
                    'prix_achat_conditionnement': ligne['prix_achat_conditionnement'],
                    'prix_vente_conditionnement': ligne['prix_vente_conditionnement'],
                    'seuil_alerte': '10',
                }
            ],
        }
        create_entree = self.client.post('/api/entrees/', payload, format='json')
        self.assertEqual(create_entree.status_code, 201, create_entree.content)
        entree_data = create_entree.json()
        self.assertEqual(entree_data.get('source_requisition'), req_id)
        self.assertTrue(entree_data.get('source_requisition_numero', '').startswith('REQ-'))

        req = Requisition.objects.get(pk=req_id)
        self.assertEqual(req.transformation_status, 'TRANSFORMEE')
        self.assertEqual(req.approvisionnements.count(), 1)
        le = LigneEntree.objects.get(entree_id=entree_data['id'])
        self.assertEqual(le.quantite, Decimal('48.00000'))  # 2 * 24
