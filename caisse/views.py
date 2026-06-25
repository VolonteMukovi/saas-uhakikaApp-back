"""API caisse : types, mouvements, sessions, paiements dettes."""
import io
from decimal import Decimal, ROUND_DOWN

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.translation import gettext as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from caisse.models import MouvementCaisse, TypeCaisse
from caisse.serializers import (
    MouvementCaisseSerializer,
    PaiementDetteReadSerializer,
    PaiementDetteWriteSerializer,
    TypeCaisseSerializer,
)
from caisse.services.caisse import mouvement_moyen_affiche
from caisse.services.session_caisse import (
    SessionCaisseError,
    require_session_caisse_ouverte,
    solde_session_courant,
)
from stock.models import DetteClient, Devise, Entreprise
from stock.services.tenant_context import get_tenant_ids as _get_tenant_ids
from stock.views import (
    BusinessPermissionMixin,
    TenantFilterMixin,
    _article_display_name,
    _format_amount,
    _get_principal_devise,
)

class TypeCaisseViewSet(TenantFilterMixin, BusinessPermissionMixin, viewsets.ModelViewSet):
    """CRUD des caisses (canaux d'encaissement) par entreprise / succursale."""

    queryset = TypeCaisse.objects.select_related('devise', 'succursale').all()
    serializer_class = TypeCaisseSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by('-est_defaut', 'nom', 'libelle', 'id')
        if self.request.query_params.get('actives_only') in ('1', 'true', 'True'):
            qs = qs.filter(is_active=True)
        code_type = self.request.query_params.get('code_type')
        if code_type:
            qs = qs.filter(code_type=code_type)
        succursale_id = self.request.query_params.get('succursale_id')
        if succursale_id:
            qs = qs.filter(succursale_id=succursale_id)
        return qs

    @action(detail=False, methods=['get'], url_path='actives')
    def actives(self, request):
        """Caisses actives du contexte courant (pour listes déroulantes frontend)."""
        qs = self.get_queryset().filter(is_active=True)
        return Response(TypeCaisseSerializer(qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='rapport-general')
    def rapport_general(self, request, pk=None):
        from caisse.services.session_caisse import rapport_par_caisse
        caisse = self.get_object()
        return Response(rapport_par_caisse(
            caisse,
            date_min=request.query_params.get('date_min'),
            date_max=request.query_params.get('date_max'),
        ))

    @action(detail=True, methods=['get'], url_path='rapport-detaille')
    def rapport_detaille(self, request, pk=None):
        from caisse.services.session_caisse import rapport_detaille_par_caisse
        caisse = self.get_object()
        return Response(rapport_detaille_par_caisse(
            caisse,
            date_min=request.query_params.get('date_min'),
            date_max=request.query_params.get('date_max'),
        ))


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
        type_caisse_id = self.request.query_params.get('type_caisse_id') or self.request.query_params.get('caisse_id')
        if type_caisse_id:
            qs = qs.filter(type_caisse_id=type_caisse_id)
        session_id = self.request.query_params.get('session_caisse_id')
        if session_id:
            qs = qs.filter(session_caisse_id=session_id)
        return qs.select_related(
            'devise', 'utilisateur', 'content_type', 'type_caisse', 'session_caisse',
        ).prefetch_related('details__type_caisse').order_by('-date', '-id')

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
            from stock.services.session_caisse import (
                SessionCaisseError,
                require_session_caisse_ouverte,
                solde_session_courant,
            )
            try:
                session = require_session_caisse_ouverte(tenant_id, branch_id, devise.pk)
                solde_disponible = solde_session_courant(session)
            except SessionCaisseError as exc:
                raise serializers.ValidationError({'detail': str(exc)})
            
            if montant > solde_disponible:
                devise_nom = devise.nom if devise else "devise inconnue"
                raise serializers.ValidationError({
                    'montant': (
                        f"Solde insuffisant en {devise_nom} pour la session ouverte. "
                        f"Solde disponible: {solde_disponible}, Montant demandé: {montant}."
                    )
                })

        if not serializer.validated_data.get('devise'):
            serializer.save(devise=devise, entreprise_id=tenant_id, succursale_id=branch_id)
        else:
            serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)

    def destroy(self, request, *args, **kwargs):
        raise serializers.ValidationError(
            {'detail': _('La suppression des mouvements financiers historiques est interdite.')}
        )

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
            devise_stats['total_entrees'] = devise_stats['total_entrees'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            devise_stats['total_sorties'] = devise_stats['total_sorties'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            devise_stats['solde'] = devise_stats['solde'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            
            # Calcul des pourcentages
            if total_global_entrees > 0:
                devise_stats['pourcentage_entrees'] = (
                    (devise_stats['total_entrees'] / total_global_entrees) * 100
                ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            
            if total_global_sorties > 0:
                devise_stats['pourcentage_sorties'] = (
                    (devise_stats['total_sorties'] / total_global_sorties) * 100
                ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            
            # Ratios et indicateurs
            devise_stats['ratio_entree_sortie'] = (
                (devise_stats['total_entrees'] / devise_stats['total_sorties']).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
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
                'total_entrees': total_global_entrees.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                'total_sorties': total_global_sorties.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                'solde_global_theorique': (total_global_entrees - total_global_sorties).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
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
            devise_info['solde'] = devise_info['solde'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            devise_info['total_entrees'] = devise_info['total_entrees'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            devise_info['total_sorties'] = devise_info['total_sorties'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        
        # Conversion de dict vers liste triée (devise principale en premier)
        soldes_list = list(soldes_par_devise.values())
        soldes_list.sort(key=lambda x: (not x['est_principale'], x['devise_sigle']))

        from rapports.utils.report_envelope import (
            build_metadata,
            get_devise_principale,
            serialize_agence,
            serialize_entreprise,
        )

        entreprise = user.get_entreprise(request)
        branch_id = getattr(request, 'branch_id', None)

        return Response({
            'rapport': 'etat-caisse',
            'titre': str(_('ÉTAT DE LA CAISSE')),
            'entreprise': serialize_entreprise(entreprise, request) if entreprise else None,
            'agence': serialize_agence(branch_id, entreprise),
            'devise': get_devise_principale(entreprise),
            'filtres': {
                'type': request.query_params.get('type'),
                'date_min': request.query_params.get('date_min'),
                'date_max': request.query_params.get('date_max'),
            },
            'resume': {
                'nb_devises_actives': len(soldes_par_devise),
                'total_mouvements_global': qs.count(),
                'devise_principale': principal_devise.sigle if principal_devise else None,
            },
            'soldes_par_devise': soldes_list,
            'details': soldes_list,
            'metadata': build_metadata(user, request),
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
            data['solde_actuel'] = data['solde_actuel'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            data['total_entrees'] = data['total_entrees'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            data['total_sorties'] = data['total_sorties'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
            
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
            devise_data['solde'] = devise_data['solde'].quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
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
                'montant': mv.montant.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
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
                    'entrees': total_entrees.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                    'sorties': total_sorties.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                    'solde': (total_entrees - total_sorties).quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                    'volume_total': volume_total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                },
                'compteurs': {
                    'nb_entrees': stat['nb_entrees'] or 0,
                    'nb_sorties': stat['nb_sorties'] or 0,
                    'nb_total': (stat['nb_entrees'] or 0) + (stat['nb_sorties'] or 0)
                },
                'moyennes': {
                    'montant_moyen_entree': (stat['montant_moyen_entree'] or Decimal('0.00')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
                    'montant_moyen_sortie': (stat['montant_moyen_sortie'] or Decimal('0.00')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                }
            }
            
            devises_comparaison.append(devise_info)
        
        # Calcul des pourcentages après avoir le total global
        for devise_info in devises_comparaison:
            volume = devise_info['totaux']['volume_total']
            if total_volume_global > 0:
                devise_info['pourcentage_volume'] = (
                    (volume / total_volume_global) * 100
                ).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
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
                'volume_global': total_volume_global.quantize(Decimal('0.00001'), rounding=ROUND_DOWN),
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
        elements.extend(pdf_gen._create_entete(entete, centered=False))
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
                tot = (pu * Decimal(str(q))).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                total_general += tot
                data.append([
                    Paragraph(_article_display_name(l.article)[:28], normal),
                    Paragraph(str(q), normal),
                    Paragraph(f"{pu:.5f}", normal),
                    Paragraph(f"{tot:.5f}", normal)
                ])
            data.append([
                Paragraph("<b>TOTAL</b>", header_style), '', '',
                Paragraph(f"<b>{total_general:.5f} {devise_obj.symbole if devise_obj else ''}</b>", header_style)
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
                tot = (pu * Decimal(str(q))).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                total_general += tot
                data.append([
                    Paragraph(_article_display_name(l.article)[:28], normal),
                    Paragraph(str(q), normal),
                    Paragraph(f"{pu:.5f}", normal),
                    Paragraph(f"{tot:.5f}", normal)
                ])
            data.append([
                Paragraph("<b>TOTAL</b>", header_style), '', '',
                Paragraph(f"<b>{total_general:.5f} {devise_obj.symbole if devise_obj else ''}</b>", header_style)
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

    @action(detail=True, methods=['get'], url_path='recu-json', permission_classes=[IsAuthenticated])
    def recu_json(self, request, pk=None):
        """
        Reçu de paiement dette en JSON (impression / PDF côté frontend).
        GET /api/paiements-dettes/{id}/recu-json/
        """
        from django.contrib.contenttypes.models import ContentType as CTModel
        from rapports.utils.report_envelope import (
            build_metadata,
            get_devise_principale,
            serialize_agence,
            serialize_entreprise,
        )

        user = request.user
        paiement = self.get_object()
        ct_dette = CTModel.objects.get_for_model(DetteClient)
        if paiement.content_type_id != ct_dette.id or not paiement.object_id:
            return Response(
                {'error': _('Mouvement invalide pour un reçu de paiement de dette.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        dette = DetteClient.objects.filter(pk=paiement.object_id).select_related(
            'client', 'devise', 'sortie',
        ).first()
        if not dette:
            return Response({'error': _('Dette introuvable.')}, status=status.HTTP_404_NOT_FOUND)

        entreprise = user.get_entreprise(request)
        tenant_id, branch_id = _get_tenant_ids(request)
        lien = None
        if dette.client and entreprise:
            lien = dette.client.liens_entreprise.filter(entreprise_id=entreprise.pk).first()

        paiement_data = PaiementDetteReadSerializer(
            paiement,
            context={'request': request, 'include_dette_details': True},
        ).data

        return Response({
            'document': 'recu_paiement_dette',
            'titre': _('REÇU DE PAIEMENT'),
            'format': 'json',
            'entreprise': serialize_entreprise(entreprise, request),
            'agence': serialize_agence(branch_id, entreprise),
            'devise': get_devise_principale(entreprise),
            'metadata': build_metadata(user, request),
            'client': {
                'id': dette.client_id,
                'nom': dette.client.nom if dette.client else '',
                'telephone': getattr(dette.client, 'telephone', '') or '',
                'is_special': bool(lien.is_special) if lien else False,
            },
            'dette': {
                'id': dette.id,
                'montant_total': str(dette.montant_total),
                'montant_paye': str(dette.montant_paye),
                'solde_restant': str(dette.solde_restant),
                'statut': dette.statut,
                'sortie_id': dette.sortie_id,
            },
            'paiement': paiement_data,
            'pdf_url': request.build_absolute_uri(
                f'/api/paiements-dettes/{paiement.pk}/recu-paiement/'
            ),
        })

    @action(detail=True, methods=['get'], url_path='recu-paiement', permission_classes=[IsAuthenticated])
    def recu_paiement_pdf(self, request, pk=None):
        """
        Reçu de paiement dette en PDF (ticket POS / impression directe).
        GET /api/paiements-dettes/{id}/recu-paiement/
        Pour JSON structuré : GET .../recu-json/
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
        lm = rm = tm = bm = 4 * mm
        content_width = POS_WIDTH - lm - rm
        buffer = io.BytesIO()
        styles = getSampleStyleSheet()

        # Polices réduites, design compact (impression POS) — même comportement que facture
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=7, leading=8, wordWrap='CJK')
        article_cell_style = ParagraphStyle('ArticleCell', parent=normal, wordWrap='CJK', allowWidows=0, allowOrphans=0)
        title_style = ParagraphStyle('Title', fontName='Helvetica-Bold', fontSize=10, leading=11, alignment=TA_CENTER, spaceAfter=1*mm)
        header_style = ParagraphStyle('Header', fontName='Helvetica-Bold', fontSize=8, leading=9, alignment=TA_LEFT)
        info_style = ParagraphStyle('Info', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_CENTER)
        footer_style = ParagraphStyle('Footer', fontName='Helvetica', fontSize=6, leading=7, alignment=TA_LEFT, textColor=colors.black)
        right_style = ParagraphStyle('Right', fontName='Helvetica', fontSize=7, leading=8, alignment=TA_RIGHT)

        elements = []

        # En-tête compact (nom + tél serrés, titre juste en dessous) — comme facture POS
        from rapports.utils.entete import get_entete_entreprise
        from rapports.utils.pdf_generator import PDFGenerator
        entete = get_entete_entreprise(entreprise)
        entete = {'entreprise': {**entete['entreprise'], 'slogan': ''}}
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete, compact=False, centered=True, logo_size_mm=12))

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
        elements.append(Paragraph(f"<b>{_('Montant dette')}</b>: {montant_total_dette:.5f} {symbole}", normal))
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
                    total_ligne = (Decimal(str(qte)) * pu).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
                    prod_data.append([
                        Paragraph(nom_article, article_cell_style),
                        Paragraph(str(qte), normal),
                        Paragraph(f"{pu:.5f} {symbole}", normal),
                        Paragraph(f"{total_ligne:.5f} {symbole}", normal),
                    ])
                prod_table = Table(prod_data, colWidths=[content_width*0.25, content_width*0.10, content_width*0.15, content_width*0.50])
                prod_table.hAlign = 'CENTER'
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
            [Paragraph(_("Montant payé (ce reçu)"), normal), Paragraph(f"<b>{paiement.montant:.5f} {symbole}</b>", normal), Paragraph(f"<b>{solde_apres:.5f} {symbole}</b>", normal)],
        ]
        table_paiement = Table(table_paiement_data, colWidths=[content_width*0.25, content_width*0.25, content_width*0.50])
        table_paiement.hAlign = 'CENTER'
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
                    Paragraph(f"{p.montant:.5f} {symbole}", normal),
                    Paragraph(moyen_h or '-', normal),
                ])
            hist_table = Table(hist_data, colWidths=[content_width*0.35, content_width*0.30, content_width*0.35])
            hist_table.hAlign = 'CENTER'
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

        # Pied de page compact (sans "push bottom") pour éviter les pages en trop.
        avail_width = content_width
        imprim_par = (paiement.utilisateur.get_full_name() or paiement.utilisateur.username) if paiement.utilisateur else (user.get_full_name() or user.username)
        footer_parts = [
            Paragraph(_("Merci pour votre confiance. Conservez ce reçu comme justificatif de paiement."), normal),
            Spacer(1, 0.5*mm),
            Paragraph(_("Imprimé par: %(user)s") % {'user': imprim_par}, footer_style),
            Paragraph(_("Le %(date)s") % {'date': timezone.now().strftime('%d/%m/%Y à %H:%M')}, footer_style),
            Spacer(1, 0.5*mm),
            Paragraph("—" * 30, footer_style),
        ]
        main_height = sum(flow.wrap(avail_width, 100000)[1] for flow in elements)
        footer_height = sum(flow.wrap(avail_width, 100000)[1] for flow in footer_parts)
        POS_HEIGHT = main_height + footer_height + tm + bm + 1.5*mm
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