from rest_framework.response import Response
from django.db.models import Sum

# Liste des bénéfices par vente

from django.shortcuts import render
from rest_framework import viewsets, status, serializers, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import (
    Entreprise, Succursale, Devise, TypeArticle, SousTypeArticle, Unite, Article, Entree, LigneEntree, Stock, Sortie, LigneSortie, LigneSortieLot, BeneficeLot, MouvementCaisse, Client, DetteClient, TypeCaisse,
)
from stock.services.caisse import creer_mouvement_caisse, mouvement_moyen_affiche
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids
from django.db import transaction, models
from django.db.models import Prefetch, Sum
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import PermissionDenied, NotFound
from django.utils.translation import gettext as _, pgettext
from .serializers import *
from users.permissions import IsSuperAdmin, IsAdmin, IsSuperAdminOrAdmin, IsSuperAdminOrReadOnlyAdmin, IsOwnerOrSuperAdmin, IsAdminOrUser
from users.serializers import UserSerializer
from stock.permissions import EntreprisePermission, IsAdminOrUser as StockIsAdminOrUser


class BusinessPermissionMixin:
    """Accès réservé aux Admin et User (Agent). SuperAdmin n'a pas accès aux données métier."""
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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from decimal import Decimal
import qrcode
from datetime import datetime
from rest_framework.decorators import action, api_view, permission_classes
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

# Configuration du logger pour tracer les suppressions automatiques d'articles
logger = logging.getLogger(__name__)


class EnterpriseFilterMixin:
    """Mixin pour filtrer automatiquement par entreprise selon le rôle de l'utilisateur"""
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset


