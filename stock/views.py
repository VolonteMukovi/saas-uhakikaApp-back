from rest_framework.response import Response
from django.db.models import Sum

# Liste des bÃ©nÃ©fices par vente

from django.shortcuts import render
from rest_framework import viewsets, status, serializers, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import (
    Entreprise,
    Succursale,
    Devise,
    TauxChange,
    TypeArticle,
    SousTypeArticle,
    Unite,
    Article,
    ConditionnementArticle,
    CodeBarresArticle,
    Entree,
    LigneEntree,
    PrixConditionnementEntree,
    Stock,
    Sortie,
    LigneSortie,
    LigneSortieLot,
    BeneficeLot,
    Client,
    ClientEntreprise,
    DetteClient,
)
from caisse.models import MouvementCaisse
from caisse.services.caisse import creer_mouvement_caisse, mouvement_moyen_affiche
from caisse.services.caisse_defaut import MSG_CAISSE_REQUISE
from caisse.services.operation_helpers import extract_type_caisse_id
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids
from stock.services.client_lifecycle import (
    build_client_balance,
    build_client_dashboard,
    build_client_movements,
    build_client_sales,
    build_client_statistics,
    parse_period_from_request,
)
from stock.services.currency import (
    CurrencyError,
    build_conversion_snapshot,
    get_exchange_rate,
    get_principal_devise as get_principal_devise_for_entreprise,
)
from django.db import transaction, models
from django.db.models import Prefetch, Q, Sum
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.translation import gettext as _, pgettext
from django.contrib.admin.models import LogEntry, ADDITION, DELETION, CHANGE
from .serializers import *
from users.permissions import IsSuperAdmin, IsAdmin, IsSuperAdminOrAdmin, IsSuperAdminOrReadOnlyAdmin, IsOwnerOrSuperAdmin, IsAdminOrUser
from users.serializers import UserSerializer
from stock.permissions import EntreprisePermission, IsAdminOrUser as StockIsAdminOrUser
from users.authentication import JWTAuthenticationWithContext
from order.authentication import ClientJWTAuthentication
from order.permissions import IsClientAuthenticated
from django.conf import settings


class BusinessPermissionMixin:
    """AccÃ¨s rÃ©servÃ© aux Admin et User (Agent). SuperAdmin n'a pas accÃ¨s aux donnÃ©es mÃ©tier."""
    permission_classes = [StockIsAdminOrUser]
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
import csv
import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.graphics.barcode import code128
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import qrcode
from datetime import datetime
from rest_framework.decorators import action, api_view, permission_classes
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Configuration du logger pour tracer les suppressions automatiques d'articles
logger = logging.getLogger(__name__)


def _parse_decimal_quantity(raw_value):
    """Parse une quantitÃ© en acceptant virgule ou point."""
    if isinstance(raw_value, Decimal):
        value = raw_value
    else:
        text = str(raw_value).strip().replace(",", ".")
        value = Decimal(text)
    if value <= 0:
        raise serializers.ValidationError({'quantite': 'La quantitÃ© doit Ãªtre supÃ©rieure Ã  0.'})
    return value


