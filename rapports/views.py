from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils import translation
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from datetime import datetime, date
from decimal import Decimal
import io

from config.pagination import StandardResultsSetPagination

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from stock.models import Stock, LigneEntree, LigneSortie, Article, Entree, Entreprise
from .serializers import (
    InventaireArticleSerializer,
    BonEntreeArticleSerializer,
    BonAchatSerializer,
    RecapitulatifAchatSerializer
)
from users.permissions import IsSuperAdminOrAdmin, IsAdminOrUser
from .utils.pdf_generator import PDFGenerator
from .utils.entete import get_entete_entreprise


class RapportsViewSet(viewsets.ViewSet):
    """
    ViewSet pour la génération des différents rapports.
    Accès réservé aux Admin et User (Agent). SuperAdmin n'a pas accès aux rapports métier.
    """
    permission_classes = [IsAdminOrUser]

    def _get_entete_entreprise(self, entreprise, user):
        """Génère l'en-tête simplifié : nom, logo, slogan, téléphone uniquement."""
        return get_entete_entreprise(entreprise)
    
    @action(detail=False, methods=['get'], url_path='inventaire')
    def inventaire(self, request):
        """
        Rapport d'inventaire des produits en stock.
        
        Paramètres optionnels:
        - date_debut: Date de début (format: YYYY-MM-DD)
        - date_fin: Date de fin (format: YYYY-MM-DD, par défaut: 31 décembre de l'année en cours)
        - type_article: Filtrer par type d'article
        - statut: Filtrer par statut (NORMAL, ALERTE, RUPTURE)
        
        GET /api/rapports/inventaire/
        GET /api/rapports/inventaire/?date_debut=2025-01-01&date_fin=2025-12-31
        GET /api/rapports/inventaire/?statut=ALERTE
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        
        # Récupération des paramètres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        type_article = request.query_params.get('type_article')
        statut_filtre = request.query_params.get('statut')
        
        # Date de fin par défaut: 31 décembre de l'année en cours
        if not date_fin:
            annee_actuelle = timezone.now().year
            date_fin = f"{annee_actuelle}-12-31"
        
        # Requête de base: stocks de l'entreprise de l'utilisateur
        eid = entreprise.pk if entreprise else None
        stocks = Stock.objects.filter(
            **({'article__entreprise_id': eid} if eid else {})
        ).select_related(
            'article',
            'article__sous_type_article',
            'article__sous_type_article__type_article',
            'article__unite'
        ).order_by('-id')
        
        # Filtrage par type d'article si spécifié
        if type_article:
            stocks = stocks.filter(
                article__sous_type_article__type_article__libelle__icontains=type_article
            )
        
        # Filtrage par statut en base (pour permettre la pagination)
        if statut_filtre:
            statut_upper = statut_filtre.upper()
            if statut_upper == 'RUPTURE':
                stocks = stocks.filter(Qte=0)
            elif statut_upper == 'ALERTE':
                stocks = stocks.filter(Qte__gt=0, Qte__lte=F('seuilAlert'))
            elif statut_upper == 'NORMAL':
                stocks = stocks.filter(Qte__gt=F('seuilAlert'))
        
        # Statistiques sur l'ensemble (sans tout charger)
        total_articles = stocks.count()
        en_rupture = stocks.filter(Qte=0).count()
        en_alerte = stocks.filter(Qte__gt=0, Qte__lte=F('seuilAlert')).count()
        normaux = stocks.filter(Qte__gt=F('seuilAlert')).count()
        
        # Pagination
        paginator = StandardResultsSetPagination()
        page_stocks = paginator.paginate_queryset(stocks, request)
        serializer = InventaireArticleSerializer(page_stocks, many=True)
        
        # Générer l'en-tête complet
        entete = self._get_entete_entreprise(entreprise, user)
        
        resp = {
            'entete': entete,
            'titre': _("RAPPORT D'INVENTAIRE"),
            'periode': {
                'date_debut': date_debut or 'Début de l\'exercice',
                'date_fin': date_fin
            },
            'statistiques': {
                'total_articles': total_articles,
                'en_alerte': en_alerte,
                'en_rupture': en_rupture,
                'normaux': normaux
            },
            'articles': serializer.data
        }
        if page_stocks is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return Response(resp)
    
    @action(detail=False, methods=['get'], url_path='inventaire/pdf')
    def inventaire_pdf(self, request):
        """
        Export PDF du rapport d'inventaire.
        Format A4, prêt pour l'impression.
        
        Paramètres: mêmes que l'action inventaire
        
        GET /api/rapports/inventaire/pdf/
        GET /api/rapports/inventaire/pdf/?statut=ALERTE
        """
        # Récupérer les données JSON du rapport
        json_response = self.inventaire(request)
        
        if json_response.status_code != 200:
            return json_response
        
        data = json_response.data
        
        # Générer le PDF
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
        eid = user.get_entreprise_id(request)
        base_filter = {'article__entreprise_id': eid} if eid else {}
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
                eid = user.get_entreprise_id(request)
                extra_filter = {'article__entreprise_id': eid} if eid else {}
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
            'articles': serializer.data
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
        """
        user = request.user
        entreprise = getattr(user, 'entreprise', None)

        # Récupérer le client_id depuis les paramètres de requête
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({
                'error': 'Le paramètre "client_id" est obligatoire',
                'exemple': '/api/rapports/clients-dettes/?client_id=CLI0001'
            }, status=status.HTTP_400_BAD_REQUEST)

        from stock.models import Client, DetteClient
        eid = entreprise.pk if entreprise else None
        client_qs = Client.objects.filter(id=client_id)
        if eid:
            client_qs = client_qs.filter(entreprise_id=eid)
        try:
            client = client_qs.get()
        except Client.DoesNotExist:
            return Response({
                'error': f'Client avec ID "{client_id}" non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)

        clients_data = []
        from decimal import Decimal

        # Traiter uniquement ce client
        c = client
        dettes_qs = DetteClient.objects.filter(client=c).select_related('devise', 'sortie')
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
                    'motif': getattr(d.sortie, 'motif', ''),
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
        """
        user = request.user
        entreprise = getattr(user, 'entreprise', None)

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

        eid = entreprise.pk if entreprise else None
        base_client_filter = {'entreprise_id': eid} if eid else {}
        clients_avec_dettes = Client.objects.filter(
            dettes__solde_restant__gt=0,
            dettes__statut='EN_COURS',
            **base_client_filter
        )
        
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
            # Récupérer toutes les dettes EN_COURS du client avec le filtre de date
            dettes_encours = DetteClient.objects.filter(
                client=client,
                **filtre_dettes
            ).select_related('devise')

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
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_clients_dettes_general_pdf(data)

        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"rapport_dettes_clients_general_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    @action(detail=False, methods=['get'], url_path='bon-achat')
    def bon_achat(self, request):
        """
        Bon d'achat - Liste des approvisionnements effectués.
        
        Liste tous les approvisionnements (entrées) à partir d'une date donnée.
        
        Paramètres:
        - date_debut: Date de début (obligatoire, format: YYYY-MM-DD)
        - date_fin: Date de fin (optionnel, format: YYYY-MM-DD)
        - article_id: Filtrer par article spécifique (optionnel)
        
        GET /api/rapports/bon-achat/?date_debut=2025-11-01
        GET /api/rapports/bon-achat/?date_debut=2025-11-01&date_fin=2025-11-30
        GET /api/rapports/bon-achat/?date_debut=2025-11-01&article_id=CAPE0001
        """
        user = request.user
        entreprise = user.get_entreprise(request)
        
        # Récupération des paramètres
        date_debut = request.query_params.get('date_debut')
        date_fin = request.query_params.get('date_fin')
        article_id = request.query_params.get('article_id')
        
        # Validation: date_debut est obligatoire
        if not date_debut:
            return Response({
                'error': 'Le paramètre "date_debut" est obligatoire',
                'exemple': '/api/rapports/bon-achat/?date_debut=2025-11-01'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Conversion des dates
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
        
        eid = entreprise.pk if entreprise else None
        base_entree_filter = {'entree__entreprise_id': eid} if eid else {}
        lignes_entree = LigneEntree.objects.filter(
            date_entree__date__gte=date_debut_obj,
            date_entree__date__lte=date_fin_obj,
            **base_entree_filter
        ).select_related(
            'article',
            'article__unite',
            'entree',
            'devise'
        ).order_by('-date_entree', '-id')
        
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
        
        # Pagination
        paginator = StandardResultsSetPagination()
        page_lignes = paginator.paginate_queryset(lignes_entree, request)
        serializer = BonAchatSerializer(page_lignes, many=True)
        
        # Générer l'en-tête complet
        entete = self._get_entete_entreprise(entreprise, user)
        
        resp = {
            'entete': entete,
            'titre': _("BON D'ACHAT - APPROVISIONNEMENTS EFFECTUÉS"),
            'periode': {
                'date_debut': date_debut,
                'date_fin': date_fin or timezone.now().date().strftime('%Y-%m-%d')
            },
            'statistiques': {
                'total_lignes': total_lignes,
                'nombre_entrees': nombre_entrees
            },
            'recapitulatif': recapitulatif,
            'achats': serializer.data
        }
        if page_lignes is not None:
            resp['count'] = paginator.page.paginator.count
            resp['next'] = paginator.get_next_link()
            resp['previous'] = paginator.get_previous_link()
            resp['page_size'] = paginator.get_page_size(request)
        return Response(resp)
    
    @action(detail=False, methods=['get'], url_path='bon-achat/pdf')
    def bon_achat_pdf(self, request):
        """
        Export PDF du bon d'achat.
        Format A4, prêt pour l'impression avec support multi-devises.
        
        Paramètres: mêmes que l'action bon_achat (date_debut obligatoire)
        
        GET /api/rapports/bon-achat/pdf/?date_debut=2025-11-01
        GET /api/rapports/bon-achat/pdf/?date_debut=2025-11-01&date_fin=2025-11-30
        """
        # Récupérer les données JSON
        json_response = self.bon_achat(request)
        
        if json_response.status_code != 200:
            return json_response
        
        data = json_response.data
        
        # Générer le PDF
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_bon_achat_pdf(data)
        
        # Créer la réponse HTTP
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        
        # Nom du fichier
        filename = f"bon_achat_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @action(detail=True, methods=['get'], url_path='fiche-stock')
    def fiche_stock_article_pdf(self, request, pk=None):
        """
        Fiche de stock pour un article spécifique.
        
        Affiche tous les mouvements (entrées et sorties) d'un article avec calcul FIFO.
        La devise est affichée une seule fois dans l'en-tête.
        
        Paramètres optionnels:
        - date_min: Date de début (format: YYYY-MM-DD)
        - date_max: Date de fin (format: YYYY-MM-DD)
        
        GET /api/rapports/{article_id}/fiche-stock/
        GET /api/rapports/{article_id}/fiche-stock/?date_min=2025-01-01&date_max=2025-12-31
        """
        user = request.user
        if not user.is_authenticated:
            return Response({'detail': "Utilisateur non authentifié."}, status=status.HTTP_403_FORBIDDEN)
        entreprise = user.get_entreprise(request)
        eid = user.get_entreprise_id(request)
        article_qs = Article.objects.filter(pk=pk)
        if eid:
            article_qs = article_qs.filter(entreprise_id=eid)
        article = article_qs.first()
        if not article:
            return Response({'detail': "Article non trouvé ou accès refusé."}, status=status.HTTP_404_NOT_FOUND)
        
        # Filtres optionnels
        date_min = request.query_params.get('date_min')
        date_max = request.query_params.get('date_max')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=10*mm,
            rightMargin=10*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']
        normal.wordWrap = 'CJK'
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading2'],
            alignment=1,
            fontSize=14,
            spaceAfter=4*mm
        )

        elements = []

        # En-tête simplifié (nom, logo, slogan, téléphone uniquement)
        entete = get_entete_entreprise(entreprise)
        pdf_gen = PDFGenerator()
        elements.extend(pdf_gen._create_entete(entete))

        # Titre : FICHE DE STOCK + nom de l'article (code en petite police)
        nom_article = article.nom_scientifique
        if article.nom_commercial:
            nom_article += f" ({article.nom_commercial})"
        title_with_article = (
            f"<b>{_('FICHE DE STOCK')}</b> — "
            f"{nom_article} <font size='8'>({article.article_id})</font>"
        )
        elements.append(Paragraph(title_with_article, title_style))
        elements.append(Spacer(1, 4*mm))

        # Récupération des mouvements
        entrees_qs = LigneEntree.objects.filter(article=article)
        sorties_qs = LigneSortie.objects.filter(article=article)
        
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
                'pu_in': float(e['prix_unitaire']),
                'q_out': 0
            })
        for s in sorties:
            mouvements.append({
                'datetime': s['date_sortie'],
                'designation': s['sortie__motif'] or _("Sortie"),
                'q_in': 0,
                'pu_in': 0.0,
                'q_out': s['quantite']
            })
        
        # Tri chronologique (entrées avant sorties pour même datetime)
        mouvements.sort(key=lambda m: (m['datetime'], 0 if m['q_in']>0 else 1))

        # En-têtes du tableau : Date, Désignation, Entrées (Qté, PU, PT), Sorties (Qté, PU, PT), Stock (Qté, PU, PT)
        header1 = [
            _("Date"), _("Désignation"),
            _("Entrées"), "", "",
            _("Sorties"), "", "",
            _("Stock"), "", ""
        ]

        header2 = [
            "", "",
            _("Qté"), _("PU"), _("PT"),
            _("Qté"), _("PU"), _("PT"),
            _("Qté"), _("PU"), _("PT")
        ]
        
        table_data = [
            [Paragraph(h, normal) for h in header1],
            [Paragraph(h, normal) for h in header2]
        ]

        # Calcul FIFO
        fifo_layers = []
        stock_qty = 0
        stock_val = 0.0

        for mv in mouvements:
            date_str = mv['datetime'].strftime('%d/%m/%Y %H:%M') if mv['datetime'] else ""
            desig = Paragraph(mv['designation'], normal)
            q_in = mv['q_in']
            pu_in = mv['pu_in']
            pt_in = q_in * pu_in
            q_out = mv['q_out']
            pt_out = 0.0

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
            pu_out = (pt_out / q_out) if q_out else 0.0

            # Construction de la ligne (sans devise dans le corps)
            row = [
                Paragraph(date_str, normal),
                desig,
                Paragraph(str(q_in) if q_in else "", normal),
                Paragraph(f"{pu_in:.2f}" if q_in else "", normal),
                Paragraph(f"{pt_in:.2f}" if q_in else "", normal),
                Paragraph(str(q_out) if q_out else "", normal),
                Paragraph(f"{pu_out:.2f}" if q_out else "", normal),
                Paragraph(f"{pt_out:.2f}" if q_out else "", normal),
                Paragraph(str(stock_qty), normal),
                Paragraph(f"{(stock_val/stock_qty):.2f}" if stock_qty else "", normal),
                Paragraph(f"{stock_val:.2f}", normal)
            ]
            table_data.append(row)

        # Ligne finale
        final_row = [
            "", Paragraph(f"<b>{_('SOLDE FINAL')}</b>", normal),
            "", "", "",
            "", "", "",
            Paragraph(f"<b>{stock_qty}</b>", normal),
            Paragraph("", normal),
            Paragraph(f"<b>{stock_val:.2f}</b>", normal)
        ]
        table_data.append(final_row)

        # Création du tableau (11 colonnes)
        table = Table(
            table_data,
            repeatRows=2,
            hAlign='CENTER'
        )
        table.setStyle(TableStyle([
            ('SPAN', (2,0), (4,0)),  # Fusionner "Entrées"
            ('SPAN', (5,0), (7,0)),  # Fusionner "Sorties" (Qté, PU, PT)
            ('SPAN', (8,0), (10,0)),  # Fusionner "Stock"
            ('BACKGROUND', (0,0), (-1,1), colors.lightgrey),
            ('FONTNAME', (0,0), (-1,1), 'Helvetica-Bold'),
            ('ALIGN', (0,0), (-1,1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (2,2), (-1,-1), 'RIGHT'),
            ('ROWBACKGROUNDS', (0,2), (-1,-1), [colors.whitesmoke, None]),
            ('TOPPADDING', (0,0), (-1,1), 6),
            ('BOTTOMPADDING', (0,0), (-1,1), 6),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph(f"© {entreprise.nom.upper()}", normal))

        doc.build(elements)
        buffer.seek(0)
        return HttpResponse(
            buffer,
            content_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="FICHE_DE_STOCK_{article.pk}.pdf"'}
        )