class TenantFilterMixin:
    """
    Mixin multi-tenant : filtre le queryset par entreprise (et succursale si connue).
    - Si le modèle a entreprise_id : filtre par request.tenant_id ; si branch_id est défini (JWT ou défaut membership), filtre aussi par succursale.
    - Agent sans succursale : filtre uniquement par entreprise (succursale_id laissée libre côté données).
    - Si tenant_lookup est défini (ex. 'entree__entreprise_id') : filtre par ce lookup.
    """
    tenant_lookup = None  # ex. 'entree__entreprise_id' pour LigneEntree

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.none() if (self.tenant_lookup or hasattr(queryset.model, 'entreprise_id')) else queryset
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
    """Return amount formatted with 2 decimals and the currency symbol.
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
        return f"{Decimal(amount):.2f} {sym}" if sym else f"{Decimal(amount):.2f}"
    except Exception:
        return str(amount)


def _article_display_name(article):
    """Retourne un nom lisible pour un article (commercial si présent, sinon scientifique)."""
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


def _get_principal_devise():
    return Devise.objects.filter(est_principal=True).first()


def _get_latest_rate(source_dev: Devise, target_dev: Devise):
    """Return Decimal rate to convert amount from source_dev to target_dev or None if not found.
   
    """
    if not source_dev or not target_dev:
        return None
    if source_dev.id == target_dev.id:
        return Decimal('1')



def _convert_amount(amount: Decimal, source_dev: Devise, target_dev: Devise, entreprise):
    """Attempt conversion; return Decimal or None when rate missing."""
    if amount is None:
        return None
    if source_dev is None and target_dev is None:
        return amount
    # if source missing assume target (no conversion)
    if source_dev is None or target_dev is None:
        return amount
    rate = _get_latest_rate(source_dev, target_dev)
    if rate is None:
        return None
    try:
        return (Decimal(amount) * rate).quantize(Decimal('0.01'))
    except Exception:
        return None




class RapportViewSet(viewsets.ViewSet):
    def get_permissions(self):
        return [StockIsAdminOrUser()]

    # NOTE: La fonction fiche_stock_article_pdf a été déplacée vers rapports/views.py
    # pour une meilleure organisation. Utilisez maintenant:
    # GET /api/rapports/{article_id}/fiche-stock/
   
    # NOTE: Les actions facture_pos_pdf et bons POS ont été déplacées vers
    # SortieViewSet et EntreeViewSet pour éviter toute ambiguïté de routes.

    @action(detail=False, methods=['get'], url_path='journal')
    def journal_pdf(self, request):
        """
        Génère le journal complet de toutes les opérations (PDF).
        Inclut : approvisionnements (entrées), ventes (sorties), mouvements de caisse, paiements de dettes.
        Filtres : month (1-12), year (ex: 2026). Par défaut = mois et année en cours.
        Ou date_min / date_max (YYYY-MM-DD) pour une plage personnalisée.
        """
        user = request.user
        principal = _get_principal_devise()
        now = timezone.now()

        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            return Response({'error': 'Contexte entreprise manquant.'}, status=400)

        # Filtrage : month/year (défaut = mois et année en cours), ou date_min/date_max pour plage personnalisée
        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')
        date_min = request.query_params.get('date_min')
        date_max = request.query_params.get('date_max')

        use_month_year = (month_param is not None or year_param is not None) or not (date_min or date_max)
        if use_month_year:
            try:
                year = int(year_param) if year_param else now.year
                month = int(month_param) if month_param else now.month
            except (TypeError, ValueError):
                year, month = now.year, now.month
            if not (1 <= month <= 12):
                month = now.month
            if year < 1900 or year > 2100:
                year = now.year
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            date_min = f"{year}-{month:02d}-01"
            date_max = f"{year}-{month:02d}-{last_day}"
            periode_txt = f"{month:02d}/{year}"
        else:
            periode_txt = _("Du %(debut)s au %(fin)s") % {'debut': date_min or '...', 'fin': date_max or '...'}

        # 1) Entrées (approvisionnements)
        qs_entrees = Entree.objects.filter(entreprise_id=tenant_id)
        if branch_id is not None:
            qs_entrees = qs_entrees.filter(succursale_id=branch_id)
        qs_entrees = qs_entrees.prefetch_related('lignes', 'lignes__article', 'lignes__devise')
        if date_min:
            qs_entrees = qs_entrees.filter(date_op__date__gte=date_min)
        if date_max:
            qs_entrees = qs_entrees.filter(date_op__date__lte=date_max)

        # 2) Sorties (ventes)
        qs_sorties = Sortie.objects.filter(entreprise_id=tenant_id)
        if branch_id is not None:
            qs_sorties = qs_sorties.filter(succursale_id=branch_id)
        qs_sorties = qs_sorties.prefetch_related('lignes', 'lignes__article', 'lignes__devise', 'client')
        if date_min:
            qs_sorties = qs_sorties.filter(date_creation__date__gte=date_min)
        if date_max:
            qs_sorties = qs_sorties.filter(date_creation__date__lte=date_max)

        # 3) Mouvements de caisse
        qs_caisse = MouvementCaisse.objects.filter(entreprise_id=tenant_id).select_related('devise', 'sortie', 'entree')
        if branch_id is not None:
            qs_caisse = qs_caisse.filter(succursale_id=branch_id)
        if date_min:
            qs_caisse = qs_caisse.filter(date__date__gte=date_min)
        if date_max:
            qs_caisse = qs_caisse.filter(date__date__lte=date_max)

        # 4) Paiements de dettes (liés à DetteClient)
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        qs_paiements = MouvementCaisse.objects.filter(
            entreprise_id=tenant_id,
            content_type=ct_dette,
            type='ENTREE',
        ).select_related('devise', 'content_type')
        if branch_id is not None:
            qs_paiements = qs_paiements.filter(succursale_id=branch_id)
        if date_min:
            qs_paiements = qs_paiements.filter(date__date__gte=date_min)
        if date_max:
            qs_paiements = qs_paiements.filter(date__date__lte=date_max)

        # Construire la liste unifiée d'événements (date, type, désignation, montant_texte, ref)
        events = []

        for e in qs_entrees:
            total_par_devise = {}
            for lig in e.lignes.all():
                dev = lig.devise or principal
                sigle = dev.sigle if dev else 'N/A'
                total_par_devise[sigle] = total_par_devise.get(sigle, Decimal('0')) + lig.quantite * lig.prix_unitaire
            montant_str = ', '.join(f"{v:.2f} {s}" for s, v in total_par_devise.items()) if total_par_devise else '-'
            events.append({
                'date': e.date_op,
                'type': 'APPROVISIONNEMENT',
                'type_display': _('Approvisionnement'),
                'designation': (e.libele or _('Entrée'))[:80],
                'montant_texte': montant_str,
                'ref': f'Entrée#{e.id}',
            })

        for s in qs_sorties:
            total_par_devise = {}
            for lig in s.lignes.all():
                dev = lig.devise or principal
                sigle = dev.sigle if dev else 'N/A'
                total_par_devise[sigle] = total_par_devise.get(sigle, Decimal('0')) + lig.quantite * lig.prix_unitaire
            montant_str = ', '.join(f"{v:.2f} {s}" for s, v in total_par_devise.items()) if total_par_devise else '-'
            client_nom = (s.client.nom if s.client else 'Anonyme')[:40]
            events.append({
                'date': s.date_creation,
                'type': 'VENTE',
                'type_display': _('Vente'),
                'designation': f"{(s.motif or _('Vente'))[:50]} - {_('Client')}: {client_nom}",
                'montant_texte': montant_str,
                'ref': f'Sortie#{s.id}',
            })

        for mv in qs_caisse:
            caisse_type_label = _('Caisse Entrée') if mv.type == 'ENTREE' else _('Caisse Sortie')
            events.append({
                'date': mv.date,
                'type': f'CAISSE_{mv.type}',
                'type_display': caisse_type_label,
                'designation': (mv.motif_affiche() or '')[:80].replace('\n', ' '),
                'montant_texte': _format_amount(mv.montant, mv.devise),
                'ref': mv.reference_piece or f"MC#{mv.id}",
            })

        from django.contrib.contenttypes.models import ContentType as CT
        ct_dette = CT.objects.get_for_model(DetteClient)
        for p in qs_paiements:
            dette = None
            if p.content_type_id == ct_dette.id and p.object_id:
                dette = DetteClient.objects.filter(pk=p.object_id).select_related('client').first()
            client_nom = (dette.client.nom if dette and dette.client else '')[:40]
            events.append({
                'date': p.date,
                'type': 'PAIEMENT_DETTE',
                'type_display': _('Paiement dette'),
                'designation': f"{_('Paiement dette')} - {client_nom}".strip()[:80],
                'montant_texte': _format_amount(p.montant, p.devise),
                'ref': p.reference_piece or f"Paiement#{p.id}",
            })

        # Tri chronologique
        events.sort(key=lambda x: x['date'])

        # Entreprise pour l'en-tête
        entreprise = user.get_entreprise(request) or Entreprise.objects.first()

        # PDF
        buffer = io.BytesIO()
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator

        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.fontSize = 9
        small = ParagraphStyle('Small', parent=normal, fontSize=8)
        title_style = ParagraphStyle('Title', parent=styles['Heading2'], alignment=1, fontSize=12, spaceAfter=2)
        header_small = ParagraphStyle('HeaderSmall', parent=normal, fontSize=8, alignment=1)

        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=14, rightMargin=14, topMargin=22, bottomMargin=18)
        elements = []

        # En-tête simplifié (nom, logo, slogan, téléphone uniquement)
        entete = get_entete_entreprise(entreprise)
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete))

        periode_label = _("Période")
        elements.append(Paragraph(f"<b>{_('JOURNAL COMPLET DES OPÉRATIONS')}</b> - {periode_label}: {periode_txt}", normal))
        gen_par = _("Généré le %(date)s par %(user)s") % {
            'date': timezone.now().strftime('%d/%m/%Y à %H:%M'),
            'user': getattr(user, 'username', _('Système'))
        }
        elements.append(Paragraph(gen_par, header_small))
        elements.append(Spacer(1, 6))

        data = [[
            Paragraph(f'<b>{_("Date/Heure")}</b>', small),
            Paragraph(f'<b>{_("Type")}</b>', small),
            Paragraph(f'<b>{_("Désignation / Motif")}</b>', small),
            Paragraph(f'<b>{_("Montant")}</b>', small),
            Paragraph(f'<b>{_("Réf.")}</b>', small),
        ]]
        for ev in events:
            data.append([
                Paragraph(ev['date'].strftime('%d/%m/%Y %H:%M'), small),
                Paragraph(ev.get('type_display', ev['type'].replace('_', ' ')), small),
                Paragraph(ev['designation'].replace('<', ' '), small),
                Paragraph(ev['montant_texte'], small),
                Paragraph(str(ev['ref'])[:30], small),
            ])

        if len(data) == 1:
            elements.append(Paragraph(_('Aucune opération pour la période.'), normal))
        else:
            table = Table(data, repeatRows=1, colWidths=[72, 58, 200, 88, 72])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)

        elements.append(Spacer(1, 8))
        total_ops = _("Total : %(count)s opération(s)") % {'count': len(events)}
        elements.append(Paragraph(f"<i>{total_ops}</i>", small))
        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': 'inline; filename="journal_complet.pdf"'})

    # Les actions de bons POS supprimées ici.

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
        # Utilisateur sans entreprise : ne voit aucune entreprise tant qu'il n'en a pas créée
        return Entreprise.objects.none()

    def perform_create(self, serializer):
        from users.models import Membership
        user = self.request.user
        if user.is_superadmin():
            raise PermissionDenied(_("Le super administrateur ne peut pas créer d'entreprise. Utilisez un compte Admin."))
        # Tout utilisateur authentifié non superadmin peut créer une entreprise.
        # Il devient automatiquement admin de cette entreprise via Membership.
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
            serializer.save()

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
        responses={200: openapi.Response('Détail entreprise ou message'), 400: 'Aucune entreprise'},
    )
    @action(detail=False, methods=['get'])
    def my_entreprise(self, request):
        """Récupérer l'entreprise de l'utilisateur connecté (admin ou agent, lecture)."""
        eid = getattr(request, 'tenant_id', None) or request.user.get_entreprise_id(request)
        ent = Entreprise.objects.filter(id=eid).first() if eid else request.user.get_entreprise(request)
        if (request.user.is_admin(request) or request.user.is_agent(request)) and ent:
            serializer = self.get_serializer(ent)
            return Response(serializer.data)
        if request.user.is_superadmin():
            return Response({'message': _("Superadmin n'appartient à aucune entreprise")})
        return Response({'error': _("Aucune entreprise associée")}, status=400)

    @swagger_auto_schema(
        operation_summary="Utilisateurs d'une entreprise",
        operation_description="Liste paginée des utilisateurs ayant un membership actif sur cette entreprise (`pk` = id entreprise).",
        responses={200: openapi.Response('Liste UserSerializer ou réponse paginée')},
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


@swagger_auto_schema(tags=['Succursales'])
class SuccursaleViewSet(BusinessPermissionMixin, viewsets.ModelViewSet):
    """
    Succursales (branches) de l'entreprise courante.
    - Liste : filtrée par entreprise (tenant_id ou premier membership).
    - Create/Update/Delete : réservé à l'Admin de l'entreprise.
    Utilisé pour le flow login (choix de la succursale si has_branches).
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
        # Agent : même visibilité que l'admin sur la liste (entreprise) ; succursale JWT sert au filtrage métier ailleurs.
        if user.is_agent(self.request):
            return Succursale.objects.filter(entreprise_id=eid, is_active=True).order_by('nom', 'id')
        # Admin : peut voir toutes les succursales de son entreprise.
        return Succursale.objects.filter(entreprise_id=eid, is_active=True).order_by('nom', 'id')

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_admin(self.request):
            raise PermissionDenied(_("Seul l'administrateur de l'entreprise peut créer une succursale."))
        eid = getattr(self.request, 'tenant_id', None) or user.get_entreprise_id(self.request)
        if not eid:
            raise PermissionDenied(_("Aucune entreprise sélectionnée."))
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
    """ViewSet pour gérer les sorties de stock (filtré par entreprise/succursale)."""
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
        default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
        with transaction.atomic():
            # Récupérer le client si fourni
            client = serializer.validated_data.get('client')
            
            lib = serializer.validated_data.get('motif', '')
            sortie = Sortie.objects.create(
                motif=lib,
                statut=serializer.validated_data.get('statut', 'PAYEE'),
                client=client,
                entreprise_id=tenant_id,
                succursale_id=branch_id
            )
            total = Decimal('0.00')
            devise_mouvement = None
            # Dictionnaire pour calculer les totaux par devise
            totaux_par_devise = {}
            
            for ligne in lignes_data:
                # Support pour les deux formats : article_id ou article
                article_id = ligne.get('article_id') or ligne.get('article')
                
                # Vérification que l'article existe
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                except Article.DoesNotExist:
                    raise serializers.ValidationError({
                        'article': f"Article avec ID {article_id} non trouvé dans votre entreprise. "
                                  f"Vérifiez que l'article existe et vous appartient."
                    })
                
                # Conversion sécurisée des données
                try:
                    qte = int(ligne.get('quantite', 0))
                except (ValueError, TypeError):
                    raise serializers.ValidationError({
                        'quantite': 'La quantité doit être un nombre entier valide.'
                    })
                
                # Prix réellement encaissé (peut être fourni manuellement pour promotions, réductions, etc.)
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
                                'prix_unitaire': 'Le prix unitaire ne peut pas être négatif.'
                            })
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            'prix_unitaire': 'Le prix unitaire doit être un nombre valide.'
                        })
                
                # Vérifier le stock disponible (somme des quantite_restante)
                stock_disponible = LigneEntree.objects.filter(
                    article=article_obj,
                    quantite_restante__gt=0
                ).aggregate(total=models.Sum('quantite_restante'))['total'] or 0
                
                if stock_disponible < qte:
                    raise serializers.ValidationError(
                        f"Stock insuffisant pour l'article {article_obj.nom_scientifique} "
                        f"(Disponible: {stock_disponible}, Demandé: {qte})"
                    )
                
                # Gestion de la devise pour chaque ligne
                devise_id = ligne.get('devise_id') or ligne.get('devise')
                if devise_id:
                    try:
                        devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id)
                    except Devise.DoesNotExist:
                        raise serializers.ValidationError(f"Devise avec ID {devise_id} non trouvée dans votre entreprise.")
                else:
                    devise_obj = default_dev
                
                # ========== LOGIQUE FIFO ==========
                # Récupérer les lots disponibles triés par date (FIFO : plus ancien en premier)
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
                    
                    # Stocker les données du lot utilisé
                    lots_utilises_data.append({
                        'lot': lot,
                        'quantite': quantite_a_prelever,
                        'prix_achat': lot.prix_unitaire,
                        'prix_vente': lot.prix_vente,  # Prix du lot (pour traçabilité)
                    })
                    
                    # Mettre à jour le lot
                    lot.quantite_restante -= quantite_a_prelever
                    lot.save()
                    
                    quantite_restante_a_sortir -= quantite_a_prelever
                    total_prix_vente += lot.prix_vente * Decimal(str(quantite_a_prelever))
                
                # Calculer le prix de vente moyen des lots (pour référence, si prix_unitaire non fourni)
                if qte > 0:
                    prix_vente_moyen_lots = total_prix_vente / Decimal(str(qte))
                else:
                    prix_vente_moyen_lots = Decimal('0.00')
                
                # Utiliser le prix réellement encaissé si fourni, sinon utiliser le prix moyen des lots
                prix_unitaire_final = prix_unitaire_encaisse if prix_unitaire_encaisse is not None else prix_vente_moyen_lots
                prix_unitaire_final = prix_unitaire_final.quantize(Decimal('0.01'))
                
                # Créer la ligne de sortie avec le prix réellement encaissé
                ligne_sortie = LigneSortie.objects.create(
                    sortie=sortie,
                    article=article_obj,
                    quantite=qte,
                    prix_unitaire=prix_unitaire_final,  # Prix réellement encaissé (peut différer du prix du lot)
                    devise=devise_obj
                )
                
                # Créer les traçabilités et bénéfices
                # IMPORTANT : Le bénéfice est calculé avec le prix réellement encaissé, pas le prix_vente du lot
                for lot_data in lots_utilises_data:
                    lot = lot_data['lot']
                    qte_lot = lot_data['quantite']
                    prix_achat = lot_data['prix_achat']
                    prix_vente_lot = lot_data['prix_vente']  # Prix du lot (pour traçabilité)
                    
                    # Traçabilité : quel lot a été utilisé (on garde le prix_vente du lot pour référence)
                    LigneSortieLot.objects.create(
                        ligne_sortie=ligne_sortie,
                        lot_entree=lot,
                        quantite=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_vente_lot  # Prix du lot (pour traçabilité)
                    )
                    
                    # Calculer le bénéfice avec le prix réellement encaissé (pas le prix_vente du lot)
                    benefice_unitaire = prix_unitaire_final - prix_achat
                    benefice_total = benefice_unitaire * Decimal(str(qte_lot))
                    
                    BeneficeLot.objects.create(
                        lot_entree=lot,
                        ligne_sortie=ligne_sortie,
                        quantite_vendue=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_unitaire_final,  # Prix réellement encaissé (pour calcul bénéfice)
                        benefice_unitaire=benefice_unitaire.quantize(Decimal('0.01')),
                        benefice_total=benefice_total.quantize(Decimal('0.01'))
                    )
                
                # Calcul du montant pour cette ligne (prix réellement encaissé)
                montant_ligne = prix_unitaire_final * Decimal(str(qte))
                
                # Accumulation par devise
                devise_key = devise_obj.sigle if devise_obj else 'DEFAULT'
                if devise_key not in totaux_par_devise:
                    totaux_par_devise[devise_key] = {
                        'devise_obj': devise_obj,
                        'total': Decimal('0.00')
                    }
                totaux_par_devise[devise_key]['total'] += montant_ligne
                
                # Mettre à jour le stock total (pour compatibilité)
                stock_obj, created = Stock.objects.get_or_create(
                    article=article_obj,
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte -= qte
                stock_obj.save()
            
            # Créer les mouvements de caisse par devise (ENTREE pour vente)
            # Si statut EN_CREDIT, montant = 0 (pas d'impact sur la caisse)
            for devise_key, devise_data in totaux_par_devise.items():
                devise_obj = devise_data['devise_obj']
                total_devise = devise_data['total']
                
                # Si vente en crédit, enregistrer avec montant 0
                montant_caisse = Decimal('0.00') if sortie.statut == 'EN_CREDIT' else total_devise
                
                if total_devise > 0:
                    creer_mouvement_caisse(
                        montant=montant_caisse.quantize(Decimal('0.01')),
                        devise=devise_obj or default_dev,
                        type_mouvement='ENTREE',
                        entreprise_id=sortie.entreprise_id,
                        succursale_id=sortie.succursale_id,
                        content_object=sortie,
                        sortie=sortie,
                        reference_piece=f'VENT-{sortie.pk}-{devise_key}',
                        motif='',
                    )
        return Response(self.get_serializer(sortie).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='produits-plus-vendus')
    def produits_plus_vendus(self, request):
        """
        Retourne les produits les plus vendus, classés par NOMBRE DE VENTES (nombre de fois
        où le produit a été vendu), pas par quantité. Ex. : un biscuit vendu 10 fois (qté 12)
        est classé avant une mayonnaise vendue 2 fois (qté 25).
        
        Paramètres de requête (optionnels) :
        - date_debut : Date de début (format: YYYY-MM-DD)
        - date_fin : Date de fin (format: YYYY-MM-DD)
        - mois : Mois (1-12)
        - annee : Année (ex: 2025)
        - limit : Nombre de résultats à retourner (défaut: 10)
        - general : true/false - Si true, ignore les filtres de date (défaut: false)
        
        Exemples :
        - GET /api/sorties/produits-plus-vendus/ (tous les temps)
        - GET /api/sorties/produits-plus-vendus/?date_debut=2025-01-01&date_fin=2025-01-31
        - GET /api/sorties/produits-plus-vendus/?mois=1&annee=2025
        - GET /api/sorties/produits-plus-vendus/?general=true
        """
        from django.db.models import Sum, Count, Q
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Récupérer les paramètres
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
        
        # Filtrage par période
        periode_info = {}
        
        if general:
            # Mode général : toutes les ventes
            periode_info = {
                'type': 'general',
                'description': 'Toutes les ventes (général)'
            }
        elif mois and annee:
            # Filtrage par mois
            try:
                mois_int = int(mois)
                annee_int = int(annee)
                if not (1 <= mois_int <= 12):
                    return Response(
                        {'error': 'Le mois doit être entre 1 et 12'},
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
                
                noms_mois = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                            'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
                periode_info = {
                    'type': 'mois',
                    'mois': mois_int,
                    'annee': annee_int,
                    'description': f"{noms_mois[mois_int]} {annee_int}"
                }
            except ValueError:
                return Response(
                    {'error': 'Format invalide pour mois ou année'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif date_debut or date_fin:
            # Filtrage par période personnalisée
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
            # Par défaut : toutes les ventes
            periode_info = {
                'type': 'general',
                'description': 'Toutes les ventes'
            }
        
        # Grouper par article et calculer les totaux
        # Classement par NOMBRE DE VENTES (nombre de fois où le produit a été vendu), pas par quantité
        # Ex. : biscuit vendu 10 fois (qté 12) > mayonnaise vendue 2 fois (qté 25) → biscuit est "plus vendu"
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
        
        # Formater les résultats
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
                'chiffre_affaires': str(Decimal(str(produit['chiffre_affaires'] or 0)).quantize(Decimal('0.01')))
            })
            rang += 1
        
        # Statistiques globales
        total_quantite = sum(p['quantite_vendue'] for p in resultats)
        # Utiliser Decimal(0) comme valeur initiale pour garantir que le résultat est un Decimal
        total_ca = sum((Decimal(str(p['chiffre_affaires'])) for p in resultats), Decimal('0.00'))
        
        return Response({
            'periode': periode_info,
            'statistiques': {
                'nombre_produits': len(resultats),
                'total_quantite_vendue': total_quantite,
                'total_chiffre_affaires': str(total_ca.quantize(Decimal('0.01'))),
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
                # Restaurer les lots utilisés
                for lot_utilise in ligne.lots_utilises.all():
                    lot = lot_utilise.lot_entree
                    lot.quantite_restante += lot_utilise.quantite
                    lot.save()
                
                # Supprimer les bénéfices associés
                BeneficeLot.objects.filter(ligne_sortie=ligne).delete()
                
                # Supprimer les traçabilités
                ligne.lots_utilises.all().delete()
                
                # Restaurer le stock total (pour compatibilité)
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
                
                # Déterminer la devise de cette ligne
                devise_ligne = ligne.devise or default_dev
                devise_key = devise_ligne.sigle if devise_ligne else 'DEFAULT'
                
                # Accumuler par devise
                if devise_key not in totaux_par_devise:
                    totaux_par_devise[devise_key] = {
                        'devise_obj': devise_ligne,
                        'total': Decimal('0.00')
                    }
                totaux_par_devise[devise_key]['total'] += montant_ligne
            
            # 3. Vérifier les soldes et créer les mouvements de caisse inverses par devise
            # Mais seulement si la vente était PAYEE (pas EN_CREDIT)
            for devise_key, devise_data in totaux_par_devise.items():
                devise_obj = devise_data['devise_obj']
                total_devise = devise_data['total']
                
                if total_devise > 0:
                    # Si la vente était en crédit, pas besoin d'annuler de mouvement caisse
                    if sortie.statut == 'EN_CREDIT':
                        continue
                    
                    # Vérifier le solde disponible pour cette devise
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
                    
                    # Créer le mouvement de caisse inverse (SORTIE)
                    creer_mouvement_caisse(
                        montant=total_devise.quantize(Decimal('0.01')),
                        devise=devise_obj or default_dev,
                        type_mouvement='SORTIE',
                        entreprise_id=sortie.entreprise_id,
                        succursale_id=sortie.succursale_id,
                        content_object=sortie,
                        sortie=sortie,
                        reference_piece=f'ANN-VENT-{sortie.pk}-{devise_key}',
                        motif='Annulation vente',
                    )
            
            sortie.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _total_sortie(self, sortie: Sortie) -> Decimal:
        total = Decimal('0.00')
        for l in sortie.lignes.all():
            pu = l.prix_unitaire or Decimal('0')
            total += pu * Decimal(str(l.quantite))
        return total.quantize(Decimal('0.01'))

    def _solde_caisse_par_devise(self, entreprise, devise, succursale_id=None):
        """Calcule le solde de caisse (tenant + devise) pour une devise spécifique."""
        if not entreprise or not devise:
            return Decimal('0.00')
        qs = MouvementCaisse.objects.filter(devise=devise, entreprise_id=entreprise.pk)
        if succursale_id is not None:
            qs = qs.filter(succursale_id=succursale_id)
        entrees = qs.filter(type='ENTREE').aggregate(total=Sum('montant'))['total'] or Decimal('0')
        sorties = qs.filter(type='SORTIE').aggregate(total=Sum('montant'))['total'] or Decimal('0')
        return (entrees - sorties).quantize(Decimal('0.01'))

    def update(self, request, *args, **kwargs):
        return self._update_common(request, *args, **kwargs, partial=False)

    def partial_update(self, request, *args, **kwargs):
        return self._update_common(request, *args, **kwargs, partial=True)

    def _update_common(self, request, *args, **kwargs):
        """Mise à jour d'une sortie avec gestion FIFO complète."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        user = request.user
        old_total = self._total_sortie(instance)
        
        lignes_data = request.data.get('lignes', [])
        if not lignes_data:
            raise serializers.ValidationError("Au moins une ligne de sortie est requise.")
        
        default_dev = Devise.objects.filter(est_principal=True).first()
        
        with transaction.atomic():
            # ========== ROLLBACK : Restaurer les lots et supprimer les traçabilités ==========
            for ancienne_ligne in instance.lignes.all():
                # Restaurer quantite_restante pour chaque lot utilisé
                for lot_utilise in ancienne_ligne.lots_utilises.all():
                    lot = lot_utilise.lot_entree
                    lot.quantite_restante += lot_utilise.quantite
                    lot.save()
                
                # Supprimer les bénéfices associés
                BeneficeLot.objects.filter(ligne_sortie=ancienne_ligne).delete()
                
                # Supprimer les traçabilités
                ancienne_ligne.lots_utilises.all().delete()
                
                # Restaurer le stock total (pour compatibilité)
                stock_obj, created = Stock.objects.get_or_create(
                    article=ancienne_ligne.article, 
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte += ancienne_ligne.quantite
                stock_obj.save()
            
            # Supprimer toutes les anciennes lignes
            instance.lignes.all().delete()
            
            # Mettre à jour les champs de la sortie
            if 'motif' in request.data:
                instance.motif = request.data['motif']
            if 'client_id' in request.data:
                client_id = request.data.get('client_id')
                if client_id:
                    try:
                        instance.client = Client.objects.get(pk=client_id)
                    except Client.DoesNotExist:
                        raise serializers.ValidationError(f"Client avec ID {client_id} non trouvé.")
                else:
                    instance.client = None
            if 'statut' in request.data:
                instance.statut = request.data.get('statut')
            instance.save()
            
            # ========== RECRÉATION : Créer les nouvelles lignes avec FIFO ==========
            totaux_par_devise = {}
            
            for ligne in lignes_data:
                article_id = ligne.get('article_id') or ligne.get('article')
                
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                except Article.DoesNotExist:
                    raise serializers.ValidationError({
                        'article': f"Article avec ID {article_id} non trouvé."
                    })
                
                try:
                    qte = int(ligne.get('quantite', 0))
                except (ValueError, TypeError):
                    raise serializers.ValidationError({
                        'quantite': 'La quantité doit être un nombre entier valide.'
                    })
                
                if qte <= 0:
                    raise serializers.ValidationError({
                        'quantite': 'La quantité doit être supérieure à 0.'
                    })
                
                # Prix réellement encaissé (peut être fourni manuellement)
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
                                'prix_unitaire': 'Le prix unitaire ne peut pas être négatif.'
                            })
                    except (ValueError, TypeError):
                        raise serializers.ValidationError({
                            'prix_unitaire': 'Le prix unitaire doit être un nombre valide.'
                        })
                
                # Vérifier le stock disponible (somme des quantite_restante)
                stock_disponible = LigneEntree.objects.filter(
                    article=article_obj,
                    quantite_restante__gt=0
                ).aggregate(total=models.Sum('quantite_restante'))['total'] or 0
                
                if stock_disponible < qte:
                    raise serializers.ValidationError(
                        f"Stock insuffisant pour l'article {article_obj.nom_scientifique} "
                        f"(Disponible: {stock_disponible}, Demandé: {qte})"
                    )
                
                # Gestion de la devise
                devise_id = ligne.get('devise_id') or ligne.get('devise')
                if devise_id:
                    try:
                        devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=instance.sortie.entreprise_id)
                    except Devise.DoesNotExist:
                        devise_obj = default_dev
                else:
                    devise_obj = default_dev
                
                # ========== LOGIQUE FIFO ==========
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
                    
                    lots_utilises_data.append({
                        'lot': lot,
                        'quantite': quantite_a_prelever,
                        'prix_achat': lot.prix_unitaire,
                        'prix_vente': lot.prix_vente,  # Prix du lot (pour traçabilité)
                    })
                    
                    lot.quantite_restante -= quantite_a_prelever
                    lot.save()
                    
                    quantite_restante_a_sortir -= quantite_a_prelever
                    total_prix_vente += lot.prix_vente * Decimal(str(quantite_a_prelever))
                
                # Calculer le prix de vente moyen des lots (pour référence, si prix_unitaire non fourni)
                if qte > 0:
                    prix_vente_moyen_lots = total_prix_vente / Decimal(str(qte))
                else:
                    prix_vente_moyen_lots = Decimal('0.00')
                
                # Utiliser le prix réellement encaissé si fourni, sinon utiliser le prix moyen des lots
                prix_unitaire_final = prix_unitaire_encaisse if prix_unitaire_encaisse is not None else prix_vente_moyen_lots
                prix_unitaire_final = prix_unitaire_final.quantize(Decimal('0.01'))
                
                # Créer la ligne de sortie avec le prix réellement encaissé
                ligne_sortie = LigneSortie.objects.create(
                    sortie=instance,
                    article=article_obj,
                    quantite=qte,
                    prix_unitaire=prix_unitaire_final,  # Prix réellement encaissé
                    devise=devise_obj
                )
                
                # Créer les traçabilités et bénéfices
                # IMPORTANT : Le bénéfice est calculé avec le prix réellement encaissé
                for lot_data in lots_utilises_data:
                    lot = lot_data['lot']
                    qte_lot = lot_data['quantite']
                    prix_achat = lot_data['prix_achat']
                    prix_vente_lot = lot_data['prix_vente']  # Prix du lot (pour traçabilité)
                    
                    LigneSortieLot.objects.create(
                        ligne_sortie=ligne_sortie,
                        lot_entree=lot,
                        quantite=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_vente_lot  # Prix du lot (pour traçabilité)
                    )
                    
                    # Calculer le bénéfice avec le prix réellement encaissé
                    benefice_unitaire = prix_unitaire_final - prix_achat
                    benefice_total = benefice_unitaire * Decimal(str(qte_lot))
                    
                    BeneficeLot.objects.create(
                        lot_entree=lot,
                        ligne_sortie=ligne_sortie,
                        quantite_vendue=qte_lot,
                        prix_achat=prix_achat,
                        prix_vente=prix_unitaire_final,  # Prix réellement encaissé (pour calcul bénéfice)
                        benefice_unitaire=benefice_unitaire.quantize(Decimal('0.01')),
                        benefice_total=benefice_total.quantize(Decimal('0.01'))
                    )
                
                # Calcul du montant pour cette ligne (prix réellement encaissé)
                montant_ligne = prix_unitaire_final * Decimal(str(qte))
                
                # Accumulation par devise
                devise_key = devise_obj.sigle if devise_obj else 'DEFAULT'
                if devise_key not in totaux_par_devise:
                    totaux_par_devise[devise_key] = {
                        'devise_obj': devise_obj,
                        'total': Decimal('0.00')
                    }
                totaux_par_devise[devise_key]['total'] += montant_ligne
                
                # Mettre à jour le stock total
                stock_obj, created = Stock.objects.get_or_create(
                    article=article_obj,
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte -= qte
                stock_obj.save()
            
            # Ajustement caisse si nécessaire
            new_total = self._total_sortie(instance)
            diff = (new_total - old_total).quantize(Decimal('0.01'))
            if diff != 0:
                mouvement_type = 'ENTREE' if diff > 0 else 'SORTIE'
                montant_abs = abs(diff)
                tenant_id = instance.entreprise_id or (user.get_entreprise_id(self.request) if user.is_authenticated else None)
                if mouvement_type == 'SORTIE' and tenant_id:
                    solde = self._solde_caisse_tenant(tenant_id, getattr(self.request, 'branch_id', None))
                    if solde < montant_abs:
                        raise serializers.ValidationError("Solde caisse insuffisant pour ajuster cette vente.")
                default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first() if tenant_id else Devise.objects.filter(est_principal=True).first()
                creer_mouvement_caisse(
                    montant=montant_abs,
                    devise=default_dev,
                    type_mouvement=mouvement_type,
                    entreprise_id=instance.entreprise_id,
                    succursale_id=instance.succursale_id,
                    content_object=instance,
                    sortie=instance,
                    reference_piece=f'AJ-VENT-{instance.pk}',
                    motif='Ajustement vente',
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

    # === Actions POS (facture & bons de sortie) déplacées depuis RapportViewSet ===
    @action(detail=True, methods=['get'], url_path='facture-pos', permission_classes=[IsAuthenticated])
    def facture_pos_pdf(self, request, pk=None):
        user = request.user
        sortie = self.get_object()
        entreprise = user.get_entreprise(request)
        POS_WIDTH = 80 * mm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()

        # Polices réduites pour facture compacte (impression POS). wordWrap pour colonne Article. Alignement à gauche.
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=7, leading=8, wordWrap='CJK')
        article_cell_style = ParagraphStyle('ArticleCell', parent=normal, wordWrap='CJK', allowWidows=0, allowOrphans=0)
        title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=10, leading=11, alignment=TA_LEFT, spaceAfter=1*mm)
        info_style = ParagraphStyle('Info', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_LEFT)
        footer_style = ParagraphStyle('Footer', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_LEFT, textColor=colors.black)

        elements = []

        # En-tête simplifié (nom, logo, téléphone) — pas de slogan sur facture pour éviter doublon avec "Imprimé par" en bas
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        entete = {'entreprise': {**entete['entreprise'], 'slogan': ''}}  # ne pas afficher le slogan en haut
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete, compact=True))
        # Pas de spacer supplémentaire : en-tête compact place déjà le titre juste en dessous

        # Titre facture (traduit)
        elements.append(Paragraph(f"<b>{_('FACTURE DE VENTE')}</b>", title_style))

        # Infos facture (traduites) — pas de devise dans l'en-tête
        devise_sortie = getattr(sortie, 'devise', None)
        if not devise_sortie:
            devise_sortie = Devise.objects.filter(est_principal=True).first()
        elements.append(Paragraph(f"{_('N° Facture')}: FACT-{sortie.pk:06d}", info_style))
        elements.append(Paragraph(f"{_('Date')}: {timezone.now().strftime('%d/%m/%Y %H:%M')}", info_style))
        elements.append(Spacer(1, 1*mm))

        # Client (labels traduits, données brutes)
        if sortie.client:
            elements.append(Paragraph(f"<b>{_('Client')}:</b> {sortie.client.nom}", normal))
            if sortie.client.adresse:
                elements.append(Paragraph(f"<b>{_('Adresse')}:</b> {sortie.client.adresse}", normal))
            if sortie.client.telephone:
                elements.append(Paragraph(f"<b>{_('Tél')}:</b> {sortie.client.telephone}", normal))
            if sortie.client.email:
                elements.append(Paragraph(f"<b>{_('Email')}:</b> {sortie.client.email}", normal))
            elements.append(Spacer(1, 1*mm))

        # Tableau articles — fond blanc, pas de couleur bleue
        lignes = sortie.lignes.all()
        # P.U. en abrégé : même taille que Qté (facture) — contexte "facture" pour EN "UP"
        pu_label = pgettext('facture', 'P.U.')
        table_data = [
            [
                Paragraph(f"<b>{_('Article')}</b>", article_cell_style),
                Paragraph(f"<b>{_('Qté')}</b>", normal),
                Paragraph(f"<b>{pu_label}</b>", normal),
                Paragraph(f"<b>{_('Total')}</b>", normal)
            ]
        ]
        total_general = Decimal('0.00')
        for ligne in lignes:
            article = ligne.article
            qte = ligne.quantite or 0
            pu_raw = getattr(ligne, 'prix_unitaire', None)
            if pu_raw is None:
                pu = Decimal('0.00')
            elif isinstance(pu_raw, Decimal):
                pu = pu_raw
            else:
                pu = Decimal(str(pu_raw))
            qte_dec = Decimal(str(qte))
            total = (qte_dec * pu).quantize(Decimal('0.01'))
            total_general = (total_general + total).quantize(Decimal('0.01'))
            pu_formatted = f"{pu.quantize(Decimal('0.01')):.2f}"
            total_formatted = f"{total:.2f}"
            table_data.append([
                Paragraph(_article_display_name(article), article_cell_style),
                Paragraph(str(qte), normal),
                Paragraph(pu_formatted, normal),
                Paragraph(total_formatted, normal)
            ])

        total_formatted = f"{total_general:.2f}"
        total_display = f"{total_formatted} {devise_sortie.symbole}" if (devise_sortie and getattr(devise_sortie, 'symbole', None)) else total_formatted
        table_data.append([
            Paragraph(f"<b>{_('TOTAL')}</b>", article_cell_style),
            Paragraph("", normal),
            Paragraph("", normal),
            Paragraph(f"<b>{total_display}</b>", normal)
        ])

        # Article 25 %, Qté 10 %, P.U. 10 % (même largeur que Qté), Total le reste — titres centrés
        article_table = Table(table_data, colWidths=[POS_WIDTH*0.25, POS_WIDTH*0.10, POS_WIDTH*0.10, POS_WIDTH*0.55])
        article_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),   # titres centrés
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # colonne Article à gauche
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Qté, P.U., Total à droite
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(article_table)
        elements.append(Spacer(1, 2*mm))

        # Pied de facture (remerciement, imprimeur, date, décorateur) — poussé en bas par le spacer
        lm = rm = tm = bm = 4*mm
        avail_width = POS_WIDTH - lm - rm
        footer_parts = [
            Paragraph(_("Merci pour votre achat !"), normal),
            Spacer(1, 0.5*mm),
            Paragraph(_("Imprimé par: %(user)s") % {'user': user.get_full_name() or user.username}, footer_style),
            Paragraph(_("Le %(date)s") % {'date': timezone.now().strftime('%d/%m/%Y à %H:%M')}, footer_style),
            Spacer(1, 1*mm),
            Paragraph("—" * 30, footer_style),
        ]
        main_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        footer_height = sum(flow.wrap(avail_width, 100000)[1] for flow in footer_parts)
        min_height = POS_WIDTH + 20*mm
        POS_HEIGHT = max(main_height + footer_height + tm + bm + 3*mm, min_height)
        # Spacer pour coller le pied en bas de la page (évite qu'il remonte en haut)
        spacer_bottom = POS_HEIGHT - tm - bm - main_height - footer_height
        if spacer_bottom > 0:
            elements.append(Spacer(1, spacer_bottom))
        elements.extend(footer_parts)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(POS_WIDTH, POS_HEIGHT),
            leftMargin=lm,
            rightMargin=rm,
            topMargin=tm,
            bottomMargin=bm,
            allowSplitting=0
        )
        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(
            buffer,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="FACTURE_{sortie.pk}.pdf"'}
        )

    @action(detail=True, methods=['get'], url_path='bon-pos', permission_classes=[IsAuthenticated])
    def bon_sortie_pos(self, request, pk=None):
        user = request.user
        sortie = self.get_object()
        POS_WIDTH = 58 * mm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()
        normal = styles['Normal']; normal.fontSize = 8; normal.wordWrap = 'CJK'
        title_style = ParagraphStyle('TitleMini', fontName='Helvetica-Bold', fontSize=9, alignment=1, spaceAfter=1)
        # Sécurise l'accès à l'entreprise (peut être None pour superadmin)
        entreprise = user.get_entreprise(request)
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        pdf_gen = PDFGenerator()
        elements = list(pdf_gen._create_entete(entete))
        elements.append(Spacer(1, 1*mm))
        elements.append(Paragraph(_("BON DE SORTIE"), title_style))
        elements.append(Paragraph(f"{_('N°')}: {sortie.pk}", normal))
        client_label = sortie.client.nom if sortie.client else _("Client Anonyme")
        elements.append(Paragraph(f"{_('Client')}: {client_label}", normal))
        elements.append(Spacer(1, 1*mm))
        lignes = sortie.lignes.all()
        header = [Paragraph(_("Art"), normal), Paragraph(_("Qté"), normal), Paragraph(_("PU"), normal), Paragraph(_("Tot"), normal)]
        data = [header]
        total_general = Decimal('0.00')
        for l in lignes:
            pu = l.prix_unitaire or Decimal('0')
            q = l.quantite or 0
            tot = (pu * Decimal(str(q))).quantize(Decimal('0.01'))
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
        ligne_sortie = serializer.save()
        stock, created = Stock.objects.get_or_create(
            article=ligne_sortie.article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        if stock.Qte < ligne_sortie.quantite:
            raise serializers.ValidationError(f"Stock insuffisant pour l'article {_article_display_name(ligne_sortie.article)}")
        stock.Qte -= ligne_sortie.quantite
        stock.save()
    
    def update(self, request, *args, **kwargs):
        """Mise à jour d'une ligne de sortie avec gestion FIFO."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Pour les lignes de sortie, la modification est complexe car elle affecte les lots FIFO
        # On recommande de modifier la sortie entière plutôt qu'une ligne individuelle
        # Mais on permet quand même la modification pour compatibilité
        
        nouvelle_quantite = request.data.get('quantite')
        if nouvelle_quantite is None:
            raise serializers.ValidationError({
                'quantite': 'La quantité est requise pour la mise à jour.'
            })
        
        try:
            nouvelle_quantite = int(nouvelle_quantite)
        except (ValueError, TypeError):
            raise serializers.ValidationError({
                'quantite': 'La quantité doit être un nombre entier valide.'
            })
        
        if nouvelle_quantite <= 0:
            raise serializers.ValidationError({
                'quantite': 'La quantité doit être supérieure à 0.'
            })
        
        old_quantite = instance.quantite
        
        with transaction.atomic():
            # Restaurer les lots de l'ancienne quantité
            for lot_utilise in instance.lots_utilises.all():
                lot = lot_utilise.lot_entree
                lot.quantite_restante += lot_utilise.quantite
                lot.save()
            
            # Supprimer les bénéfices et traçabilités
            BeneficeLot.objects.filter(ligne_sortie=instance).delete()
            instance.lots_utilises.all().delete()
            
            # Restaurer le stock
            stock_obj, created = Stock.objects.get_or_create(
                article=instance.article,
                defaults={'Qte': 0, 'seuilAlert': 0}
            )
            stock_obj.Qte += old_quantite
            stock_obj.save()
            
            # Vérifier le stock disponible pour la nouvelle quantité
            stock_disponible = LigneEntree.objects.filter(
                article=instance.article,
                quantite_restante__gt=0
            ).aggregate(total=models.Sum('quantite_restante'))['total'] or 0
            
            if stock_disponible < nouvelle_quantite:
                raise serializers.ValidationError(
                    f"Stock insuffisant pour l'article {instance.article.nom_scientifique} "
                    f"(Disponible: {stock_disponible}, Demandé: {nouvelle_quantite})"
                )
            
            # Appliquer FIFO pour la nouvelle quantité
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
                    benefice_unitaire=benefice_unitaire.quantize(Decimal('0.01')),
                    benefice_total=benefice_total.quantize(Decimal('0.01'))
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
            
            # Mettre à jour la ligne
            instance.quantite = nouvelle_quantite
            instance.prix_unitaire = prix_vente_moyen.quantize(Decimal('0.01'))
            if 'devise_id' in request.data:
                devise_id = request.data.get('devise_id')
                if devise_id:
                    instance.devise = Devise.objects.get(pk=devise_id)
            instance.save()
            
            # Mettre à jour le stock
            stock_obj.Qte -= nouvelle_quantite
            stock_obj.save()
        
        return Response(self.get_serializer(instance).data)
    
    def partial_update(self, request, *args, **kwargs):
        """Mise à jour partielle d'une ligne de sortie."""
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
        new_instance = serializer.save()
        new_article = new_instance.article
        new_quantite = new_instance.quantite
        # Remettre l'ancienne quantité dans le stock de l'ancien article
        stock_old, created = Stock.objects.get_or_create(
            article=old_article, 
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        stock_old.Qte += old_quantite
        stock_old.save()
        # Retirer la nouvelle quantité du stock du nouvel article
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


class TypeArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = TypeArticle.objects.all()
    serializer_class = TypeArticleSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-id')


class ArticleViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('-pk')

    @swagger_auto_schema(
        operation_summary='Recherche d\'articles (tenant)',
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Texte recherché (obligatoire) : nom scientifique, commercial ou code article. Ex. ?q=café',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Nombre max de résultats (défaut 25, max 100).',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description='Pagination (décalage).',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                'Résultats + meta ; champ « message » si aucun article ne correspond.',
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
                        'Indiquez ce que vous cherchez avec le paramètre « q ». '
                        'Exemple : GET /api/articles/search/?q=café'
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
            q_display = (q[:200] + '…') if len(q) > 200 else q
            if branch_id is not None:
                msg = _(
                    'Aucun article ne correspond à « %(term)s » pour cette succursale. '
                    'Essayez un autre mot-clé (nom scientifique, nom commercial ou code article), '
                    'vérifiez l’orthographe ou élargissez la recherche (autre succursale si votre rôle le permet).'
                ) % {'term': q_display}
            else:
                msg = _(
                    'Aucun article ne correspond à « %(term)s » dans votre entreprise. '
                    'Essayez un autre mot-clé (nom scientifique, nom commercial ou code article) '
                    'ou vérifiez l’orthographe.'
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
            'Statuts (1 requête agrégée sur Stock) : NORMAL (Qte > seuilAlert), '
            'ALERTE / faible (0 < Qte ≤ seuilAlert), RUPTURE (Qte = 0). '
            'Expiration proche : deux comptages distincts d’articles (lots LigneEntree avec '
            'quantite_restante > 0, date_expiration entre aujourd’hui et la fin de fenêtre) : '
            '**expiration_sous_30_jours** (+30 jours glissants), **expiration_sous_3_mois** '
            '(+3 mois calendaires). Lots déjà expirés exclus. '
            'Hors pagination. Périmètre : entreprise JWT ; succursale si présente dans le contexte.'
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
                            description='Identique à alerte (libellé métier)',
                        ),
                        'rupture': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'by_code': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Mêmes valeurs, clés NORMAL / ALERTE / RUPTURE',
                        ),
                        'sum_statuts': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description='normal + alerte + rupture (identique à total si cohérent)',
                        ),
                        'expiration_sous_30_jours': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description=(
                                'Articles distincts avec au moins un lot non épuisé '
                                'dont la date d’expiration est dans les 30 prochains jours'
                            ),
                        ),
                        'expiration_periode_30_jours': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Fenêtre [date_debut, date_fin] pour expiration_sous_30_jours',
                            properties={
                                'date_debut': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                'date_fin': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                            },
                        ),
                        'expiration_sous_3_mois': openapi.Schema(
                            type=openapi.TYPE_INTEGER,
                            description=(
                                'Articles distincts avec au moins un lot non épuisé '
                                'dont la date d’expiration est dans les 3 prochains mois (calendaires)'
                            ),
                        ),
                        'expiration_periode': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='Fenêtre [date_debut, date_fin] pour expiration_sous_3_mois',
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
        """Agrégation SQL des stocks par statut (hors pagination)."""
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
        ligne_entree = serializer.save()
        stock, created = Stock.objects.get_or_create(
            article=ligne_entree.article,
            defaults={'Qte': 0, 'seuilAlert': 0}
        )
        stock.Qte += ligne_entree.quantite
        stock.save()
    
    def update(self, request, *args, **kwargs):
        """Mise à jour d'une ligne d'entrée avec gestion FIFO."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        old_quantite = instance.quantite
        old_quantite_restante = instance.quantite_restante
        
        with transaction.atomic():
            # Restaurer le stock de l'ancienne quantité
            stock_obj, created = Stock.objects.get_or_create(
                article=instance.article,
                defaults={'Qte': 0, 'seuilAlert': 0}
            )
            stock_obj.Qte -= old_quantite
            stock_obj.save()
            
            # Mettre à jour la ligne
            updated_instance = serializer.save()
            
            # S'assurer que quantite_restante est cohérente
            nouvelle_quantite = updated_instance.quantite
            diff_quantite = nouvelle_quantite - old_quantite
            
            if diff_quantite > 0:
                # Augmentation : ajouter à quantite_restante
                updated_instance.quantite_restante += diff_quantite
            elif diff_quantite < 0:
                # Diminution : réduire quantite_restante proportionnellement
                reduction = min(abs(diff_quantite), updated_instance.quantite_restante)
                updated_instance.quantite_restante -= reduction
            
            # S'assurer que quantite_restante ne dépasse pas quantite
            if updated_instance.quantite_restante > updated_instance.quantite:
                updated_instance.quantite_restante = updated_instance.quantite
            
            updated_instance.save()
            
            # Mettre à jour le stock avec la nouvelle quantité
            stock_obj.Qte += nouvelle_quantite
            stock_obj.save()
        
        return Response(self.get_serializer(updated_instance).data)
    
    def partial_update(self, request, *args, **kwargs):
        """Mise à jour partielle d'une ligne d'entrée."""
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
                    'est_principal': "Impossible de désactiver la seule devise de l'entreprise. "
                                   "Elle doit rester principale."
                })
            
            # Promouvoir automatiquement une autre devise comme principale
            with transaction.atomic():
                serializer.save()
                # Prendre la première autre devise et la rendre principale
                premiere_autre = autres_devises.first()
                premiere_autre.est_principal = True
                premiere_autre.save()
        else:
            serializer.save()
    
    def perform_destroy(self, instance):
        autres_devises = self.get_queryset().exclude(id=instance.id)
        
        if not autres_devises.exists():
            raise serializers.ValidationError({
                'detail': "Impossible de supprimer la dernière devise de l'entreprise. "
                         "Créez une nouvelle devise avant de supprimer celle-ci."
            })
        
        with transaction.atomic():
            etait_principale = instance.est_principal
            instance.delete()
            
            # Si c'était la devise principale, promouvoir automatiquement une autre
            if etait_principale:
                premiere_autre = autres_devises.first()
                premiere_autre.est_principal = True
                premiere_autre.save()



class EntreeViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour gérer les entrées de stock avec support multi-devises (filtré par entreprise/succursale)."""
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
        """Création d'une entrée avec gestion intelligente des stocks et multi-devises."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        lignes_data = request.data.get('lignes', [])
        user = request.user
        messages_reponse = []
        
        if not lignes_data:
            raise serializers.ValidationError("Au moins une ligne d'entrée est requise.")
        tenant_id, branch_id = _get_tenant_ids(request)
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
        articles_groupes = {}
        
        for ligne in lignes_data:
            # On accepte article_id comme code produit (ex: "CAPE0001") ou comme clé primaire numérique
            article_lookup = None
            article_id = ligne.get('article') or ligne.get('article_id')
            if article_id:
                # Essayer d'abord par code produit, sinon par clé primaire
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                    article_lookup = article_obj.article_id
                except Article.DoesNotExist:
                    try:
                        article_obj = Article.objects.get(nom_commercial=article_id)
                        article_lookup = article_obj.article_id
                    except Article.DoesNotExist:
                        # Peut-être que c'est déjà la clé primaire numérique
                        article_lookup = article_id
            else:
                article_lookup = None

            qte = Decimal(str(ligne.get('quantite', 0)))
            prix_unitaire_raw = ligne.get('prix_unitaire', 0)
            try:
                prix_unitaire = Decimal(str(prix_unitaire_raw))
            except (ValueError, TypeError, InvalidOperation):
                prix_unitaire = Decimal('0.00')
            
            # Prix de vente (obligatoire pour calculer les bénéfices)
            prix_vente_raw = ligne.get('prix_vente', 0)
            try:
                prix_vente = Decimal(str(prix_vente_raw))
            except (ValueError, TypeError, InvalidOperation):
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente est obligatoire pour chaque ligne d\'entrée.'
                })
            
            if prix_vente <= 0:
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente doit être supérieur à 0.'
                })
            
            seuil_alerte = int(ligne.get('seuil_alerte', 0))
            devise_id = ligne.get('devise_id') or ligne.get('devise')
            date_expiration = ligne.get('date_expiration')

            if article_lookup in articles_groupes:
                articles_groupes[article_lookup]['quantite'] += qte
                messages_reponse.append(f"Article {article_id}: quantités additionnées ({qte} ajouté)")
            else:
                articles_groupes[article_lookup] = {
                    'quantite': qte,
                    'prix_unitaire': prix_unitaire,
                    'prix_vente': prix_vente,
                    'seuil_alerte': seuil_alerte,
                    'devise': devise_id,
                    'date_expiration': date_expiration
                }
        
        # Calcul du coût total par devise
        totaux_par_devise = {}
        
        for article_id, ligne_data in articles_groupes.items():
            q = Decimal(str(ligne_data['quantite']))
            pu = ligne_data['prix_unitaire']
            pv = ligne_data.get('prix_vente', Decimal('0.00'))  # Prix de vente
            devise_id = ligne_data['devise']
            devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id) if devise_id else default_dev
            devise_sigle = devise_obj.sigle if devise_obj else 'N/A'
            
            montant_ligne = (q * pu).quantize(Decimal('0.01'))
            
            if devise_sigle not in totaux_par_devise:
                totaux_par_devise[devise_sigle] = {
                    'devise_obj': devise_obj,
                    'total': Decimal('0.00')
                }
            
            totaux_par_devise[devise_sigle]['total'] += montant_ligne
        
        # Vérification des soldes par devise
        erreurs_solde = []
        for devise_sigle, devise_data in totaux_par_devise.items():
            devise_obj = devise_data['devise_obj']
            total_devise = devise_data['total']
            
            solde_devise = self._solde_caisse_par_devise(tenant_id, branch_id, devise_obj)
            
            if total_devise > solde_devise:
                devise_nom = devise_obj.nom if devise_obj else 'Non spécifiée'
                symbole = devise_obj.symbole if devise_obj else ''
                erreurs_solde.append(
                    f"Solde insuffisant en {devise_nom} ({devise_sigle}): "
                    f"Requis {total_devise} {symbole}, Disponible {solde_devise} {symbole}. "
                    f"Veuillez d'abord effectuer une entrée en caisse dans cette devise."
                )
        
        if erreurs_solde:
            raise serializers.ValidationError({
                'soldes_insuffisants': erreurs_solde,
                'message': 'Approvisionnement impossible: soldes insuffisants dans certaines devises.'
            })

        with transaction.atomic():
            entree = Entree.objects.create(
                libele=serializer.validated_data.get('libele', ''),
                entreprise_id=tenant_id,
                succursale_id=branch_id
            )
            
            # Traiter chaque article groupé
            for article_id, ligne_data in articles_groupes.items():
                # Correction : utiliser article_id comme clé primaire réelle
                try:
                    article_obj = Article.objects.get(article_id=article_id)
                except Article.DoesNotExist:
                    raise serializers.ValidationError({
                        'article_id': f"Aucun article trouvé avec article_id={article_id}"
                    })
                qte = ligne_data['quantite']
                prix_unitaire = ligne_data['prix_unitaire']
                prix_vente = ligne_data.get('prix_vente', Decimal('0.00'))
                seuil_alerte = ligne_data['seuil_alerte']
                date_expiration = ligne_data['date_expiration']
                devise_id = ligne_data['devise']
                devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id) if devise_id else None

                # Créer la ligne d'entrée (quantite_restante sera initialisé automatiquement dans save())
                ligne_entree = LigneEntree.objects.create(
                    entree=entree,
                    article=article_obj,
                    quantite=qte,
                    quantite_restante=qte,  # Initialiser explicitement
                    prix_unitaire=prix_unitaire,
                    prix_vente=prix_vente,
                    date_expiration=date_expiration,
                    devise=devise_obj,
                    seuil_alerte=seuil_alerte
                )

                # Gestion intelligente du stock
                stock_obj, created = Stock.objects.get_or_create(
                    article=article_obj, 
    
                    defaults={'Qte': 0, 'seuilAlert': seuil_alerte}
                )

                # Utiliser nom_commercial si disponible, sinon nom_scientifique
                article_nom = article_obj.nom_commercial or article_obj.nom_scientifique
                if created:
                    messages_reponse.append(f"Nouveau stock créé pour {article_nom}")
                else:
                    if stock_obj.Qte == 0:
                        messages_reponse.append(f"Réapprovisionnement de {article_nom} (stock était épuisé)")
                    else:
                        messages_reponse.append(f"Ajout au stock existant de {article_nom} (stock: {stock_obj.Qte} → {stock_obj.Qte + qte})")

                stock_obj.Qte += qte
                stock_obj.seuilAlert = seuil_alerte
                stock_obj.save()
                
            # Créer les mouvements de caisse par devise (dépenses approvisionnement)
            for devise_sigle, devise_data in totaux_par_devise.items():
                devise_obj = devise_data['devise_obj']
                total_devise = devise_data['total']
                
                if total_devise > 0:
                    creer_mouvement_caisse(
                        montant=total_devise,
                        devise=devise_obj,
                        type_mouvement='SORTIE',
                        entreprise_id=entree.entreprise_id,
                        succursale_id=entree.succursale_id,
                        content_object=entree,
                        entree=entree,
                        reference_piece=f'APPRO-{entree.pk}-{devise_sigle}',
                        motif='',
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
                {'error': f'Article {article_id} non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Récupérer tous les lots (disponibles et épuisés)
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
                'statut': 'Disponible' if lot.quantite_restante > 0 else 'Épuisé'
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
        Retourne les bénéfices totaux des lots vendus, avec filtre optionnel par mois/année.
        **Isolation multi-tenant :** uniquement les `BeneficeLot` dont le lot d'entrée appartient à
        l'entreprise du JWT ; si `succursale_id` est présent dans le token, filtre aussi par cette succursale.
        Par défaut : mois et année en cours.
        GET /api/entrees/benefices-totaux/
        Query params: month (1-12), year (ex: 2026). Omis = mois et année courants.
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

        # Base : période + entreprise (via le lot → entrée) ; succursale si contexte JWT défini
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

        # Pertes : on n'inclut PAS les ventes à crédit (EN_CREDIT) car ce n'est pas une perte définitive ;
        # le client doit rembourser ; la perte ne sera éventuellement considérée qu'au remboursement.
        benefices_perte = benefices.filter(benefice_total__lt=0).exclude(
            ligne_sortie__sortie__statut='EN_CREDIT'
        )
        total_perte = abs(benefices_perte.aggregate(
            total=Sum('benefice_total')
        )['total'] or Decimal('0.00'))

        nombre_lots_gagnants = benefices.filter(benefice_total__gte=0).count()
        nombre_lots_perdants = benefices_perte.count()
        nombre_lots_total = benefices.count()

        # Top 10 articles par bénéfice (agrégation SQL, pas de boucle Python sur tous les lots)
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
        
        # Évaluation de la performance
        if total_benefice > 0:
            performance = 'EXCELLENTE'
            message = f"La boutique fonctionne très bien avec un bénéfice total de {total_benefice}"
        elif total_benefice > -1000:
            performance = 'BONNE'
            message = f"La boutique fonctionne correctement avec un bénéfice de {total_benefice}"
        elif total_benefice > -5000:
            performance = 'MOYENNE'
            message = f"Attention : bénéfice négatif de {total_benefice}. Réviser les prix."
        else:
            performance = 'CRITIQUE'
            message = f"URGENT : Perte importante de {total_benefice}. Action immédiate requise."
        
        return Response({
            'resume': {
                'benefice_total': str(total_benefice),
                'total_gain': str(total_gain),
                'total_perte': str(total_perte),
                'nombre_lots_gagnants': nombre_lots_gagnants,
                'nombre_lots_perdants': nombre_lots_perdants,
                'nombre_lots_total': nombre_lots_total,
                'taux_reussite': f"{(nombre_lots_gagnants / nombre_lots_total * 100):.2f}%" if nombre_lots_total > 0 else "0%"
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
        """Mise à jour d'une entrée avec gestion FIFO complète."""
        partial = kwargs.pop('partial', False)
        entree = self.get_object()
        serializer = self.get_serializer(entree, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        lignes_data = request.data.get('lignes', [])
        user = request.user
        
        if not lignes_data:
            raise serializers.ValidationError("Au moins une ligne d'entrée est requise.")
        
        old_total = self._total_entree(entree)
        default_dev = Devise.objects.filter(est_principal=True).first()
        
        # Calcul du nouveau total et validation
        new_total = Decimal('0.00')
        articles_groupes = {}
        
        for ligne in lignes_data:
            article_id = ligne.get('article') or ligne.get('article_id')
            if not article_id:
                raise serializers.ValidationError("Chaque ligne doit avoir un article.")
            
            try:
                article_obj = Article.objects.get(article_id=article_id)
            except Article.DoesNotExist:
                raise serializers.ValidationError(f"Article {article_id} introuvable.")
            
            qte = int(ligne.get('quantite', 0))
            if qte <= 0:
                raise serializers.ValidationError("La quantité doit être supérieure à 0.")
            
            prix_unitaire_raw = ligne.get('prix_unitaire', 0)
            try:
                prix_unitaire = Decimal(str(prix_unitaire_raw))
            except (ValueError, TypeError):
                prix_unitaire = Decimal('0.00')
            
            # Prix de vente obligatoire
            prix_vente_raw = ligne.get('prix_vente', 0)
            try:
                prix_vente = Decimal(str(prix_vente_raw))
            except (ValueError, TypeError):
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente est obligatoire pour chaque ligne d\'entrée.'
                })
            
            if prix_vente <= 0:
                raise serializers.ValidationError({
                    'prix_vente': 'Le prix de vente doit être supérieur à 0.'
                })
            
            seuil_alerte = int(ligne.get('seuil_alerte', 0))
            devise_id = ligne.get('devise_id') or ligne.get('devise')
            devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=entree.entreprise_id) if devise_id else default_dev
            date_expiration = ligne.get('date_expiration')
            
            new_total += (Decimal(str(qte)) * prix_unitaire)
            
            # Regrouper par article (fusionner les doublons)
            if article_id in articles_groupes:
                articles_groupes[article_id]['quantite'] += qte
            else:
                articles_groupes[article_id] = {
                    'article_obj': article_obj,
                    'quantite': qte,
                    'prix_unitaire': prix_unitaire,
                    'prix_vente': prix_vente,
                    'seuil_alerte': seuil_alerte,
                    'devise_obj': devise_obj,
                    'date_expiration': date_expiration
                }
        
        new_total = new_total.quantize(Decimal('0.01'))
        
        # Si augmentation de dépense: vérifier solde
        diff = (new_total - old_total).quantize(Decimal('0.01'))
        if diff > 0:
            solde = self._solde_caisse(entree.entreprise_id, entree.succursale_id)
            if diff >= solde:
                raise serializers.ValidationError("Solde de la caisse insuffisant pour augmenter le coût de cette entrée.")
        
        with transaction.atomic():
            # Rollback anciennes lignes (restaurer quantite_restante et stock)
            for ancienne_ligne in entree.lignes.all():
                # Restaurer quantite_restante si des sorties ont été faites
                # On ne peut pas simplement restaurer car des sorties peuvent avoir été faites
                # On doit vérifier combien a été vendu
                quantite_vendue = ancienne_ligne.quantite - ancienne_ligne.quantite_restante
                
                # Restaurer le stock
                stock_obj, created = Stock.objects.get_or_create(
                    article=ancienne_ligne.article, 
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte -= ancienne_ligne.quantite
                stock_obj.save()
            
            # Supprimer toutes les anciennes lignes
            entree.lignes.all().delete()
            
            # Mettre à jour le libellé
            entree.libele = serializer.validated_data.get('libele', entree.libele)
            entree.save(update_fields=['libele'])
            
            # Créer les nouvelles lignes avec FIFO
            for article_id, ligne_data in articles_groupes.items():
                article_obj = ligne_data['article_obj']
                qte = ligne_data['quantite']
                prix_unitaire = ligne_data['prix_unitaire']
                prix_vente = ligne_data['prix_vente']
                seuil_alerte = ligne_data['seuil_alerte']
                devise_obj = ligne_data['devise_obj']
                date_expiration = ligne_data['date_expiration']
                
                # Créer la ligne d'entrée avec quantite_restante initialisée
                LigneEntree.objects.create(
                    entree=entree,
                    article=article_obj,
                    quantite=qte,
                    quantite_restante=qte,  # Initialiser pour FIFO
                    prix_unitaire=prix_unitaire,
                    prix_vente=prix_vente,  # Prix de vente obligatoire
                    date_expiration=date_expiration,
                    devise=devise_obj,
                    seuil_alerte=seuil_alerte
                )
                
                # Mettre à jour le stock
                stock_obj, created = Stock.objects.get_or_create(
                    article=article_obj, 
                    defaults={'Qte': 0, 'seuilAlert': seuil_alerte}
                )
                stock_obj.Qte += qte
                stock_obj.seuilAlert = seuil_alerte
                stock_obj.save()
            
            # Ajustement caisse (si diff != 0)
            if diff != 0:
                mouvement_type = 'SORTIE' if diff > 0 else 'ENTREE'
                tenant_id = entree.entreprise_id
                default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first() if tenant_id else Devise.objects.filter(est_principal=True).first()
                creer_mouvement_caisse(
                    montant=abs(diff),
                    devise=default_dev,
                    type_mouvement=mouvement_type,
                    entreprise_id=entree.entreprise_id,
                    succursale_id=entree.succursale_id,
                    content_object=entree,
                    entree=entree,
                    reference_piece=f'AJ-ENT-{entree.pk}',
                    motif='Ajustement entrée',
                )
        
        return Response(self.get_serializer(entree).data, status=status.HTTP_200_OK)
    
    def partial_update(self, request, *args, **kwargs):
        """Mise à jour partielle d'une entrée."""
        return self.update(request, *args, **kwargs, partial=True)

    def destroy(self, request, *args, **kwargs):
        entree = self.get_object()
        user = request.user
        total = self._total_entree(entree)
        
        with transaction.atomic():
            for ligne in entree.lignes.all():
                stock_obj, created = Stock.objects.get_or_create(
                    article=ligne.article, 
              
                    defaults={'Qte': 0, 'seuilAlert': 0}
                )
                stock_obj.Qte -= ligne.quantite
                stock_obj.save()
            
            if total > 0:
                tenant_id = entree.entreprise_id
                default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first() if tenant_id else Devise.objects.filter(est_principal=True).first()
                ligne_dev = entree.lignes.first()
                devise_annul = ligne_dev.devise if ligne_dev and ligne_dev.devise else default_dev
                creer_mouvement_caisse(
                    montant=total,
                    devise=devise_annul,
                    type_mouvement='ENTREE',
                    entreprise_id=entree.entreprise_id,
                    succursale_id=entree.succursale_id,
                    content_object=entree,
                    entree=entree,
                    reference_piece=f'ANN-ENT-{entree.pk}',
                    motif='Annulation entrée',
                )
            
            entree.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _total_entree(self, entree: Entree) -> Decimal:
        """Calcule le total d'une entrée."""
        total = Decimal('0.00')
        for l in entree.lignes.all():
            pu = l.prix_unitaire or Decimal('0')
            total += pu * Decimal(str(l.quantite))
        return total.quantize(Decimal('0.01'))

    def _solde_caisse(self, tenant_id=None, succursale_id=None):
        """Calcule le solde global de caisse (tenant + éventuellement succursale)."""
        from django.db.models import Sum
        qs = MouvementCaisse.objects.all()
        if tenant_id is not None:
            qs = qs.filter(entreprise_id=tenant_id)
        if succursale_id is not None:
            qs = qs.filter(succursale_id=succursale_id)
        entree_total = qs.filter(type='ENTREE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        sortie_total = qs.filter(type='SORTIE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        return entree_total - sortie_total

    def _solde_caisse_par_devise(self, tenant_id, succursale_id, devise_obj):
        """Calcule le solde de caisse (tenant + éventuellement succursale) pour une devise spécifique."""
        from django.db.models import Sum

        if not tenant_id:
            return Decimal('0.00')
        if not devise_obj:
            devise_obj = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
            if not devise_obj:
                return Decimal('0.00')

        qs = MouvementCaisse.objects.filter(
            entreprise_id=tenant_id,
            devise=devise_obj,
        )
        if succursale_id is not None:
            qs = qs.filter(succursale_id=succursale_id)

        entrees = qs.filter(type='ENTREE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        sorties = qs.filter(type='SORTIE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        return (entrees - sorties).quantize(Decimal('0.01'))

    @action(detail=True, methods=['get'], url_path='bon-pos')
    def bon_entree_pos(self, request, pk=None):
        """Génère un bon d'entrée au format POS."""
        entree = self.get_object()
        
        ent_ctx = self.request.user.get_entreprise(self.request)
        response_data = {
            'numero_entree': entree.pk,
            'date': entree.date_op.strftime('%d/%m/%Y %H:%M'),
            'libele': entree.libele,
            # 'description': entree.description, supprimé
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


class TypeCaisseViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """CRUD des types de caisse (canaux d'encaissement) par entreprise / succursale."""

    queryset = TypeCaisse.objects.all()
    serializer_class = TypeCaisseSerializer

    def get_queryset(self):
        return super().get_queryset().order_by('libelle', 'id')


class MouvementCaisseViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    queryset = MouvementCaisse.objects.all()
    serializer_class = MouvementCaisseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        t = self.request.query_params.get('type')
        if t in ('ENTREE', 'SORTIE'):
            qs = qs.filter(type=t)
        dmin = self.request.query_params.get('date_min')
        dmax = self.request.query_params.get('date_max')
        if dmin:
            qs = qs.filter(date__date__gte=dmin)
        if dmax:
            qs = qs.filter(date__date__lte=dmax)
        return qs.select_related('devise', 'utilisateur', 'content_type').prefetch_related('details__type_caisse').order_by('-date', '-id')

    def perform_create(self, serializer):
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        if not serializer.validated_data.get('devise'):
            default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
            devise = default_dev
        else:
            devise = serializer.validated_data.get('devise')

        type_mouvement = serializer.validated_data.get('type')
        montant = serializer.validated_data.get('montant', 0)
        if type_mouvement == 'SORTIE' and montant > 0 and devise:
            solde_qs = MouvementCaisse.objects.filter(devise=devise, entreprise_id=tenant_id)
            if branch_id is not None:
                solde_qs = solde_qs.filter(succursale_id=branch_id)
            solde_actuel = solde_qs.aggregate(
                total_entrees=models.Sum('montant', filter=models.Q(type='ENTREE')),
                total_sorties=models.Sum('montant', filter=models.Q(type='SORTIE'))
            )
            
            entrees = solde_actuel['total_entrees'] or Decimal('0')
            sorties = solde_actuel['total_sorties'] or Decimal('0')
            solde_disponible = entrees - sorties
            
            if montant > solde_disponible:
                devise_nom = devise.nom if devise else "devise inconnue"
                raise serializers.ValidationError({
                    'montant': f"Solde insuffisant en {devise_nom}. Solde disponible: {solde_disponible}, Montant demandé: {montant}. Veuillez d'abord effectuer un dépôt en {devise_nom}."
                })

        if not serializer.validated_data.get('devise'):
            serializer.save(devise=devise, entreprise_id=tenant_id, succursale_id=branch_id)
        else:
            serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)

    @action(detail=False, methods=['get'])
    def resume(self, request):
        """
        Retourne des statistiques détaillées par devise avec plus d'informations :
        - Nombre d'entrées et sorties par devise
        - Montants totaux par devise (entrées et sorties séparément)
        - Solde par devise
        - Pourcentages et ratios
        - Évolution récente
        """
        qs = self.get_queryset()
        user = request.user

        
        # Devise principale pour référence
        principal_devise = _get_principal_devise()
        
        # Statistiques par devise
        stats_by_devise = {}
        total_global_entrees = Decimal('0.00')
        total_global_sorties = Decimal('0.00')
        
        # Calcul des totaux globaux (pour pourcentages)
        for mv in qs:
            if mv.type == 'ENTREE':
                total_global_entrees += mv.montant
            else:
                total_global_sorties += mv.montant
        
        # Calcul des statistiques par devise
        for mv in qs:
            devise_obj = mv.devise or principal_devise
            sigle = devise_obj.sigle if devise_obj else 'N/A'
            
            if sigle not in stats_by_devise:
                stats_by_devise[sigle] = {
                    'devise_sigle': sigle,
                    'devise_nom': devise_obj.nom if devise_obj else 'Non spécifiée',
                    'devise_symbole': devise_obj.symbole if devise_obj else '',
                    'est_principale': devise_obj and devise_obj.est_principal if devise_obj else False,
                    'nb_entrees': 0,
                    'nb_sorties': 0,
                    'total_entrees': Decimal('0.00'),
                    'total_sorties': Decimal('0.00'),
                    'solde': Decimal('0.00'),
                    'mouvements_recent': [],  # 5 derniers mouvements
                    'pourcentage_entrees': Decimal('0.00'),
                    'pourcentage_sorties': Decimal('0.00')
                }
            
            # Statistiques de base
            if mv.type == 'ENTREE':
                stats_by_devise[sigle]['nb_entrees'] += 1
                stats_by_devise[sigle]['total_entrees'] += mv.montant
                stats_by_devise[sigle]['solde'] += mv.montant
            else:
                stats_by_devise[sigle]['nb_sorties'] += 1
                stats_by_devise[sigle]['total_sorties'] += mv.montant
                stats_by_devise[sigle]['solde'] -= mv.montant
            
            # Ajouter aux mouvements récents (max 5)
            if len(stats_by_devise[sigle]['mouvements_recent']) < 5:
                stats_by_devise[sigle]['mouvements_recent'].append({
                    'id': mv.id,
                    'date': mv.date.isoformat(),
                    'type': mv.type,
                    'montant': float(mv.montant),
                    'motif': (mv.motif_affiche()[:50] + '...') if len(mv.motif_affiche()) > 50 else mv.motif_affiche()
                })
        
        # Calcul des pourcentages et formatage final
        for sigle, devise_stats in stats_by_devise.items():
            # Formatage des montants
            devise_stats['total_entrees'] = devise_stats['total_entrees'].quantize(Decimal('0.01'))
            devise_stats['total_sorties'] = devise_stats['total_sorties'].quantize(Decimal('0.01'))
            devise_stats['solde'] = devise_stats['solde'].quantize(Decimal('0.01'))
            
            # Calcul des pourcentages
            if total_global_entrees > 0:
                devise_stats['pourcentage_entrees'] = (
                    (devise_stats['total_entrees'] / total_global_entrees) * 100
                ).quantize(Decimal('0.01'))
            
            if total_global_sorties > 0:
                devise_stats['pourcentage_sorties'] = (
                    (devise_stats['total_sorties'] / total_global_sorties) * 100
                ).quantize(Decimal('0.01'))
            
            # Ratios et indicateurs
            devise_stats['ratio_entree_sortie'] = (
                (devise_stats['total_entrees'] / devise_stats['total_sorties']).quantize(Decimal('0.01'))
                if devise_stats['total_sorties'] > 0 else Decimal('0.00')
            )
            
            devise_stats['nb_total_mouvements'] = devise_stats['nb_entrees'] + devise_stats['nb_sorties']
            
            # Statut du solde
            if devise_stats['solde'] > 0:
                devise_stats['statut_solde'] = 'positif'
            elif devise_stats['solde'] < 0:
                devise_stats['statut_solde'] = 'negatif'
            else:
                devise_stats['statut_solde'] = 'equilibre'
        
        # Trier par devise principale d'abord, puis par solde décroissant
        stats_list = sorted(
            stats_by_devise.values(),
            key=lambda x: (not x['est_principale'], -float(x['solde']))
        )
        
        # Résumé global
        resume_global = {
            'nb_devises_actives': len(stats_by_devise),
            'total_mouvements': qs.count(),
            'devise_principale': principal_devise.sigle if principal_devise else None,
            'repartition_par_type': {
                'total_entrees': total_global_entrees.quantize(Decimal('0.01')),
                'total_sorties': total_global_sorties.quantize(Decimal('0.01')),
                'solde_global_theorique': (total_global_entrees - total_global_sorties).quantize(Decimal('0.01'))
            }
        }
        
        return Response({
            'resume_global': resume_global,
            'devises': stats_list,
            'timestamp': timezone.now().isoformat()
        })

    @action(detail=False, methods=['get'], url_path='solde')
    def solde_caisse(self, request):
        """
        Retourne les soldes de caisse séparés par devise.
        Chaque devise a son propre solde indépendant.
        """
        qs = self.get_queryset()
        user = request.user

        
        # Devise principale pour identification
        principal_devise = _get_principal_devise()
        
        # Calcul des soldes par devise
        soldes_par_devise = {}
        
        for mv in qs:
            devise_obj = mv.devise or principal_devise
            sigle = devise_obj.sigle if devise_obj else 'N/A'
            
            # Initialisation si première fois
            if sigle not in soldes_par_devise:
                soldes_par_devise[sigle] = {
                    'devise_sigle': sigle,
                    'devise_nom': devise_obj.nom if devise_obj else 'Non spécifiée',
                    'devise_symbole': devise_obj.symbole if devise_obj else '',
                    'est_principale': devise_obj and devise_obj.est_principal if devise_obj else False,
                    'solde': Decimal('0.00'),
                    'total_entrees': Decimal('0.00'),
                    'total_sorties': Decimal('0.00'),
                    'nb_mouvements': 0
                }
            
            # Calcul du solde et statistiques
            if mv.type == 'ENTREE':
                soldes_par_devise[sigle]['solde'] += mv.montant
                soldes_par_devise[sigle]['total_entrees'] += mv.montant
            else:
                soldes_par_devise[sigle]['solde'] -= mv.montant
                soldes_par_devise[sigle]['total_sorties'] += mv.montant
            
            soldes_par_devise[sigle]['nb_mouvements'] += 1
        
        # Formatage final
        for devise_info in soldes_par_devise.values():
            devise_info['solde'] = devise_info['solde'].quantize(Decimal('0.01'))
            devise_info['total_entrees'] = devise_info['total_entrees'].quantize(Decimal('0.01'))
            devise_info['total_sorties'] = devise_info['total_sorties'].quantize(Decimal('0.01'))
        
        # Conversion de dict vers liste triée (devise principale en premier)
        soldes_list = list(soldes_par_devise.values())
        soldes_list.sort(key=lambda x: (not x['est_principale'], x['devise_sigle']))
        
        return Response({
            'soldes_par_devise': soldes_list,
            'devise_principale': principal_devise.sigle if principal_devise else None,
            'nb_devises_actives': len(soldes_par_devise),
            'total_mouvements_global': qs.count()
        })

    @action(detail=False, methods=['get'], url_path='tableau-bord')
    def tableau_bord_multi_devises(self, request):
        """
        Tableau de bord complet avec séparation par devise.
        Retourne toutes les informations nécessaires pour l'affichage frontend.
        """
        qs = self.get_queryset()
        user = request.user

        
        # Devise principale
        principal_devise = _get_principal_devise()
        
        # Dictionnaire pour accumuler les données par devise
        devises_data = {}
        
        for mv in qs:
            devise_obj = mv.devise or principal_devise
            sigle = devise_obj.sigle if devise_obj else 'N/A'
            
            # Initialisation de la devise si première fois
            if sigle not in devises_data:
                devises_data[sigle] = {
                    'devise_info': {
                        'sigle': sigle,
                        'nom': devise_obj.nom if devise_obj else 'Non spécifiée',
                        'symbole': devise_obj.symbole if devise_obj else '',
                        'est_principale': devise_obj and devise_obj.est_principal if devise_obj else False,
                    },
                    'solde_actuel': Decimal('0.00'),
                    'total_entrees': Decimal('0.00'),
                    'total_sorties': Decimal('0.00'),
                    'nb_entrees': 0,
                    'nb_sorties': 0,
                    'mouvements_recents': [],
                    'evolution_7j': []  # Pour le graphique
                }
            
            devise_data = devises_data[sigle]
            
            # Calculs principaux
            if mv.type == 'ENTREE':
                devise_data['solde_actuel'] += mv.montant
                devise_data['total_entrees'] += mv.montant
                devise_data['nb_entrees'] += 1
            else:
                devise_data['solde_actuel'] -= mv.montant
                devise_data['total_sorties'] += mv.montant
                devise_data['nb_sorties'] += 1
            
            # Mouvements récents (garder les 10 derniers)
            mouvement_info = {
                'id': mv.id,
                'date': mv.date,
                'type': mv.type,
                'montant': mv.montant,
                'motif': mv.motif_affiche(),
                'moyen': '',
                'reference_piece': mv.reference_piece
            }
            devise_data['mouvements_recents'].append(mouvement_info)
        
        # Post-traitement pour chaque devise
        for sigle, data in devises_data.items():
            # Formatage des montants
            data['solde_actuel'] = data['solde_actuel'].quantize(Decimal('0.01'))
            data['total_entrees'] = data['total_entrees'].quantize(Decimal('0.01'))
            data['total_sorties'] = data['total_sorties'].quantize(Decimal('0.01'))
            
            # Tri des mouvements récents par date (plus récents en premier)
            data['mouvements_recents'].sort(key=lambda x: x['date'], reverse=True)
            data['mouvements_recents'] = data['mouvements_recents'][:10]  # Garder seulement les 10 derniers
            
            # Calcul du statut du solde
            data['statut_solde'] = 'positif' if data['solde_actuel'] >= 0 else 'negatif'
            
            # Calcul du pourcentage de variation (factice pour l'instant)
            data['variation_pourcentage'] = 0  # À calculer selon la période précédente si besoin
        
        # Conversion en liste triée (devise principale en premier)
        devises_list = list(devises_data.values())
        devises_list.sort(key=lambda x: (not x['devise_info']['est_principale'], x['devise_info']['sigle']))
        
        # Statistiques globales
        total_devises = len(devises_data)
        total_mouvements = qs.count()
        devises_positives = sum(1 for d in devises_data.values() if d['solde_actuel'] > 0)
        devises_negatives = total_devises - devises_positives
        
        return Response({
            'devises': devises_list,
            'statistiques_globales': {
                'nb_devises_actives': total_devises,
                'nb_devises_positives': devises_positives,
                'nb_devises_negatives': devises_negatives,
                'total_mouvements': total_mouvements,
                'devise_principale': principal_devise.sigle if principal_devise else None
            },
            'periode': {
                'debut': qs.first().date if qs.exists() else None,
                'fin': qs.last().date if qs.exists() else None
            }
        })

    @action(detail=False, methods=['get'], url_path='soldes-simples')
    def soldes_simples(self, request):
        """
        Endpoint simple pour récupérer juste les soldes par devise.
        Optimisé pour l'affichage de widgets frontend.
        """
        qs = self.get_queryset()
        user = request.user

        
        # Devise principale
        principal_devise = _get_principal_devise()
        
        # Calcul rapide des soldes
        from django.db.models import Sum, Q
        
        # Soldes par devise via aggregation
        soldes_entrees = qs.filter(type='ENTREE').values('devise__sigle', 'devise__nom', 'devise__symbole', 'devise__est_principal').annotate(total=Sum('montant'))
        soldes_sorties = qs.filter(type='SORTIE').values('devise__sigle', 'devise__nom', 'devise__symbole', 'devise__est_principal').annotate(total=Sum('montant'))
        
        # Consolidation
        soldes_finaux = {}
        
        # Traitement des entrées
        for entree in soldes_entrees:
            sigle = entree['devise__sigle'] or (principal_devise.sigle if principal_devise else 'N/A')
            if sigle not in soldes_finaux:
                soldes_finaux[sigle] = {
                    'sigle': sigle,
                    'nom': entree['devise__nom'] or (principal_devise.nom if principal_devise else 'N/A'),
                    'symbole': entree['devise__symbole'] or (principal_devise.symbole if principal_devise else ''),
                    'est_principale': entree['devise__est_principal'] or False,
                    'solde': Decimal('0.00')
                }
            soldes_finaux[sigle]['solde'] += (entree['total'] or Decimal('0.00'))
        
        # Traitement des sorties
        for sortie in soldes_sorties:
            sigle = sortie['devise__sigle'] or (principal_devise.sigle if principal_devise else 'N/A')
            if sigle not in soldes_finaux:
                soldes_finaux[sigle] = {
                    'sigle': sigle,
                    'nom': sortie['devise__nom'] or (principal_devise.nom if principal_devise else 'N/A'),
                    'symbole': sortie['devise__symbole'] or (principal_devise.symbole if principal_devise else ''),
                    'est_principale': sortie['devise__est_principal'] or False,
                    'solde': Decimal('0.00')
                }
            soldes_finaux[sigle]['solde'] -= (sortie['total'] or Decimal('0.00'))
        
        # Formatage et tri
        soldes_list = []
        for devise_data in soldes_finaux.values():
            devise_data['solde'] = devise_data['solde'].quantize(Decimal('0.01'))
            devise_data['statut'] = 'positif' if devise_data['solde'] >= 0 else 'negatif'
            soldes_list.append(devise_data)
        
        # Tri : devise principale en premier
        soldes_list.sort(key=lambda x: (not x['est_principale'], x['sigle']))
        
        return Response({
            'soldes': soldes_list,
            'devise_principale': principal_devise.sigle if principal_devise else None,
            'timestamp': timezone.now()
        })

    @action(detail=False, methods=['get'], url_path='mouvements-par-devise')
    def mouvements_par_devise(self, request):
        """
        Récupère les mouvements filtrés par devise.
        Paramètres : ?devise=USD&limit=20
        """
        qs = self.get_queryset()
        
        # Filtres
        devise_param = request.query_params.get('devise')
        limit_param = request.query_params.get('limit', 20)
        
        try:
            limit = int(limit_param)
        except (ValueError, TypeError):
            limit = 20
            
        if devise_param:
            qs = qs.filter(devise__sigle=devise_param)
        
        # Tri par date décroissante et limitation
        mouvements = qs.order_by('-date')[:limit]
        
        # Sérialisation simplifiée
        mouvements_data = []
        for mv in mouvements:
            mouvements_data.append({
                'id': mv.id,
                'date': mv.date,
                'type': mv.type,
                'montant': mv.montant.quantize(Decimal('0.01')),
                'motif': mv.motif_affiche(),
                'moyen': '',
                'reference_piece': mv.reference_piece,
                'devise': {
                    'sigle': mv.devise.sigle if mv.devise else 'N/A',
                    'symbole': mv.devise.symbole if mv.devise else '',
                    'nom': mv.devise.nom if mv.devise else 'Non spécifiée'
                },
                'sortie_id': mv.sortie_id,
                'entree_id': mv.entree_id
            })
        
        return Response({
            'mouvements': mouvements_data,
            'filtre_devise': devise_param,
            'total_affiches': len(mouvements_data),
            'limite': limit
        })

    @action(detail=False, methods=['get'], url_path='comparaison-devises')
    def comparaison_devises(self, request):
        """
        Compare les performances entre devises avec des métriques utiles.
        """
        qs = self.get_queryset()
        user = request.user

        # Calculs par devise
        from django.db.models import Sum, Count, Avg
        
        # Agrégations par devise
        stats_devises = qs.values(
            'devise__sigle', 'devise__nom', 'devise__symbole', 'devise__est_principal'
        ).annotate(
            total_entrees=Sum('montant', filter=models.Q(type='ENTREE')),
            total_sorties=Sum('montant', filter=models.Q(type='SORTIE')),
            nb_entrees=Count('id', filter=models.Q(type='ENTREE')),
            nb_sorties=Count('id', filter=models.Q(type='SORTIE')),
            montant_moyen_entree=Avg('montant', filter=models.Q(type='ENTREE')),
            montant_moyen_sortie=Avg('montant', filter=models.Q(type='SORTIE'))
        )
        
        # Devise principale
        principal_devise = _get_principal_devise()
        
        # Traitement des résultats
        devises_comparaison = []
        total_volume_global = Decimal('0.00')
        
        for stat in stats_devises:
            sigle = stat['devise__sigle'] or (principal_devise.sigle if principal_devise else 'N/A')
            total_entrees = stat['total_entrees'] or Decimal('0.00')
            total_sorties = stat['total_sorties'] or Decimal('0.00')
            volume_total = total_entrees + total_sorties
            
            total_volume_global += volume_total
            
            devise_info = {
                'devise': {
                    'sigle': sigle,
                    'nom': stat['devise__nom'] or (principal_devise.nom if principal_devise else 'N/A'),
                    'symbole': stat['devise__symbole'] or (principal_devise.symbole if principal_devise else ''),
                    'est_principale': stat['devise__est_principal'] or False
                },
                'totaux': {
                    'entrees': total_entrees.quantize(Decimal('0.01')),
                    'sorties': total_sorties.quantize(Decimal('0.01')),
                    'solde': (total_entrees - total_sorties).quantize(Decimal('0.01')),
                    'volume_total': volume_total.quantize(Decimal('0.01'))
                },
                'compteurs': {
                    'nb_entrees': stat['nb_entrees'] or 0,
                    'nb_sorties': stat['nb_sorties'] or 0,
                    'nb_total': (stat['nb_entrees'] or 0) + (stat['nb_sorties'] or 0)
                },
                'moyennes': {
                    'montant_moyen_entree': (stat['montant_moyen_entree'] or Decimal('0.00')).quantize(Decimal('0.01')),
                    'montant_moyen_sortie': (stat['montant_moyen_sortie'] or Decimal('0.00')).quantize(Decimal('0.01'))
                }
            }
            
            devises_comparaison.append(devise_info)
        
        # Calcul des pourcentages après avoir le total global
        for devise_info in devises_comparaison:
            volume = devise_info['totaux']['volume_total']
            if total_volume_global > 0:
                devise_info['pourcentage_volume'] = (
                    (volume / total_volume_global) * 100
                ).quantize(Decimal('0.01'))
            else:
                devise_info['pourcentage_volume'] = Decimal('0.00')
        
        # Tri par volume décroissant
        devises_comparaison.sort(
            key=lambda x: (not x['devise']['est_principale'], -float(x['totaux']['volume_total']))
        )
        
        return Response({
            'devises': devises_comparaison,
            'resume_global': {
                'nb_devises': len(devises_comparaison),
                'volume_global': total_volume_global.quantize(Decimal('0.01')),
                'devise_dominante': devises_comparaison[0]['devise']['sigle'] if devises_comparaison else None
            },
            'timestamp': timezone.now()
        })

    @action(detail=False, methods=['get'])
    def export(self, request):
        # Export simple CSV
        import csv
        from django.utils.encoding import smart_str
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mouvements_caisse.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date','Type','Montant','Motif','Moyen','Référence'])
        for m in self.get_queryset():
            montant_str = _format_amount(m.montant, m.devise if hasattr(m, 'devise') else None, request.user.get_entreprise(request))
            writer.writerow([
                m.date.isoformat(), m.type, montant_str, smart_str(m.motif_affiche()), '', m.reference_piece or ''
            ])
        return response

    @action(detail=True, methods=['get'], url_path='bon-pos')
    def bon_pos(self, request, pk=None):
        """
        Ticket POS pour un mouvement de caisse (design type facture).
        - Lié à une sortie → BON DE SORTIE avec détail des articles.
        - Lié à une entrée → BON D'ENTRÉE avec détail des articles.
        - Sinon → BON CAISSE (entrée/sortie) avec motif et montant.
        """
        mv = self.get_object()
        entreprise = request.user.get_entreprise(request) or Entreprise.objects.first()

        POS_WIDTH = 80 * mm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=12, leading=14, alignment=TA_CENTER, spaceAfter=2*mm)
        subtitle_style = ParagraphStyle('Subtitle', fontName='Helvetica-Bold', fontSize=10, leading=11, alignment=TA_CENTER, spaceAfter=1*mm)
        header_style = ParagraphStyle('Header', fontName='Helvetica-Bold', fontSize=8, leading=9, alignment=TA_CENTER)
        info_style = ParagraphStyle('Info', fontName='Helvetica', fontSize=7, leading=8, alignment=TA_CENTER)
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=8, leading=9, wordWrap='CJK')
        footer_style = ParagraphStyle('Footer', fontName='Helvetica', fontSize=7, leading=8, alignment=TA_CENTER, textColor=colors.grey)

        elements = []

        # En-tête simplifié : nom, logo, slogan, téléphone uniquement
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete))
        elements.append(Spacer(1, 1*mm))

        if mv.sortie_id:
            sortie = mv.sortie
            elements.append(Paragraph("<b>BON DE SORTIE</b>", subtitle_style))
            elements.append(Paragraph(f"N° {sortie.pk}  ·  Mvt caisse #{mv.pk}", info_style))
            elements.append(Paragraph(f"Date: {mv.date.strftime('%d/%m/%Y %H:%M')}", info_style))
            devise_obj = getattr(mv, 'devise', None) or (getattr(sortie, 'devise', None) or Devise.objects.filter(est_principal=True).first())
            if devise_obj:
                elements.append(Paragraph(f"Devise: {devise_obj.sigle}", info_style))
            elements.append(Spacer(1, 1*mm))
            elements.append(Paragraph("─" * 42, info_style))
            elements.append(Spacer(1, 1*mm))

            lignes = sortie.lignes.select_related('article').all()
            col_w = [POS_WIDTH * 0.42, POS_WIDTH * 0.18, POS_WIDTH * 0.20, POS_WIDTH * 0.20]
            data = [[
                Paragraph("<b>Article</b>", header_style),
                Paragraph("<b>Qté</b>", header_style),
                Paragraph("<b>P.U.</b>", header_style),
                Paragraph("<b>Total</b>", header_style)
            ]]
            total_general = Decimal('0.00')
            for l in lignes:
                pu = l.prix_unitaire or Decimal('0')
                q = l.quantite or 0
                tot = (pu * Decimal(str(q))).quantize(Decimal('0.01'))
                total_general += tot
                data.append([
                    Paragraph(_article_display_name(l.article)[:28], normal),
                    Paragraph(str(q), normal),
                    Paragraph(f"{pu:.2f}", normal),
                    Paragraph(f"{tot:.2f}", normal)
                ])
            data.append([
                Paragraph("<b>TOTAL</b>", header_style), '', '',
                Paragraph(f"<b>{total_general:.2f} {devise_obj.symbole if devise_obj else ''}</b>", header_style)
            ])
            table = Table(data, colWidths=col_w)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)

        elif mv.entree_id:
            entree = mv.entree
            elements.append(Paragraph("<b>BON D'ENTRÉE</b>", subtitle_style))
            elements.append(Paragraph(f"N° Entrée {entree.pk}  ·  Mvt caisse #{mv.pk}", info_style))
            elements.append(Paragraph(f"Date: {mv.date.strftime('%d/%m/%Y %H:%M')}", info_style))
            if entree.libele:
                elements.append(Paragraph(f"Libellé: {entree.libele}", info_style))
            elements.append(Spacer(1, 1*mm))
            elements.append(Paragraph("─" * 42, info_style))
            elements.append(Spacer(1, 1*mm))

            lignes = entree.lignes.select_related('article', 'devise').all()
            devise_obj = getattr(mv, 'devise', None) or Devise.objects.filter(est_principal=True).first()
            col_w = [POS_WIDTH * 0.42, POS_WIDTH * 0.18, POS_WIDTH * 0.20, POS_WIDTH * 0.20]
            data = [[
                Paragraph("<b>Article</b>", header_style),
                Paragraph("<b>Qté</b>", header_style),
                Paragraph("<b>P.U.</b>", header_style),
                Paragraph("<b>Total</b>", header_style)
            ]]
            total_general = Decimal('0.00')
            for l in lignes:
                pu = l.prix_unitaire or Decimal('0')
                q = l.quantite or 0
                tot = (pu * Decimal(str(q))).quantize(Decimal('0.01'))
                total_general += tot
                data.append([
                    Paragraph(_article_display_name(l.article)[:28], normal),
                    Paragraph(str(q), normal),
                    Paragraph(f"{pu:.2f}", normal),
                    Paragraph(f"{tot:.2f}", normal)
                ])
            data.append([
                Paragraph("<b>TOTAL</b>", header_style), '', '',
                Paragraph(f"<b>{total_general:.2f} {devise_obj.symbole if devise_obj else ''}</b>", header_style)
            ])
            table = Table(data, colWidths=col_w)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)

        else:
            elements.append(Paragraph(
                "<b>BON D'ENTRÉE CAISSE</b>" if mv.type == 'ENTREE' else "<b>BON DE SORTIE CAISSE</b>",
                subtitle_style
            ))
            elements.append(Paragraph(f"Mvt #{mv.pk}  ·  {mv.date.strftime('%d/%m/%Y %H:%M')}", info_style))
            elements.append(Spacer(1, 1*mm))
            elements.append(Paragraph("─" * 42, info_style))
            elements.append(Spacer(1, 1*mm))

            montant_fmt = _format_amount(mv.montant, getattr(mv, 'devise', None))
            data = [
                [Paragraph("<b>Montant</b>", header_style), Paragraph(montant_fmt, normal)],
                [Paragraph("<b>Motif</b>", header_style), Paragraph((mv.motif_affiche() or '-')[:80], normal)],
            ]
            if mv.reference_piece:
                data.append([Paragraph("<b>Réf.</b>", header_style), Paragraph(mv.reference_piece[:30], normal)])
            col_w = [POS_WIDTH * 0.35, POS_WIDTH * 0.65]
            table = Table(data, colWidths=col_w)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(table)

        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph("─" * 42, footer_style))
        elements.append(Paragraph("Merci pour votre confiance", footer_style))

        lm = rm = 5*mm
        tm = bm = 4*mm
        avail_width = POS_WIDTH - lm - rm
        content_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        POS_HEIGHT = content_height + tm + bm + 5*mm
        doc = SimpleDocTemplate(buffer, pagesize=(POS_WIDTH, POS_HEIGHT), leftMargin=lm, rightMargin=rm, topMargin=tm, bottomMargin=bm, allowSplitting=0)
        doc.build(elements)
        buffer.seek(0)
        filename = f"MVT_{mv.pk}.pdf"
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{filename}"'})



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
        Possibilité de filtrer par type_article avec ?type_article=<id>
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
        Liste les sous-types groupés par type d'article.
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


class ClientViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour la gestion des clients (filtré par entreprise/succursale)."""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by('-date_enregistrement', '-id')
        # Liste : filtre optionnel ?is_special=true|false (strictement sur la liste)
        if getattr(self, 'action', None) == 'list':
            raw = self.request.query_params.get('is_special')
            if raw is not None:
                v = str(raw).strip().lower()
                if v in ('true', '1', 'yes', 'oui'):
                    qs = qs.filter(is_special=True)
                elif v in ('false', '0', 'no', 'non'):
                    qs = qs.filter(is_special=False)
        return qs

    @swagger_auto_schema(
        operation_summary='Recherche de clients (tenant)',
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description='Texte recherché (obligatoire) : nom, téléphone, adresse, e-mail ou code client. Ex. ?q=dupont',
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description='Nombre max de résultats (défaut 25, max 100).',
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description='Pagination (décalage).',
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Response(
                'Résultats + meta ; champ « message » si aucun client ne correspond.',
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
                        'Indiquez ce que vous cherchez avec le paramètre « q ». '
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
            q_display = (q[:200] + '…') if len(q) > 200 else q
            if branch_id is not None:
                msg = _(
                    'Aucun client ne correspond à « %(term)s » pour cette succursale. '
                    'Essayez un autre mot-clé (nom, téléphone, adresse, e-mail ou code client), '
                    'vérifiez l’orthographe ou élargissez la recherche (autre succursale si votre rôle le permet).'
                ) % {'term': q_display}
            else:
                msg = _(
                    'Aucun client ne correspond à « %(term)s » dans votre entreprise. '
                    'Essayez un autre mot-clé (nom, téléphone, adresse, e-mail ou code client) '
                    'ou vérifiez l’orthographe.'
                ) % {'term': q_display}
            payload['message'] = msg
        return Response(payload)

    @action(detail=True, methods=['get'])
    def dettes(self, request, pk=None):
        """
        Liste toutes les dettes d'un client spécifique (paginated).
        GET /api/clients/{id}/dettes/
        """
        client = self.get_object()
        dettes = DetteClient.objects.filter(client=client).select_related(
            'client', 'devise', 'sortie'
        ).prefetch_related('paiements').order_by('-date_creation', '-id')
        page = self.paginate_queryset(dettes)
        if page is not None:
            serializer = DetteClientSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DetteClientSerializer(dettes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def total_dettes(self, request, pk=None):
        """
        Calcule le total des dettes d'un client.
        GET /api/clients/{id}/total_dettes/
        """
        client = self.get_object()
        dettes = DetteClient.objects.filter(client=client)
        
        total_general = dettes.aggregate(
            total=Sum('montant_total'),
            paye=Sum('montant_paye'),
            restant=Sum('solde_restant')
        )
        
        return Response({
            'client_id': client.id,
            'client_nom': client.nom,
            'nombre_dettes': dettes.count(),
            'montant_total_dettes': total_general['total'] or 0,
            'montant_total_paye': total_general['paye'] or 0,
            'solde_restant_total': total_general['restant'] or 0,
            'dettes_en_cours': dettes.filter(statut='EN_COURS').count(),
            'dettes_payees': dettes.filter(statut='PAYEE').count(),
            'dettes_en_retard': dettes.filter(statut='RETARD').count(),
        })


class DetteClientViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """ViewSet pour la gestion des dettes clients (filtré par entreprise/succursale)."""
    queryset = DetteClient.objects.select_related('client', 'devise', 'sortie').all()
    serializer_class = DetteClientSerializer

    def get_queryset(self):
        return super().get_queryset().select_related('client', 'devise', 'sortie').order_by('-date_creation', '-id')

    def perform_create(self, serializer):
        sortie = serializer.validated_data.get('sortie')
        if sortie and sortie.statut != 'EN_CREDIT':
            raise serializers.ValidationError({
                'sortie': f"Impossible de créer une dette pour cette sortie. "
                         f"La sortie #{sortie.pk} (Client: {sortie.client.nom if sortie.client else 'Anonyme'}) a le statut '{sortie.statut}'. "
                         f"Seules les sorties avec le statut 'EN_CREDIT' peuvent générer une dette."
            })
        if sortie and DetteClient.objects.filter(sortie=sortie).exists():
            raise serializers.ValidationError({
                'sortie': f"Une dette existe déjà pour la sortie #{sortie.pk}."
            })
        date_echeance = serializer.validated_data.get('date_echeance') or (timezone.now().date() + timezone.timedelta(days=30))
        tenant_id, branch_id = self.get_tenant_ids()
        if not tenant_id:
            raise serializers.ValidationError({'non_field_errors': 'Contexte entreprise manquant.'})
        serializer.save(date_echeance=date_echeance, entreprise_id=tenant_id, succursale_id=branch_id)

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
        Liste toutes les dettes payées (paginated).
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
        Liste tous les mouvements de paiement liés à cette dette (paginated).
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


class PaiementDetteViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """Paiements de dettes via MouvementCaisse liés à DetteClient (content_type / object_id). URLs inchangées."""
    queryset = MouvementCaisse.objects.filter(type='ENTREE')
    serializer_class = PaiementDetteReadSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        ct_dette = ContentType.objects.get_for_model(DetteClient)
        return (
            super()
            .get_queryset()
            .filter(content_type=ct_dette)
            .select_related('devise', 'utilisateur', 'content_type')
            .prefetch_related('details__type_caisse')
            .order_by('-date', '-id')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return PaiementDetteWriteSerializer
        return PaiementDetteReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = PaiementDetteWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        mc = serializer.save()
        return Response(
            PaiementDetteReadSerializer(mc, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='recu-paiement', permission_classes=[IsAuthenticated])
    def recu_paiement_pdf(self, request, pk=None):
        """
        Génère le reçu de paiement (PDF) pour un paiement de dette.
        S'inspire du design de la facture de vente. Peut être utilisé à chaque paiement (partiel ou total).
        GET /api/paiements-dettes/{id}/recu-paiement/
        """
        from django.contrib.contenttypes.models import ContentType as CTModel

        user = request.user
        paiement = self.get_object()
        ct_dette = CTModel.objects.get_for_model(DetteClient)
        if paiement.content_type_id != ct_dette.id or not paiement.object_id:
            return Response({'error': _('Mouvement invalide pour un reçu de paiement de dette.')}, status=400)
        dette = DetteClient.objects.filter(pk=paiement.object_id).select_related('client').first()
        if not dette:
            return Response({'error': _('Dette introuvable.')}, status=404)
        client = dette.client
        entreprise = user.get_entreprise(request)

        POS_WIDTH = 80 * mm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()

        # Polices réduites, design compact (impression POS) — même comportement que facture
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=7, leading=8, wordWrap='CJK')
        article_cell_style = ParagraphStyle('ArticleCell', parent=normal, wordWrap='CJK', allowWidows=0, allowOrphans=0)
        title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=10, leading=11, alignment=TA_LEFT, spaceAfter=1*mm)
        header_style = ParagraphStyle('Header', fontName='Helvetica-Bold', fontSize=8, leading=9, alignment=TA_LEFT)
        info_style = ParagraphStyle('Info', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_LEFT)
        footer_style = ParagraphStyle('Footer', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_LEFT, textColor=colors.black)
        right_style = ParagraphStyle('Right', fontName='Helvetica', fontSize=7, leading=8, alignment=TA_RIGHT)

        elements = []

        # En-tête compact (nom + tél serrés, titre juste en dessous) — comme facture POS
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        entete = {'entreprise': {**entete['entreprise'], 'slogan': ''}}
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete, compact=True))

        # Titre au début : REÇU DE PAIEMENT
        elements.append(Paragraph(f"<b>{_('REÇU DE PAIEMENT')}</b>", title_style))
        devise_obj = paiement.devise or dette.devise or Devise.objects.filter(est_principal=True).first()
        symbole = (devise_obj.symbole or devise_obj.sigle or '') if devise_obj else ''

        elements.append(Paragraph(f"{_('N° Reçu')}: RECU-{paiement.pk:06d}", info_style))
        elements.append(Paragraph(f"{_('Date et heure')}: {paiement.date.strftime('%d/%m/%Y %H:%M')}", info_style))
        elements.append(Spacer(1, 1*mm))

        # CLIENT (labels traduits)
        elements.append(Paragraph(f"<b>{_('Client')}</b>", header_style))
        elements.append(Paragraph(f"{_('Nom')}: {client.nom}", normal))
        if getattr(client, 'adresse', None) and client.adresse:
            elements.append(Paragraph(f"{_('Adresse')}: {client.adresse}", normal))
        if getattr(client, 'telephone', None) and client.telephone:
            elements.append(Paragraph(f"{_('Tél')}: {client.telephone}", normal))
        if getattr(client, 'email', None) and client.email:
            elements.append(Paragraph(f"{_('Email')}: {client.email}", normal))
        elements.append(Spacer(1, 1*mm))

        # Montant dette (une ligne, sans détail)
        montant_total_dette = dette.montant_total
        solde_apres = dette.solde_restant
        elements.append(Paragraph(f"<b>{_('Montant dette')}</b>: {montant_total_dette:.2f} {symbole}", normal))
        elements.append(Spacer(1, 1*mm))

        # Produits concernés par la dette — même répartition que facture (Article 25 %, Qté 10 %, P.U. 10 %, Total 55 %)
        sortie = dette.sortie
        if sortie and hasattr(sortie, 'lignes'):
            lignes_sortie = sortie.lignes.select_related('article').all()
            if lignes_sortie:
                elements.append(Paragraph(f"<b>{_('Produits concernés par la dette')}</b>", header_style))
                prod_data = [
                    [Paragraph(f"<b>{_('Article')}</b>", article_cell_style), Paragraph(f"<b>{_('Qté')}</b>", normal), Paragraph(f"<b>{_('P.U.')}</b>", normal), Paragraph(f"<b>{_('Total')}</b>", normal)],
                ]
                for ligne in lignes_sortie:
                    article = ligne.article
                    nom_article = _article_display_name(article)
                    qte = ligne.quantite or 0
                    pu = Decimal(str(ligne.prix_unitaire or 0))
                    total_ligne = (Decimal(str(qte)) * pu).quantize(Decimal('0.01'))
                    prod_data.append([
                        Paragraph(nom_article, article_cell_style),
                        Paragraph(str(qte), normal),
                        Paragraph(f"{pu:.2f} {symbole}", normal),
                        Paragraph(f"{total_ligne:.2f} {symbole}", normal),
                    ])
                prod_table = Table(prod_data, colWidths=[POS_WIDTH*0.25, POS_WIDTH*0.10, POS_WIDTH*0.15, POS_WIDTH*0.50])
                prod_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                    ('LEFTPADDING', (0, 0), (-1, -1), 2),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(prod_table)
                elements.append(Spacer(1, 1.5*mm))

        # Détail du paiement — Libellé 25 %, Valeur et Reste en colonnes côte à côte
        elements.append(Paragraph(f"<b>{_('Détail du paiement')}</b>", header_style))
        table_paiement_data = [
            [Paragraph(f"<b>{_('Libellé')}</b>", normal), Paragraph(f"<b>{_('Valeur')}</b>", normal), Paragraph(f"<b>{_('Reste')}</b>", normal)],
            [Paragraph(_("Montant payé (ce reçu)"), normal), Paragraph(f"<b>{paiement.montant:.2f} {symbole}</b>", normal), Paragraph(f"<b>{solde_apres:.2f} {symbole}</b>", normal)],
        ]
        table_paiement = Table(table_paiement_data, colWidths=[POS_WIDTH*0.25, POS_WIDTH*0.25, POS_WIDTH*0.50])
        table_paiement.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(table_paiement)
        elements.append(Spacer(1, 1.5*mm))

        # Historique des paiements (fond blanc, traduit)
        autres_paiements = (
            MouvementCaisse.objects.filter(
                content_type=ct_dette,
                object_id=dette.pk,
                type='ENTREE',
            )
            .exclude(pk=paiement.pk)
            .select_related('devise')
            .prefetch_related('details__type_caisse')
            .order_by('-date')[:5]
        )
        if autres_paiements.exists():
            elements.append(Paragraph(f"<b>{_('Autres paiements sur cette dette')}</b>", header_style))
            hist_data = [[Paragraph(f"<b>{_('Date')}</b>", normal), Paragraph(f"<b>{_('Montant')}</b>", normal), Paragraph(f"<b>{_('Moyen')}</b>", normal)]]
            for p in autres_paiements:
                moyen_h = mouvement_moyen_affiche(p) or '-'
                hist_data.append([
                    Paragraph(p.date.strftime('%d/%m/%Y %H:%M'), normal),
                    Paragraph(f"{p.montant:.2f} {symbole}", normal),
                    Paragraph(moyen_h or '-', normal),
                ])
            hist_table = Table(hist_data, colWidths=[POS_WIDTH*0.35, POS_WIDTH*0.30, POS_WIDTH*0.35])
            hist_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(hist_table)
            elements.append(Spacer(1, 1*mm))

        # Pied de page (comme facture POS) — poussé en bas par un spacer, avec décorateur
        lm = rm = tm = bm = 4*mm
        avail_width = POS_WIDTH - lm - rm
        imprim_par = (paiement.utilisateur.get_full_name() or paiement.utilisateur.username) if paiement.utilisateur else (user.get_full_name() or user.username)
        footer_parts = [
            Paragraph(_("Merci pour votre confiance. Conservez ce reçu comme justificatif de paiement."), normal),
            Spacer(1, 0.5*mm),
            Paragraph(_("Imprimé par: %(user)s") % {'user': imprim_par}, footer_style),
            Paragraph(_("Le %(date)s") % {'date': timezone.now().strftime('%d/%m/%Y à %H:%M')}, footer_style),
            Spacer(1, 1*mm),
            Paragraph("—" * 30, footer_style),
        ]
        main_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        footer_height = sum(flow.wrap(avail_width, 100000)[1] for flow in footer_parts)
        min_height = POS_WIDTH + 20*mm
        POS_HEIGHT = max(main_height + footer_height + tm + bm + 3*mm, min_height)
        spacer_bottom = POS_HEIGHT - tm - bm - main_height - footer_height
        if spacer_bottom > 0:
            elements.append(Spacer(1, spacer_bottom))
        elements.extend(footer_parts)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(POS_WIDTH, POS_HEIGHT),
            leftMargin=lm,
            rightMargin=rm,
            topMargin=tm,
            bottomMargin=bm,
            allowSplitting=0
        )
        doc.build(elements)
        buffer.seek(0)
        filename = f"RECU_PAIEMENT_{paiement.pk}.pdf"
        return HttpResponse(buffer, content_type='application/pdf', headers={'Content-Disposition': f'inline; filename="{filename}"'})