class EnterpriseFilterMixin:
    """Mixin pour filtrer automatiquement par entreprise selon le rÃ´le de l'utilisateur"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset


class TenantFilterMixin:
    """
    Mixin multi-tenant : filtre le queryset par entreprise (et succursale si connue).
    - Si le modÃ¨le a entreprise_id : filtre par request.tenant_id ; si branch_id est dÃ©fini (JWT ou dÃ©faut membership), filtre aussi par succursale.
    - Agent sans succursale : filtre uniquement par entreprise (succursale_id laissÃ©e libre cÃ´tÃ© donnÃ©es).
    - Si tenant_lookup est dÃ©fini (ex. 'entree__entreprise_id') : filtre par ce lookup.
    """
    tenant_lookup = None  # ex. 'entree__entreprise_id' pour LigneEntree

    def get_queryset(self):
        queryset = super().get_queryset()
        # Support portail client (JWT dÃ©diÃ©) : `request.user` est vide, mais
        # `request.client` / `request.client_membership` sont prÃ©sents.
        if not self.request.user.is_authenticated and getattr(self.request, "client", None) is None:
            return queryset.none() if (self.tenant_lookup or hasattr(queryset.model, 'entreprise_id')) else queryset

        if getattr(self.request, "client", None) is not None:
            m = getattr(self.request, "client_membership", None)
            tenant_id = getattr(m, "entreprise_id", None)
            branch_id = getattr(m, "succursale_id", None)
        else:
            tenant_id, branch_id = _get_tenant_ids(self.request)
        if tenant_id is None:
            return queryset.none() if (self.tenant_lookup or hasattr(queryset.model, 'entreprise_id')) else queryset
        # Agent sans succursale dans le JWT : filtre uniquement par entreprise (pas par succursale).
        if self.tenant_lookup:
            return queryset.filter(**{self.tenant_lookup: tenant_id})
        if not hasattr(queryset.model, 'entreprise_id'):
            return queryset
        queryset = queryset.filter(entreprise_id=tenant_id)
        if hasattr(queryset.model, 'succursale_id') and branch_id is not None:
            queryset = queryset.filter(succursale_id=branch_id)
        return queryset

    def get_tenant_ids(self):
        return _get_tenant_ids(self.request)

    def perform_create(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        model = getattr(serializer.Meta, 'model', None)
        if model and hasattr(model, 'entreprise_id') and tenant_id is not None:
            serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)
        else:
            serializer.save()


def _format_amount(amount: Decimal, devise_obj, entreprise=None):
    """Return amount formatted with 5 decimals and the currency symbol.
    devise_obj may be None; fallback to principal devise.
    """
    try:
        if devise_obj and getattr(devise_obj, 'symbole', None):
            sym = devise_obj.symbole
        else:
            pr = Devise.objects.filter(est_principal=True).first()
            sym = pr.symbole if pr and getattr(pr, 'symbole', None) else ''
    except Exception:
        sym = ''
    try:
        amt = Decimal(str(amount)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        return f"{amt:.5f} {sym}" if sym else f"{amt:.5f}"
    except Exception:
        return str(amount)


def _article_display_name(article):
    """Retourne un nom lisible pour un article (commercial si prÃ©sent, sinon scientifique)."""
    if not article:
        return ''
    nom_comm = getattr(article, 'nom_commercial', None)
    nom_sci = getattr(article, 'nom_scientifique', None)
    if nom_comm:
        return f"{nom_comm} ({nom_sci})" if nom_sci else nom_comm
    if nom_sci:
        return nom_sci
    # fallback to article_id or repr
    return getattr(article, 'article_id', str(article))


def _get_principal_devise(entreprise_id=None):
    if entreprise_id:
        return get_principal_devise_for_entreprise(entreprise_id)
    return Devise.objects.filter(est_principal=True).first()


def _get_entreprise_exchange_rates(entreprise):
    """Retourne la liste brute des taux de change stockes dans la config entreprise."""
    if not entreprise:
        return []
    try:
        config_data = entreprise.get_config_dict()
    except Exception:
        return []
    integrations = config_data.get('integrations') or {}
    rates = integrations.get('exchange_rates') or []
    return rates if isinstance(rates, list) else []


def _exchange_rate_sort_key(entry):
    return (
        str(entry.get('effective_at') or ''),
        str(entry.get('created_at') or ''),
        int(entry.get('id') or 0),
    )


def _get_latest_exchange_rate_entry(entreprise, source_dev_id, target_dev_id):
    latest = None
    for entry in _get_entreprise_exchange_rates(entreprise):
        if entry.get('source_devise_id') != source_dev_id:
            continue
        if entry.get('target_devise_id') != target_dev_id:
            continue
        if entry.get('is_active', True) is False:
            continue
        if latest is None or _exchange_rate_sort_key(entry) > _exchange_rate_sort_key(latest):
            latest = entry
    return latest


def _persist_exchange_rates(entreprise, rates, user_id=None):
    entreprise.merge_config(
        {'integrations': {'exchange_rates': rates}},
        user_id=user_id,
    )
    entreprise.save(update_fields=['config'])


def _serialize_exchange_rate_entry(entry, entreprise):
    devise_ids = {
        entry.get('source_devise_id'),
        entry.get('target_devise_id'),
    }
    devises = {
        d.id: d
        for d in Devise.objects.filter(
            entreprise=entreprise,
            id__in=[did for did in devise_ids if did],
        )
    }
    source = devises.get(entry.get('source_devise_id'))
    target = devises.get(entry.get('target_devise_id'))
    return {
        'id': entry.get('id'),
        'source_devise_id': entry.get('source_devise_id'),
        'target_devise_id': entry.get('target_devise_id'),
        'source_devise': DeviseSerializer(source).data if source else None,
        'target_devise': DeviseSerializer(target).data if target else None,
        'taux': str(entry.get('rate')),
        'date_application': entry.get('effective_at'),
        'is_active': bool(entry.get('is_active', True)),
        'created_at': entry.get('created_at'),
        'created_by_user_id': entry.get('created_by_user_id'),
    }


def _extract_exchange_rate_payload(data):
    source_id = (
        data.get('source_devise_id')
        or data.get('source_devise')
        or data.get('devise_source_id')
        or data.get('devise_source')
    )
    target_id = (
        data.get('target_devise_id')
        or data.get('target_devise')
        or data.get('devise_cible_id')
        or data.get('devise_cible')
    )
    rate_raw = data.get('taux')
    if rate_raw in (None, ''):
        rate_raw = data.get('rate')
    if rate_raw in (None, ''):
        rate_raw = data.get('taux_change')
    effective_at = data.get('date_application') or data.get('effective_at')
    is_active = data.get('is_active', True)
    return source_id, target_id, rate_raw, effective_at, is_active


def _get_latest_rate(source_dev: Devise, target_dev: Devise, entreprise_id=None):
    if not source_dev or not target_dev:
        return None
    try:
        return get_exchange_rate(
            source_dev,
            target_dev,
            entreprise_id=entreprise_id or source_dev.entreprise_id,
        )
    except CurrencyError:
        return None


def _convert_amount(amount: Decimal, source_dev: Devise, target_dev: Devise, entreprise):
    """Attempt conversion; return Decimal or None when rate missing."""
    if amount is None:
        return None
    if source_dev is None and target_dev is None:
        return amount
    # if source missing assume target (no conversion)
    if source_dev is None or target_dev is None:
        return amount
    rate = _get_latest_rate(
        source_dev,
        target_dev,
        entreprise_id=getattr(entreprise, 'id', None) if entreprise else getattr(source_dev, 'entreprise_id', None),
    )
    if rate is None:
        return None
    try:
        return (Decimal(amount) * rate).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    except Exception:
        return None




class RapportViewSet(viewsets.ViewSet):
    def get_permissions(self):
        return [StockIsAdminOrUser()]

    # NOTE: La fonction fiche_stock_article_pdf a Ã©tÃ© dÃ©placÃ©e vers rapports/views.py
    # pour une meilleure organisation. Utilisez maintenant:
    # GET /api/rapports/{article_id}/fiche-stock/
   
    # NOTE: Les actions facture_pos_pdf et bons POS ont Ã©tÃ© dÃ©placÃ©es vers
    # SortieViewSet et EntreeViewSet pour Ã©viter toute ambiguÃ¯tÃ© de routes.

    @action(detail=False, methods=['get'], url_path='journal')
    def journal(self, request):
        """
        Journal complet des opÃ©rations (JSON pour le frontend).

        Inclut : approvisionnements, ventes, mouvements de caisse, paiements de dettes.
        Filtres : month (1-12), year (ex: 2026). Par dÃ©faut = mois et annÃ©e en cours.
        Ou date_min / date_max (YYYY-MM-DD) pour une plage personnalisÃ©e.
        Pagination : page, page_size (dÃ©faut). complet=true pour toute la liste.

        GET /api/rapports/journal/
        GET /api/rapports/journal/?month=6&year=2026
        GET /api/rapports/journal/?date_min=2026-01-01&date_max=2026-01-31
        """
        from rapports.utils.journal_data import build_journal_report_data
        from rapports.utils.report_envelope import wrap_report_response

        user = request.user
        principal = _get_principal_devise()
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            return Response({'error': 'Contexte entreprise manquant.'}, status=400)

        body = build_journal_report_data(
            request=request,
            user=user,
            tenant_id=tenant_id,
            branch_id=branch_id,
            principal_devise=principal,
        )

        events = body.get('details') or body.get('operations') or []
        complet = request.query_params.get('complet', '').lower() in ('true', '1', 'yes', 'oui')
        if not complet and events:
            try:
                page = int(request.query_params.get('page', 1))
            except (TypeError, ValueError):
                page = 1
            page = max(1, page)
            try:
                from config.pagination import StandardResultsSetPagination
                page_size = int(
                    request.query_params.get(
                        'page_size', StandardResultsSetPagination.page_size
                    )
                )
                max_ps = StandardResultsSetPagination.max_page_size
            except (TypeError, ValueError):
                from config.pagination import StandardResultsSetPagination
                page_size = StandardResultsSetPagination.page_size
                max_ps = StandardResultsSetPagination.max_page_size
            page_size = max(1, min(page_size, max_ps))
            count = len(events)
            import math
            total_pages = max(1, math.ceil(count / page_size)) if count else 1
            if page > total_pages and count:
                page = total_pages
            start = (page - 1) * page_size
            page_events = events[start : start + page_size]
            body['details'] = page_events
            body['operations'] = page_events
            body['pagination'] = {
                'page': page,
                'page_size': page_size,
                'count': count,
                'total_pages': total_pages,
                'has_next': start + page_size < count,
                'has_previous': page > 1,
            }
            body.setdefault('filtres', {})['complet'] = False
        else:
            body.setdefault('filtres', {})['complet'] = True

        wrapped = wrap_report_response(
            rapport='journal',
            titre=body.get('titre', 'journal'),
            request=request,
            user=user,
            data=body,
            eid=tenant_id,
            branch_id=branch_id,
        )
        return Response(wrapped)

    # Les actions de bons POS supprimÃ©es ici.

@swagger_auto_schema(tags=['Entreprises'])
class EntrepriseViewSet(viewsets.ModelViewSet):
    """
    Gestion des entreprises.
    - SuperAdmin : Read (list, retrieve) + Delete uniquement. Pas de Create ni Update.
    - Admin : CRUD sur sa propre entreprise.
    - User (Agent) : lecture seule (retrieve/list) sur son entreprise (branding : logo, slogan, etc.).
    """
    queryset = Entreprise.objects.all()
    serializer_class = EntrepriseSerializer
    permission_classes = [EntreprisePermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Entreprise.objects.none()
        if user.is_superadmin():
            return Entreprise.objects.all().order_by('-id')
        if user.is_admin(self.request) or user.is_agent(self.request):
            eid = getattr(self.request, 'tenant_id', None) or user.get_entreprise_id(self.request)
            if eid:
                return Entreprise.objects.filter(id=eid).order_by('-id')
            return Entreprise.objects.none()
        # Utilisateur sans entreprise : ne voit aucune entreprise tant qu'il n'en a pas crÃ©Ã©e
        return Entreprise.objects.none()

    def create(self, request, *args, **kwargs):
        """Crée ou met à jour l'entreprise provisoire — jamais de doublon."""
        from rest_framework.exceptions import ValidationError
        from inscription.services.entreprise_saas import (
            entreprise_est_configuree,
            evaluer_et_marquer_configuration,
        )
        from users.services.membership_context import get_primary_membership

        user = request.user
        if user.is_superadmin():
            return super().create(request, *args, **kwargs)

        membership = get_primary_membership(user, request)
        if membership:
            ent = membership.entreprise
            if entreprise_est_configuree(ent) and ent.configuration_complete:
                raise ValidationError({
                    'detail': _(
                        'Votre entreprise est déjà configurée. '
                        'Utilisez la modification pour mettre à jour vos informations.'
                    ),
                    'code': 'entreprise_deja_configuree',
                    'entreprise_id': ent.id,
                })
            serializer = self.get_serializer(ent, data=request.data)
            serializer.is_valid(raise_exception=True)
            entreprise = serializer.save()
            evaluer_et_marquer_configuration(entreprise)
            data = dict(serializer.data)
            data['mis_a_jour'] = True
            data['code'] = 'entreprise_mise_a_jour'
            return Response(data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        from users.models import Membership

        user = self.request.user
        if user.is_superadmin():
            raise PermissionDenied(_("Le super administrateur ne peut pas crÃ©er d'entreprise. Utilisez un compte Admin."))

        entreprise = serializer.save()
        Membership.objects.get_or_create(
            user=user,
            entreprise=entreprise,
            defaults={'role': 'admin', 'is_active': True},
        )

    def perform_update(self, serializer):
        user = self.request.user
        entreprise = self.get_object()
        if user.is_superadmin():
            raise PermissionDenied(_("Le super administrateur ne peut pas modifier une entreprise."))
        if user.is_admin(self.request):
            # Admin : autorise uniquement si l'utilisateur a une membership active pour cette entreprise
            is_member = (
                user.memberships.filter(entreprise=entreprise, is_active=True).exists()
            )
            if not is_member:
                raise PermissionDenied(_("Vous ne pouvez modifier que votre propre entreprise."))
            ent = serializer.save()
            from inscription.services.entreprise_saas import evaluer_et_marquer_configuration
            evaluer_et_marquer_configuration(ent)

    def perform_destroy(self, instance):
        from users.models import Membership
        user = self.request.user
        if user.is_superadmin():
            instance.delete()
        elif user.is_admin(self.request):
            # Admin : autorise uniquement si l'utilisateur a une membership active pour cette entreprise
            is_member = (
                user.memberships.filter(entreprise=instance, is_active=True).exists()
            )
            if not is_member:
                raise PermissionDenied(_("Vous ne pouvez supprimer que votre propre entreprise."))
            Membership.objects.filter(user=user, entreprise=instance).delete()
            instance.delete()

    @swagger_auto_schema(
        operation_summary="Mon entreprise (contexte JWT / admin ou agent)",
        operation_description="Retourne l'entreprise du contexte courant (admin ou agent) ; message si superadmin.",
        responses={200: openapi.Response('DÃ©tail entreprise ou message'), 400: 'Aucune entreprise'},
    )
    @action(detail=False, methods=['get'])
    def my_entreprise(self, request):
        """RÃ©cupÃ©rer l'entreprise de l'utilisateur connectÃ© (admin ou agent, lecture)."""
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        ent = Entreprise.objects.filter(id=eid).first() if eid else request.user.get_entreprise(request)
        if (request.user.is_admin(request) or request.user.is_agent(request)) and ent:
            serializer = self.get_serializer(ent)
            return Response(serializer.data)
        if request.user.is_superadmin():
            return Response({'message': _("Superadmin n'appartient Ã  aucune entreprise")})
        return Response({'error': _("Aucune entreprise associÃ©e")}, status=400)

    @swagger_auto_schema(
        operation_summary="Utilisateurs d'une entreprise",
        operation_description="Liste paginÃ©e des utilisateurs ayant un membership actif sur cette entreprise (`pk` = id entreprise).",
        responses={200: openapi.Response('Liste UserSerializer ou rÃ©ponse paginÃ©e')},
    )
    @action(detail=True, methods=['get'])
    def users(self, request, pk=None):
        """Lister tous les utilisateurs d'une entreprise (paginated, via Membership)."""
        entreprise = self.get_object()
        users = get_user_model().objects.filter(memberships__entreprise=entreprise, memberships__is_active=True).distinct().order_by('-date_joined', '-id')
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = UserSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        user_serializer = UserSerializer(users, many=True)
        return Response(user_serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Statistiques de l'entreprise"""
        entreprise = self.get_object()
        stats = {
            'nombre_utilisateurs': get_user_model().objects.filter(memberships__entreprise=entreprise, memberships__is_active=True).distinct().count(),
            'nombre_articles': Article.objects.filter(entreprise=entreprise).count(),
            'nombre_sorties': Sortie.objects.filter(entreprise=entreprise).count(),
            'nombre_entrees': Entree.objects.filter(entreprise=entreprise).count(),
            'valeur_stock': Stock.objects.filter(article__entreprise=entreprise).aggregate(
                total=Sum('Qte')
            )['total'] or 0
        }
        return Response(stats)

    def _assert_entreprise_config_read(self, request, entreprise):
        user = request.user
        if user.is_superadmin():
            return
        eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
        if eid != entreprise.id:
            raise PermissionDenied(_('AccÃ¨s refusÃ© Ã  cette entreprise.'))
        if not (user.is_admin(request) or user.is_agent(request)):
            raise PermissionDenied(_('AccÃ¨s refusÃ© Ã  cette entreprise.'))

    def _assert_entreprise_config_write(self, request, entreprise):
        user = request.user
        if user.is_superadmin():
            raise PermissionDenied(_("Le super administrateur ne peut pas modifier la configuration."))
        if not user.is_admin(request):
            raise PermissionDenied(_('AccÃ¨s rÃ©servÃ© aux administrateurs de l\'entreprise.'))
        eid = getattr(request, 'tenant_id', None) or user.get_entreprise_id(request)
        if eid != entreprise.id:
            raise PermissionDenied(_('AccÃ¨s refusÃ© Ã  cette entreprise.'))

    @swagger_auto_schema(
        operation_summary='Configuration JSON entreprise',
        methods=['get'],
        responses={200: 'Objet EntrepriseConfig'},
    )
    @swagger_auto_schema(
        operation_summary='Merge partiel configuration entreprise',
        methods=['patch'],
        responses={200: 'Objet EntrepriseConfig'},
    )
    @action(detail=True, methods=['get', 'patch'], url_path='config')
    def entreprise_config(self, request, pk=None):
        """
        GET /api/entreprises/{id}/config/ â€” config parsÃ©e (dÃ©faut si vide).
        PATCH â€” merge par section (admin entreprise).
        """
        entreprise = self.get_object()
        if request.method == 'GET':
            self._assert_entreprise_config_read(request, entreprise)
            return Response(entreprise.get_config_dict())
        self._assert_entreprise_config_write(request, entreprise)
        if not isinstance(request.data, dict):
            raise serializers.ValidationError({'detail': _('Le corps de la requÃªte doit Ãªtre un objet JSON.')})
        merged = entreprise.merge_config(request.data, user_id=request.user.pk)
        entreprise.save(update_fields=['config'])
        response = Response(merged)
        from config.http.etag import compute_resource_etag
        entreprise.refresh_from_db()
        response['ETag'] = compute_resource_etag(self, entreprise, request)
        return response

    @action(
        detail=True,
        methods=['put', 'delete'],
        url_path=r'config/document-appearance/(?P<report_type>[^/.]+)',
    )
    def document_appearance_config(self, request, pk=None, report_type=None):
        """
        PUT â€” remplace la config d'un type de rapport.
        DELETE â€” supprime la clÃ© (retour aux dÃ©fauts frontend).
        """
        from stock.services.entreprise_config import (
            VALID_REPORT_TYPES,
            remove_document_appearance,
            replace_document_appearance,
        )

        entreprise = self.get_object()
        if report_type not in VALID_REPORT_TYPES:
            raise serializers.ValidationError({
                'detail': _('Type de rapport inconnu : %(type)s') % {'type': report_type},
            })

        if request.method == 'DELETE':
            self._assert_entreprise_config_write(request, entreprise)
            merged = remove_document_appearance(
                entreprise.get_config_dict(),
                report_type,
                user_id=request.user.pk,
            )
            entreprise.set_config_dict(merged)
            entreprise.save(update_fields=['config'])
            return Response(merged)

        self._assert_entreprise_config_write(request, entreprise)
        if not isinstance(request.data, dict):
            raise serializers.ValidationError({'detail': _('Le corps de la requÃªte doit Ãªtre un objet JSON.')})
        merged = replace_document_appearance(
            entreprise.get_config_dict(),
            report_type,
            request.data,
            user_id=request.user.pk,
        )
        entreprise.set_config_dict(merged)
        entreprise.save(update_fields=['config'])
        return Response(merged)


@swagger_auto_schema(tags=['Succursales'])
class SuccursaleViewSet(BusinessPermissionMixin, viewsets.ModelViewSet):
    """
    Succursales (branches) de l'entreprise courante.
    - Liste : filtrÃ©e par entreprise (tenant_id ou premier membership).
    - Create/Update/Delete : rÃ©servÃ© Ã  l'Admin de l'entreprise.
    UtilisÃ© pour le flow login (choix de la succursale si has_branches).
    """
    queryset = Succursale.objects.all()
    serializer_class = SuccursaleSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Succursale.objects.none()
        eid = getattr(self.request, 'tenant_id', None) or user.get_entreprise_id(self.request)
        if not eid:
            return Succursale.objects.none()
        # Agent : mÃªme visibilitÃ© que l'admin sur la liste (entreprise) ; succursale JWT sert au filtrage mÃ©tier ailleurs.
        if user.is_agent(self.request):
            return Succursale.objects.filter(entreprise_id=eid, is_active=True).order_by('nom', 'id')
        # Admin : peut voir toutes les succursales de son entreprise.
        return Succursale.objects.filter(entreprise_id=eid, is_active=True).order_by('nom', 'id')

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_admin(self.request):
            raise PermissionDenied(_("Seul l'administrateur de l'entreprise peut crÃ©er une succursale."))
        eid = getattr(self.request, 'tenant_id', None) or user.get_entreprise_id(self.request)
        if not eid:
            raise PermissionDenied(_("Aucune entreprise sÃ©lectionnÃ©e."))
        from abonnements.services.limites import verifier_creation_succursale
        verifier_creation_succursale(eid, self.request)
        entreprise = Entreprise.objects.get(id=eid)
        serializer.save(entreprise=entreprise)

    def perform_update(self, serializer):
        if not self.request.user.is_admin(self.request):
            raise PermissionDenied(_("Seul l'administrateur peut modifier une succursale."))
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_admin(self.request):
            raise PermissionDenied(_("Seul l'administrateur peut supprimer une succursale."))
        instance.is_active = False
        instance.save()


class SortieViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour gÃ©rer les sorties de stock (filtrÃ© par entreprise/succursale)."""
    queryset = Sortie.objects.all()
    serializer_class = SortieSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related(
            Prefetch(
                'lignes',
                queryset=LigneSortie.objects.select_related(
                    'article__sous_type_article',
                    'article__unite',
                    'devise'
                )
            )
        ).order_by('-date_creation')


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lignes_data = request.data.get('lignes', [])
        user = request.user
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        statut_demande = serializer.validated_data.get('statut', 'PAYEE')
        client = serializer.validated_data.get('client')
        if statut_demande == 'EN_CREDIT' and not client:
            raise serializers.ValidationError({
                'client': _('Client obligatoire pour une vente à crédit.'),
            })
        from abonnements.services.limites import verifier_vente_sortie
        verifier_vente_sortie(tenant_id, statut_demande, request)
        default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
        with transaction.atomic():
            # RÃ©cupÃ©rer le client si fourni
            client = serializer.validated_data.get('client')
            
            lib = serializer.validated_data.get('motif', '')
            sortie = Sortie.objects.create(
                motif=lib,
                statut=serializer.validated_data.get('statut', 'PAYEE'),
                client=client,
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                devise_reference=default_dev,
            )
            total = Decimal('0.00')
            devise_mouvement = None
            # Dictionnaire pour calculer les totaux par devise
            totaux_par_devise = {}
            
            for ligne in lignes_data:
                # Support pour les deux formats : article_id ou article
                article_id = ligne.get('article_id') or ligne.get('article')
                
                # VÃ©rification que l'article existe
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                except Article.DoesNotExist:
                    raise serializers.ValidationError({
                        'article': f"Article avec ID {article_id} non trouvÃ© dans votre entreprise. "
                                  f"VÃ©rifiez que l'article existe et vous appartient."
                    })
                
                # Conversion sÃ©curisÃ©e des donnÃ©es
                try:
                    qte_saisie = _parse_decimal_quantity(ligne.get('quantite', 0))
                except (InvalidOperation, TypeError, ValueError):
                    raise serializers.ValidationError({
                        'quantite': 'La quantitÃ© doit Ãªtre un nombre dÃ©cimal valide.'
                    })
                if qte_saisie <= 0:
                    raise serializers.ValidationError({'quantite': 'La quantité doit être supérieure à 0.'})
                conditionnement_id = ligne.get('conditionnement_id') or ligne.get('conditionnement')
                conditionnement_obj = None
                if conditionnement_id:
                    try:
                        conditionnement_obj = ConditionnementArticle.objects.get(
                            pk=conditionnement_id,
                            article=article_obj,
                        )
                    except ConditionnementArticle.DoesNotExist:
                        raise serializers.ValidationError({
                            'conditionnement_id': f'Conditionnement {conditionnement_id} introuvable pour cet article.'
                        })
                    multiplicateur = Decimal(str(conditionnement_obj.multiplicateur_base or '1'))
                    if multiplicateur <= 0:
                        raise serializers.ValidationError({'conditionnement_id': 'Multiplicateur conditionnement invalide.'})
                    qte = (qte_saisie * multiplicateur).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                else:
                    qte = qte_saisie
                
                # Prix rÃ©ellement encaissÃ© (peut Ãªtre fourni manuellement pour promotions, rÃ©ductions, etc.)
                pu_raw = ligne.get('prix_unitaire')
                prix_unitaire_encaisse = None
                if pu_raw is not None:
                    try:
                        if isinstance(pu_raw, Decimal):
                            prix_unitaire_encaisse = pu_raw
                        else:
                            prix_unitaire_encaisse = Decimal(str(pu_raw))
                        if prix_unitaire_encaisse < 0:
                            raise serializers.ValidationError({
                                'prix_unitaire': 'Le prix unitaire ne peut pas Ãªtre nÃ©gatif.'
                            })
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            'prix_unitaire': 'Le prix unitaire doit Ãªtre un nombre valide.'
                        })
                
                # VÃ©rifier le stock disponible (somme des quantite_restante)
                stock_disponible = LigneEntree.objects.filter(
                    article=article_obj,
                    quantite_restante__gt=0
                ).aggregate(total=models.Sum('quantite_restante'))['total'] or 0
                
                if stock_disponible < qte:
                    raise serializers.ValidationError(
                        f"Stock insuffisant pour l'article {article_obj.nom_scientifique} "
                        f"(Disponible: {stock_disponible}, DemandÃ©: {qte})"
                    )
                
                # Gestion de la devise pour chaque ligne
                devise_id = ligne.get('devise_id') or ligne.get('devise')
                if devise_id:
                    try:
                        devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id)
                    except Devise.DoesNotExist:
                        raise serializers.ValidationError(f"Devise avec ID {devise_id} non trouvÃ©e dans votre entreprise.")
                else:
                    devise_obj = default_dev
                
                # ========== LOGIQUE FIFO ==========
                # RÃ©cupÃ©rer les lots disponibles triÃ©s par date (FIFO : plus ancien en premier)
                lots_disponibles = LigneEntree.objects.filter(
                    article=article_obj,
                    quantite_restante__gt=0
                ).order_by('date_entree', 'id')  # FIFO
                
                quantite_restante_a_sortir = qte
                lots_utilises_data = []
                prix_vente_moyen_lots = Decimal('0.00')
                total_prix_vente = Decimal('0.00')
                
                # Consommer les lots en FIFO
                for lot in lots_disponibles:
                    if quantite_restante_a_sortir <= 0:
                        break
                    
                    quantite_a_prelever = min(lot.quantite_restante, quantite_restante_a_sortir)
                    
                    # Stocker les donnÃ©es du lot utilisÃ©
                    lots_utilises_data.append({
                        'lot': lot,
                        'quantite': quantite_a_prelever,
                        'prix_achat': lot.prix_unitaire,
                        'prix_vente': lot.prix_vente_unitaire_base or lot.prix_vente,  # Prix du lot (pour traÃ§abilitÃ©)
                    })
                    
                    # Mettre Ã  jour le lot
                    lot.quantite_restante -= quantite_a_prelever
                    lot.save()
                    
                    quantite_restante_a_sortir -= quantite_a_prelever
                    unit_sale_price = lot.prix_vente_unitaire_base or lot.prix_vente
                    if conditionnement_obj is not None:
                        prix_specifique = PrixConditionnementEntree.objects.filter(
                            ligne_entree=lot,
                            conditionnement=conditionnement_obj,
                        ).order_by('-est_prix_principal', 'id').first()
                        if prix_specifique is not None:
                            unit_sale_price = (
                                prix_specifique.prix_vente / Decimal(str(conditionnement_obj.multiplicateur_base))
                            ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                    total_prix_vente += unit_sale_price * Decimal(str(quantite_a_prelever))
                
                # Calculer le prix de vente moyen des lots (pour rÃ©fÃ©rence, si prix_unitaire non fourni)
                if qte > 0:
                    prix_vente_moyen_lots = total_prix_vente / Decimal(str(qte))
                else:
                    prix_vente_moyen_lots = Decimal('0.00')
                
                # Utiliser le prix rÃ©ellement encaissÃ© si fourni, sinon utiliser le prix moyen des lots
                prix_unitaire_final = prix_unitaire_encaisse if prix_unitaire_encaisse is not None else prix_vente_moyen_lots
                prix_unitaire_final = prix_unitaire_final.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                
                # Créer la ligne de sortie avec le prix réellement encaissé
                montant_ligne = (prix_unitaire_final * Decimal(str(qte))).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                snapshot_ligne = build_conversion_snapshot(
                    entreprise_id=sortie.entreprise_id,
                    amount=montant_ligne,
                    devise_source=devise_obj or default_dev,
                )
                ligne_sortie = LigneSortie.objects.create(
                    sortie=sortie,
                    article=article_obj,
                    quantite=qte,
                    prix_unitaire=prix_unitaire_final,
                    devise=devise_obj,
                    devise_reference=snapshot_ligne['devise_reference'],
                    taux_change=snapshot_ligne['taux_change'],
                    montant_reference=snapshot_ligne['montant_reference'],
                )
                
                # CrÃ©er les traÃ§abilitÃ©s et bÃ©nÃ©fices
                # IMPORTANT : Le bÃ©nÃ©fice est calculÃ© avec le prix rÃ©ellement encaissÃ©, pas le prix_vente du lot
                for lot_data in lots_utilises_data:
                    lot = lot_data['lot']
                    qte_lot = lot_data['quantite']
                    prix_achat = lot_data['prix_achat']
                    prix_vente_lot = lot_data['prix_vente']  # Prix du lot (pour traÃ§abilitÃ©)
                    
                    # TraÃ§abilitÃ© : quel lot a Ã©tÃ© utilisÃ© (on garde le prix_vente du lot pour rÃ©fÃ©rence)
                    LigneSortieLot.objects.create(
                        ligne_sortie=ligne_sortie,
                        lot_entree=lot,
                        quantite=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_vente_lot  # Prix du lot (pour traÃ§abilitÃ©)
                    )
                    
                    # Calculer le bÃ©nÃ©fice avec le prix rÃ©ellement encaissÃ© (pas le prix_vente du lot)
                    benefice_unitaire = prix_unitaire_final - prix_achat
                    benefice_total = benefice_unitaire * Decimal(str(qte_lot))
                    
                    BeneficeLot.objects.create(
                        lot_entree=lot,
                        ligne_sortie=ligne_sortie,
                        quantite_vendue=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_unitaire_final,  # Prix rÃ©ellement encaissÃ© (pour calcul bÃ©nÃ©fice)
                        benefice_unitaire=benefice_unitaire.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                        benefice_total=benefice_total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                    )
                
                # Calcul du montant pour cette ligne (prix réellement encaissé)
                
                # Accumulation par devise
                devise_key = devise_obj.sigle if devise_obj else 'DEFAULT'
                if devise_key not in totaux_par_devise:
                    totaux_par_devise[devise_key] = {
                        'devise_obj': devise_obj,
                        'total': Decimal('0.00')
                    }
                totaux_par_devise[devise_key]['total'] += montant_ligne
                
                # Mettre Ã  jour le stock total (pour compatibilitÃ©)
                stock_obj, created = Stock.objects.get_or_create(
                    article=article_obj,
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte -= qte
                stock_obj.save()
            
            # CrÃ©er les mouvements de caisse par devise (ENTREE pour vente)
            # Si statut EN_CREDIT, montant = 0 (pas d'impact sur la caisse)
            type_caisse_id = extract_type_caisse_id(request.data)
            encaissement_requis = any(
                sortie.statut != 'EN_CREDIT' and devise_data['total'] > 0
                for devise_data in totaux_par_devise.values()
            )
            if encaissement_requis and not type_caisse_id:
                raise serializers.ValidationError({
                    'type_caisse_id': str(MSG_CAISSE_REQUISE),
                })
            for devise_key, devise_data in totaux_par_devise.items():
                devise_obj = devise_data['devise_obj']
                total_devise = devise_data['total']
                
                # Si vente en crÃ©dit, enregistrer avec montant 0
                montant_caisse = Decimal('0.00') if sortie.statut == 'EN_CREDIT' else total_devise
                
                if total_devise > 0:
                    devise_mouvement = devise_obj or default_dev
                    snapshot_mouvement = build_conversion_snapshot(
                        entreprise_id=sortie.entreprise_id,
                        amount=montant_caisse.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                        devise_source=devise_mouvement,
                    )
                    creer_mouvement_caisse(
                        montant=montant_caisse.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                        devise=devise_mouvement,
                        type_mouvement='ENTREE',
                        entreprise_id=sortie.entreprise_id,
                        succursale_id=sortie.succursale_id,
                        content_object=sortie,
                        sortie=sortie,
                        reference_piece=f'VENT-{sortie.pk}-{devise_key}',
                        motif='',
                        utilisateur=user,
                        type_caisse_id=type_caisse_id,
                        devise_reference=snapshot_mouvement['devise_reference'],
                        taux_change=snapshot_mouvement['taux_change'],
                        montant_reference=snapshot_mouvement['montant_reference'],
                    )

            if sortie.statut == 'EN_CREDIT':
                from stock.services.credit_sale_debt import (
                    create_dette_for_credit_sortie,
                    resolve_sortie_primary_devise,
                )

                primary_dev = resolve_sortie_primary_devise(sortie, default_devise=default_dev)
                if primary_dev and not sortie.devise_id:
                    sortie.devise = primary_dev
                    sortie.save(update_fields=['devise'])
                try:
                    create_dette_for_credit_sortie(sortie, default_devise=default_dev, raise_if_exists=True)
                except ValueError as exc:
                    raise serializers.ValidationError({'non_field_errors': str(exc)}) from exc
        return Response(self.get_serializer(sortie).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='produits-plus-vendus')
    def produits_plus_vendus(self, request):
        """
        Retourne les produits les plus vendus, classÃ©s par NOMBRE DE VENTES (nombre de fois
        oÃ¹ le produit a Ã©tÃ© vendu), pas par quantitÃ©. Ex. : un biscuit vendu 10 fois (qtÃ© 12)
        est classÃ© avant une mayonnaise vendue 2 fois (qtÃ© 25).
        
        ParamÃ¨tres de requÃªte (optionnels) :
        - date_debut : Date de dÃ©but (format: YYYY-MM-DD)
        - date_fin : Date de fin (format: YYYY-MM-DD)
        - mois : Mois (1-12)
        - annee : AnnÃ©e (ex: 2025)
        - limit : Nombre de rÃ©sultats Ã  retourner (dÃ©faut: 10)
        - general : true/false - Si true, ignore les filtres de date (dÃ©faut: false)
        
        Exemples :
        - GET /api/sorties/produits-plus-vendus/ (tous les temps)
        - GET /api/sorties/produits-plus-vendus/?date_debut=2025-01-01&date_fin=2025-01-31
        - GET /api/sorties/produits-plus-vendus/?mois=1&annee=2025
        - GET /api/sorties/produits-plus-vendus/?general=true
        """
        from django.db.models import Sum, Count, Q
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # RÃ©cupÃ©rer les paramÃ¨tres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        mois = request.query_params.get('mois')
        annee = request.query_params.get('annee')
        limit = int(request.query_params.get('limit', 10))
        general = request.query_params.get('general', 'false').lower() == 'true'
        
        # Base queryset : toutes les lignes de sortie
        # Utiliser date_sortie de LigneSortie pour le filtrage
        tenant_id, branch_id = self.get_tenant_ids()
        lignes_sortie = LigneSortie.objects.select_related(
            'article',
            'article__unite',
            'article__sous_type_article',
            'sortie'
        )
        if tenant_id:
            lignes_sortie = lignes_sortie.filter(sortie__entreprise_id=tenant_id)
        else:
            lignes_sortie = lignes_sortie.none()
        if branch_id is not None:
            lignes_sortie = lignes_sortie.filter(sortie__succursale_id=branch_id)
        
        # Filtrage par pÃ©riode
        periode_info = {}
        
        if general:
            # Mode gÃ©nÃ©ral : toutes les ventes
            periode_info = {
                'type': 'general',
                'description': 'Toutes les ventes (gÃ©nÃ©ral)'
            }
        elif mois and annee:
            # Filtrage par mois
            try:
                mois_int = int(mois)
                annee_int = int(annee)
                if not (1 <= mois_int <= 12):
                    return Response(
                        {'error': 'Le mois doit Ãªtre entre 1 et 12'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Premier et dernier jour du mois
                date_debut_mois = timezone.make_aware(datetime(annee_int, mois_int, 1))
                if mois_int == 12:
                    date_fin_mois = timezone.make_aware(datetime(annee_int + 1, 1, 1)) - timedelta(days=1)
                else:
                    date_fin_mois = timezone.make_aware(datetime(annee_int, mois_int + 1, 1)) - timedelta(days=1)
                
                lignes_sortie = lignes_sortie.filter(
                    date_sortie__gte=date_debut_mois,
                    date_sortie__lte=date_fin_mois
                )
                
                noms_mois = ['', 'Janvier', 'FÃ©vrier', 'Mars', 'Avril', 'Mai', 'Juin',
                            'Juillet', 'AoÃ»t', 'Septembre', 'Octobre', 'Novembre', 'DÃ©cembre']
                periode_info = {
                    'type': 'mois',
                    'mois': mois_int,
                    'annee': annee_int,
                    'description': f"{noms_mois[mois_int]} {annee_int}"
                }
            except ValueError:
                return Response(
                    {'error': 'Format invalide pour mois ou annÃ©e'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif date_debut or date_fin:
            # Filtrage par pÃ©riode personnalisÃ©e
            try:
                if date_debut:
                    date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                    date_debut_dt = timezone.make_aware(datetime.combine(date_debut_obj, datetime.min.time()))
                    lignes_sortie = lignes_sortie.filter(date_sortie__gte=date_debut_dt)
                
                if date_fin:
                    date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                    date_fin_dt = timezone.make_aware(datetime.combine(date_fin_obj, datetime.max.time()))
                    lignes_sortie = lignes_sortie.filter(date_sortie__lte=date_fin_dt)
                
                periode_info = {
                    'type': 'periode',
                    'date_debut': date_debut,
                    'date_fin': date_fin,
                    'description': f"Du {date_debut or '...'} au {date_fin or '...'}"
                }
            except ValueError:
                return Response(
                    {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Par dÃ©faut : toutes les ventes
            periode_info = {
                'type': 'general',
                'description': 'Toutes les ventes'
            }
        
        # Grouper par article et calculer les totaux
        # Classement par NOMBRE DE VENTES (nombre de fois oÃ¹ le produit a Ã©tÃ© vendu), pas par quantitÃ©
        # Ex. : biscuit vendu 10 fois (qtÃ© 12) > mayonnaise vendue 2 fois (qtÃ© 25) â†’ biscuit est "plus vendu"
        produits_vendus = lignes_sortie.values(
            'article__article_id',
            'article__nom_scientifique',
            'article__nom_commercial',
            'article__unite__libelle'
        ).annotate(
            quantite_totale=Sum('quantite'),
            nombre_ventes=Count('id', distinct=True),
            chiffre_affaires=Sum(models.F('quantite') * models.F('prix_unitaire'))
        ).order_by('-nombre_ventes')[:limit]
        
        # Formater les rÃ©sultats
        resultats = []
        rang = 1
        for produit in produits_vendus:
            resultats.append({
                'rang': rang,
                'article_id': produit['article__article_id'],
                'nom_scientifique': produit['article__nom_scientifique'],
                'nom_commercial': produit['article__nom_commercial'] or '',
                'unite': produit['article__unite__libelle'] or 'N/A',
                'quantite_vendue': produit['quantite_totale'],
                'nombre_ventes': produit['nombre_ventes'],
                'chiffre_affaires': str(Decimal(str(produit['chiffre_affaires'] or 0)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
            })
            rang += 1
        
        # Statistiques globales
        total_quantite = sum(p['quantite_vendue'] for p in resultats)
        # Utiliser Decimal(0) comme valeur initiale pour garantir que le rÃ©sultat est un Decimal
        total_ca = sum((Decimal(str(p['chiffre_affaires'])) for p in resultats), Decimal('0.00'))
        
        return Response({
            'periode': periode_info,
            'classement': {
                'critere': 'nombre_ventes',
                'description': 'Classement par nombre de ventes (nombre de lignes de vente par article), pas par quantite ni par chiffre d''affaires.',
            },
            'statistiques': {
                'nombre_produits': len(resultats),
                'total_quantite_vendue': total_quantite,
                'total_chiffre_affaires': str(total_ca.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                'date_calcul': timezone.now().isoformat()
            },
            'produits': resultats
        })

    def destroy(self, request, *args, **kwargs):
        sortie = self.get_object()
        user = request.user
        with transaction.atomic():
            # 1. Restaurer les lots et le stock pour chaque ligne (FIFO inverse)
            for ligne in sortie.lignes.all():
                # Restaurer les lots utilisÃ©s
                for lot_utilise in ligne.lots_utilises.all():
                    lot = lot_utilise.lot_entree
                    lot.quantite_restante += lot_utilise.quantite
                    lot.save()
                
                # Supprimer les bÃ©nÃ©fices associÃ©s
                BeneficeLot.objects.filter(ligne_sortie=ligne).delete()
                
                # Supprimer les traÃ§abilitÃ©s
                ligne.lots_utilises.all().delete()
                
                # Restaurer le stock total (pour compatibilitÃ©)
                stock, created = Stock.objects.get_or_create(
                    article=ligne.article, 
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock.Qte += ligne.quantite
                stock.save()
            
            # 2. Calculer les totaux par devise pour l'annulation caisse
            default_dev = Devise.objects.filter(est_principal=True).first()
            totaux_par_devise = {}
            
            for ligne in sortie.lignes.all():
                # Calculer le montant de cette ligne
                montant_ligne = (ligne.prix_unitaire or Decimal('0')) * Decimal(str(ligne.quantite))
                
                # DÃ©terminer la devise de cette ligne
                devise_ligne = ligne.devise or default_dev
                devise_key = devise_ligne.sigle if devise_ligne else 'DEFAULT'
                
                # Accumuler par devise
                if devise_key not in totaux_par_devise:
                    totaux_par_devise[devise_key] = {
                        'devise_obj': devise_ligne,
                        'total': Decimal('0.00')
                    }
                totaux_par_devise[devise_key]['total'] += montant_ligne
            
            # 3. VÃ©rifier les soldes et crÃ©er les mouvements de caisse inverses par devise
            # Mais seulement si la vente Ã©tait PAYEE (pas EN_CREDIT)
            type_caisse_id = extract_type_caisse_id(request.data)
            annulation_caisse_requise = (
                sortie.statut != 'EN_CREDIT'
                and any(d['total'] > 0 for d in totaux_par_devise.values())
            )
            if annulation_caisse_requise and not type_caisse_id:
                raise serializers.ValidationError({'type_caisse_id': str(MSG_CAISSE_REQUISE)})
            for devise_key, devise_data in totaux_par_devise.items():
                devise_obj = devise_data['devise_obj']
                total_devise = devise_data['total']
                
                if total_devise > 0:
                    # Si la vente Ã©tait en crÃ©dit, pas besoin d'annuler de mouvement caisse
                    if sortie.statut == 'EN_CREDIT':
                        continue
                    
                    # VÃ©rifier le solde disponible pour cette devise
                    solde_devise = self._solde_caisse_par_devise(
                        user.get_entreprise(self.request),
                        devise_obj,
                        succursale_id=sortie.succursale_id,
                    )
                    if solde_devise < total_devise:
                        raise serializers.ValidationError(
                            f"Solde caisse insuffisant en {devise_key} pour annuler cette vente. "
                            f"Solde disponible: {solde_devise}, Montant requis: {total_devise}"
                        )
                    
                    # CrÃ©er le mouvement de caisse inverse (SORTIE)
                    devise_mouvement = devise_obj or default_dev
                    snapshot_mouvement = build_conversion_snapshot(
                        entreprise_id=sortie.entreprise_id,
                        amount=total_devise.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                        devise_source=devise_mouvement,
                    )
                    creer_mouvement_caisse(
                        montant=total_devise.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                        devise=devise_mouvement,
                        type_mouvement='SORTIE',
                        entreprise_id=sortie.entreprise_id,
                        succursale_id=sortie.succursale_id,
                        content_object=sortie,
                        sortie=sortie,
                        reference_piece=f'ANN-VENT-{sortie.pk}-{devise_key}',
                        motif='Annulation vente',
                        type_caisse_id=type_caisse_id,
                        devise_reference=snapshot_mouvement['devise_reference'],
                        taux_change=snapshot_mouvement['taux_change'],
                        montant_reference=snapshot_mouvement['montant_reference'],
                    )
            
            sortie.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _total_sortie(self, sortie: Sortie) -> Decimal:
        total = Decimal('0.00')
        for l in sortie.lignes.all():
            pu = l.prix_unitaire or Decimal('0')
            total += pu * Decimal(str(l.quantite))
        return total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

    def _solde_caisse_par_devise(self, entreprise, devise, succursale_id=None):
        """Calcule le solde de caisse (tenant + devise) pour une devise spÃ©cifique."""
        if not entreprise or not devise:
            return Decimal('0.00')
        qs = MouvementCaisse.objects.filter(devise=devise, entreprise_id=entreprise.pk)
        if succursale_id is not None:
            qs = qs.filter(succursale_id=succursale_id)
        entrees = qs.filter(type='ENTREE').aggregate(total=Sum('montant'))['total'] or Decimal('0')
        sorties = qs.filter(type='SORTIE').aggregate(total=Sum('montant'))['total'] or Decimal('0')
        return (entrees - sorties).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

    def update(self, request, *args, **kwargs):
        return self._update_common(request, *args, **kwargs, partial=False)

    def partial_update(self, request, *args, **kwargs):
        return self._update_common(request, *args, **kwargs, partial=True)

    def _update_common(self, request, *args, **kwargs):
        """Mise a jour d'une sortie avec gestion FIFO, caisse et dette."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        lignes_data = request.data.get('lignes')

        if lignes_data is not None and not lignes_data:
            raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})
        if not partial and lignes_data is None:
            raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})

        from stock.services.sortie_update_service import update_sortie_from_payload

        type_caisse_id = extract_type_caisse_id(request.data)
        with transaction.atomic():
            instance = update_sortie_from_payload(
                instance,
                request.data,
                utilisateur=request.user,
                type_caisse_id=type_caisse_id,
            )

        return Response(self.get_serializer(instance).data)


    def _solde_caisse(self, entreprise):
        from django.db.models import Sum
        if not entreprise:
            return Decimal('0')
        qs = MouvementCaisse.objects.filter(entreprise_id=entreprise.pk)
        entree = qs.filter(type='ENTREE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        sortie = qs.filter(type='SORTIE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        return entree - sortie

    def _solde_caisse_tenant(self, tenant_id, branch_id=None):
        from django.db.models import Sum
        qs = MouvementCaisse.objects.filter(entreprise_id=tenant_id)
        if branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        entree = qs.filter(type='ENTREE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        sortie = qs.filter(type='SORTIE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        return entree - sortie

    # === Actions POS (facture & bons de sortie) dÃ©placÃ©es depuis RapportViewSet ===
    @action(detail=True, methods=['get'], url_path='facture-pos', permission_classes=[IsAuthenticated])
    def facture_pos_pdf(self, request, pk=None):
        user = request.user
        sortie = self.get_object()
        entreprise = user.get_entreprise(request)
        POS_WIDTH = 58 * mm
        lm, rm, tm, bm = 1.2 * mm, 1.2 * mm, 2 * mm, 2 * mm
        content_width = POS_WIDTH - lm - rm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        mono = ParagraphStyle(
            'MonoTicket',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=6.4,
            leading=7.1,
            alignment=TA_LEFT,
            wordWrap='CJK',
        )
        elements = []

        from pos.printer_service import MP2258Printer
        ticket_lines = MP2258Printer().build_facture_ticket_lines(sortie, entreprise, user)
        for raw in ticket_lines:
            txt = (raw or '').rstrip('\n')
            if txt.strip() == '':
                elements.append(Spacer(1, 0.6 * mm))
            else:
                # preformatted look: Courier + spaces preserved
                safe = txt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
                elements.append(Paragraph(safe, mono))

        avail_width = content_width
        main_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        POS_HEIGHT = main_height + tm + bm + 4.0 * mm

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(POS_WIDTH, POS_HEIGHT),
            leftMargin=lm,
            rightMargin=rm,
            topMargin=tm,
            bottomMargin=bm,
            allowSplitting=0,
        )
        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(
            buffer,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="FACTURE_{sortie.pk}.pdf"'},
        )

    @action(detail=True, methods=['post'], url_path='facture-pos-print', permission_classes=[IsAuthenticated])
    def facture_pos_print(self, request, pk=None):
        """
        Impression ticket POS (ESC/POS) pour MP-2258 via port sÃ©rie.
        NÃ©cessite POS_PRINTER_PORT configurÃ© (ex: COM3).
        """
        user = request.user
        sortie = self.get_object()
        entreprise = user.get_entreprise(request)

        backend = str(getattr(settings, 'POS_PRINTER_BACKEND', 'serial') or 'serial').lower()
        if backend == 'windows':
            printer_name = (getattr(settings, 'POS_PRINTER_NAME', '') or '').strip()
            if not printer_name:
                return Response({'error': "Imprimante Windows non configurÃ©e (POS_PRINTER_NAME)."}, status=501)
        else:
            port = getattr(settings, 'POS_PRINTER_PORT', None)
            if not port:
                return Response({'error': "Port imprimante non configurÃ© (POS_PRINTER_PORT)."}, status=501)

        try:
            from pos.printer_service import MP2258Printer
        except Exception as e:
            return Response(
                {'error': f"Service ESC/POS indisponible: {e}"},
                status=501,
            )

        printer = None
        try:
            printer = MP2258Printer()
            printer.print_facture(sortie, entreprise, user)
            return Response({'status': 'impression lancÃ©e'})
        except ImportError as e:
            return Response(
                {'error': f"DÃ©pendance manquante pour ESC/POS: {e}. Installez python-escpos."},
                status=501,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        finally:
            try:
                if printer:
                    printer.close()
            except Exception:
                pass

    @action(detail=True, methods=['post'], url_path='bon-pos-print', permission_classes=[IsAuthenticated])
    def bon_sortie_pos_print(self, request, pk=None):
        """
        Impression ticket reÃ§u (bon de sortie) en ESC/POS.
        """
        user = request.user
        sortie = self.get_object()
        entreprise = user.get_entreprise(request)

        backend = str(getattr(settings, 'POS_PRINTER_BACKEND', 'serial') or 'serial').lower()
        if backend == 'windows':
            printer_name = (getattr(settings, 'POS_PRINTER_NAME', '') or '').strip()
            if not printer_name:
                return Response({'error': "Imprimante Windows non configurÃ©e (POS_PRINTER_NAME)."}, status=501)
        else:
            port = getattr(settings, 'POS_PRINTER_PORT', None)
            if not port:
                return Response({'error': "Port imprimante non configurÃ© (POS_PRINTER_PORT)."}, status=501)

        try:
            from pos.printer_service import MP2258Printer
        except Exception as e:
            return Response(
                {'error': f"Service ESC/POS indisponible: {e}"},
                status=501,
            )

        printer = None
        try:
            printer = MP2258Printer()
            printer.print_recu(sortie, entreprise, user)
            return Response({'status': 'impression lancÃ©e'})
        except ImportError as e:
            return Response(
                {'error': f"DÃ©pendance manquante pour ESC/POS: {e}. Installez python-escpos."},
                status=501,
            )
        except Exception as e:
            return Response({'error': str(e)}, status=500)
        finally:
            try:
                if printer:
                    printer.close()
            except Exception:
                pass

    @action(detail=True, methods=['get'], url_path='bon-pos', permission_classes=[IsAuthenticated])
    def bon_sortie_pos(self, request, pk=None):
        user = request.user
        sortie = self.get_object()
        POS_WIDTH = 58 * mm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        normal = styles['Normal']; normal.fontSize = 8; normal.wordWrap = 'CJK'
        title_style = ParagraphStyle('TitleMini', fontName='Helvetica-Bold', fontSize=9, alignment=1, spaceAfter=1)
        # SÃ©curise l'accÃ¨s Ã  l'entreprise (peut Ãªtre None pour superadmin)
        entreprise = user.get_entreprise(request)
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        pdf_gen = PDFGenerator()
        elements = list(pdf_gen._create_entete(entete, centered=False))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph(_("BON DE SORTIE"), title_style))
        elements.append(Paragraph(f"{_('NÂ°')}: {sortie.pk}", normal))
        client_label = sortie.client.nom if sortie.client else _("Client Anonyme")
        elements.append(Paragraph(f"{_('Client')}: {client_label}", normal))
        elements.append(Spacer(1, 1*mm))
        lignes = sortie.lignes.all()
        header = [Paragraph(_("Art"), normal), Paragraph(_("QtÃ©"), normal), Paragraph(_("PU"), normal), Paragraph(_("Tot"), normal)]
        data = [header]
        total_general = Decimal('0.00')
        for l in lignes:
            pu = l.prix_unitaire or Decimal('0')
            q = l.quantite or 0
            tot = (pu * Decimal(str(q))).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            total_general += tot
            # prefer line-level devise, then sortie.devise
            line_dev = getattr(l, 'devise', None) or getattr(sortie, 'devise', None)
            data.append([
                Paragraph(_article_display_name(l.article), normal),
                Paragraph(str(q), normal),
                Paragraph(_format_amount(pu, line_dev, entreprise), normal),
                Paragraph(_format_amount(tot, line_dev, entreprise), normal)
            ])
        # single total row after the loop
        data.append([Paragraph(f'<b>{_("Total")}</b>', normal), Paragraph('', normal), Paragraph('', normal), Paragraph(f"<b>{_format_amount(total_general, getattr(sortie, 'devise', None), entreprise)}</b>", normal)])
        table = Table(data, colWidths=[POS_WIDTH*0.40, POS_WIDTH*0.15, POS_WIDTH*0.20, POS_WIDTH*0.25])
        table.setStyle(TableStyle([
            ('FONTNAME',(0,0),(-1,-1),'Helvetica'),
            ('FONTSIZE',(0,0),(-1,-1),8),
            ('ALIGN',(1,0),(-1,-1),'RIGHT'),
            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
            ('BOTTOMPADDING',(0,0),(-1,-1),1),
            ('TOPPADDING',(0,0),(-1,-1),1),
            ('LEFTPADDING',(0,0),(-1,-1),1),
            ('RIGHTPADDING',(0,0),(-1,-1),1),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.6*mm))
        elements.append(Paragraph(_("-- Fin --"), normal))
        lm = rm = tm = bm = 4*mm
        avail_width = POS_WIDTH - lm - rm
        content_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        POS_HEIGHT = content_height + tm + bm + 2*mm
        doc = SimpleDocTemplate(buffer, pagesize=(POS_WIDTH, POS_HEIGHT), leftMargin=lm, rightMargin=rm, topMargin=tm, bottomMargin=bm, allowSplitting=0)
        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': f'inline; filename="BON_SORTIE_{sortie.pk}.pdf"'})

    @action(detail=True, methods=['get'], url_path='bon-sortie-pos')
    def bon_sortie_pos_alias(self, request, pk=None):
        return self.bon_sortie_pos(request, pk=pk)


class LigneSortieViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    tenant_lookup = 'sortie__entreprise_id'
    serializer_class = LigneSortieSerializer
    queryset = LigneSortie.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related('article', 'sortie').order_by('-date_sortie', '-id')

    def perform_create(self, serializer):
        user = self.request.user
        devise_ligne = serializer.validated_data.get('devise')
        montant_ligne = (serializer.validated_data.get('prix_unitaire') or Decimal('0.00')) * serializer.validated_data.get('quantite', Decimal('0.00'))
        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=getattr(serializer.validated_data.get('sortie'), 'entreprise_id', None),
            amount=montant_ligne,
            devise_source=devise_ligne,
        )
        ligne_sortie = serializer.save(
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
        )
        stock, created = Stock.objects.get_or_create(
            article=ligne_sortie.article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        if stock.Qte < ligne_sortie.quantite:
            raise serializers.ValidationError(f"Stock insuffisant pour l'article {_article_display_name(ligne_sortie.article)}")
        stock.Qte -= ligne_sortie.quantite
        stock.save()
    
    def update(self, request, *args, **kwargs):
        """Mise Ã  jour d'une ligne de sortie avec gestion FIFO."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Pour les lignes de sortie, la modification est complexe car elle affecte les lots FIFO
        # On recommande de modifier la sortie entiÃ¨re plutÃ´t qu'une ligne individuelle
        # Mais on permet quand mÃªme la modification pour compatibilitÃ©
        
        nouvelle_quantite = request.data.get('quantite')
        if nouvelle_quantite is None:
            raise serializers.ValidationError({
                'quantite': 'La quantitÃ© est requise pour la mise Ã  jour.'
            })
        
        try:
            nouvelle_quantite = _parse_decimal_quantity(nouvelle_quantite)
        except (InvalidOperation, ValueError, TypeError):
            raise serializers.ValidationError({
                'quantite': 'La quantitÃ© doit Ãªtre un nombre dÃ©cimal valide.'
            })
        
        old_quantite = instance.quantite
        
        with transaction.atomic():
            # Restaurer les lots de l'ancienne quantitÃ©
            for lot_utilise in instance.lots_utilises.all():
                lot = lot_utilise.lot_entree
                lot.quantite_restante += lot_utilise.quantite
                lot.save()
            
            # Supprimer les bÃ©nÃ©fices et traÃ§abilitÃ©s
            BeneficeLot.objects.filter(ligne_sortie=instance).delete()
            instance.lots_utilises.all().delete()
            
            # Restaurer le stock
            stock_obj, created = Stock.objects.get_or_create(
                article=instance.article,
                defaults={'Qte': 0, 'seuilAlert': 0}
            )
            stock_obj.Qte += old_quantite
            stock_obj.save()
            
            # VÃ©rifier le stock disponible pour la nouvelle quantitÃ©
            stock_disponible = LigneEntree.objects.filter(
                article=instance.article,
                quantite_restante__gt=0
            ).aggregate(total=models.Sum('quantite_restante'))['total'] or 0
            
            if stock_disponible < nouvelle_quantite:
                raise serializers.ValidationError(
                    f"Stock insuffisant pour l'article {instance.article.nom_scientifique} "
                    f"(Disponible: {stock_disponible}, DemandÃ©: {nouvelle_quantite})"
                )
            
            # Appliquer FIFO pour la nouvelle quantitÃ©
            lots_disponibles = LigneEntree.objects.filter(
                article=instance.article,
                quantite_restante__gt=0
            ).order_by('date_entree', 'id')
            
            quantite_restante_a_sortir = nouvelle_quantite
            total_prix_vente = Decimal('0.00')
            
            for lot in lots_disponibles:
                if quantite_restante_a_sortir <= 0:
                    break
                
                quantite_a_prelever = min(lot.quantite_restante, quantite_restante_a_sortir)
                
                LigneSortieLot.objects.create(
                    ligne_sortie=instance,
                    lot_entree=lot,
                    quantite=quantite_a_prelever,
                    prix_achat=lot.prix_unitaire,
                    prix_vente=lot.prix_vente
                )
                
                benefice_unitaire = lot.prix_vente - lot.prix_unitaire
                benefice_total = benefice_unitaire * Decimal(str(quantite_a_prelever))
                
                BeneficeLot.objects.create(
                    lot_entree=lot,
                    ligne_sortie=instance,
                    quantite_vendue=quantite_a_prelever,
                    prix_achat=lot.prix_unitaire,
                    prix_vente=lot.prix_vente,
                    benefice_unitaire=benefice_unitaire.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                    benefice_total=benefice_total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                )
                
                lot.quantite_restante -= quantite_a_prelever
                lot.save()
                
                quantite_restante_a_sortir -= quantite_a_prelever
                total_prix_vente += lot.prix_vente * Decimal(str(quantite_a_prelever))
            
            # Calculer le prix moyen
            if nouvelle_quantite > 0:
                prix_vente_moyen = total_prix_vente / Decimal(str(nouvelle_quantite))
            else:
                prix_vente_moyen = Decimal('0.00')
            
            # Mettre Ã  jour la ligne
            instance.quantite = nouvelle_quantite
            instance.prix_unitaire = prix_vente_moyen.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            if 'devise_id' in request.data:
                devise_id = request.data.get('devise_id')
                if devise_id:
                    instance.devise = Devise.objects.get(pk=devise_id)
            snapshot_ligne = build_conversion_snapshot(
                entreprise_id=instance.sortie.entreprise_id,
                amount=(instance.prix_unitaire * instance.quantite).quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                devise_source=instance.devise,
            )
            instance.devise_reference = snapshot_ligne['devise_reference']
            instance.taux_change = snapshot_ligne['taux_change']
            instance.montant_reference = snapshot_ligne['montant_reference']
            instance.save()
            
            # Mettre Ã  jour le stock
            stock_obj.Qte -= nouvelle_quantite
            stock_obj.save()
        
        return Response(self.get_serializer(instance).data)
    
    def partial_update(self, request, *args, **kwargs):
        """Mise Ã  jour partielle d'une ligne de sortie."""
        return self.update(request, *args, **kwargs, partial=True)

    def perform_destroy(self, instance):
        user = self.request.user
        stock, created = Stock.objects.get_or_create(
            article=instance.article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        stock.Qte += instance.quantite
        stock.save()
        instance.delete()

    def perform_update(self, serializer):
        user = self.request.user
        old_instance = self.get_object()
        old_article = old_instance.article
        old_quantite = old_instance.quantite
        devise_ligne = serializer.validated_data.get('devise') or old_instance.devise
        montant_ligne = (serializer.validated_data.get('prix_unitaire') or old_instance.prix_unitaire or Decimal('0.00')) * (serializer.validated_data.get('quantite') or old_instance.quantite or Decimal('0.00'))
        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=old_instance.sortie.entreprise_id,
            amount=montant_ligne,
            devise_source=devise_ligne,
        )
        new_instance = serializer.save(
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
        )
        new_article = new_instance.article
        new_quantite = new_instance.quantite
        # Remettre l'ancienne quantitÃ© dans le stock de l'ancien article
        stock_old, created = Stock.objects.get_or_create(
            article=old_article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        stock_old.Qte += old_quantite
        stock_old.save()
        # Retirer la nouvelle quantitÃ© du stock du nouvel article
        stock_new, created = Stock.objects.get_or_create(
            article=new_article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        if stock_new.Qte < new_quantite:
            raise serializers.ValidationError(f"Stock insuffisant pour l'article {_article_display_name(new_article)}")
        stock_new.Qte -= new_quantite
        stock_new.save()

class UniteViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = Unite.objects.all()
    serializer_class = UniteSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-id')


class ConditionnementArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = ConditionnementArticle.objects.select_related('article').all()
    serializer_class = ConditionnementArticleSerializer
    tenant_lookup = 'article__entreprise_id'

    def get_queryset(self):
        return super().get_queryset().order_by('article_id', '-est_defaut', 'nom', 'id')

    def perform_create(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        article = serializer.validated_data['article']
        if tenant_id and article.entreprise_id != tenant_id:
            raise serializers.ValidationError({'article_id': 'Article hors entreprise courante.'})
        serializer.save()

    def perform_update(self, serializer):
        tenant_id, _ = self.get_tenant_ids()
        article = serializer.validated_data.get('article', serializer.instance.article)
        if tenant_id and article.entreprise_id != tenant_id:
            raise serializers.ValidationError({'article_id': 'Article hors entreprise courante.'})
        serializer.save()


class PrixConditionnementEntreeViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = PrixConditionnementEntree.objects.select_related(
        'ligne_entree__entree',
        'ligne_entree__article',
        'conditionnement',
        'devise',
    ).all()
    serializer_class = PrixConditionnementEntreeSerializer
    tenant_lookup = 'ligne_entree__entree__entreprise_id'

    def get_queryset(self):
        return super().get_queryset().order_by('-id')

    def _validate_relations(self, payload):
        ligne_entree = payload.get('ligne_entree') or self.get_object().ligne_entree
        conditionnement = payload.get('conditionnement') or self.get_object().conditionnement
        devise = payload.get('devise') or self.get_object().devise
        if ligne_entree.article_id != conditionnement.article_id:
            raise serializers.ValidationError({
                'conditionnement_id': 'Le conditionnement doit appartenir au même article que la ligne d’entrée.',
            })
        if devise.entreprise_id != ligne_entree.entree.entreprise_id:
            raise serializers.ValidationError({
                'devise_id': 'La devise doit appartenir à l’entreprise de la ligne d’entrée.',
            })

    def perform_create(self, serializer):
        self._validate_relations(serializer.validated_data)
        instance = serializer.save()
        if instance.est_prix_principal:
            PrixConditionnementEntree.objects.filter(
                ligne_entree=instance.ligne_entree,
                est_prix_principal=True,
            ).exclude(pk=instance.pk).update(est_prix_principal=False)

    def perform_update(self, serializer):
        self._validate_relations(serializer.validated_data)
        instance = serializer.save()
        if instance.est_prix_principal:
            PrixConditionnementEntree.objects.filter(
                ligne_entree=instance.ligne_entree,
                est_prix_principal=True,
            ).exclude(pk=instance.pk).update(est_prix_principal=False)


class CodeBarresArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = CodeBarresArticle.objects.select_related(
        'article',
        'conditionnement',
        'entreprise',
        'succursale',
        'cree_par',
    ).all()
    serializer_class = CodeBarresArticleSerializer
    tenant_lookup = 'entreprise_id'

    def get_queryset(self):
        qs = super().get_queryset().order_by('article_id', 'conditionnement_id', '-est_principal', 'code')
        article_id = self.request.query_params.get('article_id')
        if article_id:
            qs = qs.filter(article_id=article_id)
        conditionnement_id = self.request.query_params.get('conditionnement_id')
        if conditionnement_id:
            qs = qs.filter(conditionnement_id=conditionnement_id)
        est_actif = self.request.query_params.get('est_actif')
        if est_actif is not None:
            qs = qs.filter(est_actif=str(est_actif).lower() in ('1', 'true', 'yes'))
        return qs

    def perform_create(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        article = serializer.validated_data['article']
        if article.entreprise_id != tenant_id:
            raise serializers.ValidationError({'article_id': 'Article hors entreprise courante.'})
        conditionnement = serializer.validated_data['conditionnement']
        if conditionnement.article_id != article.article_id:
            raise serializers.ValidationError({
                'conditionnement_id': 'Le conditionnement doit appartenir à l’article.',
            })
        serializer.save(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            cree_par=self.request.user if self.request.user.is_authenticated else None,
        )

    def perform_update(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        article = serializer.validated_data.get('article', serializer.instance.article)
        if tenant_id and article.entreprise_id != tenant_id:
            raise serializers.ValidationError({'article_id': 'Article hors entreprise courante.'})
        conditionnement = serializer.validated_data.get('conditionnement', serializer.instance.conditionnement)
        if conditionnement.article_id != article.article_id:
            raise serializers.ValidationError({
                'conditionnement_id': 'Le conditionnement doit appartenir à l’article.',
            })
        serializer.save(
            entreprise_id=tenant_id or serializer.instance.entreprise_id,
            succursale_id=branch_id if branch_id is not None else serializer.instance.succursale_id,
        )

    @action(detail=False, methods=['post'], url_path='generer')
    def generer(self, request):
        """
        Génère un code-barres interne Code128 pour un conditionnement.
        POST { article_id, conditionnement_id, format?: numerique|structure, remplacer?: false }
        """
        from stock.services.code_barres_interne import generer_code_barres_interne, normalize_format

        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            return Response(
                {'detail': _('Contexte entreprise manquant.')},
                status=status.HTTP_403_FORBIDDEN,
            )

        article_id = request.data.get('article_id')
        conditionnement_id = request.data.get('conditionnement_id')
        if not article_id or not conditionnement_id:
            return Response(
                {'detail': _('article_id et conditionnement_id sont obligatoires.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            article = Article.objects.get(article_id=article_id, entreprise_id=tenant_id)
        except Article.DoesNotExist:
            return Response(
                {'article_id': _('Article introuvable.')},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            conditionnement = ConditionnementArticle.objects.get(
                pk=conditionnement_id,
                article=article,
            )
        except ConditionnementArticle.DoesNotExist:
            return Response(
                {'conditionnement_id': _('Conditionnement introuvable pour cet article.')},
                status=status.HTTP_404_NOT_FOUND,
            )

        format_code = request.data.get('format', 'numerique')
        try:
            normalize_format(format_code)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        remplacer = str(request.data.get('remplacer', False)).lower() in ('1', 'true', 'yes')

        try:
            instance = generer_code_barres_interne(
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                article=article,
                conditionnement=conditionnement,
                utilisateur=request.user,
                format_code=format_code,
                remplacer=remplacer,
            )
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        data = CodeBarresArticleSerializer(instance, context={'request': request}).data
        data['etiquette_url'] = request.build_absolute_uri(
            f'/api/codes-barres-articles/{instance.pk}/etiquette/'
        )
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='generer-manquants')
    def generer_manquants(self, request):
        """Génère des codes pour tous les conditionnements actifs sans code-barres."""
        from stock.services.code_barres_interne import generer_codes_manquants_article, normalize_format

        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            return Response(
                {'detail': _('Contexte entreprise manquant.')},
                status=status.HTTP_403_FORBIDDEN,
            )

        article_id = request.data.get('article_id')
        if not article_id:
            return Response(
                {'article_id': _('article_id est obligatoire.')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            article = Article.objects.get(article_id=article_id, entreprise_id=tenant_id)
        except Article.DoesNotExist:
            return Response(
                {'article_id': _('Article introuvable.')},
                status=status.HTTP_404_NOT_FOUND,
            )

        format_code = request.data.get('format', 'numerique')
        try:
            normalize_format(format_code)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        try:
            created = generer_codes_manquants_article(
                entreprise_id=tenant_id,
                succursale_id=branch_id,
                article=article,
                utilisateur=request.user,
                format_code=format_code,
            )
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        ser = CodeBarresArticleSerializer(created, many=True, context={'request': request})
        return Response(
            {
                'count': len(created),
                'codes_barres': ser.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='etiquette')
    def etiquette(self, request, pk=None):
        """PDF étiquette Code128 imprimable."""
        from stock.services.code_barres_interne import build_etiquette_pdf

        instance = self.get_object()
        entreprise = request.user.get_entreprise(request) if request.user.is_authenticated else instance.entreprise
        pdf_bytes = build_etiquette_pdf(instance, entreprise=entreprise)
        filename = f'etiquette_{instance.article_id}_{instance.pk}.pdf'
        return HttpResponse(
            pdf_bytes,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="{filename}"'},
        )


class CodeBarresLookupView(BusinessPermissionMixin, viewsets.ViewSet):
    """GET /api/stock/code-barres/lookup/?code=..."""

    @swagger_auto_schema(
        operation_summary='Recherche article par code-barres scanné',
        manual_parameters=[
            openapi.Parameter(
                'code',
                openapi.IN_QUERY,
                description='Valeur scannée par le lecteur (EAN, Code128, interne…)',
                type=openapi.TYPE_STRING,
                required=True,
            ),
        ],
    )
    def list(self, request):
        from stock.services.code_barres_lookup import lookup_code_barres

        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response(
                {'found': False, 'message': 'Contexte entreprise manquant.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        code = request.query_params.get('code', '')
        payload = lookup_code_barres(code, tenant_id=tenant_id, branch_id=branch_id)
        http_status = status.HTTP_200_OK if payload.get('found') else status.HTTP_404_NOT_FOUND
        return Response(payload, status=http_status)


class TypeArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = TypeArticle.objects.all()
    serializer_class = TypeArticleSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-id')


class ArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    # Important: try portal client auth first; a portal token is NOT a SimpleJWT staff token.
    authentication_classes = [ClientJWTAuthentication, JWTAuthenticationWithContext]

    def get_permissions(self):
        # Portail client : lecture/recherche uniquement.
        if getattr(self.request, "client", None) is not None:
            if self.request.method in permissions.SAFE_METHODS:
                return [IsClientAuthenticated()]
            return [permissions.IsAuthenticated()]  # forcera un 403 (pas d'Ã©criture pour client)
        return super().get_permissions()

    def get_queryset(self):
        return super().get_queryset().order_by('-pk')

    @swagger_auto_schema(
        operation_summary='Recherche d\'articles (tenant)',
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Texte recherchÃ© (obligatoire) : nom scientifique, commercial ou code article. Ex. ?q=cafÃ©',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Nombre max de rÃ©sultats (dÃ©faut 25, max 100).',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description='Pagination (dÃ©calage).',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                'RÃ©sultats + meta ; champ Â« message Â» si aucun article ne correspond.',
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
        },
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """Recherche scoping entreprise/succursale ; index FULLTEXT MySQL + repli jetons courts."""
        from stock.services.article_search import DEFAULT_LIMIT, MAX_LIMIT, search_articles

        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response(
                {'detail': 'Contexte entreprise manquant.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response(
                {
                    'detail': _(
                        'Indiquez ce que vous cherchez avec le paramÃ¨tre Â« q Â». '
                        'Exemple : GET /api/articles/search/?q=cafÃ©'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = int(request.query_params.get('limit', DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        try:
            offset = int(request.query_params.get('offset', 0))
        except (TypeError, ValueError):
            offset = 0
        limit = min(max(1, limit), MAX_LIMIT)
        offset = max(0, offset)

        articles, meta = search_articles(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            q=q,
            limit=limit,
            offset=offset,
        )
        ser = ArticleSearchSerializer(articles, many=True, context={'request': request})
        payload = {'results': ser.data, 'meta': meta}
        if meta.get('total', 0) == 0:
            q_display = (q[:200] + 'â€¦') if len(q) > 200 else q
            if branch_id is not None:
                msg = _(
                    'Aucun article ne correspond Ã  Â« %(term)s Â» pour cette succursale. '
                    'Essayez un autre mot-clÃ© (nom scientifique, nom commercial ou code article), '
                    'vÃ©rifiez lâ€™orthographe ou Ã©largissez la recherche (autre succursale si votre rÃ´le le permet).'
                ) % {'term': q_display}
            else:
                msg = _(
                    'Aucun article ne correspond Ã  Â« %(term)s Â» dans votre entreprise. '
                    'Essayez un autre mot-clÃ© (nom scientifique, nom commercial ou code article) '
                    'ou vÃ©rifiez lâ€™orthographe.'
                ) % {'term': q_display}
            payload['message'] = msg
        return Response(payload)

    def perform_create(self, serializer):
        super().perform_create(serializer)
        article = serializer.instance
        Stock.objects.create(article=article, Qte=0, seuilAlert=0)


class StockViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ReadOnlyModelViewSet):
    tenant_lookup = 'article__entreprise_id'
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

    def get_queryset(self):
        return super().get_queryset().select_related('article').order_by('-id')

    @swagger_auto_schema(
        operation_summary='Statistiques stocks par statut (tenant)',
        operation_description=(
            'Statuts (1 requÃªte agrÃ©gÃ©e sur Stock) : NORMAL (Qte > seuilAlert), '
            'ALERTE / faible (0 < Qte â‰¤ seuilAlert), RUPTURE (Qte = 0). '
            'Expiration proche : deux comptages distincts dâ€™articles (lots LigneEntree avec '
            'quantite_restante > 0, date_expiration entre aujourdâ€™hui et la fin de fenÃªtre) : '
            '**expiration_sous_30_jours** (+30 jours glissants), **expiration_sous_3_mois** '
            '(+3 mois calendaires). Lots dÃ©jÃ  expirÃ©s exclus. '
            'Hors pagination. PÃ©rimÃ¨tre : entreprise JWT ; succursale si prÃ©sente dans le contexte.'
        ),
        responses={
            200: openapi.Response(
                'Totaux par statut',
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'normal': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'alerte': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'faible': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='Identique Ã  alerte (libellÃ© mÃ©tier)',
                        ),
                        'rupture': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'by_code': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='MÃªmes valeurs, clÃ©s NORMAL / ALERTE / RUPTURE',
                        ),
                        'sum_statuts': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='normal + alerte + rupture (identique Ã  total si cohÃ©rent)',
                        ),
                        'expiration_sous_30_jours': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description=(
                                'Articles distincts avec au moins un lot non Ã©puisÃ© '
                                'dont la date dâ€™expiration est dans les 30 prochains jours'
                            ),
                        ),
                        'expiration_periode_30_jours': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='FenÃªtre [date_debut, date_fin] pour expiration_sous_30_jours',
                            properties={
                                'date_debut': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'date_fin': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                            },
                        ),
                        'expiration_sous_3_mois': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description=(
                                'Articles distincts avec au moins un lot non Ã©puisÃ© '
                                'dont la date dâ€™expiration est dans les 3 prochains mois (calendaires)'
                            ),
                        ),
                        'expiration_periode': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='FenÃªtre [date_debut, date_fin] pour expiration_sous_3_mois',
                            properties={
                                'date_debut': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'date_fin': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                            },
                        ),
                    },
                ),
            ),
        },
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """AgrÃ©gation SQL des stocks par statut (hors pagination)."""
        from stock.services.stock_stats import aggregate_stock_stats

        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response(
                {'detail': _('Contexte entreprise manquant.')},
                status=status.HTTP_403_FORBIDDEN,
            )
        payload = aggregate_stock_stats(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
        )
        return Response(
            {
                'total': payload['total'],
                'normal': payload['normal'],
                'alerte': payload['alerte'],
                'faible': payload['faible'],
                'rupture': payload['rupture'],
                'sum_statuts': payload['sum_statuts'],
                'by_code': payload['by_code'],
                'expiration_sous_30_jours': payload['expiration_sous_30_jours'],
                'expiration_periode_30_jours': payload['expiration_periode_30_jours'],
                'expiration_sous_3_mois': payload['expiration_sous_3_mois'],
                'expiration_periode': payload['expiration_periode'],
            }
        )


class LigneEntreeViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    tenant_lookup = 'entree__entreprise_id'
    queryset = LigneEntree.objects.all()
    serializer_class = LigneEntreeSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-date_entree', '-id')

    def perform_create(self, serializer):
        devise_ligne = serializer.validated_data.get('devise')
        montant_ligne = (serializer.validated_data.get('prix_unitaire') or Decimal('0.00')) * serializer.validated_data.get('quantite', Decimal('0.00'))
        entree_obj = serializer.validated_data.get('entree')
        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=getattr(entree_obj, 'entreprise_id', None),
            amount=montant_ligne,
            devise_source=devise_ligne,
        )
        ligne_entree = serializer.save(
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
        )
        stock, created = Stock.objects.get_or_create(
            article=ligne_entree.article,
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        stock.Qte += ligne_entree.quantite
        stock.save()
    
    def update(self, request, *args, **kwargs):
        """Mise a jour d'une ligne d'entree via le service entree."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        article = validated.get('article', instance.article)
        payload = {
            'lignes': [{
                'id': instance.pk,
                'article_id': article.pk,
                'quantite': validated.get('quantite', instance.quantite),
                'prix_unitaire': validated.get('prix_unitaire', instance.prix_unitaire),
                'prix_vente': validated.get('prix_vente', instance.prix_vente),
                'date_expiration': validated.get('date_expiration', instance.date_expiration),
                'devise_id': (validated.get('devise') or instance.devise).pk if (validated.get('devise') or instance.devise) else None,
                'seuil_alerte': validated.get('seuil_alerte', instance.seuil_alerte),
            }],
        }
        from stock.services.entree_update_service import update_entree_from_payload

        with transaction.atomic():
            update_entree_from_payload(instance.entree, payload)
            updated_instance = LigneEntree.objects.get(pk=instance.pk)

        return Response(self.get_serializer(updated_instance).data)

    def partial_update(self, request, *args, **kwargs):
        """Mise Ã  jour partielle d'une ligne d'entrÃ©e."""
        return self.update(request, *args, **kwargs, partial=True)


class DeviseViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """CRUD pour les devises de l'entreprise avec gestion de la devise principale unique."""
    queryset = Devise.objects.all()
    serializer_class = DeviseSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-id')

    def perform_create(self, serializer):
        tenant_id, _ = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        est_principal = serializer.validated_data.get('est_principal', False)
        if est_principal:
            with transaction.atomic():
                Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).update(est_principal=False)
                serializer.save(entreprise_id=tenant_id)
        else:
            has_principal = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).exists()
            if not has_principal:
                serializer.validated_data['est_principal'] = True
            serializer.save(entreprise_id=tenant_id)
    
    def perform_update(self, serializer):
        instance = self.get_object()
        tenant_id = instance.entreprise_id
        est_principal = serializer.validated_data.get('est_principal', instance.est_principal)
        if est_principal and not instance.est_principal:
            with transaction.atomic():
                Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).exclude(id=instance.id).update(est_principal=False)
                serializer.save()
        elif not est_principal and instance.est_principal:
            autres_devises = self.get_queryset().exclude(id=instance.id)
            
            if not autres_devises.exists():
                raise serializers.ValidationError({
                    'est_principal': "Impossible de dÃ©sactiver la seule devise de l'entreprise. "
                                   "Elle doit rester principale."
                })
            
            # Promouvoir automatiquement une autre devise comme principale
            with transaction.atomic():
                serializer.save()
                # Prendre la premiÃ¨re autre devise et la rendre principale
                premiere_autre = autres_devises.first()
                premiere_autre.est_principal = True
                premiere_autre.save()
        else:
            serializer.save()
    
    def perform_destroy(self, instance):
        autres_devises = self.get_queryset().exclude(id=instance.id)
        
        if not autres_devises.exists():
            raise serializers.ValidationError({
                'detail': "Impossible de supprimer la derniÃ¨re devise de l'entreprise. "
                         "CrÃ©ez une nouvelle devise avant de supprimer celle-ci."
            })
        
        with transaction.atomic():
            etait_principale = instance.est_principal
            instance.delete()
            
            # Si c'Ã©tait la devise principale, promouvoir automatiquement une autre
            if etait_principale:
                premiere_autre = autres_devises.first()
                premiere_autre.est_principal = True
                premiere_autre.save()


class TauxChangeViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = TauxChange.objects.select_related('devise_source', 'devise_cible', 'cree_par').all()
    serializer_class = TauxChangeSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-date_application', '-id')

    def perform_create(self, serializer):
        tenant_id, _ = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        serializer.save(entreprise_id=tenant_id, cree_par=self.request.user)

    def perform_update(self, serializer):
        serializer.save()



@api_view(['GET', 'POST'])
@permission_classes([StockIsAdminOrUser])
def taux_change_collection(request):
    tenant_id, _ = _get_tenant_ids(request)
    if tenant_id is None:
        raise PermissionDenied(_("Contexte entreprise manquant."))

    entreprise = get_object_or_404(Entreprise, pk=tenant_id)

    if request.method == 'GET':
        latest_by_pair = {}
        for entry in _get_entreprise_exchange_rates(entreprise):
            if entry.get('is_active', True) is False:
                continue
            pair_key = (entry.get('source_devise_id'), entry.get('target_devise_id'))
            current = latest_by_pair.get(pair_key)
            if current is None or _exchange_rate_sort_key(entry) > _exchange_rate_sort_key(current):
                latest_by_pair[pair_key] = entry
        payload = [
            _serialize_exchange_rate_entry(entry, entreprise)
            for entry in sorted(
                latest_by_pair.values(),
                key=lambda item: (
                    item.get('source_devise_id') or 0,
                    item.get('target_devise_id') or 0,
                ),
            )
        ]
        return Response(payload)

    source_id, target_id, rate_raw, effective_at, is_active = _extract_exchange_rate_payload(request.data)
    if not source_id or not target_id:
        raise serializers.ValidationError({
            'detail': _("Les devises source et cible sont obligatoires."),
        })

    try:
        source_devise = Devise.objects.get(pk=source_id, entreprise_id=tenant_id)
    except Devise.DoesNotExist as exc:
        raise NotFound(_("Devise source introuvable pour cette entreprise.")) from exc
    try:
        target_devise = Devise.objects.get(pk=target_id, entreprise_id=tenant_id)
    except Devise.DoesNotExist as exc:
        raise NotFound(_("Devise cible introuvable pour cette entreprise.")) from exc

    try:
        rate = Decimal(str(rate_raw).replace(',', '.'))
    except (InvalidOperation, AttributeError):
        raise serializers.ValidationError({'taux': _("Le taux de change est invalide.")})
    if rate <= 0:
        raise serializers.ValidationError({'taux': _("Le taux de change doit etre superieur a 0.")})

    now_iso = timezone.now().isoformat()
    current_rates = _get_entreprise_exchange_rates(entreprise)
    new_entry = {
        'id': max([int(item.get('id') or 0) for item in current_rates] + [0]) + 1,
        'source_devise_id': source_devise.id,
        'target_devise_id': target_devise.id,
        'rate': str(rate),
        'effective_at': effective_at or now_iso,
        'is_active': bool(is_active),
        'created_at': now_iso,
        'created_by_user_id': getattr(request.user, 'id', None),
    }
    current_rates.append(new_entry)
    _persist_exchange_rates(entreprise, current_rates, user_id=getattr(request.user, 'id', None))
    return Response(_serialize_exchange_rate_entry(new_entry, entreprise), status=status.HTTP_201_CREATED)


class EntreeViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour gÃ©rer les entrÃ©es de stock avec support multi-devises (filtrÃ© par entreprise/succursale)."""
    queryset = Entree.objects.all()
    serializer_class = EntreeSerializer

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch(
                'lignes',
                queryset=LigneEntree.objects.select_related(
                    'article__sous_type_article',
                    'article__unite',
                    'devise',
                ),
            )
        ).order_by('-date_op')

    def perform_create(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        if tenant_id:
            serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)
        else:
            serializer.save()

    def create(self, request, *args, **kwargs):
        """CrÃ©ation d'une entrÃ©e avec gestion intelligente des stocks et multi-devises."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        lignes_data = request.data.get('lignes', [])
        user = request.user
        messages_reponse = []
        
        if not lignes_data:
            raise serializers.ValidationError("Au moins une ligne d'entrÃ©e est requise.")
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
        articles_groupes = {}
        
        for ligne in lignes_data:
            # On accepte article_id comme code produit (ex: "CAPE0001") ou comme clÃ© primaire numÃ©rique
            article_lookup = None
            article_id = ligne.get('article') or ligne.get('article_id')
            if article_id:
                # Essayer d'abord par code produit, sinon par clÃ© primaire
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                    article_lookup = article_obj.article_id
                except Article.DoesNotExist:
                    try:
                        article_obj = Article.objects.get(nom_commercial=article_id)
                        article_lookup = article_obj.article_id
                    except Article.DoesNotExist:
                        # Peut-Ãªtre que c'est dÃ©jÃ  la clÃ© primaire numÃ©rique
                        article_lookup = article_id
            else:
                article_lookup = None

            raw_quantite = ligne.get('quantite')
            if raw_quantite is None:
                raw_quantite = ligne.get('quantite_base')
            if raw_quantite is None:
                raw_quantite = ligne.get('quantite_saisie')
            try:
                qte = _parse_decimal_quantity(raw_quantite or 0)
            except (InvalidOperation, TypeError, ValueError):
                raise serializers.ValidationError({'quantite': 'La quantitÃ© doit Ãªtre un nombre dÃ©cimal valide.'})
            prix_unitaire_raw = ligne.get('prix_unitaire')
            if prix_unitaire_raw is None:
                prix_unitaire_raw = ligne.get('prix_achat_unitaire_base')
            if prix_unitaire_raw is None:
                prix_unitaire_raw = ligne.get('prix_achat_conditionnement')
                cond_id = ligne.get('conditionnement_id') or ligne.get('conditionnement')
                if prix_unitaire_raw is not None and cond_id and article_lookup:
                    try:
                        article_obj_tmp = Article.objects.get(article_id=article_lookup)
                        cond_tmp = ConditionnementArticle.objects.get(pk=cond_id, article=article_obj_tmp)
                        mult_tmp = Decimal(str(cond_tmp.multiplicateur_base or '1'))
                        if mult_tmp > 0:
                            prix_unitaire_raw = (Decimal(str(prix_unitaire_raw)) / mult_tmp).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                    except Exception:
                        pass
            if prix_unitaire_raw is None:
                prix_unitaire_raw = 0
            try:
                prix_unitaire = Decimal(str(prix_unitaire_raw))
            except (ValueError, TypeError, InvalidOperation):
                prix_unitaire = Decimal('0.00')
            
            # Prix de vente (obligatoire pour calculer les bÃ©nÃ©fices)
            prix_vente_raw = ligne.get('prix_vente')
            if prix_vente_raw is None:
                prix_vente_raw = ligne.get('prix_vente_unitaire_base')
            if prix_vente_raw is None:
                prix_vente_raw = ligne.get('prix_vente_conditionnement')
                cond_id = ligne.get('conditionnement_id') or ligne.get('conditionnement')
                if prix_vente_raw is not None and cond_id and article_lookup:
                    try:
                        article_obj_tmp = Article.objects.get(article_id=article_lookup)
                        cond_tmp = ConditionnementArticle.objects.get(pk=cond_id, article=article_obj_tmp)
                        mult_tmp = Decimal(str(cond_tmp.multiplicateur_base or '1'))
                        if mult_tmp > 0:
                            prix_vente_raw = (Decimal(str(prix_vente_raw)) / mult_tmp).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                    except Exception:
                        pass
            if prix_vente_raw is None:
                prix_vente_raw = 0
            try:
                prix_vente = Decimal(str(prix_vente_raw))
            except (ValueError, TypeError, InvalidOperation):
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente est obligatoire pour chaque ligne d\'entrÃ©e.'
                })
            
            if prix_vente <= 0:
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente doit Ãªtre supÃ©rieur Ã  0.'
                })
            
            try:
                seuil_alerte = Decimal(str(ligne.get('seuil_alerte', 0)).replace(",", "."))
            except (InvalidOperation, TypeError, ValueError):
                seuil_alerte = Decimal('0')
            devise_id = ligne.get('devise_id') or ligne.get('devise')
            date_expiration = ligne.get('date_expiration')

            if article_lookup in articles_groupes:
                articles_groupes[article_lookup]['quantite'] += qte
                messages_reponse.append(f"Article {article_id}: quantitÃ©s additionnÃ©es ({qte} ajoutÃ©)")
            else:
                articles_groupes[article_lookup] = {
                    'quantite': qte,
                    'prix_unitaire': prix_unitaire,
                    'prix_vente': prix_vente,
                    'seuil_alerte': seuil_alerte,
                    'devise': devise_id,
                    'date_expiration': date_expiration
                }
        
        with transaction.atomic():
            stock_states = {}
            for article_id, ligne_data in articles_groupes.items():
                article_obj = Article.objects.get(article_id=article_id)
                stock_obj = Stock.objects.filter(article=article_obj).first()
                stock_states[article_id] = {
                    'article_nom': article_obj.nom_commercial or article_obj.nom_scientifique,
                    'previous_qte': stock_obj.Qte if stock_obj else Decimal('0'),
                    'had_stock': stock_obj is not None,
                    'quantite': ligne_data['quantite'],
                }

            entree = serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)

            for article_id, state in stock_states.items():
                article_nom = state['article_nom']
                previous_qte = state['previous_qte']
                qte = state['quantite']
                if not state['had_stock']:
                    messages_reponse.append(f"Nouveau stock cree pour {article_nom}")
                elif previous_qte == 0:
                    messages_reponse.append(f"Reapprovisionnement de {article_nom} (stock etait epuise)")
                else:
                    messages_reponse.append(
                        f"Ajout au stock existant de {article_nom} (stock: {previous_qte} -> {previous_qte + qte})"
                    )

        # Retourner la réponse avec les messages informatifs
        response_data = self.get_serializer(entree).data
        response_data['messages'] = messages_reponse
        response_data['articles_traites'] = len(articles_groupes)
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='lots-par-article/(?P<article_id>[^/.]+)')
    def lots_par_article(self, request, article_id=None):
        """
        Retourne tous les lots disponibles pour un article (fiche de stock par lot).
        GET /api/entrees/lots-par-article/{article_id}/
        """
        try:
            tenant_id, branch_id = self.get_tenant_ids()
            article_qs = Article.objects.filter(article_id=article_id, entreprise_id=tenant_id) if tenant_id else Article.objects.none()
            if branch_id is not None:
                article_qs = article_qs.filter(succursale_id=branch_id)
            article = article_qs.get()
        except Article.DoesNotExist:
            return Response(
                {'error': f'Article {article_id} non trouvÃ©'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # RÃ©cupÃ©rer tous les lots (disponibles et Ã©puisÃ©s)
        tenant_id, branch_id = self.get_tenant_ids()
        lots = LigneEntree.objects.filter(article=article, entree__entreprise_id=tenant_id)
        if branch_id is not None:
            lots = lots.filter(entree__succursale_id=branch_id)
        lots = lots.order_by('date_entree', 'id')
        
        lots_data = []
        stock_total = 0
        
        for lot in lots:
            stock_total += lot.quantite_restante
            benefice_potentiel = (lot.prix_vente - lot.prix_unitaire) * Decimal(str(lot.quantite_restante))
            
            lots_data.append({
                'lot_id': lot.id,
                'entree_id': lot.entree.id,
                'quantite_totale': lot.quantite,
                'quantite_restante': lot.quantite_restante,
                'quantite_vendue': lot.quantite - lot.quantite_restante,
                'prix_achat': str(lot.prix_unitaire),
                'prix_vente': str(lot.prix_vente),
                'benefice_unitaire': str(lot.prix_vente - lot.prix_unitaire),
                'benefice_potentiel': str(benefice_potentiel),
                'date_entree': lot.date_entree.isoformat(),
                'date_expiration': lot.date_expiration.isoformat() if lot.date_expiration else None,
                'devise': lot.devise.sigle if lot.devise else None,
                'statut': 'Disponible' if lot.quantite_restante > 0 else 'Ã‰puisÃ©'
            })
        
        return Response({
            'article': {
                'id': article.article_id,
                'nom_scientifique': article.nom_scientifique,
                'nom_commercial': article.nom_commercial,
            },
            'stock_total': stock_total,
            'nombre_lots': len(lots_data),
            'lots': lots_data
        })
    
    @action(detail=False, methods=['get'], url_path='benefices-totaux')
    def benefices_totaux(self, request):
        """
        Retourne les bÃ©nÃ©fices totaux des lots vendus, avec filtre optionnel par mois/annÃ©e.
        **Isolation multi-tenant :** uniquement les `BeneficeLot` dont le lot d'entrÃ©e appartient Ã 
        l'entreprise du JWT ; si `succursale_id` est prÃ©sent dans le token, filtre aussi par cette succursale.
        Par dÃ©faut : mois et annÃ©e en cours.
        GET /api/entrees/benefices-totaux/
        Query params: month (1-12), year (ex: 2026). Omis = mois et annÃ©e courants.
        """
        from django.db.models import Sum, Count

        tenant_id, branch_id = self.get_tenant_ids()
        if tenant_id is None:
            return Response(
                {
                    'error': _(
                        'Contexte entreprise manquant. Utilisez un JWT avec entreprise_id / membership_id '
                        '(ex. login puis select-context).'
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
        except (TypeError, ValueError):
            year, month = now.year, now.month
        if not (1 <= month <= 12):
            month = now.month
        if year < 1900 or year > 2100:
            year = now.year

        # Base : pÃ©riode + entreprise (via le lot â†’ entrÃ©e) ; succursale si contexte JWT dÃ©fini
        benefices = BeneficeLot.objects.filter(
            date_calcul__year=year,
            date_calcul__month=month,
            lot_entree__entree__entreprise_id=tenant_id,
        )
        if branch_id is not None:
            benefices = benefices.filter(lot_entree__entree__succursale_id=branch_id)

        total_benefice = benefices.aggregate(
            total=Sum('benefice_total')
        )['total'] or Decimal('0.00')

        total_gain = benefices.filter(benefice_total__gte=0).aggregate(
            total=Sum('benefice_total')
        )['total'] or Decimal('0.00')

        # Pertes : on n'inclut PAS les ventes Ã  crÃ©dit (EN_CREDIT) car ce n'est pas une perte dÃ©finitive ;
        # le client doit rembourser ; la perte ne sera Ã©ventuellement considÃ©rÃ©e qu'au remboursement.
        benefices_perte = benefices.filter(benefice_total__lt=0).exclude(
            ligne_sortie__sortie__statut='EN_CREDIT'
        )
        total_perte = abs(benefices_perte.aggregate(
            total=Sum('benefice_total')
        )['total'] or Decimal('0.00'))

        nombre_lots_gagnants = benefices.filter(benefice_total__gte=0).count()
        nombre_lots_perdants = benefices_perte.count()
        nombre_lots_total = benefices.count()

        # Top 10 articles par bÃ©nÃ©fice (agrÃ©gation SQL, pas de boucle Python sur tous les lots)
        par_article_qs = (
            benefices.values(
                'lot_entree__article_id',
                'lot_entree__article__nom_scientifique',
            )
            .annotate(
                benefice_total_agg=Sum('benefice_total'),
                nombre_lots=Count('id'),
            )
            .order_by('-benefice_total_agg')[:10]
        )
        benefices_par_article_list = [
            {
                'article_id': row['lot_entree__article_id'],
                'nom': row['lot_entree__article__nom_scientifique'] or '',
                'benefice_total': str(row['benefice_total_agg'] or Decimal('0')),
                'nombre_lots': row['nombre_lots'],
            }
            for row in par_article_qs
        ]

        nombre_articles_distincts = (
            benefices.values('lot_entree__article_id').distinct().count()
        )

        # Ã‰valuation de la performance (ne jamais qualifier de Â« bonne Â» une pÃ©riode en perte)
        seuil_perte_moderee = Decimal('-500')
        seuil_perte_grave = Decimal('-5000')
        if total_benefice > 0:
            performance = 'EXCELLENTE'
            message = (
                f"PÃ©riode profitable : bÃ©nÃ©fice total {total_benefice}. "
                "Conserver la vigilance sur les marges par article."
            )
        elif total_benefice == 0:
            performance = 'NEUTRE'
            message = (
                "Ã‰quilibre sur la pÃ©riode (bÃ©nÃ©fice net nul). "
                "Surveiller les lots perdants dans le dÃ©tail par article."
            )
        elif total_benefice >= seuil_perte_moderee:
            performance = 'A_SURVEILLER'
            message = (
                f"PÃ©riode en lÃ©gÃ¨re perte (bÃ©nÃ©fice net {total_benefice}). "
                "RÃ©viser les prix de vente, les remises et les articles les plus dÃ©ficitaires."
            )
        elif total_benefice >= seuil_perte_grave:
            performance = 'PREOCCUPANTE'
            message = (
                f"Perte significative sur la pÃ©riode ({total_benefice}). "
                "Analyser le coÃ»t d'achat, la politique tarifaire et les sorties Ã  crÃ©dit."
            )
        else:
            performance = 'CRITIQUE'
            message = (
                f"Perte trÃ¨s importante ({total_benefice}). "
                "Action urgente : revue des marges, du stock et des conditions de vente."
            )
        
        return Response({
            'resume': {
                'benefice_total': str(total_benefice),
                'total_gain': str(total_gain),
                'total_perte': str(total_perte),
                'nombre_lots_gagnants': nombre_lots_gagnants,
                'nombre_lots_perdants': nombre_lots_perdants,
                'nombre_lots_total': nombre_lots_total,
                'taux_reussite': f"{(nombre_lots_gagnants / nombre_lots_total * 100):.5f}%" if nombre_lots_total > 0 else "0%"
            },
            'performance': {
                'statut': performance,
                'message': message,
                'benefice_total': str(total_benefice)
            },
            'benefices_par_article': benefices_par_article_list,
            'details': {
                'entreprise_id': tenant_id,
                'succursale_id': branch_id,
                'nombre_articles': nombre_articles_distincts,
                'date_calcul': timezone.now().isoformat(),
                'mois': month,
                'annee': year,
                'periode': f"{year}-{month:02d}",
            },
        })

    def update(self, request, *args, **kwargs):
        """Mise Ã  jour d'une entrÃ©e avec gestion FIFO complÃ¨te."""
        partial = kwargs.pop('partial', False)
        entree = self.get_object()
        serializer = self.get_serializer(entree, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        data = dict(request.data)
        if 'libele' in serializer.validated_data:
            data['libele'] = serializer.validated_data['libele']
        if 'description' in serializer.validated_data:
            data['description'] = serializer.validated_data['description']

        if not partial and not data.get('lignes'):
            raise serializers.ValidationError({'lignes': "Au moins une ligne d'entrée est requise."})

        from stock.services.entree_update_service import update_entree_from_payload

        with transaction.atomic():
            entree = update_entree_from_payload(entree, data)

        return Response(self.get_serializer(entree).data, status=status.HTTP_200_OK)

    
    def partial_update(self, request, *args, **kwargs):
        """Mise à jour partielle d'une entrée."""
        return self.update(request, *args, **kwargs, partial=True)

    def destroy(self, request, *args, **kwargs):
        entree = self.get_object()
        
        with transaction.atomic():
            for ligne in entree.lignes.all():
                stock_obj, created = Stock.objects.get_or_create(
                    article=ligne.article,
                    defaults={'Qte': 0, 'seuilAlert': 0},
                )
                stock_obj.Qte -= ligne.quantite
                stock_obj.save()
            
            entree.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='bon-pos')
    def bon_entree_pos(self, request, pk=None):
        """Génère un bon d'entrée au format POS."""
        entree = self.get_object()
        
        ent_ctx = self.request.user.get_entreprise(self.request)
        response_data = {
            'numero_entree': entree.pk,
            'date': entree.date_op.strftime('%d/%m/%Y %H:%M'),
            'libele': entree.libele,
            # 'description': entree.description, supprimÃ©
            'entreprise': ent_ctx.nom if ent_ctx else '',
            'lignes': [],
            'total': Decimal('0.00')
        }
        
        total = Decimal('0.00')
        for ligne in entree.lignes.all():
            sous_total = (ligne.prix_unitaire or Decimal('0')) * Decimal(str(ligne.quantite))
            total += sous_total
            
            response_data['lignes'].append({
                'article': _article_display_name(ligne.article),
                'quantite': ligne.quantite,
                'prix_unitaire': ligne.prix_unitaire,
                'sous_total': sous_total,
                'devise': ligne.devise.sigle if ligne.devise else 'N/A'
            })
        
        response_data['total'] = total
        
        return Response(response_data)


class SousTypeArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des sous-types d'articles.
    CRUD complet avec filtrage automatique par type d'article.
    """
    queryset = SousTypeArticle.objects.select_related('type_article').all()
    serializer_class = SousTypeArticleSerializer


    def get_queryset(self):
        """
        Filtre les sous-types d'articles.
        PossibilitÃ© de filtrer par type_article avec ?type_article=<id>
        """
        queryset = super().get_queryset().select_related('type_article')
        
        # Filtrage par type_article si fourni en query param
        type_article_id = self.request.query_params.get('type_article', None)
        if type_article_id:
            queryset = queryset.filter(type_article_id=type_article_id)
        
        return queryset.order_by('-id')

    @action(detail=False, methods=['get'])
    def par_type(self, request):
        """
        Liste les sous-types groupÃ©s par type d'article.
        GET /api/soustypearticles/par_type/
        """
        from collections import defaultdict
        
        sous_types = self.get_queryset()
        grouped = defaultdict(list)
        
        for st in sous_types:
            grouped[st.type_article.libelle].append({
                'id': st.id,
                'libelle': st.libelle,
                'description': st.description
            })
        
        return Response(dict(grouped))


class ClientViewSet(BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour la gestion des clients (filtrÃ© par entreprise/succursale via `ClientEntreprise`)."""

    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_permissions(self):
        # Inscription / crÃ©ation de fiche client sans compte staff (ex. portail public).
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = (
            Client.objects.all()
            .prefetch_related("liens_entreprise__entreprise", "liens_entreprise__succursale")
            .order_by("-date_enregistrement", "-id")
        )
        tenant_id, branch_id = _get_tenant_ids(self.request)
        if tenant_id is not None:
            qs = qs.filter(liens_entreprise__entreprise_id=tenant_id).distinct()
        if branch_id is not None and tenant_id is not None:
            qs = qs.filter(
                Q(liens_entreprise__entreprise_id=tenant_id)
                & (
                    Q(liens_entreprise__succursale_id=branch_id)
                    | Q(liens_entreprise__succursale__isnull=True)
                )
            ).distinct()
        if getattr(self, "action", None) == "list":
            raw = self.request.query_params.get("is_special")
            if raw is not None:
                v = str(raw).strip().lower()
                if v in ("true", "1", "yes", "oui"):
                    qs = qs.filter(liens_entreprise__is_special=True)
                elif v in ("false", "0", "no", "non"):
                    qs = qs.filter(liens_entreprise__is_special=False)
        return qs

    @swagger_auto_schema(
        operation_summary='Recherche de clients (tenant)',
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Texte recherchÃ© (obligatoire) : nom, tÃ©lÃ©phone, adresse, e-mail ou code client. Ex. ?q=dupont',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Nombre max de rÃ©sultats (dÃ©faut 25, max 100).',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description='Pagination (dÃ©calage).',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                'RÃ©sultats + meta ; champ Â« message Â» si aucun client ne correspond.',
                schema=openapi.Schema(type=openapi.TYPE_OBJECT),
            ),
        },
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        from stock.services.client_search import DEFAULT_LIMIT, MAX_LIMIT, search_clients

        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response(
                {'detail': 'Contexte entreprise manquant.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return Response(
                {
                    'detail': _(
                        'Indiquez ce que vous cherchez avec le paramÃ¨tre Â« q Â». '
                        'Exemple : GET /api/clients/search/?q=dupont'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            limit = int(request.query_params.get('limit', DEFAULT_LIMIT))
        except (TypeError, ValueError):
            limit = DEFAULT_LIMIT
        try:
            offset = int(request.query_params.get('offset', 0))
        except (TypeError, ValueError):
            offset = 0
        limit = min(max(1, limit), MAX_LIMIT)
        offset = max(0, offset)

        clients, meta = search_clients(
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            q=q,
            limit=limit,
            offset=offset,
        )
        ser = ClientSearchSerializer(clients, many=True, context={'request': request})
        payload = {'results': ser.data, 'meta': meta}
        if meta.get('total', 0) == 0:
            q_display = (q[:200] + 'â€¦') if len(q) > 200 else q
            if branch_id is not None:
                msg = _(
                    'Aucun client ne correspond Ã  Â« %(term)s Â» pour cette succursale. '
                    'Essayez un autre mot-clÃ© (nom, tÃ©lÃ©phone, adresse, e-mail ou code client), '
                    'vÃ©rifiez lâ€™orthographe ou Ã©largissez la recherche (autre succursale si votre rÃ´le le permet).'
                ) % {'term': q_display}
            else:
                msg = _(
                    'Aucun client ne correspond Ã  Â« %(term)s Â» dans votre entreprise. '
                    'Essayez un autre mot-clÃ© (nom, tÃ©lÃ©phone, adresse, e-mail ou code client) '
                    'ou vÃ©rifiez lâ€™orthographe.'
                ) % {'term': q_display}
            payload['message'] = msg
        return Response(payload)

    @swagger_auto_schema(
        operation_summary="Associer un client existant Ã  lâ€™entreprise (ClientEntreprise)",
        operation_description=(
            "CrÃ©e une association `ClientEntreprise` **sans** recrÃ©er le client.\n\n"
            "- Le client est identifiÃ© par `client_id` **ou** `email`.\n"
            "- Lâ€™entreprise est celle du contexte JWT (`entreprise_id`).\n"
            "- EmpÃªche les doublons : si le lien existe dÃ©jÃ  â†’ 400."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                "client_id": openapi.Schema(type=openapi.TYPE_STRING, description="Ex. `CLI0001` (optionnel si email fourni)."),
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL, description="Email du client (optionnel si client_id fourni)."),
                "succursale_id": openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True, description="Succursale optionnelle."),
                "is_special": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Marquer client spÃ©cial pour ce lien (optionnel)."),
            },
        ),
        responses={201: ClientEntrepriseSerializer, 400: "Erreur de validation"},
        tags=["Clients â€” associations entreprise"],
    )
    @action(detail=False, methods=["post"], url_path="associate-entreprise")
    def associate_entreprise(self, request):
        tenant_id, _ = _get_tenant_ids(request)
        if tenant_id is None:
            return Response({"detail": _("Contexte entreprise manquant.")}, status=status.HTTP_403_FORBIDDEN)

        client_id = (request.data.get("client_id") or "").strip()
        email = (request.data.get("email") or "").strip()
        if not client_id and not email:
            return Response(
                {"detail": _("Indiquez Â« client_id Â» ou Â« email Â».")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Client.objects.all()
        if client_id:
            qs = qs.filter(pk=client_id)
        else:
            qs = qs.filter(email__iexact=email)
        client = qs.first()
        if not client:
            return Response({"detail": _("Client introuvable.")}, status=status.HTTP_404_NOT_FOUND)

        if ClientEntreprise.objects.filter(client=client, entreprise_id=tenant_id).exists():
            return Response({"detail": _("Ce client est dÃ©jÃ  associÃ© Ã  cette entreprise.")}, status=status.HTTP_400_BAD_REQUEST)

        succursale_id = request.data.get("succursale_id", None)
        if succursale_id is not None and str(succursale_id).strip() != "":
            try:
                succursale_id = int(succursale_id)
            except (TypeError, ValueError):
                return Response({"detail": _("Le champ Â« succursale_id Â» doit Ãªtre un entier.")}, status=status.HTTP_400_BAD_REQUEST)
            if not Succursale.objects.filter(pk=succursale_id, entreprise_id=tenant_id).exists():
                return Response({"detail": _("Succursale invalide pour cette entreprise.")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            succursale_id = None

        is_special = request.data.get("is_special", False)
        is_special = bool(is_special) if isinstance(is_special, bool) else str(is_special).strip().lower() in ("true", "1", "yes", "oui")

        link = ClientEntreprise.objects.create(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=succursale_id,
            is_special=is_special,
        )
        out = ClientEntrepriseSerializer(link, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)

    def _client_period_or_400(self, request):
        try:
            return parse_period_from_request(request), None
        except ValueError as exc:
            return None, Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='dashboard')
    def dashboard(self, request, pk=None):
        client = self.get_object()
        period, error_response = self._client_period_or_400(request)
        if error_response is not None:
            return error_response
        tenant_id, branch_id = _get_tenant_ids(request)
        payload = build_client_dashboard(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        return Response(payload)

    @action(detail=True, methods=['get'], url_path='statistiques')
    def statistiques(self, request, pk=None):
        client = self.get_object()
        period, error_response = self._client_period_or_400(request)
        if error_response is not None:
            return error_response
        tenant_id, branch_id = _get_tenant_ids(request)
        payload = build_client_statistics(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        return Response(payload)

    @action(detail=True, methods=['get'], url_path='solde')
    def solde(self, request, pk=None):
        client = self.get_object()
        period, error_response = self._client_period_or_400(request)
        if error_response is not None:
            return error_response
        tenant_id, branch_id = _get_tenant_ids(request)
        payload = build_client_balance(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        return Response(payload)

    @action(detail=True, methods=['get'], url_path='ventes')
    def ventes(self, request, pk=None):
        client = self.get_object()
        period, error_response = self._client_period_or_400(request)
        if error_response is not None:
            return error_response
        tenant_id, branch_id = _get_tenant_ids(request)
        ventes = build_client_sales(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        page = self.paginate_queryset(ventes)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(ventes)

    @action(detail=True, methods=['get'], url_path='achats')
    def achats(self, request, pk=None):
        """Historique des achats article par article (lignes de sortie), paginé."""
        from order.branch_scope import branch_q_for_staff_sortie
        from order.services.client_portal_achats import (
            achats_lignes_qs,
            parse_achats_filters,
            serialize_achat_ligne,
        )

        client = self.get_object()
        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response({'detail': 'Contexte entreprise manquant.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            filters = parse_achats_filters(request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        qs = achats_lignes_qs(
            client=client,
            entreprise_id=tenant_id,
            branch_q=branch_q_for_staff_sortie(branch_id),
            filters=filters,
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response([serialize_achat_ligne(l) for l in page])
        return Response([serialize_achat_ligne(l) for l in qs])

    @action(detail=True, methods=['get'], url_path='achats/articles')
    def achats_articles(self, request, pk=None):
        """Synthèse des achats par article (agrégation SQL)."""
        from order.branch_scope import branch_q_for_staff_sortie
        from order.services.client_portal_achats import achats_par_article, parse_achats_filters

        client = self.get_object()
        tenant_id, branch_id = _get_tenant_ids(request)
        if tenant_id is None:
            return Response({'detail': 'Contexte entreprise manquant.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            filters = parse_achats_filters(request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            limit = min(max(1, int(request.query_params.get('limit', 100))), 500)
        except (TypeError, ValueError):
            limit = 100
        data = achats_par_article(
            client=client,
            entreprise_id=tenant_id,
            branch_q=branch_q_for_staff_sortie(branch_id),
            filters=filters,
            limit=limit,
        )
        return Response({'count': len(data), 'results': data})

    @action(detail=True, methods=['get'], url_path='mouvements')
    def mouvements(self, request, pk=None):
        client = self.get_object()
        period, error_response = self._client_period_or_400(request)
        if error_response is not None:
            return error_response
        tenant_id, branch_id = _get_tenant_ids(request)
        movements = build_client_movements(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        page = self.paginate_queryset(movements)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(movements)

    @action(detail=True, methods=['get'])
    def dettes(self, request, pk=None):
        """
        Liste toutes les dettes d'un client spÃ©cifique (paginated).
        GET /api/clients/{id}/dettes/
        """
        client = self.get_object()
        tenant_id, branch_id = _get_tenant_ids(request)
        dettes = DetteClient.objects.filter(client=client).select_related(
            'client', 'devise', 'sortie'
        )
        if tenant_id is not None:
            dettes = dettes.filter(entreprise_id=tenant_id)
        if branch_id is not None:
            dettes = dettes.filter(succursale_id=branch_id)
        dettes = dettes.order_by('-date_creation', '-id')
        page = self.paginate_queryset(dettes)
        ctx = {'request': request, 'include_paiements': False}
        if page is not None:
            serializer = DetteClientSerializer(page, many=True, context=ctx)
            return self.get_paginated_response(serializer.data)
        serializer = DetteClientSerializer(dettes, many=True, context=ctx)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def total_dettes(self, request, pk=None):
        """
        Calcule le total des dettes d'un client.
        GET /api/clients/{id}/total_dettes/
        """
        from stock.services.client_lifecycle import build_client_balance, parse_period_from_request

        client = self.get_object()
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            return Response({'detail': 'Contexte entreprise manquant.'}, status=403)
        try:
            period = parse_period_from_request(request)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        balance = build_client_balance(
            client=client,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            period=period,
        )
        dettes = DetteClient.objects.filter(client=client, entreprise_id=tenant_id)
        if branch_id is not None:
            dettes = dettes.filter(succursale_id=branch_id)
        return Response({
            'client_id': client.id,
            'client_nom': client.nom,
            'nombre_dettes': dettes.count(),
            'montant_total_dettes': balance['solde']['total_du'],
            'montant_total_paye': balance['solde']['total_paye'],
            'solde_restant_total': balance['solde']['solde_restant'],
            'dettes_en_cours': dettes.filter(statut='EN_COURS').count(),
            'dettes_payees': dettes.filter(statut='PAYEE').count(),
            'dettes_en_retard': dettes.filter(statut='RETARD').count(),
            'totaux_par_devise': balance['totaux_par_devise'],
        })


class ClientEntrepriseViewSet(BusinessPermissionMixin, viewsets.ReadOnlyModelViewSet):
    """Lecture des associations `Client â†” Entreprise` (multi-tenant, succursale optionnelle)."""

    queryset = ClientEntreprise.objects.select_related("client", "entreprise", "succursale").all()
    serializer_class = ClientEntrepriseSerializer

    @swagger_auto_schema(
        operation_summary="Liste des associations client â†” entreprise",
        operation_description=(
            "Liste paginÃ©e des liens `ClientEntreprise`.\n\n"
            "- **PÃ©rimÃ¨tre** : entreprise du JWT (et succursale si le contexte lâ€™impose).\n"
            "- **Filtres** : `client_id`, `succursale_id`, `is_special`.\n"
            "- **Pagination** : `page`, `page_size`."
        ),
        manual_parameters=[
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description="NumÃ©ro de page."),
            openapi.Parameter(
                "page_size",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Taille de page (dÃ©faut 25, max 200).",
            ),
            openapi.Parameter(
                "client_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                description="Filtrer par identifiant client (ex. `CLI0001`).",
            ),
            openapi.Parameter(
                "succursale_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="Filtrer par succursale (id).",
            ),
            openapi.Parameter(
                "is_special",
                openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                description="Filtrer les liens marquÃ©s client spÃ©cial (`true` / `false`).",
            ),
        ],
        tags=["Clients â€” associations entreprise"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset().order_by("-id")

        tenant_id, branch_id = _get_tenant_ids(self.request)
        if tenant_id is not None:
            qs = qs.filter(entreprise_id=tenant_id)
        if branch_id is not None:
            # Inclure aussi les liens â€œsans succursaleâ€ (historique / catalogue global)
            qs = qs.filter(Q(succursale_id=branch_id) | Q(succursale__isnull=True))

        p = self.request.query_params
        client_id = p.get("client_id")
        if client_id:
            qs = qs.filter(client_id=client_id)

        if p.get("is_special") is not None:
            v = str(p.get("is_special")).strip().lower()
            if v in ("true", "1", "yes", "oui"):
                qs = qs.filter(is_special=True)
            elif v in ("false", "0", "no", "non"):
                qs = qs.filter(is_special=False)

        succursale_id = p.get("succursale_id")
        if succursale_id:
            try:
                sid = int(succursale_id)
                qs = qs.filter(succursale_id=sid)
            except (TypeError, ValueError):
                pass

        return qs


class DetteClientViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour la gestion des dettes clients (filtrÃ© par entreprise/succursale)."""
    queryset = DetteClient.objects.select_related('client', 'devise', 'sortie').all()
    serializer_class = DetteClientSerializer

    def get_queryset(self):
        return super().get_queryset().select_related('client', 'devise', 'sortie').order_by('-date_creation', '-id')

    def _assert_correction_permission(self, request):
        if not (request.user.is_superadmin() or request.user.is_admin(request)):
            raise PermissionDenied(
                _("Accès réservé aux administrateurs pour les corrections de dettes.")
            )

    def _log_correction(self, *, request, dette, action: str, reason: str, payload: dict):
        try:
            LogEntry.objects.log_action(
                user_id=request.user.pk if request.user and request.user.is_authenticated else None,
                content_type_id=ContentType.objects.get_for_model(DetteClient).pk,
                object_id=str(dette.pk),
                object_repr=f"DetteClient#{dette.pk} client={dette.client_id}",
                action_flag=action,
                change_message=json.dumps({
                    'module': 'dette_correction',
                    'reason': reason or '',
                    **payload,
                }, ensure_ascii=False),
            )
        except Exception:
            logger.exception("Journal correction dette: échec log_action (dette_id=%s)", getattr(dette, 'pk', None))

    def _delete_dette_and_related_payments(self, *, request, dette, reason: str):
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        paiements_qs = MouvementCaisse.objects.filter(
            content_type=ct_dette,
            object_id=dette.pk,
        )
        paiements_count = paiements_qs.count()
        paiements_total = paiements_qs.aggregate(s=Sum('montant'))['s'] or Decimal('0')
        paiement_ids = list(paiements_qs.values_list('id', flat=True))

        dette_snapshot = {
            'dette_id': dette.pk,
            'client_id': dette.client_id,
            'sortie_id': dette.sortie_id,
            'montant_total': str(dette.montant_total),
            'montant_paye': str(dette.montant_paye),
            'solde_restant': str(dette.solde_restant),
            'paiements_count': paiements_count,
            'paiements_total': str(paiements_total),
            'paiement_ids': paiement_ids,
        }
        paiements_qs.delete()
        dette.delete()
        self._log_correction(
            request=request,
            dette=dette,
            action=DELETION,
            reason=reason,
            payload=dette_snapshot,
        )
        return dette_snapshot

    def perform_create(self, serializer):
        sortie = serializer.validated_data.get('sortie')
        if sortie and sortie.statut != 'EN_CREDIT':
            raise serializers.ValidationError({
                'sortie': f"Impossible de crÃ©er une dette pour cette sortie. "
                         f"La sortie #{sortie.pk} (Client: {sortie.client.nom if sortie.client else 'Anonyme'}) a le statut '{sortie.statut}'. "
                         f"Seules les sorties avec le statut 'EN_CREDIT' peuvent gÃ©nÃ©rer une dette."
            })
        if sortie and DetteClient.objects.filter(sortie=sortie).exists():
            raise serializers.ValidationError({
                'sortie': f"Une dette existe dÃ©jÃ  pour la sortie #{sortie.pk}."
            })
        date_echeance = serializer.validated_data.get('date_echeance') or (timezone.now().date() + timezone.timedelta(days=30))
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        devise_dette = serializer.validated_data.get('devise') or getattr(sortie, 'devise', None) or _get_principal_devise(tenant_id)
        if not devise_dette:
            raise serializers.ValidationError({'devise_id': _('Devise requise pour créer une dette.')})
        snapshot = build_conversion_snapshot(
            entreprise_id=tenant_id,
            amount=serializer.validated_data.get('montant_total'),
            devise_source=devise_dette,
        )
        serializer.save(
            date_echeance=date_echeance,
            entreprise_id=tenant_id,
            succursale_id=branch_id,
            devise=devise_dette,
            devise_reference=snapshot['devise_reference'],
            taux_change=snapshot['taux_change'],
            montant_reference=snapshot['montant_reference'],
        )

    @action(detail=False, methods=['get'])
    def en_retard(self, request):
        """
        Liste toutes les dettes en retard (paginated).
        GET /api/dettes/en_retard/
        """
        dettes = self.get_queryset().filter(statut='RETARD')
        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def en_cours(self, request):
        """
        Liste toutes les dettes en cours (paginated).
        GET /api/dettes/en_cours/
        """
        dettes = self.get_queryset().filter(statut='EN_COURS')
        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def payees(self, request):
        """
        Liste toutes les dettes payÃ©es (paginated).
        GET /api/dettes/payees/
        """
        dettes = self.get_queryset().filter(statut='PAYEE')
        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(dettes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='paiements')
    def paiements(self, request, pk=None):
        """
        Liste tous les mouvements de paiement liÃ©s Ã  cette dette (paginated).
        GET /api/dettes/{id}/paiements/
        """
        dette = self.get_object()
        paiements_qs = (
            dette._paiements_mouvements_qs()
            .select_related('devise', 'utilisateur')
            .prefetch_related('details__type_caisse')
            .order_by('-date', '-id')
        )
        page = self.paginate_queryset(paiements_qs)
        if page is not None:
            serializer = PaiementDetteReadSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = PaiementDetteReadSerializer(paiements_qs, many=True, context={'request': request})
        return Response(serializer.data)


    def destroy(self, request, *args, **kwargs):
        self._assert_correction_permission(request)
        raw_confirm = request.data.get('confirm', request.query_params.get('confirm', False))
        raw_reason = request.data.get('reason', request.query_params.get('reason', ''))
        confirm = raw_confirm if isinstance(raw_confirm, bool) else str(raw_confirm).strip().lower() in ('1', 'true', 'yes', 'oui')
        ser = DetteCorrectionDeleteSerializer(data={'confirm': confirm, 'reason': raw_reason})
        ser.is_valid(raise_exception=True)
        reason = (ser.validated_data.get('reason') or '').strip()
        dette = self.get_object()
        with transaction.atomic():
            snapshot = self._delete_dette_and_related_payments(
                request=request,
                dette=dette,
                reason=reason,
            )
        return Response(
            {
                'success': True,
                'message': _("Dette supprimée avec tous les paiements liés."),
                **snapshot,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='cleanup-client')
    def cleanup_client(self, request):
        self._assert_correction_permission(request)
        serializer = DetteClientCleanupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.validated_data['client']
        reason = (serializer.validated_data.get('reason') or '').strip()

        dettes = self.get_queryset().filter(client=client).order_by('id')
        if not dettes.exists():
            return Response(
                {'detail': _("Aucune dette trouvée pour ce client dans ce périmètre.")},
                status=status.HTTP_404_NOT_FOUND,
            )

        deleted = []
        with transaction.atomic():
            for dette in dettes:
                deleted.append(
                    self._delete_dette_and_related_payments(
                        request=request,
                        dette=dette,
                        reason=reason,
                    )
                )

        total_montant = sum(Decimal(x['montant_total']) for x in deleted)
        total_paiements = sum(Decimal(x['paiements_total']) for x in deleted)
        total_paiements_count = sum(int(x['paiements_count']) for x in deleted)
        return Response(
            {
                'success': True,
                'message': _("Nettoyage des dettes du client terminé."),
                'client_id': client.id,
                'client_nom': client.nom,
                'dettes_supprimees': len(deleted),
                'montant_total_dettes_supprimees': str(total_montant),
                'paiements_supprimes_count': total_paiements_count,
                'paiements_supprimes_total': str(total_paiements),
                'details': deleted,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='manual-create')
    def manual_create(self, request):
        self._assert_correction_permission(request)
        serializer = DetteManuelleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v = serializer.validated_data
        client = v['client']
        montant_total = v['montant_total']
        montant_deja_paye = v.get('montant_deja_paye') or Decimal('0')
        commentaire = (v.get('commentaire') or '').strip()
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            return Response({'detail': _('Contexte entreprise manquant.')}, status=status.HTTP_403_FORBIDDEN)

        devise = v.get('devise') or _get_principal_devise(tenant_id)
        if not devise:
            return Response({'detail': _('Aucune devise disponible pour créer cette dette.')}, status=status.HTTP_400_BAD_REQUEST)

        date_dette = v.get('date_dette')
        date_echeance = v.get('date_echeance')
        statut = 'PAYEE' if montant_deja_paye == montant_total else 'EN_COURS'
        sortie_statut = 'PAYEE' if statut == 'PAYEE' else 'EN_CREDIT'

        with transaction.atomic():
            sortie = Sortie.objects.create(
                motif=commentaire or _('Dette manuelle de correction'),
                client=client,
                devise=devise,
                statut=sortie_statut,
                entreprise_id=tenant_id,
                succursale_id=branch_id,
            )
            snapshot = build_conversion_snapshot(
                entreprise_id=tenant_id,
                amount=montant_total,
                devise_source=devise,
            )
            dette = DetteClient.objects.create(
                client=client,
                sortie=sortie,
                montant_total=montant_total,
                devise=devise,
                devise_reference=snapshot['devise_reference'],
                taux_change=snapshot['taux_change'],
                montant_reference=snapshot['montant_reference'],
                date_echeance=date_echeance,
                statut=statut,
                commentaire=commentaire or _('Création manuelle pour correction historique.'),
                entreprise_id=tenant_id,
                succursale_id=branch_id,
            )
            if date_dette:
                DetteClient.objects.filter(pk=dette.pk).update(date_creation=date_dette)
                dette.refresh_from_db()

            paiement_reprise = None
            if montant_deja_paye > 0:
                paiement_reprise = creer_mouvement_caisse(
                    montant=montant_deja_paye,
                    devise=devise,
                    type_mouvement='ENTREE',
                    entreprise_id=tenant_id,
                    succursale_id=branch_id,
                    content_object=dette,
                    utilisateur=request.user if request.user.is_authenticated else None,
                    reference_piece=f'REG-DETTE-{dette.pk}',
                    motif=_('Régularisation historique de dette'),
                    moyen='REGULARISATION',
                    categorie='PAIEMENT_DETTE',
                    skip_session_check=True,
                    date_operation=date_dette,
                )

            self._log_correction(
                request=request,
                dette=dette,
                action=ADDITION,
                reason=commentaire,
                payload={
                    'manual_create': True,
                    'sortie_id': sortie.pk,
                    'montant_total': str(montant_total),
                    'montant_deja_paye': str(montant_deja_paye),
                    'solde_restant': str(dette.solde_restant),
                    'date_dette': date_dette.isoformat() if date_dette else None,
                    'date_echeance': date_echeance.isoformat() if date_echeance else None,
                    'paiement_reprise_id': paiement_reprise.pk if paiement_reprise else None,
                },
            )

        data = DetteClientSerializer(dette, context={'request': request}).data
        return Response(
            {
                'success': True,
                'message': _('Dette manuelle créée avec succès.'),
                'dette': data,
                'montant_deja_paye_enregistre': str(montant_deja_paye),
                'solde_restant': str(dette.solde_restant),
            },
            status=status.HTTP_201_CREATED,
        )

