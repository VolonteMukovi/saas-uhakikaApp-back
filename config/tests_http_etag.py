"""Tests alignement ETag GET (middleware) / If-Match (preconditions)."""
from django.test import RequestFactory, TestCase
from rest_framework.renderers import JSONRenderer

from config.http.etag import compute_resource_etag, compute_serialized_etag, compute_weak_etag
from stock.models import Entreprise
from stock.serializers import EntrepriseSerializer


class EtagAlignmentTests(TestCase):
    def test_serialized_etag_matches_json_renderer(self):
        ent = Entreprise.objects.create(
            nom='Test SA',
            secteur='Commerce',
            pays='CD',
            adresse='Goma',
            telephone='+243',
            email='test@example.com',
            nif='NIF1',
            responsable='Chef',
            config='{"version":1}',
        )
        data = EntrepriseSerializer(ent).data
        body = JSONRenderer().render(data)
        self.assertEqual(compute_serialized_etag(data), compute_weak_etag(body))

    def test_compute_resource_etag_uses_serializer(self):
        ent = Entreprise.objects.create(
            nom='Test SA 2',
            secteur='Commerce',
            pays='CD',
            adresse='Goma',
            telephone='+243',
            email='test2@example.com',
            nif='NIF2',
            responsable='Chef',
        )

        class FakeView:
            def get_serializer(self, instance):
                return EntrepriseSerializer(instance)

        etag = compute_resource_etag(FakeView(), ent)
        expected = compute_serialized_etag(EntrepriseSerializer(ent).data)
        self.assertEqual(etag, expected)
