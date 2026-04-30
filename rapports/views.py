from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum, Q, F, DecimalField, OuterRef, Subquery, Value, Exists, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils import translation
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from decimal import Decimal
import io
import math

from config.pagination import StandardResultsSetPagination


class InventaireResultsSetPagination(StandardResultsSetPagination):
    """Pagination uniquement si complet=false : plafond élevé pour les gros inventaires."""
    max_page_size = 5000


class InventaireStockLine:
    """Ligne d'inventaire : article + quantités (stock réel ou 0 si aucune fiche Stock)."""
    __slots__ = ('article', 'Qte', 'seuilAlert')

    def __init__(self, article, qte=0, seuil=0):
        self.article = article
        self.Qte = qte
        self.seuilAlert = seuil

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from stock.models import (
    Stock,
    LigneEntree,
    LigneSortie,
    Sortie,
    Article,
    Entree,
    Entreprise,
    DetteClient,
)
from .serializers import (
    InventaireArticleSerializer,
    BonEntreeArticleSerializer,
    BonAchatSerializer,
    RecapitulatifAchatSerializer
)
from users.permissions import IsSuperAdminOrAdmin, IsAdminOrUser
from .utils.pdf_generator import PDFGenerator
from .utils.entete import get_entete_entreprise


def _dettes_rapport_is_special_filter(request):
    """
    Filtre « client spécial » pour les rapports dettes (query string, pas body).
    - Param absent : uniquement clients spéciaux (is_special=True), comme demandé métier.
    - is_special=true : spéciaux uniquement.
    - is_special=false : clients standards uniquement.
    - is_special=all (ou both, *, any, tous) : tous les clients (sans filtre sur is_special).

    Returns:
        dict: {'is_special': bool} pour filtrer via `ClientEntreprise` (lien entreprise courant)
        None: aucun filtre sur is_special
    Raises:
        ValueError: paramètre non reconnu
    """
    raw = request.query_params.get('is_special')
    if raw is None:
        return {'is_special': True}
    raw_l = str(raw).strip().lower()
    if raw_l in ('all', 'both', '*', 'any', 'tous'):
        return None
    if raw_l in ('true', '1', 'yes', 'oui'):
        return {'is_special': True}
    if raw_l in ('false', '0', 'no', 'non'):
        return {'is_special': False}
    raise ValueError(
        _('Paramètre is_special invalide pour ce rapport. Utilisez: true, false, ou all.')
    )


def _format_report_quantity(value, max_decimals=3):
    """Affiche une quantité sans zéros inutiles (41.00 -> 41)."""
    if value is None or value == '':
        return ''
    try:
        d = Decimal(str(value))
        quantum = Decimal('1').scaleb(-max_decimals)
        d = d.quantize(quantum)
        s = f"{d:f}"
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s
    except Exception:
        return str(value)


