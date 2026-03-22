from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from stock.models import Entreprise
from users.models import Membership


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class AgentEntrepriseBrandingTests(APITestCase):
    """Branding entreprise (logo, slogan) lisible par un agent comme un admin."""

    def setUp(self):
        self.entreprise = Entreprise.objects.create(
            nom="Branding Co",
            secteur="commerce",
            pays="FR",
            adresse="1 rue Test",
            telephone="000",
            email="b@example.com",
            nif="NIF1",
            responsable="Resp",
            slogan="Notre slogan test",
            has_branches=False,
        )
        User = get_user_model()
        self.agent = User.objects.create_user(
            username="agent_brand",
            email="agent@example.com",
            password="secretpass123",
        )
        Membership.objects.create(
            user=self.agent,
            entreprise=self.entreprise,
            role="user",
            is_active=True,
        )

    def test_agent_get_entreprise_detail_returns_200_with_slogan(self):
        self.client.force_authenticate(user=self.agent)
        url = f"/api/entreprises/{self.entreprise.id}/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data.get("slogan"), "Notre slogan test")
        self.assertIn("logo", r.data)

    def test_login_returns_entreprise_with_slogan_for_agent(self):
        r = self.client.post(
            "/api/auth/",
            {"username": "agent_brand", "password": "secretpass123"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        ent = body.get("user", {}).get("entreprise") or {}
        self.assertEqual(ent.get("slogan"), "Notre slogan test")
        self.assertIn("logo", ent)
