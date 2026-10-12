"""Journal des suppressions de ventes : GET /api/logs-suppressions/."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import (
    Article,
    Entreprise,
    LigneSortie,
    LogSuppression,
    Sortie,
    SousTypeArticle,
    Stock,
    TypeArticle,
    Unite,
)
from users.models import Membership

D = Decimal


def _entreprise(suffix):
    return Entreprise.objects.create(
        nom=f'E-{suffix}', secteur='s', pays='CD', adresse='a', telephone='t',
        email=f'{suffix}@example.com', nif=f'n-{suffix}', responsable='resp',
    )


@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
class LogSuppressionTests(APITestCase):
    def setUp(self):
        self.entreprise = _entreprise('logs')
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin_logs', email='logs@example.com', password='secretpass123',
            first_name='Awa', last_name='Kabeya',
        )
        Membership.objects.create(user=self.admin, entreprise=self.entreprise, role='admin', is_active=True)
        self.client.force_authenticate(user=self.admin)

        unite = Unite.objects.create(libelle='pcs', entreprise=self.entreprise)
        type_art = TypeArticle.objects.create(libelle='Produit', entreprise=self.entreprise)
        sous = SousTypeArticle.objects.create(libelle='Divers', type_article=type_art, entreprise=self.entreprise)
        self.article = Article.objects.create(
            nom_scientifique='Savon', nom_commercial='Savon', sous_type_article=sous,
            unite=unite, entreprise=self.entreprise,
        )
        Stock.objects.create(article=self.article, Qte=D('10'), seuilAlert=D('0'))

    def _sortie(self, quantite='2'):
        # Prix 0 : pas de mouvement de caisse inverse requis à la suppression.
        sortie = Sortie.objects.create(motif='Vente', statut='PAYEE', entreprise=self.entreprise)
        ligne = LigneSortie.objects.create(
            sortie=sortie, article=self.article, quantite=D(quantite), prix_unitaire=D('0'),
        )
        return sortie, ligne

    def test_suppression_sortie_journalisee(self):
        sortie, _ = self._sortie('3')
        resp = self.client.delete(f'/api/sorties/{sortie.pk}/')
        self.assertEqual(resp.status_code, 204, resp.content)

        log = LogSuppression.objects.get()
        self.assertEqual(log.sortie_numero, sortie.pk)
        self.assertEqual(log.article_id, self.article.pk)
        self.assertEqual(log.quantite, D('3'))
        self.assertEqual(log.motif, LogSuppression.MOTIF_SORTIE)
        self.assertEqual(log.utilisateur_nom, 'Awa Kabeya')

    def test_retrait_impossible_ne_journalise_rien(self):
        # Les lignes de vente sont en lecture seule : un article se retire en modifiant la vente.
        autre = Article.objects.create(
            nom_scientifique='Brosse', nom_commercial='Brosse', sous_type_article=self.article.sous_type_article,
            unite=self.article.unite, entreprise=self.entreprise,
        )
        Stock.objects.create(article=autre, Qte=D('5'), seuilAlert=D('0'))
        sortie, _ligne = self._sortie('2')
        LigneSortie.objects.create(sortie=sortie, article=autre, quantite=D('1'), prix_unitaire=D('0'))
        resp = self.client.patch(
            f'/api/sorties/{sortie.pk}/',
            {'lignes': [{'article_id': autre.pk, 'quantite': '1', 'prix_unitaire': '0'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, 400, resp.content)  # stock FIFO absent dans ce jeu de test
        self.assertFalse(LogSuppression.objects.exists())  # tout ou rien : rien n'est journalisé

    def test_suppression_ligne_journalisee_avec_stock(self):
        from stock.models import Devise, Entree, LigneEntree

        devise = Devise.objects.create(sigle='USD', nom='Dollar', symbole='$', est_principal=True, entreprise=self.entreprise)
        autre = Article.objects.create(
            nom_scientifique='Brosse', nom_commercial='Brosse', sous_type_article=self.article.sous_type_article,
            unite=self.article.unite, entreprise=self.entreprise,
        )
        entree = Entree.objects.create(libele='Appro', entreprise=self.entreprise)
        for article in (self.article, autre):
            LigneEntree.objects.create(
                article=article, entree=entree, quantite=D('10'), prix_unitaire=D('0'), prix_vente=D('1'),
                devise=devise,
            )
        Stock.objects.update_or_create(article=autre, defaults={'Qte': D('10'), 'seuilAlert': D('0')})
        Stock.objects.filter(article=self.article).update(Qte=D('10'))
        lignes = [
            {'article_id': self.article.pk, 'quantite': '2', 'prix_unitaire': '0', 'devise_id': devise.pk,
             'motif_prix_exception': 'Échantillon offert'},
            {'article_id': autre.pk, 'quantite': '1', 'prix_unitaire': '0', 'devise_id': devise.pk,
             'motif_prix_exception': 'Échantillon offert'},
        ]
        created = self.client.post('/api/sorties/', {'motif': 'Cadeau client', 'lignes': lignes}, format='json')
        self.assertEqual(created.status_code, 201, created.content)
        sortie_id = created.json()['id']
        resp = self.client.patch(f'/api/sorties/{sortie_id}/', {'lignes': lignes[1:]}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        log = LogSuppression.objects.get()
        self.assertEqual(log.motif, LogSuppression.MOTIF_LIGNE)
        self.assertEqual(log.sortie_numero, sortie_id)
        self.assertEqual(log.article_id, self.article.pk)
        self.assertEqual(Stock.objects.get(article=self.article).Qte, D('10'))

    def test_liste_format_front_et_isolation_tenant(self):
        sortie, _ = self._sortie()
        self.client.delete(f'/api/sorties/{sortie.pk}/')
        autre = _entreprise('autre')
        LogSuppression.objects.create(
            entreprise=autre, article_nom='Secret', sortie_numero=999, utilisateur_nom='X',
        )

        resp = self.client.get('/api/logs-suppressions/', {'page': 1, 'page_size': 25})
        self.assertEqual(resp.status_code, 200, resp.content)
        rows = resp.json()['results']
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['article_nom'], 'Savon')
        self.assertEqual(row['entreprise_nom'], self.entreprise.nom)
        self.assertRegex(row['date_suppression_formatee'], r'^\d{2}/\d{2}/\d{4} à \d{2}:\d{2}$')
        self.assertTrue(row['temps_ecoule'])

    def test_recherche_et_tri(self):
        for _i in range(2):
            sortie, _ = self._sortie()
            self.client.delete(f'/api/sorties/{sortie.pk}/')
        numero = LogSuppression.objects.order_by('id').first().sortie_numero

        resp = self.client.get('/api/logs-suppressions/', {'search': f'#{numero}'})
        self.assertEqual([r['sortie_numero'] for r in resp.json()['results']], [numero])

        resp = self.client.get('/api/logs-suppressions/', {'ordering': 'sortie_numero'})
        numeros = [r['sortie_numero'] for r in resp.json()['results']]
        self.assertEqual(numeros, sorted(numeros))

    def test_lecture_seule(self):
        resp = self.client.post('/api/logs-suppressions/', {}, format='json')
        self.assertEqual(resp.status_code, 405)