class RapportsViewSet(viewsets.ViewSet):
    """
    ViewSet pour la génération des différents rapports.
    Accès réservé aux Admin et User (Agent). SuperAdmin n'a pas accès aux rapports métier.
    """
    permission_classes = [IsAdminOrUser]

    @staticmethod
    def _build_meta_generation(user):
        return {
            'printed_at': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'printed_by': (user.get_full_name() or user.username) if user else '',
        }

    def _get_entete_entreprise(self, entreprise, user):
        """Génère l'en-tête simplifié : nom, logo, slogan, téléphone uniquement."""
        return get_entete_entreprise(entreprise)

    def _get_tenant_ids_strict(self, request):
        """
        Contexte multi-tenant :
        - entreprise obligatoire (via membership / JWT).
        - succursale : depuis JWT ou default_succursale ; peut être None (agent sans succursale).
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        eid = entreprise.pk if entreprise else None
        branch_id = getattr(request, 'branch_id', None)

        if branch_id is None and user.is_agent(request):
            m = user.get_current_membership(request)
            branch_id = m.default_succursale_id if m else None

        return eid, branch_id

    @staticmethod
    def _default_exercice_dates(request):
        """
        Période d'exercice par défaut (comptabilité courante) : 1er janv. → 31 déc.
        de l'année de référence (année courante si date_fin absente, sinon année de date_fin).
        """
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        y_now = timezone.now().year
        if not date_fin:
            date_fin = f'{y_now}-12-31'
        if not date_debut:
            try:
                y = int(str(date_fin).strip()[:4])
            except (ValueError, TypeError):
                y = y_now
            date_debut = f'{y}-01-01'
        return date_debut, date_fin

    @staticmethod
    def _parse_inventaire_date_bounds(request):
        """Valide date_debut / date_fin (YYYY-MM-DD) et retourne (str, str, date, date)."""
        date_debut_s, date_fin_s = RapportsViewSet._default_exercice_dates(request)
        try:
            d0 = date.fromisoformat(str(date_debut_s).strip()[:10])
            d1 = date.fromisoformat(str(date_fin_s).strip()[:10])
        except ValueError:
            raise ValidationError(
                {
                    'detail': _(
                        'date_debut et date_fin doivent être au format ISO YYYY-MM-DD '
                        '(ex. 2026-01-01).'
                    )
                }
            )
        if d0 > d1:
            raise ValidationError(
                {'detail': _('date_debut doit être antérieure ou égale à date_fin.')}
            )
        return date_debut_s, date_fin_s, d0, d1

    def _filter_articles_mouvements_periode(self, article_qs, request, d_debut: date, d_fin: date):
        """
        Garde les articles ayant au moins une ligne d'entrée ou de sortie sur la période
        (date du bon d'entrée / de la sortie, partie date uniquement, bornes inclusives).
        """
        user = request.user
        eid, branch_id = self._get_tenant_ids_strict(request)
        if not eid:
            return article_qs.none()

        le = LigneEntree.objects.filter(
            article_id=OuterRef('article_id'),
            entree__entreprise_id=eid,
            entree__date_op__date__gte=d_debut,
            entree__date_op__date__lte=d_fin,
        )
        if user.is_agent(request) and branch_id is not None:
            le = le.filter(entree__succursale_id=branch_id)

        ls = LigneSortie.objects.filter(
            article_id=OuterRef('article_id'),
            sortie__entreprise_id=eid,
            sortie__date_creation__date__gte=d_debut,
            sortie__date_creation__date__lte=d_fin,
        )
        if user.is_agent(request) and branch_id is not None:
            ls = ls.filter(sortie__succursale_id=branch_id)

        return article_qs.filter(Q(Exists(le)) | Q(Exists(ls)))

    def _inventaire_article_queryset(self, request):
        """
        Tous les articles du tenant (entreprise + succursale si agent avec branche),
        avec quantités issues de Stock (0 si aucune fiche Stock pour l'article).
        """
        user = request.user
        eid, branch_id = self._get_tenant_ids_strict(request)
        if not eid:
            return Article.objects.none()

        stock_sq = Stock.objects.filter(article_id=OuterRef('article_id'))
        qs = (
            Article.objects.filter(entreprise_id=eid)
            .annotate(
                inv_qte=Coalesce(
                    Subquery(stock_sq.values('Qte')[:1]),
                    Value(Decimal('0.000')),
                    output_field=DecimalField(max_digits=12, decimal_places=3),
                ),
                inv_seuil=Coalesce(
                    Subquery(stock_sq.values('seuilAlert')[:1]),
                    Value(Decimal('0.000')),
                    output_field=DecimalField(max_digits=12, decimal_places=3),
                ),
            )
            .select_related(
                'sous_type_article',
                'sous_type_article__type_article',
                'unite',
            )
            .order_by('nom_scientifique', 'article_id')
        )
        if user.is_agent(request) and branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        return qs

    def _serialize_inventaire(self, request, *, force_complet: bool = False):
        """
        Corps du rapport d'inventaire (dict prêt pour JSON ou PDF).
        Par défaut (complet=true) : tous les articles, sans pagination.
        complet=false : pagination (page_size jusqu'à 5000).
        Si filtrer_mouvements=true : seuls les articles avec au moins une entrée ou une sortie
        dont la date tombe dans [date_debut, date_fin] (tenant-scopé). Sinon : catalogue complet.
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        date_debut, date_fin, d0, d1 = self._parse_inventaire_date_bounds(request)
        type_article = request.query_params.get('type_article')
        statut_filtre = request.query_params.get('statut')
        filtrer_mouvements = request.query_params.get('filtrer_mouvements', 'false').lower() in (
            'true',
            '1',
            'yes',
            'oui',
        )
        if force_complet:
            complet = True
        else:
            complet = request.query_params.get('complet', 'true').lower() not in (
                'false',
                '0',
                'no',
                'non',
            )

        qs = self._inventaire_article_queryset(request)
        if filtrer_mouvements:
            qs = self._filter_articles_mouvements_periode(qs, request, d0, d1)
        if type_article:
            qs = qs.filter(
                sous_type_article__type_article__libelle__icontains=type_article
            )
        if statut_filtre:
            statut_upper = statut_filtre.upper()
            if statut_upper == 'RUPTURE':
                qs = qs.filter(inv_qte=0)
            elif statut_upper == 'ALERTE':
                qs = qs.filter(inv_qte__gt=0, inv_qte__lte=F('inv_seuil'))
            elif statut_upper == 'NORMAL':
                qs = qs.filter(inv_qte__gt=F('inv_seuil'))

        lines = [
            InventaireStockLine(a, a.inv_qte, a.inv_seuil) for a in qs
        ]
        total_articles = len(lines)
        en_rupture = sum(1 for L in lines if L.Qte == 0)
        en_alerte = sum(1 for L in lines if L.Qte > 0 and L.Qte <= L.seuilAlert)
        normaux = sum(1 for L in lines if L.Qte > L.seuilAlert)

        entete = self._get_entete_entreprise(entreprise, user)
        resp = {
            'entete': entete,
            'titre': _("RAPPORT D'INVENTAIRE"),
            'periode': {
                'date_debut': date_debut,
                'date_fin': date_fin,
            },
            'filtres': {
                'filtrer_mouvements': filtrer_mouvements,
                'description': _(
                    'Si filtrer_mouvements=true : articles ayant au moins une entrée '
                    '(date du bon) ou une sortie (date de création) dans l’intervalle.'
                )
                if filtrer_mouvements
                else _('Catalogue complet du tenant : la période sert uniquement à l’affichage.'),
            },
            'statistiques': {
                'total_articles': total_articles,
                'en_alerte': en_alerte,
                'en_rupture': en_rupture,
                'normaux': normaux,
            },
            'complet': complet,
        }

        if complet:
            resp['articles'] = InventaireArticleSerializer(lines, many=True).data
            return resp

        paginator = InventaireResultsSetPagination()
        page_lines = paginator.paginate_queryset(lines, request)
        resp['articles'] = InventaireArticleSerializer(page_lines, many=True).data
        if page_lines is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return resp

    @action(detail=False, methods=['get'], url_path='inventaire')
    def inventaire(self, request):
        """
        Rapport d'inventaire : **tous** les articles catalogue du tenant (entreprise / succursale),
        avec stock et seuils (0 si aucune fiche Stock).

        Paramètres optionnels:
        - date_debut, date_fin: YYYY-MM-DD (validés). Défaut exercice : 01-01 → 31-12 (année courante ou année de date_fin).
        - filtrer_mouvements: false (défaut) = tout le catalogue du tenant (période = libellé + validation des dates) ;
          true = ne garder que les articles avec au moins une entrée ou une sortie dans l’intervalle.
        - type_article: Filtrer par type d'article (libellé)
        - statut: Filtrer par statut (NORMAL, ALERTE, RUPTURE)
        - complet: true (défaut) = liste intégrale sans pagination ; false = pagination (page_size jusqu'à 5000)

        GET /api/rapports/inventaire/
        GET /api/rapports/inventaire/?date_debut=2026-01-01&date_fin=2026-12-31
        GET /api/rapports/inventaire/?filtrer_mouvements=false
        GET /api/rapports/inventaire/?statut=ALERTE&complet=false
        """
        return Response(self._serialize_inventaire(request))

    @action(detail=False, methods=['get'], url_path='inventaire/pdf')
    def inventaire_pdf(self, request):
        """
        Export PDF du rapport d'inventaire.
        Format A4, prêt pour l'impression.
        Liste **complète** (tous les articles du tenant), sans pagination.

        Paramètres: mêmes que l'action inventaire (dates, filtrer_mouvements, type_article, statut).

        GET /api/rapports/inventaire/pdf/
        GET /api/rapports/inventaire/pdf/?date_debut=2026-01-01&date_fin=2026-06-30
        GET /api/rapports/inventaire/pdf/?filtrer_mouvements=false
        """
        data = self._serialize_inventaire(request, force_complet=True)
        data['meta_generation'] = self._build_meta_generation(request.user)

        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_inventaire_pdf(data)
        
        # Créer la réponse HTTP avec le PDF
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Nom du fichier avec la date
        filename = f"inventaire_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _get_bon_entree_queryset_and_stats(self, request):
        """Retourne (queryset stocks, dict statistiques) pour le rapport de réquisition."""
        user = request.user
        eid, branch_id = self._get_tenant_ids_strict(request)
        base_filter = {'article__entreprise_id': eid} if eid else {}
        if user.is_agent(request) and branch_id is not None:
            base_filter['article__succursale_id'] = branch_id
        inclure_normaux = request.query_params.get('inclure_normaux', 'false').lower() == 'true'
        if inclure_normaux:
            stocks = Stock.objects.filter(**base_filter)
        else:
            stocks = Stock.objects.filter(
                Q(Qte=0) | Q(Qte__lte=F('seuilAlert')),
                **base_filter
            )
        stocks = stocks.select_related(
            'article',
            'article__sous_type_article',
            'article__sous_type_article__type_article',
            'article__unite'
        ).order_by('-id')
        total = stocks.count()
        en_rupture = stocks.filter(Qte=0).count()
        en_alerte = stocks.filter(Qte__gt=0, Qte__lte=F('seuilAlert')).count()
        return stocks, {
            'total_articles': total,
            'en_rupture': en_rupture,
            'en_alerte': en_alerte
        }

    @action(detail=False, methods=['get'], url_path='bon-entree')
    def bon_entree(self, request):
        """
        Rapport de réquisition.
        
        Liste les articles dont le stock est au seuil d'alerte ou en rupture.
        Les colonnes 'quantite' et 'prix_total' sont vides pour être remplies manuellement
        lors de l'approvisionnement.
        
        Paramètres optionnels:
        - inclure_normaux: true/false (par défaut: false) - Inclure aussi les articles en stock normal
        
        GET /api/rapports/bon-entree/
        GET /api/rapports/bon-entree/?inclure_normaux=true
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        stocks, statistiques = self._get_bon_entree_queryset_and_stats(request)
        
        # Pagination pour l'API JSON
        paginator = StandardResultsSetPagination()
        page_stocks = paginator.paginate_queryset(stocks, request)
        serializer = BonEntreeArticleSerializer(page_stocks, many=True)
        entete = self._get_entete_entreprise(entreprise, user)
        
        resp = {
            'entete': entete,
            'titre': _("RAPPORT DE RÉQUISITION"),
            'instructions': _('Remplir manuellement les colonnes "Quantité" et "Prix Total" lors de l\'approvisionnement. Les montants sont en devise principale mentionnée dans l\'en-tête.'),
            'statistiques': statistiques,
            'articles': serializer.data
        }
        if page_stocks is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return Response(resp)
    
    @action(detail=False, methods=['get'], url_path='bon-entree/pdf')
    def bon_entree_pdf(self, request):
        """
        Export PDF du rapport de réquisition.
        Format A4, prêt pour l'impression avec colonnes à remplir manuellement.
        
        Paramètres: inclure_normaux (optionnel), extra_articles (optionnel, ex. PRLI0007 ou ID1,ID2 pour ajouter des articles en état normal), lang (fr/en).
        
        GET /api/rapports/bon-entree/pdf/
        GET /api/rapports/bon-entree/pdf/?extra_articles=PRLI0007&lang=fr
        """
        # Activer la langue de la requête pour que le PDF soit traduit (titre, sous-titres, etc.)
        lang = (request.GET.get("lang") or getattr(request, "LANGUAGE_CODE", "fr") or "fr").strip().lower()
        if lang not in ("en", "fr"):
            lang = "fr"
        translation.activate(lang)

        # Données pour le PDF : tous les articles (en rupture + en alerte), sans pagination, + extra_articles (ex. état normal)
        user = request.user
        entreprise = user.get_entreprise(request)
        stocks, statistiques = self._get_bon_entree_queryset_and_stats(request)
        stocks_list = list(stocks)
        # Articles supplémentaires demandés (ex. état normal) : ?extra_articles=PRLI0007 ou extra_articles=ID1,ID2
        extra_param = (request.GET.get('extra_articles') or '').strip()
        extra_ids = [x.strip() for x in extra_param.split(',') if x.strip()]
        if extra_ids:
            existing_ids = {s.article.article_id for s in stocks_list}
            extra_ids_to_add = [aid for aid in extra_ids if aid not in existing_ids]
            if extra_ids_to_add:
                eid, branch_id = self._get_tenant_ids_strict(request)
                extra_filter = {'article__entreprise_id': eid} if eid else {}
                if user.is_agent(request) and branch_id is not None:
                    extra_filter['article__succursale_id'] = branch_id
                extra_stocks = Stock.objects.filter(
                    article__article_id__in=extra_ids_to_add,
                    **extra_filter
                ).select_related(
                    'article',
                    'article__sous_type_article',
                    'article__sous_type_article__type_article',
                    'article__unite'
                ).order_by('article__article_id')
                stocks_list.extend(list(extra_stocks))
        serializer = BonEntreeArticleSerializer(stocks_list, many=True)
        entete = self._get_entete_entreprise(entreprise, user)
        data = {
            'entete': entete,
            'titre': _("RAPPORT DE RÉQUISITION"),
            'instructions': _('Remplir manuellement les colonnes "Quantité" et "Prix Total" lors de l\'approvisionnement. Les montants sont en devise principale mentionnée dans l\'en-tête.'),
            'statistiques': statistiques,
            'articles': serializer.data,
            'meta_generation': self._build_meta_generation(user),
        }

        # Générer le PDF (toutes les _() dans le générateur utilisent la langue active)
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_bon_entree_pdf(data)
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response["Content-Language"] = lang
        # Nom du fichier
        filename = f"rapport_requisition_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    @action(detail=False, methods=['get'], url_path='clients-dettes')
    def clients_dettes(self, request):
        """
        Retourne un client spécifique avec ses dettes détaillées (JSON).
        
        Paramètre obligatoire:
        - client_id: ID du client (ex: CLI0001)
        
        GET /api/rapports/clients-dettes/?client_id=CLI0001

        Filtre is_special (query) — même logique que clients-dettes-general :
        par défaut (param absent) seuls les clients spéciaux sont visibles ;
        is_special=all pour tout client du tenant ; true / false pour forcer le périmètre.
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        eid, branch_id = self._get_tenant_ids_strict(request)

        try:
            special_kw = _dettes_rapport_is_special_filter(request)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer le client_id depuis les paramètres de requête
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({
                'error': 'Le paramètre "client_id" est obligatoire',
                'exemple': '/api/rapports/clients-dettes/?client_id=CLI0001'
            }, status=status.HTTP_400_BAD_REQUEST)

        from stock.models import Client, DetteClient
        client_qs = Client.objects.filter(id=client_id)
        if eid:
            client_qs = client_qs.filter(liens_entreprise__entreprise_id=eid).distinct()
        if user.is_agent(request) and branch_id is not None and eid:
            client_qs = client_qs.filter(
                Q(liens_entreprise__entreprise_id=eid)
                & (
                    Q(liens_entreprise__succursale_id=branch_id)
                    | Q(liens_entreprise__succursale__isnull=True)
                )
            ).distinct()
        try:
            client = client_qs.get()
        except Client.DoesNotExist:
            return Response({
                'error': f'Client avec ID "{client_id}" non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)

        lien = client.liens_entreprise.filter(entreprise_id=eid).first() if eid else None
        if special_kw is not None and (not lien or lien.is_special != special_kw['is_special']):
            return Response({
                'error': _(
                    'Client non trouvé ou hors du périmètre du filtre is_special pour ce rapport.'
                )
            }, status=status.HTTP_404_NOT_FOUND)

        clients_data = []
        from decimal import Decimal

        # Traiter uniquement ce client
        c = client
        dettes_qs = DetteClient.objects.filter(client=c).select_related('devise', 'sortie')
        if user.is_agent(request) and branch_id is not None:
            dettes_qs = dettes_qs.filter(succursale_id=branch_id)
        dettes = []
        # per-client totals for EN_COURS
        tot_montant_encours_client = Decimal('0.00')
        tot_paye_encours_client = Decimal('0.00')
        tot_solde_encours_client = Decimal('0.00')

        for d in dettes_qs:
            # accumulate per-client totals for 'EN_COURS' dettes
            if d.statut == 'EN_COURS':
                try:
                    tot_montant_encours_client += d.montant_total or Decimal('0.00')
                except Exception:
                    pass
                try:
                    tot_paye_encours_client += d.montant_paye or Decimal('0.00')
                except Exception:
                    pass
                try:
                    tot_solde_encours_client += d.solde_restant or Decimal('0.00')
                except Exception:
                    pass

            # include sortie products (articles) for this debt's sortie
            sortie_info = None
            if d.sortie:
                produits = []
                lignes = LigneSortie.objects.filter(sortie=d.sortie).select_related('article')
                for ls in lignes:
                    art = ls.article
                    produits.append({
                        'article_id': getattr(art, 'article_id', None),
                        'nom_scientifique': getattr(art, 'nom_scientifique', ''),
                        'nom_commercial': getattr(art, 'nom_commercial', ''),
                        'quantite': ls.quantite,
                        'prix_unitaire': str(ls.prix_unitaire)
                    })
                sortie_info = {
                    'id': d.sortie.id,
                    'motif': getattr(d.sortie, 'motif', '') or '',
                    'produits': produits
                }

            dettes.append({
                'id': d.id,
                'sortie': sortie_info,
                'montant_total': str(d.montant_total),
                'montant_paye': str(d.montant_paye),
                'solde_restant': str(d.solde_restant),
                'devise': {'id': d.devise.id, 'sigle': d.devise.sigle, 'nom': d.devise.nom, 'symbole': d.devise.symbole} if d.devise else None,
                'date_creation': d.date_creation.strftime('%Y-%m-%d %H:%M') if d.date_creation else None,
                'date_echeance': d.date_echeance.strftime('%Y-%m-%d') if d.date_echeance else None,
                'statut': d.statut,
                'commentaire': d.commentaire
            })

        clients_data.append({
            'id': c.id,
            'nom': c.nom,
            'telephone': c.telephone,
            'adresse': c.adresse,
            'email': c.email,
            'is_special': c.is_special,
            'date_enregistrement': c.date_enregistrement.strftime('%Y-%m-%d %H:%M') if c.date_enregistrement else None,
            'dettes': dettes,
            'totaux_encours': {
                'montant_total': str(tot_montant_encours_client.quantize(Decimal('0.01'))),
                'montant_paye': str(tot_paye_encours_client.quantize(Decimal('0.01'))),
                'solde_restant': str(tot_solde_encours_client.quantize(Decimal('0.01')))
            }
        })

        entete = self._get_entete_entreprise(entreprise, user) if entreprise else self._get_entete_entreprise(Entreprise.objects.first(), user)

        # Calculer les totaux pour ce client uniquement
        client_totaux = clients_data[0].get('totaux_encours', {}) if clients_data else {}

        return Response({
            'entete': entete,
            'titre': _("Dettes du client: %(nom)s") % {'nom': client.nom},
            'clients': clients_data,
            'totaux_encours': {
                'montant_total': client_totaux.get('montant_total', '0.00'),
                'montant_paye': client_totaux.get('montant_paye', '0.00'),
                'solde_restant': client_totaux.get('solde_restant', '0.00')
            }
        })

    @action(detail=False, methods=['get'], url_path='clients-dettes/pdf')
    def clients_dettes_pdf(self, request):
        """Génère le PDF des clients et dettes."""
        json_response = self.clients_dettes(request)
        if json_response.status_code != 200:
            return json_response

        data = json_response.data
        data['meta_generation'] = self._build_meta_generation(request.user)
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_clients_dettes_pdf(data)

        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"clients_dettes_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'], url_path='clients-dettes-general')
    def clients_dettes_general(self, request):
        """
        Rapport général synthétique des dettes clients.
        Liste tous les clients ayant des dettes (solde_restant > 0) avec leurs totaux.
        Rapport synthétique sans détails des dettes individuelles.
        
        Paramètres optionnels:
        - date_debut: Date de début (format: YYYY-MM-DD) - Si fournie, filtre les dettes créées à partir de cette date
        - date_fin: Date de fin (format: YYYY-MM-DD) - Optionnel, filtre les dettes créées jusqu'à cette date
        
        GET /api/rapports/clients-dettes-general/
        GET /api/rapports/clients-dettes-general/?date_debut=2025-01-01
        GET /api/rapports/clients-dettes-general/?date_debut=2025-01-01&date_fin=2025-12-31

        Filtre is_special (query) :
        - absent → uniquement clients spéciaux (is_special=true) ;
        - is_special=true / false → périmètre explicite ;
        - is_special=all → tous les clients (spéciaux + standards), toujours scoping entreprise/succursale.
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        eid, branch_id = self._get_tenant_ids_strict(request)

        try:
            special_kw = _dettes_rapport_is_special_filter(request)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        from stock.models import Client, DetteClient
        from decimal import Decimal

        # Récupération des paramètres de date
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        
        # Conversion des dates si fournies
        date_debut_obj = None
        date_fin_obj = None
        
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Format de date_debut invalide. Utilisez le format YYYY-MM-DD',
                    'exemple': '2025-01-01'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Format de date_fin invalide. Utilisez le format YYYY-MM-DD',
                    'exemple': '2025-12-31'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que date_debut <= date_fin si les deux sont fournies
        if date_debut_obj and date_fin_obj and date_debut_obj > date_fin_obj:
            return Response({
                'error': 'La date_debut doit être antérieure ou égale à la date_fin'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Construire le filtre de base pour les dettes
        filtre_dettes = {
            'solde_restant__gt': 0,
            'statut': 'EN_COURS'
        }
        
        # Ajouter le filtre de date si fourni
        if date_debut_obj:
            filtre_dettes['date_creation__date__gte'] = date_debut_obj
        if date_fin_obj:
            filtre_dettes['date_creation__date__lte'] = date_fin_obj

        clients_avec_dettes = Client.objects.filter(
            dettes__solde_restant__gt=0,
            dettes__statut='EN_COURS',
        )
        if eid:
            clients_avec_dettes = clients_avec_dettes.filter(dettes__entreprise_id=eid)
        if user.is_agent(request) and branch_id is not None:
            clients_avec_dettes = clients_avec_dettes.filter(dettes__succursale_id=branch_id)

        if special_kw is not None and eid:
            clients_avec_dettes = clients_avec_dettes.filter(
                liens_entreprise__entreprise_id=eid,
                liens_entreprise__is_special=special_kw['is_special'],
            ).distinct()

        # Appliquer le filtre de date sur les dettes si nécessaire
        if date_debut_obj or date_fin_obj:
            if date_debut_obj:
                clients_avec_dettes = clients_avec_dettes.filter(
                    dettes__date_creation__date__gte=date_debut_obj
                )
            if date_fin_obj:
                clients_avec_dettes = clients_avec_dettes.filter(
                    dettes__date_creation__date__lte=date_fin_obj
                )
        
        clients_avec_dettes = clients_avec_dettes.distinct().order_by('-date_enregistrement', 'nom')

        # Pagination : ne traiter que les clients de la page courante
        paginator = StandardResultsSetPagination()
        page_clients = paginator.paginate_queryset(clients_avec_dettes, request)
        if page_clients is None:
            page_clients = clients_avec_dettes

        clients_data = []
        tot_montant_global = Decimal('0.00')
        tot_paye_global = Decimal('0.00')
        tot_solde_global = Decimal('0.00')

        for client in page_clients:
            lien = client.liens_entreprise.filter(entreprise_id=eid).first() if eid else None
            # Récupérer toutes les dettes EN_COURS du client avec le filtre de date
            dettes_encours = DetteClient.objects.filter(
                client=client,
                **filtre_dettes
            ).select_related('devise')
            if user.is_agent(request) and branch_id is not None:
                dettes_encours = dettes_encours.filter(succursale_id=branch_id)

            # Calculer les totaux pour ce client
            tot_montant_client = Decimal('0.00')
            tot_paye_client = Decimal('0.00')
            tot_solde_client = Decimal('0.00')

            for dette in dettes_encours:
                tot_montant_client += dette.montant_total or Decimal('0.00')
                tot_paye_client += dette.montant_paye or Decimal('0.00')
                tot_solde_client += dette.solde_restant or Decimal('0.00')

            # Ne garder que les clients avec un solde > 0
            if tot_solde_client > 0:
                clients_data.append({
                    'id': client.id,
                    'nom': client.nom,
                    'telephone': client.telephone or '',
                    'adresse': client.adresse or '',
                    'email': client.email or '',
                    'is_special': bool(lien.is_special) if lien else False,
                    'totaux_encours': {
                        'montant_total': str(tot_montant_client.quantize(Decimal('0.01'))),
                        'montant_paye': str(tot_paye_client.quantize(Decimal('0.01'))),
                        'solde_restant': str(tot_solde_client.quantize(Decimal('0.01')))
                    }
                })

                # Accumuler les totaux globaux (pour la page uniquement en pagination)
                tot_montant_global += tot_montant_client
                tot_paye_global += tot_paye_client
                tot_solde_global += tot_solde_client

        entete = self._get_entete_entreprise(entreprise, user) if entreprise else self._get_entete_entreprise(Entreprise.objects.first(), user)

        # Construire le titre avec la période si des dates sont fournies
        titre = _('Rapport général des dettes clients')
        periode = None
        if date_debut_obj or date_fin_obj:
            if date_debut_obj and date_fin_obj:
                titre = _('Rapport général des dettes clients (%(debut)s - %(fin)s)') % {'debut': date_debut_obj.strftime('%d/%m/%Y'), 'fin': date_fin_obj.strftime('%d/%m/%Y')}
                periode = {
                    'date_debut': date_debut,
                    'date_fin': date_fin
                }
            elif date_debut_obj:
                titre = _('Rapport général des dettes clients (à partir du %(date)s)') % {'date': date_debut_obj.strftime('%d/%m/%Y')}
                periode = {
                    'date_debut': date_debut,
                    'date_fin': None
                }
            elif date_fin_obj:
                titre = _('Rapport général des dettes clients (jusqu\'au %(date)s)') % {'date': date_fin_obj.strftime('%d/%m/%Y')}
                periode = {
                    'date_debut': None,
                    'date_fin': date_fin
                }

        resp = {
            'entete': entete,
            'titre': titre,
            'periode': periode,
            'clients': clients_data,
            'totaux_globaux': {
                'montant_total': str(tot_montant_global.quantize(Decimal('0.01'))),
                'montant_paye': str(tot_paye_global.quantize(Decimal('0.01'))),
                'solde_restant': str(tot_solde_global.quantize(Decimal('0.01'))),
                'nombre_clients': len(clients_data)
            }
        }
        if page_clients is not None and paginator.page is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return Response(resp)

    @action(detail=False, methods=['get'], url_path='clients-dettes-general/pdf')
    def clients_dettes_general_pdf(self, request):
        """Génère le PDF du rapport général synthétique des dettes clients."""
        json_response = self.clients_dettes_general(request)
        if json_response.status_code != 200:
            return json_response

        data = json_response.data
        data['meta_generation'] = self._build_meta_generation(request.user)
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_clients_dettes_general_pdf(data)

        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"rapport_dettes_clients_general_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    def _build_bon_achat_data(self, request, *, for_pdf=False):
        """
        Construit les données du bon d'achat.
        - for_pdf=False: pagination JSON active
        - for_pdf=True: liste complète (sans pagination) pour export PDF
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        
        # Récupération des paramètres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        article_id = request.query_params.get('article_id')
        entree_id = request.query_params.get('entree_id')
        
        # Mode 1: entree_id fourni -> filtre direct par entrée, sans dates obligatoires.
        # Mode 2: pas de entree_id -> filtrage par période (date_debut requis).
        if entree_id:
            try:
                entree_id_int = int(str(entree_id).strip())
            except (TypeError, ValueError):
                return Response(
                    {
                        'error': 'Le paramètre "entree_id" doit être un entier valide',
                        'exemple': '/api/rapports/bon-achat/?entree_id=12'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            date_debut_obj = None
            date_fin_obj = None
        else:
            if not date_debut:
                return Response({
                    'error': 'Le paramètre "date_debut" est obligatoire (sauf si entree_id est fourni)',
                    'exemple': '/api/rapports/bon-achat/?date_debut=2025-11-01'
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                if date_fin:
                    date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                else:
                    date_fin_obj = timezone.now().date()
            except ValueError:
                return Response({
                    'error': 'Format de date invalide. Utilisez le format YYYY-MM-DD',
                    'exemple': '2025-11-01'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        eid, branch_id = self._get_tenant_ids_strict(request)
        base_entree_filter = {'entree__entreprise_id': eid} if eid else {}
        if user.is_agent(request) and branch_id is not None:
            base_entree_filter['entree__succursale_id'] = branch_id
        lignes_entree = LigneEntree.objects.filter(**base_entree_filter).select_related(
            'article',
            'article__unite',
            'entree',
            'devise'
        ).order_by('-date_entree', '-id')
        if entree_id:
            lignes_entree = lignes_entree.filter(entree_id=entree_id_int)
        else:
            lignes_entree = lignes_entree.filter(
                date_entree__date__gte=date_debut_obj,
                date_entree__date__lte=date_fin_obj,
            )
        
        # Filtrage par article si spécifié
        if article_id:
            lignes_entree = lignes_entree.filter(article__article_id=article_id)
        
        # Statistiques sur l'ensemble
        total_lignes = lignes_entree.count()
        nombre_entrees = lignes_entree.values('entree').distinct().count()
        
        # Calcul des totaux par devise (sur tout le queryset pour les stats)
        totaux_par_devise = lignes_entree.values(
            'devise__sigle',
            'devise__symbole'
        ).annotate(
            nombre_lignes=Sum('quantite'),
            total_montant=Sum(
                F('quantite') * F('prix_unitaire'),
                output_field=DecimalField(max_digits=14, decimal_places=2)
            )
        )
        
        # Formatage des totaux
        recapitulatif = []
        for total in totaux_par_devise:
            recapitulatif.append({
                'devise_sigle': total['devise__sigle'] or 'N/A',
                'devise_symbole': total['devise__symbole'] or '',
                'nombre_lignes': total['nombre_lignes'],
                'total_montant': total['total_montant'] or Decimal('0.00')
            })
        
        if for_pdf:
            lignes_list = list(lignes_entree)
            serializer = BonAchatSerializer(lignes_list, many=True)
            pagination_meta = None
        else:
            # Pagination JSON uniquement
            paginator = StandardResultsSetPagination()
            page_lignes = paginator.paginate_queryset(lignes_entree, request)
            serializer = BonAchatSerializer(page_lignes, many=True)
            pagination_meta = {
                'count': paginator.page.paginator.count if page_lignes is not None else len(serializer.data),
                'next': paginator.get_next_link() if page_lignes is not None else None,
                'previous': paginator.get_previous_link() if page_lignes is not None else None,
                'page_size': paginator.get_page_size(request) if page_lignes is not None else None,
            }
        
        # Générer l'en-tête complet
        entete = self._get_entete_entreprise(entreprise, user)

        entree_details = None
        if entree_id:
            entree_obj = lignes_entree.select_related('entree', 'entree__succursale', 'entree__entreprise').first()
            if entree_obj and getattr(entree_obj, 'entree', None):
                e = entree_obj.entree
                entree_details = {
                    'id': e.id,
                    'libele': e.libele,
                    'description': getattr(e, 'description', '') or '',
                    'date_op': e.date_op.strftime('%Y-%m-%d %H:%M') if getattr(e, 'date_op', None) else None,
                    'entreprise': getattr(getattr(e, 'entreprise', None), 'nom', '') or '',
                    'succursale': getattr(getattr(e, 'succursale', None), 'nom', '') or '',
                }
        
        resp = {
            'entete': entete,
            'titre': _("BON D'ACHAT - APPROVISIONNEMENTS EFFECTUÉS"),
            'periode': {
                'date_debut': date_debut,
                'date_fin': (date_fin or timezone.now().date().strftime('%Y-%m-%d')) if not entree_id else None
            },
            'statistiques': {
                'total_lignes': total_lignes,
                'nombre_entrees': nombre_entrees
            },
            'entree_details': entree_details,
            'recapitulatif': recapitulatif,
            'achats': serializer.data,
            'meta_generation': self._build_meta_generation(user),
        }
        if not for_pdf and pagination_meta is not None:
            resp['count'] = pagination_meta['count']
            resp['next'] = pagination_meta['next']
            resp['previous'] = pagination_meta['previous']
            resp['page_size'] = pagination_meta['page_size']
        return resp

    @action(detail=False, methods=['get'], url_path='bon-achat')
    def bon_achat(self, request):
        """
        Bon d'achat - Liste des approvisionnements effectués.
        
        Liste tous les approvisionnements (entrées) à partir d'une date donnée.
        
        Paramètres:
        - entree_id: Filtrer par N° d'entrée spécifique (optionnel, prioritaire)
        - date_debut: Date de début (obligatoire si entree_id absent, format: YYYY-MM-DD)
        - date_fin: Date de fin (optionnel, format: YYYY-MM-DD)
        - article_id: Filtrer par article spécifique (optionnel)
        
        GET /api/rapports/bon-achat/?entree_id=12
        GET /api/rapports/bon-achat/?date_debut=2025-11-01
        GET /api/rapports/bon-achat/?date_debut=2025-11-01&date_fin=2025-11-30
        GET /api/rapports/bon-achat/?date_debut=2025-11-01&article_id=CAPE0001
        GET /api/rapports/bon-achat/?entree_id=12&article_id=CAPE0001
        """
        data = self._build_bon_achat_data(request, for_pdf=False)
        if isinstance(data, Response):
            return data
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='bon-achat/pdf')
    def bon_achat_pdf(self, request):
        """
        Export PDF du bon d'achat.
        Format A4, prêt pour l'impression avec support multi-devises.
        
        Paramètres: mêmes que l'action bon_achat (entree_id possible sans dates)
        
        GET /api/rapports/bon-achat/pdf/?entree_id=12
        GET /api/rapports/bon-achat/pdf/?date_debut=2025-11-01
        GET /api/rapports/bon-achat/pdf/?date_debut=2025-11-01&date_fin=2025-11-30
        GET /api/rapports/bon-achat/pdf/?entree_id=12&article_id=CAPE0001
        """
        # Données complètes (sans pagination) pour le PDF
        data = self._build_bon_achat_data(request, for_pdf=True)
        if isinstance(data, Response):
            return data
        
        # Générer le PDF
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_bon_achat_pdf(data)
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Nom du fichier
        filename = f"bon_achat_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    def _parse_ventes_dates(self, request):
        """
        Période des ventes avec priorités:
        1) date_jour (prioritaire)
        2) mois + annee
        3) date_debut + date_fin
        """
        date_jour = (request.query_params.get('date_jour') or '').strip()
        mois = (request.query_params.get('mois') or '').strip()
        annee = (request.query_params.get('annee') or '').strip()
        ds = (request.query_params.get('date_debut') or '').strip()
        df = (request.query_params.get('date_fin') or '').strip()

        if date_jour:
            try:
                d = date.fromisoformat(date_jour[:10])
            except ValueError:
                raise ValidationError({'detail': _('Format date_jour invalide (YYYY-MM-DD).')})
            return d, d

        if mois or annee:
            if not (mois and annee):
                raise ValidationError({'detail': _('Les paramètres mois et annee doivent être fournis ensemble.')})
            try:
                m = int(mois)
                y = int(annee)
            except ValueError:
                raise ValidationError({'detail': _('mois et annee doivent être numériques.')})
            if m < 1 or m > 12:
                raise ValidationError({'detail': _('mois doit être compris entre 1 et 12.')})
            if y < 1900 or y > 2100:
                raise ValidationError({'detail': _('annee invalide.')})
            from calendar import monthrange
            d0 = date(y, m, 1)
            d1 = date(y, m, monthrange(y, m)[1])
            return d0, d1

        if not ds or not df:
            raise ValidationError(
                {
                    'detail': _(
                        'Fournissez soit date_jour, soit mois+annee, soit date_debut et date_fin '
                        '(format YYYY-MM-DD) pour le rapport des ventes.'
                    )
                }
            )
        try:
            d0 = date.fromisoformat(ds[:10])
            d1 = date.fromisoformat(df[:10])
        except ValueError:
            raise ValidationError({'detail': _('Formats date_debut / date_fin invalides (YYYY-MM-DD).')})
        if d0 > d1:
            raise ValidationError({'detail': _('date_debut doit être antérieure ou égale à date_fin.')})
        return d0, d1

    def _build_ventes_report(self, request, *, for_pdf=False):
        """
        Construit le JSON du rapport des ventes (lignes de sortie : article, qté, PU, référence).

        JSON (for_pdf=False) : pagination SQL via page / page_size ; totaux sur toute la période en agrégat BDD.
        PDF (for_pdf=True) : toutes les lignes, sans clé pagination.
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        d0, d1 = self._parse_ventes_dates(request)
        client_id = (request.query_params.get('client_id') or '').strip()
        client_nom = (request.query_params.get('client_nom') or '').strip()
        reference = (request.query_params.get('reference') or '').strip()
        statut_paiement = (request.query_params.get('statut_paiement') or '').strip().upper()
        montant_min_raw = (request.query_params.get('montant_min') or '').strip()
        montant_max_raw = (request.query_params.get('montant_max') or '').strip()
        eid, branch_id = self._get_tenant_ids_strict(request)
        if not eid:
            raise ValidationError({'detail': _('Contexte entreprise manquant.')})

        montant_min = None
        montant_max = None
        if montant_min_raw:
            try:
                montant_min = Decimal(montant_min_raw.replace(',', '.'))
            except Exception:
                raise ValidationError({'detail': _('montant_min invalide.')})
        if montant_max_raw:
            try:
                montant_max = Decimal(montant_max_raw.replace(',', '.'))
            except Exception:
                raise ValidationError({'detail': _('montant_max invalide.')})
        if montant_min is not None and montant_max is not None and montant_min > montant_max:
            raise ValidationError({'detail': _('montant_min doit être inférieur ou égal à montant_max.')})
        if statut_paiement and statut_paiement not in ('COMPTANT', 'CREDIT'):
            raise ValidationError({'detail': _('statut_paiement doit être COMPTANT ou CREDIT.')})

        base_sortie = {'sortie__entreprise_id': eid}
        if user.is_agent(request) and branch_id is not None:
            base_sortie['sortie__succursale_id'] = branch_id

        lignes_qs = (
            LigneSortie.objects.filter(
                sortie__date_creation__date__gte=d0,
                sortie__date_creation__date__lte=d1,
                **base_sortie,
            )
            .select_related('sortie', 'sortie__client', 'article', 'devise')
            .prefetch_related('lots_utilises__lot_entree')
            .order_by('sortie__date_creation', 'sortie_id', 'id')
        )

        if client_id:
            lignes_qs = lignes_qs.filter(sortie__client_id=client_id)
        if client_nom:
            lignes_qs = lignes_qs.filter(sortie__client__nom__icontains=client_nom)
        if reference:
            ref_q = Q(sortie__motif__icontains=reference)
            if reference.isdigit():
                ref_q = ref_q | Q(sortie_id=int(reference))
            ref_up = reference.upper()
            if ref_up.startswith('FACT-'):
                fact_part = ref_up.replace('FACT-', '').strip()
                if fact_part.isdigit():
                    ref_q = ref_q | Q(sortie_id=int(fact_part))
            lignes_qs = lignes_qs.filter(ref_q)
        if montant_min is not None or montant_max is not None:
            line_total = ExpressionWrapper(
                F('quantite') * F('prix_unitaire'),
                output_field=DecimalField(max_digits=20, decimal_places=2),
            )
            if montant_min is not None:
                lignes_qs = lignes_qs.annotate(_line_total=line_total).filter(_line_total__gte=montant_min)
            if montant_max is not None:
                lignes_qs = lignes_qs.annotate(_line_total=line_total).filter(_line_total__lte=montant_max)

        if statut_paiement:
            dettes_non_soldees = DetteClient.objects.filter(
                sortie_id=OuterRef('sortie_id'),
                statut__in=['EN_COURS', 'RETARD'],
            )
            lignes_qs = lignes_qs.annotate(_has_credit=Exists(dettes_non_soldees))
            if statut_paiement == 'CREDIT':
                lignes_qs = lignes_qs.filter(Q(sortie__statut='EN_CREDIT') | Q(_has_credit=True))
            else:  # COMPTANT
                lignes_qs = lignes_qs.filter(sortie__statut='PAYEE', _has_credit=False)

        sortie_scope = Sortie.objects.filter(
            entreprise_id=eid,
            date_creation__date__gte=d0,
            date_creation__date__lte=d1,
        )
        if user.is_agent(request) and branch_id is not None:
            sortie_scope = sortie_scope.filter(succursale_id=branch_id)
        if client_id:
            sortie_scope = sortie_scope.filter(client_id=client_id)
        if client_nom:
            sortie_scope = sortie_scope.filter(client__nom__icontains=client_nom)
        if reference:
            ref_q_scope = Q(motif__icontains=reference)
            if reference.isdigit():
                ref_q_scope = ref_q_scope | Q(id=int(reference))
            sortie_scope = sortie_scope.filter(ref_q_scope)
        if statut_paiement == 'CREDIT':
            sortie_scope = sortie_scope.filter(statut='EN_CREDIT')
        elif statut_paiement == 'COMPTANT':
            sortie_scope = sortie_scope.filter(statut='PAYEE')

        # Totaux sur la période complète (requêtes agrégées, sans charger toutes les lignes)
        agg = lignes_qs.aggregate(
            total_qte=Sum('quantite'),
            total_montant=Sum(
                ExpressionWrapper(
                    F('quantite') * F('prix_unitaire'),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                )
            ),
        )
        tot_qte = Decimal(str(agg['total_qte'] or 0))
        tot_m_vente = (agg['total_montant'] or Decimal('0')).quantize(Decimal('0.01'))
        total_benefice = Decimal('0.00')
        for ls in lignes_qs:
            if ls.lots_utilises.exists():
                benef_ligne = sum(
                    (Decimal(str(lu.quantite)) * (Decimal(str(lu.prix_vente)) - Decimal(str(lu.prix_achat))))
                    for lu in ls.lots_utilises.all()
                )
            else:
                pu_achat_ls = ls.get_cout_achat_unitaire()
                if not isinstance(pu_achat_ls, Decimal):
                    pu_achat_ls = Decimal(str(pu_achat_ls))
                pu_vente_ls = ls.prix_unitaire
                if not isinstance(pu_vente_ls, Decimal):
                    pu_vente_ls = Decimal(str(pu_vente_ls))
                benef_ligne = Decimal(str(ls.quantite)) * (pu_vente_ls - pu_achat_ls)
            total_benefice += benef_ligne
        total_benefice = total_benefice.quantize(Decimal('0.01'))
        total_sorties = sortie_scope.count()
        total_clients = sortie_scope.exclude(client_id__isnull=True).values('client_id').distinct().count()
        sorties_credit = sortie_scope.filter(statut='EN_CREDIT').count()
        sorties_comptant = sortie_scope.filter(statut='PAYEE').count()

        pagination_meta = None
        if for_pdf:
            page_slice_qs = lignes_qs
        else:
            try:
                page = int(request.query_params.get('page', 1))
            except (TypeError, ValueError):
                page = 1
            page = max(1, page)
            try:
                page_size = int(
                    request.query_params.get(
                        'page_size', StandardResultsSetPagination.page_size
                    )
                )
            except (TypeError, ValueError):
                page_size = StandardResultsSetPagination.page_size
            page_size = max(
                1, min(page_size, StandardResultsSetPagination.max_page_size)
            )

            count = lignes_qs.count()
            total_pages = max(1, math.ceil(count / page_size)) if count else 1
            if page > total_pages and count:
                page = total_pages
            start = (page - 1) * page_size
            page_slice_qs = lignes_qs[start : start + page_size]

            pagination_meta = {
                'page': page,
                'page_size': page_size,
                'count': count,
                'total_pages': total_pages,
                'has_next': start + page_size < count,
                'has_previous': page > 1,
            }

        # Une fois le queryset slicé (pagination), Django interdit .distinct() dessus : on matérialise la page.
        page_lines = list(page_slice_qs)

        lignes_ventes = []
        for ligne in page_lines:
            s = ligne.sortie
            pu_achat = ligne.get_cout_achat_unitaire()
            if not isinstance(pu_achat, Decimal):
                pu_achat = Decimal(str(pu_achat))
            pu_vente = ligne.prix_unitaire
            if not isinstance(pu_vente, Decimal):
                pu_vente = Decimal(str(pu_vente))
            q = ligne.quantite
            qd = Decimal(str(q or 0))
            if ligne.lots_utilises.exists():
                benefice_ligne = sum(
                    (Decimal(str(lu.quantite)) * (Decimal(str(lu.prix_vente)) - Decimal(str(lu.prix_achat))))
                    for lu in ligne.lots_utilises.all()
                ).quantize(Decimal('0.01'))
            else:
                benefice_ligne = (qd * (pu_vente - pu_achat)).quantize(Decimal('0.01'))
            ref = f"FACT-{int(s.id):06d}"

            lignes_ventes.append(
                {
                    'sortie_id': s.id,
                    'date': s.date_creation.strftime('%Y-%m-%d %H:%M') if s.date_creation else '',
                    'client': s.client.nom if s.client else _('Client anonyme'),
                    'statut_paiement': 'CREDIT' if (s.statut == 'EN_CREDIT') else 'COMPTANT',
                    'article': ligne.article.nom_scientifique,
                    'pu_achat': str(pu_achat.quantize(Decimal('0.01'))),
                    'pu_vente': str(pu_vente),
                    'quantite': q,
                    'benefice': str(benefice_ligne),
                    'reference': ref,
                }
            )

        out = {
            'entete': self._get_entete_entreprise(entreprise, user),
            'titre': _("RAPPORT DES VENTES"),
            'periode': {'date_debut': str(d0), 'date_fin': str(d1)},
            'lignes_ventes': lignes_ventes,
            'total_quantite': tot_qte,
            'total_montant_vente': str(tot_m_vente),
            'meta_generation': self._build_meta_generation(user),
            'filtres': {
                'client_id': client_id or None,
                'client_nom': client_nom or None,
                'reference': reference or None,
                'statut_paiement': statut_paiement or None,
                'montant_min': str(montant_min) if montant_min is not None else None,
                'montant_max': str(montant_max) if montant_max is not None else None,
                'date_jour': (request.query_params.get('date_jour') or None),
                'mois': (request.query_params.get('mois') or None),
                'annee': (request.query_params.get('annee') or None),
            },
            'resume_global': {
                'total_sorties': total_sorties,
                'total_clients': total_clients,
                'sorties_comptant': sorties_comptant,
                'sorties_credit': sorties_credit,
                'total_quantite': str(tot_qte),
                'total_montant_vente': str(tot_m_vente),
                'total_benefice': str(total_benefice),
            },
        }
        # Titre dynamique selon filtres actifs
        titre_suffix = []
        if request.query_params.get('date_jour'):
            titre_suffix.append(_("Journalier"))
        elif request.query_params.get('mois') and request.query_params.get('annee'):
            titre_suffix.append(_("Mensuel"))
        else:
            titre_suffix.append(_("Période"))
        if client_id or client_nom:
            titre_suffix.append(_("Client"))
        if statut_paiement:
            titre_suffix.append(statut_paiement)
        if montant_min is not None or montant_max is not None:
            titre_suffix.append(_("Montant"))
        if titre_suffix:
            out['titre'] = f"{out['titre']} ({' | '.join(titre_suffix)})"
        if pagination_meta is not None:
            out['pagination'] = pagination_meta
        return out

    @action(detail=False, methods=['get'], url_path='ventes')
    def ventes(self, request):
        """
        Rapport des ventes sur une période stricte.

        Paramètres obligatoires:
        - date_jour (YYYY-MM-DD), ou mois+annee, ou date_debut+date_fin.

        Filtres optionnels:
        - client_id, client_nom, reference
        - montant_min, montant_max
        - statut_paiement = COMPTANT | CREDIT

        Pagination (requêtes BDD directes : LIMIT/OFFSET + agrégats SQL pour les totaux période) :
        - page (défaut 1), page_size (défaut 25, max 200).

        Les champs total_quantite et total_montant_vente portent sur **toute la période**, pas seulement la page.

        Contenu:
        - Lignes : article, quantité, PU achat (FIFO), PU vente, référence (sortie + pièce caisse si présente).

        GET /api/rapports/ventes/?date_jour=2026-01-31
        GET /api/rapports/ventes/?mois=1&annee=2026
        GET /api/rapports/ventes/?date_debut=2026-01-01&date_fin=2026-01-31&page=1&page_size=25
        GET /api/rapports/ventes/?date_debut=2026-01-01&date_fin=2026-01-31&client_id=CLI0001&statut_paiement=CREDIT
        """
        try:
            return Response(self._build_ventes_report(request))
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='ventes/pdf')
    def ventes_pdf(self, request):
        """
        Export PDF du rapport des ventes (mêmes paramètres que /ventes/).

        GET /api/rapports/ventes/pdf/?date_jour=2026-01-31
        GET /api/rapports/ventes/pdf/?mois=1&annee=2026
        GET /api/rapports/ventes/pdf/?date_debut=2026-01-01&date_fin=2026-01-31&client_id=CLI0001&statut_paiement=COMPTANT
        """
        try:
            data = self._build_ventes_report(request, for_pdf=True)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_ventes_pdf(data)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"rapport_ventes_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _build_fiche_stock_data(self, request, pk=None):
        """Construit les données (JSON/PDF) de la fiche de stock avec calcul FIFO."""
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied(_("Utilisateur non authentifié."))
        entreprise = user.get_entreprise(request)
        eid, branch_id = self._get_tenant_ids_strict(request)
        article_qs = Article.objects.filter(pk=pk)
        if eid:
            article_qs = article_qs.filter(entreprise_id=eid)
        if user.is_agent(request) and branch_id is not None:
            article_qs = article_qs.filter(succursale_id=branch_id)
        article = article_qs.first()
        if not article:
            raise NotFound(_("Article non trouvé ou accès refusé."))

        date_min = request.query_params.get('date_min')
        date_max = request.query_params.get('date_max')

        stock_row = Stock.objects.filter(article=article).first()
        type_article = getattr(getattr(article, 'sous_type_article', None), 'type_article', None)

        # Récupération des mouvements
        entrees_qs = LigneEntree.objects.filter(article=article)
        sorties_qs = LigneSortie.objects.filter(article=article)
        if user.is_agent(request) and branch_id is not None:
            entrees_qs = entrees_qs.filter(entree__succursale_id=branch_id)
            sorties_qs = sorties_qs.filter(sortie__succursale_id=branch_id)
        
        if date_min:
            entrees_qs = entrees_qs.filter(date_entree__date__gte=date_min)
            sorties_qs = sorties_qs.filter(date_sortie__date__gte=date_min)
        if date_max:
            entrees_qs = entrees_qs.filter(date_entree__date__lte=date_max)
            sorties_qs = sorties_qs.filter(date_sortie__date__lte=date_max)
        
        entrees = entrees_qs.values('date_entree', 'quantite', 'prix_unitaire', 'entree__libele')
        sorties = sorties_qs.values('date_sortie', 'quantite', 'sortie__motif')

        # Construction de la liste des mouvements
        mouvements = []
        for e in entrees:
            mouvements.append({
                'datetime': e['date_entree'],
                'designation': e['entree__libele'] or _("Entrée"),
                'q_in': e['quantite'],
                'pu_in': e['prix_unitaire'] or Decimal('0'),
                'q_out': 0
            })
        for s in sorties:
            mouvements.append({
                'datetime': s['date_sortie'],
                'designation': s.get('sortie__motif') or _("Sortie"),
                'q_in': 0,
                'pu_in': Decimal('0'),
                'q_out': s['quantite']
            })
        
        # Tri chronologique (entrées avant sorties pour même datetime)
        mouvements.sort(key=lambda m: (m['datetime'], 0 if m['q_in']>0 else 1))

        # Calcul FIFO
        fifo_layers = []
        stock_qty = Decimal('0')
        stock_val = Decimal('0')
        rows = []

        for mv in mouvements:
            q_in = Decimal(str(mv['q_in'] or 0))
            pu_in = mv['pu_in']
            pt_in = q_in * pu_in
            q_out = Decimal(str(mv['q_out'] or 0))
            pt_out = Decimal('0')

            if q_in:
                # Entrée
                fifo_layers.append([q_in, pu_in])
                stock_qty += q_in
                stock_val += pt_in
            else:
                # Sortie avec calcul FIFO
                reste = q_out
                for layer in fifo_layers:
                    if reste == 0:
                        break
                    take = min(layer[0], reste)
                    pt_out += take * layer[1]
                    layer[0] -= take
                    reste -= take
                fifo_layers = [l for l in fifo_layers if l[0] > 0]
                stock_qty -= q_out
                stock_val -= pt_out

            # PU sortie = coût moyen sorti (PT / Qté)
            pu_out = (pt_out / q_out) if q_out else Decimal('0')
            stock_pu = (stock_val / stock_qty) if stock_qty else Decimal('0')
            rows.append(
                {
                    'datetime': mv['datetime'].strftime('%Y-%m-%d %H:%M') if mv['datetime'] else '',
                    'designation': mv['designation'],
                    'entree': {
                        'quantite': str(q_in),
                        'pu': str(pu_in.quantize(Decimal('0.01'))),
                        'pt': str(pt_in.quantize(Decimal('0.01'))),
                    } if q_in else None,
                    'sortie': {
                        'quantite': str(q_out),
                        'pu': str(pu_out.quantize(Decimal('0.01'))),
                        'pt': str(pt_out.quantize(Decimal('0.01'))),
                    } if q_out else None,
                    'stock': {
                        'quantite': str(stock_qty),
                        'pu': str(stock_pu.quantize(Decimal('0.01'))) if stock_qty else '',
                        'pt': str(stock_val.quantize(Decimal('0.01'))),
                    },
                }
            )

        return {
            'entete': get_entete_entreprise(entreprise),
            'titre': _("FICHE DE STOCK"),
            'article_details': {
                'article_id': article.article_id,
                'nom_scientifique': article.nom_scientifique,
                'nom_commercial': article.nom_commercial,
                'type_article': getattr(type_article, 'libelle', None),
                'sous_type_article': getattr(getattr(article, 'sous_type_article', None), 'libelle', None),
                'unite': getattr(getattr(article, 'unite', None), 'nom', None),
                'stock_actuel': str(getattr(stock_row, 'Qte', 0) or 0),
                'seuil_alerte': str(getattr(stock_row, 'seuilAlert', 0) or 0),
                'prix_vente_reference': str(Decimal(str(getattr(stock_row, 'prix_vente', 0) or 0)).quantize(Decimal('0.01'))),
            },
            'filtres': {'date_min': date_min, 'date_max': date_max},
            'mouvements': rows,
            'solde_final': {
                'quantite': str(stock_qty),
                'valeur': str(stock_val.quantize(Decimal('0.01'))),
            },
            'meta_generation': self._build_meta_generation(user),
        }

    @action(detail=True, methods=['get'], url_path='fiche-stock/json')
    def fiche_stock_article_json(self, request, pk=None):
        """Retourne la fiche de stock en JSON (même logique FIFO que le PDF)."""
        try:
            return Response(self._build_fiche_stock_data(request, pk=pk))
        except (PermissionDenied, NotFound) as exc:
            return Response({'detail': str(exc)}, status=getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST))

    @action(detail=True, methods=['get'], url_path='fiche-stock')
    def fiche_stock_article_pdf(self, request, pk=None):
        """Fiche de stock PDF pour un article spécifique."""
        try:
            data = self._build_fiche_stock_data(request, pk=pk)
        except (PermissionDenied, NotFound) as exc:
            return Response({'detail': str(exc)}, status=getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.wordWrap = 'CJK'
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading2'],
            alignment=1,
            fontSize=14,
            spaceAfter=4 * mm,
        )

        elements = []
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(data['entete']))

        a = data.get('article_details') or {}
        nom_article = a.get('nom_scientifique') or ''
        if a.get('nom_commercial'):
            nom_article += f" ({a.get('nom_commercial')})"
        elements.append(
            Paragraph(
                f"<b>{_('FICHE DE STOCK')}</b> — {nom_article} <font size='8'>({a.get('article_id') or ''})</font>",
                title_style,
            )
        )
        elements.append(Spacer(1, 2 * mm))
        info_style = ParagraphStyle('ArticleInfoLine', parent=normal, fontSize=8.5, leading=11, spaceAfter=1)
        elements.append(Paragraph(f"<b>{_('Code')}:</b> {a.get('article_id') or ''}   |   <b>{_('Unité')}:</b> {a.get('unite') or '—'}", info_style))
        elements.append(Paragraph(f"<b>{_('Type')}:</b> {a.get('type_article') or '—'}   |   <b>{_('Sous-type')}:</b> {a.get('sous_type_article') or '—'}", info_style))
        elements.append(Paragraph(f"<b>{_('Stock')}:</b> {_format_report_quantity(a.get('stock_actuel') or 0)}   |   <b>{_('Seuil')}:</b> {_format_report_quantity(a.get('seuil_alerte') or 0)}   |   <b>{_('Prix vente')}:</b> {a.get('prix_vente_reference') or '0.00'}", info_style))
        elements.append(Spacer(1, 5 * mm))

        header1 = [_("Date"), _("Désignation"), _("Entrées"), "", "", _("Sorties"), "", "", _("Stock"), "", ""]
        header2 = ["", "", _("Qté"), _("PU"), _("PT"), _("Qté"), _("PU"), _("PT"), _("Qté"), _("PU"), _("PT")]
        table_data = [[Paragraph(h, normal) for h in header1], [Paragraph(h, normal) for h in header2]]

        for mv in data.get('mouvements') or []:
            entree = mv.get('entree') or {}
            sortie = mv.get('sortie') or {}
            stock = mv.get('stock') or {}
            row = [
                Paragraph(str(mv.get('datetime') or ''), normal),
                Paragraph(str(mv.get('designation') or ''), normal),
                Paragraph(_format_report_quantity(entree.get('quantite')) if entree else "", normal),
                Paragraph(str(entree.get('pu') or ''), normal),
                Paragraph(str(entree.get('pt') or ''), normal),
                Paragraph(_format_report_quantity(sortie.get('quantite')) if sortie else "", normal),
                Paragraph(str(sortie.get('pu') or ''), normal),
                Paragraph(str(sortie.get('pt') or ''), normal),
                Paragraph(_format_report_quantity(stock.get('quantite')), normal),
                Paragraph(str(stock.get('pu') or ''), normal),
                Paragraph(str(stock.get('pt') or ''), normal),
            ]
            table_data.append(row)

        sf = data.get('solde_final') or {}
        table_data.append(
            [
                "",
                Paragraph(f"<b>{_('SOLDE FINAL')}</b>", normal),
                "", "", "", "", "", "",
                Paragraph(f"<b>{_format_report_quantity(sf.get('quantite'))}</b>", normal),
                Paragraph("", normal),
                Paragraph(f"<b>{sf.get('valeur') or '0.00'}</b>", normal),
            ]
        )

        table = Table(table_data, repeatRows=2, hAlign='CENTER')
        table.setStyle(TableStyle([
            ('SPAN', (2, 0), (4, 0)),
            ('SPAN', (5, 0), (7, 0)),
            ('SPAN', (8, 0), (10, 0)),
            ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (2, 2), (-1, -1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.whitesmoke, None]),
            ('TOPPADDING', (0, 0), (-1, 1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 1), 6),
            ('BACKGROUND', (0, len(table_data) - 1), (-1, len(table_data) - 1), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, len(table_data) - 1), (-1, len(table_data) - 1), colors.whitesmoke),
            ('FONTNAME', (0, len(table_data) - 1), (-1, len(table_data) - 1), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 4 * mm))
        pdf_gen._build_with_footer(doc, elements, {'meta_generation': data.get('meta_generation') or {}})
        buffer.seek(0)
        return HttpResponse(
            buffer,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="FICHE_DE_STOCK_{a.get("article_id") or pk}.pdf"'},
        )


