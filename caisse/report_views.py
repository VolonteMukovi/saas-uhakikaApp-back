"""Endpoints alias JSON pour rapports caisse (/api/caisse/{id}/...)."""
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from caisse.models import TypeCaisse
from caisse.services.rapports_caisse import (
    build_mouvements_caisse,
    build_rapport_detaille_caisse,
    build_rapport_general_caisse,
    parse_rapport_filtres_from_request,
)
from stock.services.tenant_context import get_tenant_ids
from users.permissions import IsAdminOrUser


class _TenantCaisseMixin:
    permission_classes = [IsAdminOrUser]

    def get_caisse(self, pk: int) -> TypeCaisse:
        tenant_id, _ = get_tenant_ids(self.request)
        if not tenant_id:
            raise PermissionDenied(_('Contexte entreprise manquant.'))
        return get_object_or_404(TypeCaisse, pk=pk, entreprise_id=tenant_id)


class CaisseRapportGeneralAPIView(_TenantCaisseMixin, APIView):
    """GET /api/caisse/{id}/rapport-general/"""

    def get(self, request, pk):
        caisse = self.get_caisse(pk)
        filtres = parse_rapport_filtres_from_request(request)
        return Response(build_rapport_general_caisse(caisse, filtres))


class CaisseRapportDetailleAPIView(_TenantCaisseMixin, APIView):
    """GET /api/caisse/{id}/rapport-detaille/"""

    def get(self, request, pk):
        caisse = self.get_caisse(pk)
        filtres = parse_rapport_filtres_from_request(request)
        return Response(build_rapport_detaille_caisse(caisse, filtres))


class CaisseMouvementsAPIView(_TenantCaisseMixin, APIView):
    """GET /api/caisse/{id}/mouvements/"""

    def get(self, request, pk):
        caisse = self.get_caisse(pk)
        filtres = parse_rapport_filtres_from_request(request)
        return Response(build_mouvements_caisse(caisse, filtres))
