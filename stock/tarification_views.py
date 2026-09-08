"""API lecture seule — catalogue de tarification (dernier prix de vente)."""
from __future__ import annotations

from django.db.models import Exists, OuterRef
from rest_framework import status, viewsets
from rest_framework.response import Response

from stock.models import Article, LigneEntree
from stock.permissions import IsAdminOrUser as StockIsAdminOrUser
from stock.services import tarification as tarification_service
from stock.services.tenant_context import get_tenant_ids


class TarificationViewSet(viewsets.ViewSet):
    """
    Liste tous les articles de l'entreprise avec leur dernier prix de vente.

    Articles jamais approvisionnés inclus : ``prix_vente_* = null``,
    ``prix_manquant = true``, ``prix_vente_affiche = "....."``.
    """

    permission_classes = [StockIsAdminOrUser]

    def list(self, request, *args, **kwargs):
        tenant_id, branch_id = get_tenant_ids(request)
        if not tenant_id:
            return Response(
                {'detail': 'Contexte entreprise manquant.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = request.query_params
        search = params.get('search') or params.get('q')
        type_id = params.get('type_article') or params.get('type_article_id')
        sous_type_id = params.get('sous_type_article') or params.get('sous_type_article_id')
        succursale = params.get('succursale') or params.get('succursale_id')
        if succursale in (None, ''):
            succursale_id = branch_id
        else:
            try:
                succursale_id = int(succursale)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'succursale_id invalide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        prix_flag = params.get('prix_manquant')
        prix_manquant = None
        if prix_flag is not None and str(prix_flag).strip() != '':
            prix_manquant = str(prix_flag).lower() in ('1', 'true', 'yes', 'oui')

        try:
            type_article_id = int(type_id) if type_id not in (None, '') else None
            sous_type_article_id = int(sous_type_id) if sous_type_id not in (None, '') else None
        except (TypeError, ValueError):
            return Response(
                {'detail': 'type_article_id / sous_type_article_id invalide.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = tarification_service.build_queryset_tarification(
            entreprise_id=tenant_id,
            succursale_id=succursale_id,
            search=search,
            type_article_id=type_article_id,
            sous_type_article_id=sous_type_article_id,
        )

        has_entree = LigneEntree.objects.filter(article_id=OuterRef('pk'))
        if prix_manquant is True:
            qs = qs.annotate(_has_entree=Exists(has_entree)).filter(_has_entree=False)
        elif prix_manquant is False:
            qs = qs.annotate(_has_entree=Exists(has_entree)).filter(_has_entree=True)

        page = self.paginate_queryset(qs)
        envelope = {
            'rapport': 'tarification',
            'instructions_frontend': {
                'afficher_placeholder_prix': tarification_service.PRIX_PLACEHOLDER,
                'prix_null_si_jamais_approvisionne': True,
                'conditionnements_inclus': True,
            },
        }
        if page is not None:
            results, resume_page = tarification_service.build_tarification_page(list(page))
            response = self.get_paginated_response(results)
            data = response.data
            if isinstance(data, dict):
                data.update(envelope)
                data['resume'] = resume_page
            return Response(data)

        results, resume = tarification_service.build_tarification_page(list(qs))
        return Response({
            **envelope,
            'count': len(results),
            'results': results,
            'resume': resume,
        })

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            from django.conf import settings
            from django.utils.module_loading import import_string
            from rest_framework.pagination import PageNumberPagination

            paginator_path = getattr(settings, 'REST_FRAMEWORK', {}).get('DEFAULT_PAGINATION_CLASS')
            if paginator_path:
                self._paginator = import_string(paginator_path)()
            else:
                self._paginator = PageNumberPagination()
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)
