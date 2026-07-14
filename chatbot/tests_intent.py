"""Tests unitaires sur la classification d'intentions (sans API)."""
from django.test import SimpleTestCase

from chatbot.services.intent_classifier import classify_intent, normalize_user_message


class IntentClassifierDeepTests(SimpleTestCase):
    def test_normalize_typos(self):
        self.assertIn('approvisionnements', normalize_user_message('approvisionement'))
        self.assertIn('qui ont des', normalize_user_message('qui au des dettes'))
        self.assertIn('quels sont', normalize_user_message('quel sont'))

    def test_top4_defaults_all_time(self):
        r = classify_intent('quel sont les 4 premiers articles les plus vendus ?')
        self.assertEqual(r.intent, 'top_selling_products')
        self.assertEqual(r.top_n, 4)
        self.assertEqual(r.period, 'all_time')

    def test_followup_non_en_general(self):
        r = classify_intent(
            'non en general',
            conversation_context={
                'last_intent': 'top_selling_products',
                'last_entities': {'limit': 4, 'period': 'today'},
            },
        )
        self.assertEqual(r.intent, 'top_selling_products')
        self.assertEqual(r.period, 'all_time')
        self.assertEqual(r.top_n, 4)
        self.assertTrue(r.follow_up)
        self.assertIsNotNone(r.preface)

    def test_approvisionnements_today(self):
        r = classify_intent("quel sont mes approvisionnements d'aujourd'hui ?")
        self.assertEqual(r.intent, 'approvisionnement_today')

    def test_dettes_en_cours_not_client(self):
        r = classify_intent('Combien de dettes en cours ?')
        self.assertEqual(r.intent, 'debt_summary')
        self.assertIsNone(r.client_hint)

    def test_clients_with_debts_typo(self):
        r = classify_intent('donne moi quelque client qui au des dettes')
        self.assertEqual(r.intent, 'clients_with_debts')
        self.assertIsNone(r.client_hint)

    def test_requisition_stock_status(self):
        r = classify_intent(
            'fais-moi une réquisition en fonction des statuts de stock des produits'
        )
        self.assertEqual(r.intent, 'stock_requisition_pdf')

    def test_facture_blessing_ignores_old_entity(self):
        r = classify_intent(
            'donne moi la facture PDF pour Blessing ou ce qu’il a acheté',
            conversation_context={
                'last_intent': 'clients_with_debts',
                'last_entities': {'client': 'qui au des dettes'},
            },
        )
        self.assertEqual(r.intent, 'client_invoice_pdf')
        self.assertIsNotNone(r.client_hint)
        self.assertIn('blessing', r.client_hint.lower())

    def test_je_veux_qu_on_parle(self):
        r = classify_intent('je veux qu’on parle')
        self.assertEqual(r.intent, 'petite_conversation')

    def test_entreprise_context(self):
        r = classify_intent('je travaille sur quelle entreprise ?')
        self.assertEqual(r.intent, 'contexte_utilisateur')

    def test_merci_prefix_does_not_hide_requisition(self):
        r = classify_intent(
            'merci , quel sont les produits que je peux approvisionner , donc la recquisition'
        )
        self.assertEqual(r.intent, 'stock_requisition_pdf')
        self.assertNotEqual(r.intent, 'remerciement')

    def test_bonjour_prefix_with_stock_question(self):
        r = classify_intent('bonjour, j ai combien d articles en rupture ?')
        self.assertEqual(r.intent, 'stock_rupture_list')

    def test_pure_merci_still_remerciement(self):
        r = classify_intent('merci beaucoup')
        self.assertEqual(r.intent, 'remerciement')
