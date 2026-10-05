from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum, Q, F, DecimalField, OuterRef, Subquery, Value, Exists, ExpressionWrapper, Count
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import datetime, date
from decimal import Decimal, ROUND_DOWN, InvalidOperation
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

from rest_framework.exceptions import NotFound

from stock.models import (
    Stock,
    LigneEntree,
    LigneSortie,
    Sortie,
    Article,
    Entree,
    InventaireSession,
    InventaireLigne,
)
from .serializers import (
    InventaireArticleSerializer,
    RapportInventaireSessionLigneSerializer,
    INVENTAIRE_STATUTS_REFERENCE,
    BonEntreeArticleSerializer,
    BonAchatSerializer,
    RecapitulatifAchatSerializer,
    _stock_statut_code,
    _seuil_article,
)
from users.permissions import IsAdminOrUser
from .utils.report_envelope import wrap_report_response


class RapportsViewSet(viewsets.ViewSet):
    """
    ViewSet pour les rapports métier (données JSON uniquement).
    Le frontend gère l'affichage, l'impression et l'export PDF/Excel.
    Accès réservé aux Admin et User (Agent). SuperAdmin n'a pas accès aux rapports métier.
    """
    permission_classes = [IsAdminOrUser]

    def _report_response(self, request, rapport: str, data: dict):
        """Enveloppe standard + Response DRF."""
        titre = data.get('titre') or rapport
        eid, branch_id = self._get_tenant_ids_strict(request)
        wrapped = wrap_report_response(
            rapport=rapport,
            titre=titre,
            request=request,
            user=request.user,
            data=data,
            eid=eid,
            branch_id=branch_id,
        )
        return Response(wrapped)

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
                    F('stock__Qte'),
                    Subquery(stock_sq.values('Qte')[:1]),
                    Value(Decimal('0.000')),
                    output_field=DecimalField(max_digits=12, decimal_places=5),
                ),
                inv_seuil=Coalesce(
                    F('stock__seuilAlert'),
                    Subquery(stock_sq.values('seuilAlert')[:1]),
                    Value(Decimal('0.000')),
                    output_field=DecimalField(max_digits=12, decimal_places=5),
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

    @staticmethod
    def _inventaire_stats_catalogue(lines):
        total = len(lines)
        en_rupture = sum(1 for L in lines if L.Qte <= 0)
        en_alerte = sum(
            1 for L in lines
            if L.Qte > 0 and L.seuilAlert > 0 and L.Qte <= L.seuilAlert
        )
        normaux = sum(
            1 for L in lines
            if L.Qte > 0 and (L.seuilAlert <= 0 or L.Qte > L.seuilAlert)
        )
        return {
            'total_articles': total,
            'en_alerte': en_alerte,
            'en_rupture': en_rupture,
            'normaux': normaux,
            'lignes_comptees': 0,
            'lignes_non_comptees': total,
            'ecarts_positifs': 0,
            'ecarts_negatifs': 0,
            'ecarts_nuls': 0,
            'conformes': 0,
        }

    @staticmethod
    def _inventaire_stats_session(lignes_qs):
        from decimal import Decimal, ROUND_DOWN

        lignes = list(lignes_qs)
        total = len(lignes)
        comptees = sum(1 for l in lignes if l.stock_physique is not None)
        ecarts_pos = sum(1 for l in lignes if l.ecart is not None and l.ecart > 0)
        ecarts_neg = sum(1 for l in lignes if l.ecart is not None and l.ecart < 0)
        ecarts_nuls = sum(1 for l in lignes if l.ecart is not None and l.ecart == 0)
        en_rupture = sum(
            1 for l in lignes
            if _stock_statut_code(l.stock_theorique, _seuil_article(l.article)) == 'RUPTURE'
        )
        en_alerte = sum(
            1 for l in lignes
            if _stock_statut_code(l.stock_theorique, _seuil_article(l.article)) == 'ALERTE'
        )
        normaux = sum(
            1 for l in lignes
            if _stock_statut_code(l.stock_theorique, _seuil_article(l.article)) == 'NORMAL'
        )
        capital_logiciel = sum((l.montant_logiciel for l in lignes), Decimal('0'))
        capital_physique = sum(
            (l.montant_physique for l in lignes if l.montant_physique is not None),
            Decimal('0'),
        )
        ecart_financier = capital_physique - capital_logiciel
        ecarts_montant = [
            l.ecart_montant for l in lignes if l.ecart_montant is not None
        ]
        total_ecart_positif = sum((m for m in ecarts_montant if m > 0), Decimal('0'))
        total_ecart_negatif = sum((-m for m in ecarts_montant if m < 0), Decimal('0'))
        total_ecart_montant = sum(ecarts_montant, Decimal('0'))

        def _money(value: Decimal) -> str:
            return str(value.quantize(Decimal('0.00001'), rounding=ROUND_DOWN))

        return {
            'total_articles': total,
            'en_alerte': en_alerte,
            'en_rupture': en_rupture,
            'normaux': normaux,
            'lignes_comptees': comptees,
            'lignes_non_comptees': total - comptees,
            'ecarts_positifs': ecarts_pos,
            'ecarts_negatifs': ecarts_neg,
            'ecarts_nuls': ecarts_nuls,
            'conformes': ecarts_nuls,
            'capital_logiciel': _money(capital_logiciel),
            'capital_physique': _money(capital_physique),
            'ecart_financier': _money(ecart_financier),
            'capital_reel_stock': _money(capital_physique),
            'total_montant_logiciel': _money(capital_logiciel),
            'total_montant_physique': _money(capital_physique),
            'total_ecart_montant': _money(total_ecart_montant),
            'total_ecart_positif': _money(total_ecart_positif),
            'total_ecart_negatif': _money(total_ecart_negatif),
        }

    def _serialize_inventaire_session(self, request, session, *, force_complet: bool = False):
        """Rapport d'inventaire basé sur une session opérationnelle (comptage + écarts)."""
        statut_filtre = request.query_params.get('statut')
        statut_ligne_filtre = request.query_params.get('statut_ligne')
        if force_complet:
            complet = True
        else:
            complet = request.query_params.get('complet', 'true').lower() not in (
                'false', '0', 'no', 'non',
            )

        lignes_qs = (
            session.lignes.select_related(
                'article__unite',
                'article__sous_type_article',
                'article__sous_type_article__type_article',
            )
            .order_by('article__nom_scientifique', 'article_id')
        )

        if statut_ligne_filtre:
            code = statut_ligne_filtre.upper().replace(' ', '_')
            if code == 'NON_COMPTÉ' or code == 'NON_COMpte':
                lignes_qs = lignes_qs.filter(stock_physique__isnull=True)
            elif code == 'CONFORME':
                lignes_qs = lignes_qs.filter(ecart=0)
            elif code == 'ECART_POSITIF':
                lignes_qs = lignes_qs.filter(ecart__gt=0)
            elif code == 'ECART_NEGATIF':
                lignes_qs = lignes_qs.filter(ecart__lt=0)

        if statut_filtre:
            # Filtre stock sur stock théorique figé — post-filter en Python
            statut_upper = statut_filtre.upper()
            filtered = []
            for ligne in lignes_qs:
                code = _stock_statut_code(ligne.stock_theorique, _seuil_article(ligne.article))
                if code == statut_upper:
                    filtered.append(ligne.pk)
            lignes_qs = lignes_qs.filter(pk__in=filtered)

        stats = self._inventaire_stats_session(
            session.lignes.select_related('article').order_by('article__nom_scientifique')
        )

        resp = {
            'titre': _("RAPPORT D'INVENTAIRE"),
            'mode': 'session',
            'session': {
                'id': session.pk,
                'libelle': session.libelle,
                'statut': session.statut,
                'statut_libelle': session.get_statut_display(),
                'date_inventaire': session.date_inventaire.isoformat(),
                'date_demarrage': session.date_demarrage.isoformat() if session.date_demarrage else None,
                'date_validation': session.date_validation.isoformat() if session.date_validation else None,
                'perimetre': session.perimetre,
                'entree_ajustement_id': session.entree_ajustement_id,
                'sortie_ajustement_id': session.sortie_ajustement_id,
            },
            'periode': {
                'date_debut': session.date_inventaire.isoformat(),
                'date_fin': session.date_inventaire.isoformat(),
            },
            'filtres': {
                'session_id': session.pk,
                'statut': statut_filtre,
                'statut_ligne': statut_ligne_filtre,
                'complet': complet,
            },
            'statuts': INVENTAIRE_STATUTS_REFERENCE,
            'statistiques': stats,
            # Bloc totaux financiers pour le PDF / affichage FE.
            'totaux_financiers': {
                'total_logiciel': stats.get('capital_logiciel'),
                'total_physique': stats.get('capital_physique'),
                'ecart_financier': stats.get('ecart_financier'),
                'capital_reel_stock': stats.get('capital_reel_stock'),
                'total_ecart_montant': stats.get('total_ecart_montant'),
                'total_ecart_positif': stats.get('total_ecart_positif'),
                'total_ecart_negatif': stats.get('total_ecart_negatif'),
            },
            'complet': complet,
        }

        if complet:
            data = RapportInventaireSessionLigneSerializer(lignes_qs, many=True).data
            resp['articles'] = data
            resp['details'] = data
            return resp

        paginator = InventaireResultsSetPagination()
        page_qs = paginator.paginate_queryset(list(lignes_qs), request)
        data = RapportInventaireSessionLigneSerializer(page_qs, many=True).data
        resp['articles'] = data
        resp['details'] = data
        if page_qs is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return resp

    def _serialize_inventaire(self, request, *, force_complet: bool = False):
        """
        Corps du rapport d'inventaire (dict prêt pour JSON ou PDF).
        Par défaut (complet=true) : tous les articles, sans pagination.
        complet=false : pagination (page_size jusqu'à 5000).
        Si filtrer_mouvements=true : seuls les articles avec au moins une entrée ou une sortie
        dont la date tombe dans [date_debut, date_fin] (tenant-scopé). Sinon : catalogue complet.
        """
        user = request.user
        date_debut, date_fin, d0, d1 = self._parse_inventaire_date_bounds(request)
        type_article = request.query_params.get('type_article')
        statut_filtre = request.query_params.get('statut')
        seulement_en_stock = request.query_params.get('seulement_en_stock', 'false').lower() in (
            'true', '1', 'yes', 'oui',
        )
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
        if seulement_en_stock:
            qs = qs.filter(inv_qte__gt=0)
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
                qs = qs.filter(inv_qte__gt=0, inv_seuil__gt=0, inv_qte__lte=F('inv_seuil'))
            elif statut_upper == 'NORMAL':
                qs = qs.filter(inv_qte__gt=0).filter(
                    Q(inv_qte__gt=F('inv_seuil')) | Q(inv_seuil=0)
                )

        lines = [
            InventaireStockLine(a, a.inv_qte, a.inv_seuil) for a in qs
        ]
        stats = self._inventaire_stats_catalogue(lines)

        resp = {
            'titre': _("RAPPORT D'INVENTAIRE"),
            'mode': 'catalogue',
            'session': None,
            'periode': {
                'date_debut': date_debut,
                'date_fin': date_fin,
            },
            'filtres': {
                'filtrer_mouvements': filtrer_mouvements,
                'seulement_en_stock': seulement_en_stock,
                'type_article': type_article,
                'statut': statut_filtre,
                'statut_ligne': None,
                'session_id': None,
                'complet': complet,
            },
            'statuts': INVENTAIRE_STATUTS_REFERENCE,
            'statistiques': stats,
            'complet': complet,
        }

        if complet:
            resp['articles'] = InventaireArticleSerializer(lines, many=True).data
            resp['details'] = resp['articles']
            return resp

        paginator = InventaireResultsSetPagination()
        page_lines = paginator.paginate_queryset(lines, request)
        resp['articles'] = InventaireArticleSerializer(page_lines, many=True).data
        resp['details'] = resp['articles']
        if page_lines is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return resp

    @action(detail=False, methods=['get'], url_path='inventaire')
    def inventaire(self, request):
        """
        **Rapport d'inventaire** JSON (affichage / export frontend).

        Deux modes :
        - **catalogue** (défaut) : stock théorique actuel, colonnes inventaire avec
          `stock_physique` et `ecart` vides (`statut_ligne_code`: NON_APPLICABLE).
        - **session** (`session_id`) : session opérationnelle avec comptage, écarts,
          statuts ligne (NON_COMPTÉ, CONFORME, ECART_POSITIF, ECART_NEGATIF).

        Paramètres :
        - session_id : ID session `/api/inventaires/` (rapport après comptage)
        - statut : NORMAL | ALERTE | RUPTURE (stock théorique)
        - statut_ligne : NON_COMPTÉ | CONFORME | ECART_POSITIF | ECART_NEGATIF (mode session)
        - seulement_en_stock, type_article, filtrer_mouvements, complet, date_debut, date_fin

        GET /api/rapports/inventaire/
        GET /api/rapports/inventaire/?session_id=1
        GET /api/rapports/inventaire/?statut=ALERTE&seulement_en_stock=true
        """
        session_id = request.query_params.get('session_id')
        if session_id:
            eid, branch_id = self._get_tenant_ids_strict(request)
            try:
                session = InventaireSession.objects.get(pk=int(session_id), entreprise_id=eid)
            except (InventaireSession.DoesNotExist, ValueError, TypeError):
                raise ValidationError({'session_id': 'Session d\'inventaire introuvable.'})
            if branch_id is not None and session.succursale_id not in (None, branch_id):
                raise PermissionDenied('Session hors de votre succursale.')
            if session.statut == InventaireSession.STATUT_BROUILLON:
                raise ValidationError({
                    'session_id': 'Démarrez la session avant d\'éditer le rapport (POST .../demarrer/).',
                })
            data = self._serialize_inventaire_session(request, session)
        else:
            data = self._serialize_inventaire(request)
        return self._report_response(request, 'inventaire', data)

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

    def _bon_entree_stocks_with_extras(self, request):
        """Liste complète des stocks réquisition (+ extra_articles optionnels)."""
        user = request.user
        stocks, _ = self._get_bon_entree_queryset_and_stats(request)
        stocks_list = list(stocks)
        extra_param = (request.query_params.get('extra_articles') or '').strip()
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
        return stocks_list

    @staticmethod
    def _enrich_bon_entree_statistiques(statistiques, articles_data):
        montant = Decimal('0')
        qte_commande = Decimal('0')
        for row in articles_data or []:
            try:
                montant += Decimal(str(row.get('montant_estime') or row.get('prix_total') or '0'))
                qte_commande += Decimal(str(row.get('quantite_a_commander') or '0'))
            except (InvalidOperation, TypeError, ValueError):
                continue
        enriched = dict(statistiques)
        enriched['montant_estime_total'] = str(
            montant.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        )
        enriched['quantite_a_commander_total'] = str(
            qte_commande.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        )
        return enriched

    def _build_bon_entree_data(self, request, *, paginate: bool = True):
        stocks, statistiques = self._get_bon_entree_queryset_and_stats(request)
        inclure_normaux = request.query_params.get('inclure_normaux', 'false').lower() == 'true'
        extra_param = (request.query_params.get('extra_articles') or '').strip()

        if paginate and not extra_param:
            paginator = StandardResultsSetPagination()
            page_stocks = paginator.paginate_queryset(stocks, request)
            articles_data = BonEntreeArticleSerializer(page_stocks, many=True).data
            stats = self._enrich_bon_entree_statistiques(statistiques, articles_data)
            resp = {
                'titre': _("RAPPORT DE RÉQUISITION"),
                'instructions': _(
                    'Quantités et montants estimés calculés automatiquement : stock actuel, '
                    'dernier prix d\'achat, quantité suggérée (jusqu\'au seuil) et montant estimé. '
                    'Ajustez côté client si besoin avant de passer commande.'
                ),
                'filtres': {
                    'inclure_normaux': inclure_normaux,
                    'extra_articles': extra_param or None,
                },
                'statistiques': stats,
                'totaux': {
                    'montant_estime_total': stats.get('montant_estime_total'),
                    'quantite_a_commander_total': stats.get('quantite_a_commander_total'),
                },
                'articles': articles_data,
                'details': articles_data,
            }
            if page_stocks is not None:
                resp['count'] = paginator.page.paginator.count
                resp['next'] = paginator.get_next_link()
                resp['previous'] = paginator.get_previous_link()
                resp['page_size'] = paginator.get_page_size(request)
            return resp

        stocks_list = self._bon_entree_stocks_with_extras(request)
        articles_data = BonEntreeArticleSerializer(stocks_list, many=True).data
        stats = self._enrich_bon_entree_statistiques(statistiques, articles_data)
        return {
            'titre': _("RAPPORT DE RÉQUISITION"),
            'instructions': _(
                'Quantités et montants estimés calculés automatiquement : stock actuel, '
                'dernier prix d\'achat, quantité suggérée (jusqu\'au seuil) et montant estimé. '
                'Ajustez côté client si besoin avant de passer commande.'
            ),
            'filtres': {
                'inclure_normaux': inclure_normaux,
                'extra_articles': extra_param or None,
            },
            'statistiques': stats,
            'totaux': {
                'montant_estime_total': stats.get('montant_estime_total'),
                'quantite_a_commander_total': stats.get('quantite_a_commander_total'),
            },
            'articles': articles_data,
            'details': articles_data,
        }

    @action(detail=False, methods=['get'], url_path='bon-entree')
    def bon_entree(self, request):
        """
        Rapport de réquisition (JSON) — préparation des achats.

        Chaque ligne inclut : stock actuel, dernier PU d'achat, quantité suggérée
        (`quantite_a_commander`) et montant estimé (`montant_estime` / `prix_total`).

        Paramètres:
        - inclure_normaux: true/false (défaut false)
        - extra_articles: IDs séparés par virgule (ex. PRLI0007,ID2)
        - complet: true = sans pagination (défaut si extra_articles présent)
        - page, page_size: pagination standard

        GET /api/rapports/bon-entree/
        GET /api/rapports/bon-entree/?inclure_normaux=true&extra_articles=PRLI0007
        """
        complet = request.query_params.get('complet', '').lower() in ('true', '1', 'yes', 'oui')
        has_extras = bool((request.query_params.get('extra_articles') or '').strip())
        paginate = not (complet or has_extras)
        data = self._build_bon_entree_data(request, paginate=paginate)
        return self._report_response(request, 'bon-entree', data)

    def _build_bon_achat_data(self, request, *, complet: bool = False):
        """
        Construit les données du bon d'achat (JSON).
        - complet=False: pagination JSON active
        - complet=True: liste intégrale sans pagination
        """
        user = request.user

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
        # order_by() avant values().annotate() casse le GROUP BY (une ligne par enregistrement)
        totaux_par_devise = lignes_entree.order_by().values(
            'devise__sigle',
            'devise__symbole',
        ).annotate(
            nombre_lignes=Count('id'),
            total_montant=Sum(
                F('quantite') * F('prix_unitaire'),
                output_field=DecimalField(max_digits=14, decimal_places=5),
            )
        )

        montant_global = Decimal('0')
        recapitulatif = []
        for total in totaux_par_devise:
            ligne_montant = total['total_montant'] or Decimal('0')
            montant_global += ligne_montant
            recapitulatif.append({
                'devise_sigle': total['devise__sigle'] or 'N/A',
                'devise_symbole': total['devise__symbole'] or '',
                'nombre_lignes': total['nombre_lignes'] or 0,
                'total_montant': str(
                    ligne_montant.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                ),
            })
        
        if complet:
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
            'titre': _("BON D'ACHAT - APPROVISIONNEMENTS EFFECTUÉS"),
            'periode': {
                'date_debut': date_debut,
                'date_fin': (date_fin or timezone.now().date().strftime('%Y-%m-%d')) if not entree_id else None
            },
            'filtres': {
                'entree_id': entree_id,
                'date_debut': date_debut,
                'date_fin': date_fin,
                'article_id': article_id,
                'complet': complet,
            },
            'statistiques': {
                'total_lignes': total_lignes,
                'nombre_entrees': nombre_entrees,
                'montant_total': str(
                    montant_global.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                ),
            },
            'totaux': {
                'montant_total': str(
                    montant_global.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                ),
                'recapitulatif_devises': recapitulatif,
            },
            'entree_details': entree_details,
            'recapitulatif': recapitulatif,
            'achats': serializer.data,
            'details': serializer.data,
        }
        if not complet and pagination_meta is not None:
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
        complet = request.query_params.get('complet', '').lower() in ('true', '1', 'yes', 'oui')
        data = self._build_bon_achat_data(request, complet=complet)
        if isinstance(data, Response):
            return data
        return self._report_response(request, 'bon-achat', data)

    def _empty_ventes_report(self, message, filtres=None):
        zero_amount = '0.00000'
        zero_resume = {
            'nombre_ventes': 0,
            'total_clients': 0,
            'sorties_comptant': 0,
            'sorties_credit': 0,
            'total_comptant': zero_amount,
            'total_credit': zero_amount,
            'total_general': zero_amount,
            'total_quantite': '0',
            'total_benefice': zero_amount,
            'total_remises': zero_amount,
            'total_taxes': zero_amount,
            'total_annulations': zero_amount,
        }
        return {
            'success': False,
            'message': message,
            'titre': _("RAPPORT DES VENTES"),
            'session': None,
            'periode': None,
            'ventes': [],
            'lignes_ventes': [],
            'details': [],
            'totaux': dict(zero_resume),
            'resume_global': dict(zero_resume),
            'filtres': filtres or {},
        }

    def _resolve_ventes_session(self, request, eid, branch_id):
        from caisse.constants import CAISSE_DEFAUT_CODE
        from caisse.models import SessionCaisse

        user = request.user
        session_id_raw = (request.query_params.get('session_id') or '').strip()
        session_numero = (request.query_params.get('session_numero') or '').strip()
        session_uuid = (request.query_params.get('session_uuid') or '').strip()
        agence_id_raw = (
            request.query_params.get('agence_id')
            or request.query_params.get('succursale_id')
            or ''
        ).strip()

        if session_uuid:
            raise ValidationError(
                {
                    'detail': _(
                        "Le parametre session_uuid n'est pas supporte par ce projet. "
                        'Utilisez session_id ou session_numero.'
                    )
                }
            )

        agence_id = None
        if agence_id_raw:
            try:
                agence_id = int(agence_id_raw)
            except ValueError:
                raise ValidationError({'detail': _('agence_id / succursale_id doit etre un entier.')})

        qs = SessionCaisse.objects.select_related(
            'type_caisse', 'devise', 'ouvert_par', 'succursale', 'entreprise'
        ).filter(
            entreprise_id=eid,
            type_caisse__est_defaut=True,
            type_caisse__code_type=CAISSE_DEFAUT_CODE,
        )

        if user.is_agent(request) and branch_id is not None:
            qs = qs.filter(succursale_id=branch_id)
        elif agence_id is not None:
            qs = qs.filter(succursale_id=agence_id)

        if session_id_raw:
            try:
                session_id = int(session_id_raw)
            except ValueError:
                raise ValidationError({'detail': _('session_id doit etre un entier.')})
            session = qs.filter(pk=session_id).first()
            if not session:
                raise ValidationError({'detail': _('Session introuvable pour cette entreprise / agence.')})
            return session, False

        if session_numero:
            session = qs.filter(numero=session_numero).first()
            if not session:
                raise ValidationError({'detail': _('Session introuvable pour ce numero.')})
            return session, False

        session = qs.filter(statut='OUVERTE').order_by('-ouvert_le', '-id').first()
        return session, True

    def _build_ventes_report(self, request, *, complet: bool = False):
        """
        Construit le JSON du rapport des ventes par session de caisse.

        - Si session_id / session_numero est fourni : charge cette session, quel que soit son statut.
        - Sinon : charge automatiquement la session ouverte du contexte courant.
        - Si aucune session ouverte n'existe : renvoie une reponse vide avec message explicite.
        """
        user = request.user
        client_id = (request.query_params.get('client_id') or '').strip()
        client_nom = (request.query_params.get('client_nom') or '').strip()
        reference = (request.query_params.get('reference') or '').strip()
        statut_paiement = (
            request.query_params.get('statut_paiement')
            or request.query_params.get('type_vente')
            or ''
        ).strip().upper()
        montant_min_raw = (request.query_params.get('montant_min') or '').strip()
        montant_max_raw = (request.query_params.get('montant_max') or '').strip()
        session_statut = (request.query_params.get('session_statut') or '').strip().upper()
        eid, branch_id = self._get_tenant_ids_strict(request)
        if not eid:
            raise ValidationError({'detail': _('Contexte entreprise manquant.')})

        filtres = {
            'session_id': request.query_params.get('session_id') or None,
            'session_numero': request.query_params.get('session_numero') or None,
            'session_statut': session_statut or None,
            'agence_id': request.query_params.get('agence_id') or request.query_params.get('succursale_id') or None,
            'entreprise_id': eid,
            'client_id': client_id or None,
            'client_nom': client_nom or None,
            'reference': reference or None,
            'statut_paiement': statut_paiement or None,
            'montant_min': montant_min_raw or None,
            'montant_max': montant_max_raw or None,
        }

        session, auto_selected = self._resolve_ventes_session(request, eid, branch_id)
        if session is None:
            return self._empty_ventes_report(
                _(
                    'Aucune session en cours. Veuillez selectionner une session pour consulter '
                    'le rapport des ventes.'
                ),
                filtres=filtres,
            )

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
            raise ValidationError({'detail': _('montant_min doit etre inferieur ou egal a montant_max.')})
        if statut_paiement and statut_paiement not in ('COMPTANT', 'CREDIT'):
            raise ValidationError({'detail': _('statut_paiement doit etre COMPTANT ou CREDIT.')})

        session_start = session.ouvert_le
        session_end = session.cloture_le or timezone.now()
        if session_end < session_start:
            session_end = session_start

        sortie_scope = Sortie.objects.filter(
            entreprise_id=eid,
            date_creation__gte=session_start,
            date_creation__lte=session_end,
        )
        if session.succursale_id is not None:
            sortie_scope = sortie_scope.filter(succursale_id=session.succursale_id)
        elif user.is_agent(request) and branch_id is not None:
            sortie_scope = sortie_scope.filter(succursale_id=branch_id)

        if client_id:
            sortie_scope = sortie_scope.filter(client_id=client_id)
        if client_nom:
            sortie_scope = sortie_scope.filter(client__nom__icontains=client_nom)
        if reference:
            ref_q_scope = Q(motif__icontains=reference)
            if reference.isdigit():
                ref_q_scope = ref_q_scope | Q(id=int(reference))
            ref_up_scope = reference.upper()
            if ref_up_scope.startswith('FACT-'):
                fact_part_scope = ref_up_scope.replace('FACT-', '').strip()
                if fact_part_scope.isdigit():
                    ref_q_scope = ref_q_scope | Q(id=int(fact_part_scope))
            sortie_scope = sortie_scope.filter(ref_q_scope)

        lignes_qs = (
            LigneSortie.objects.filter(sortie_id__in=Subquery(sortie_scope.values('id')))
            .select_related('sortie', 'sortie__client', 'article', 'devise')
            .prefetch_related('lots_utilises__lot_entree')
            .order_by('sortie__date_creation', 'sortie_id', 'id')
        )

        if montant_min is not None or montant_max is not None:
            line_total = ExpressionWrapper(
                F('quantite') * F('prix_unitaire'),
                output_field=DecimalField(max_digits=20, decimal_places=5),
            )
            if montant_min is not None:
                lignes_qs = lignes_qs.annotate(_line_total=line_total).filter(_line_total__gte=montant_min)
            if montant_max is not None:
                lignes_qs = lignes_qs.annotate(_line_total=line_total).filter(_line_total__lte=montant_max)

        if statut_paiement:
            if statut_paiement == 'CREDIT':
                lignes_qs = lignes_qs.filter(sortie__statut='EN_CREDIT')
            else:
                lignes_qs = lignes_qs.filter(sortie__statut='PAYEE')

        sortie_scope_filtered = sortie_scope.filter(
            pk__in=Subquery(lignes_qs.values('sortie_id').distinct())
        )

        line_total_expr = ExpressionWrapper(
            F('quantite') * F('prix_unitaire'),
            output_field=DecimalField(max_digits=20, decimal_places=5),
        )
        agg = lignes_qs.aggregate(
            total_qte=Sum('quantite'),
            total_montant=Sum(line_total_expr),
            total_comptant=Sum(line_total_expr, filter=Q(sortie__statut='PAYEE')),
            total_credit=Sum(line_total_expr, filter=Q(sortie__statut='EN_CREDIT')),
        )
        tot_qte = Decimal(str(agg['total_qte'] or 0))
        tot_m_vente = (agg['total_montant'] or Decimal('0')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        total_comptant = (agg['total_comptant'] or Decimal('0')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        total_credit = (agg['total_credit'] or Decimal('0')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

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
        total_benefice = total_benefice.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

        total_sorties = sortie_scope_filtered.count()
        total_clients = sortie_scope_filtered.exclude(client_id__isnull=True).values('client_id').distinct().count()
        sorties_credit = sortie_scope_filtered.filter(statut='EN_CREDIT').count()
        sorties_comptant = sortie_scope_filtered.filter(statut='PAYEE').count()

        pagination_meta = None
        if complet:
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
            page_size = max(1, min(page_size, StandardResultsSetPagination.max_page_size))

            count = lignes_qs.count()
            total_pages = max(1, math.ceil(count / page_size)) if count else 1
            if page > total_pages and count:
                page = total_pages
            start = (page - 1) * page_size
            page_slice_qs = lignes_qs[start:start + page_size]
            pagination_meta = {
                'page': page,
                'page_size': page_size,
                'count': count,
                'total_pages': total_pages,
                'has_next': start + page_size < count,
                'has_previous': page > 1,
                'mode': 'lignes_ventes',
            }

        page_lines = list(page_slice_qs)

        lignes_ventes = []
        ventes_map = {}
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
            total_ligne = (qd * pu_vente).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            if ligne.lots_utilises.exists():
                benefice_ligne = sum(
                    (Decimal(str(lu.quantite)) * (Decimal(str(lu.prix_vente)) - Decimal(str(lu.prix_achat))))
                    for lu in ligne.lots_utilises.all()
                ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            else:
                benefice_ligne = (qd * (pu_vente - pu_achat)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            ref = f"FACT-{int(s.id):06d}"

            ligne_data = {
                'sortie_id': s.id,
                'ligne_id': ligne.id,
                'date': s.date_creation.strftime('%Y-%m-%d %H:%M') if s.date_creation else '',
                'client': s.client.nom if s.client else _('Client anonyme'),
                'client_id': s.client_id,
                'statut_paiement': 'CREDIT' if (s.statut == 'EN_CREDIT') else 'COMPTANT',
                'article': ligne.article.nom_scientifique,
                'article_id': ligne.article.article_id,
                'pu_achat': str(pu_achat.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                'pu_vente': str(pu_vente.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                'quantite': q,
                'montant_ligne': str(total_ligne),
                'benefice': str(benefice_ligne),
                'reference': ref,
            }
            lignes_ventes.append(ligne_data)

            if s.id not in ventes_map:
                ventes_map[s.id] = {
                    'sortie_id': s.id,
                    'reference': ref,
                    'date': s.date_creation.strftime('%Y-%m-%d %H:%M') if s.date_creation else '',
                    'client': s.client.nom if s.client else _('Client anonyme'),
                    'client_id': s.client_id,
                    'statut_paiement': 'CREDIT' if (s.statut == 'EN_CREDIT') else 'COMPTANT',
                    'nombre_lignes': 0,
                    'total_vente': Decimal('0.00000'),
                    'total_benefice': Decimal('0.00000'),
                    'lignes': [],
                }
            ventes_map[s.id]['nombre_lignes'] += 1
            ventes_map[s.id]['total_vente'] += total_ligne
            ventes_map[s.id]['total_benefice'] += benefice_ligne
            ventes_map[s.id]['lignes'].append(ligne_data)

        ventes = []
        for vente in ventes_map.values():
            vente['total_vente'] = str(vente['total_vente'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
            vente['total_benefice'] = str(vente['total_benefice'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN))
            ventes.append(vente)

        ventes.sort(key=lambda row: (row['date'], row['sortie_id']))

        session_user_name = ''
        if session.ouvert_par:
            session_user_name = session.ouvert_par.get_full_name() or session.ouvert_par.username

        out = {
            'success': True,
            'message': _(
                'Session en cours chargee par defaut.'
            ) if auto_selected else _('Rapport genere pour la session selectionnee.'),
            'titre': _("RAPPORT DES VENTES"),
            'session': {
                'id': session.pk,
                'uuid': None,
                'numero': session.numero,
                'statut': session.statut,
                'date_ouverture': session.ouvert_le.isoformat() if session.ouvert_le else None,
                'date_cloture': session.cloture_le.isoformat() if session.cloture_le else None,
                'utilisateur': session_user_name,
                'utilisateur_id': session.ouvert_par_id,
                'caisse': session.type_caisse.nom or session.type_caisse.libelle,
                'caisse_id': session.type_caisse_id,
                'devise_id': session.devise_id,
                'devise_sigle': session.devise.sigle if session.devise else None,
                'agence_id': session.succursale_id,
                'agence_nom': session.succursale.nom if session.succursale else None,
                'entreprise_id': session.entreprise_id,
                'selection_automatique': auto_selected,
            },
            'periode': {
                'date_debut': session_start.date().isoformat(),
                'date_fin': session_end.date().isoformat(),
                'date_ouverture': session_start.isoformat() if session_start else None,
                'date_cloture': session_end.isoformat() if session_end else None,
            },
            'ventes': ventes,
            'lignes_ventes': lignes_ventes,
            'details': lignes_ventes,
            'filtres': filtres,
            'totaux': {
                'total_comptant': str(total_comptant),
                'total_credit': str(total_credit),
                'total_general': str(tot_m_vente),
                'total_quantite': str(tot_qte),
                'total_benefice': str(total_benefice),
                'total_remises': '0.00000',
                'total_taxes': '0.00000',
                'total_annulations': '0.00000',
            },
            'resume_global': {
                'nombre_ventes': total_sorties,
                'total_clients': total_clients,
                'sorties_comptant': sorties_comptant,
                'sorties_credit': sorties_credit,
                'total_comptant': str(total_comptant),
                'total_credit': str(total_credit),
                'total_general': str(tot_m_vente),
                'total_quantite': str(tot_qte),
                'total_benefice': str(total_benefice),
                'total_remises': '0.00000',
                'total_taxes': '0.00000',
                'total_annulations': '0.00000',
            },
        }
        out['titre'] = f"{out['titre']} ({session.numero})"
        if pagination_meta is not None:
            out['pagination'] = pagination_meta
        return out

    @action(detail=False, methods=['get'], url_path='ventes')
    def ventes(self, request):
        """
        Rapport des ventes par session de caisse.

        Parametres principaux:
        - session_id : identifiant de session (tout statut accepte)
        - session_numero : numero de session (tout statut accepte)

        Comportement par defaut:
        - si aucun parametre de session n'est fourni, le backend charge la session ouverte du contexte courant
        - si aucune session ouverte n'existe, l'API retourne une reponse vide avec message explicite

        Filtres optionnels:
        - client_id, client_nom, reference
        - montant_min, montant_max
        - statut_paiement = COMPTANT | CREDIT
        - agence_id / succursale_id (utile surtout pour les admins)

        Pagination:
        - page (defaut 1), page_size (defaut 25, max 200)
        - complet=true pour recuperer toutes les lignes

        Exemples:
        GET /api/rapports/ventes/
        GET /api/rapports/ventes/?session_id=12&page=1&page_size=25
        GET /api/rapports/ventes/?session_numero=SESS-2026-00012&statut_paiement=CREDIT
        """
        try:
            complet = request.query_params.get('complet', '').lower() in ('true', '1', 'yes', 'oui')
            data = self._build_ventes_report(request, complet=complet)
            return self._report_response(request, 'ventes', data)
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

    def _build_fiche_stock_data(self, request, pk=None):
        """Construit les données JSON de la fiche de stock avec calcul FIFO."""
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied(_("Utilisateur non authentifié."))
        eid, branch_id = self._get_tenant_ids_strict(request)
        if not eid:
            raise PermissionDenied(_("Contexte entreprise manquant."))
        article_qs = Article.objects.filter(pk=pk, entreprise_id=eid)
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
                        'pu': str(pu_in.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                        'pt': str(pt_in.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                    } if q_in else None,
                    'sortie': {
                        'quantite': str(q_out),
                        'pu': str(pu_out.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                        'pt': str(pt_out.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                    } if q_out else None,
                    'stock': {
                        'quantite': str(stock_qty),
                        'pu': str(stock_pu.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)) if stock_qty else '',
                        'pt': str(stock_val.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
                    },
                }
            )

        return {
            'titre': _("FICHE DE STOCK"),
            'article_details': {
                'article_id': article.article_id,
                'nom_scientifique': article.nom_scientifique,
                'nom_commercial': article.nom_commercial,
                'type_article': getattr(type_article, 'libelle', None),
                'sous_type_article': getattr(getattr(article, 'sous_type_article', None), 'libelle', None),
                'unite': getattr(getattr(article, 'unite', None), 'libelle', None),
                'stock_actuel': str(getattr(stock_row, 'Qte', 0) or 0),
                'seuil_alerte': str(getattr(stock_row, 'seuilAlert', 0) or 0),
                'prix_vente_reference': str(
                    Decimal(str(getattr(stock_row, 'prix_vente', 0) or 0)).quantize(
                        Decimal('0.00001'), rounding=ROUND_DOWN
                    )
                ),
            },
            'periode': {
                'date_debut': date_min,
                'date_fin': date_max,
            },
            'filtres': {'date_min': date_min, 'date_max': date_max},
            'mouvements': rows,
            'details': rows,
            'solde_final': {
                'quantite': str(stock_qty),
                'valeur': str(stock_val.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)),
            },
        }

    @action(detail=True, methods=['get'], url_path='fiche-stock/json')
    def fiche_stock_article_json(self, request, pk=None):
        """Alias JSON de fiche-stock (rétrocompatibilité)."""
        return self.fiche_stock_article(request, pk=pk)

    @action(detail=True, methods=['get'], url_path='fiche-stock')
    def fiche_stock_article(self, request, pk=None):
        """Fiche de stock JSON pour un article (mouvements FIFO)."""
        try:
            data = self._build_fiche_stock_data(request, pk=pk)
            return self._report_response(request, 'fiche-stock', data)
        except (PermissionDenied, NotFound) as exc:
            return Response({'detail': str(exc)}, status=getattr(exc, 'status_code', status.HTTP_400_BAD_REQUEST))


