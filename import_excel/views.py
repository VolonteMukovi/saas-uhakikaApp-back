import io
import openpyxl
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from stock.models import Article, Devise, SousTypeArticle, Unite, Stock, Client
from stock.serializers import EntreeSerializer, ArticleSerializer
import json

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_template(request):
    """Télécharge un fichier Excel modèle pour l'approvisionnement."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Approvisionnement'
    entetes = ['article_id', 'quantite', 'prix_unitaire', 'prix_vente', 'devise_id', 'seuil_alerte', 'date_expiration']
    ws.append(entetes)
    # Style entête
    header_fill = PatternFill(start_color='FFB300', end_color='FFB300', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    header_align = Alignment(horizontal='center', vertical='center')
    thin = Side(border_style="thin", color="000000")
    for col in range(1, len(entetes)+1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    # Exemple de lignes (prix_vente doit être >= prix_unitaire pour avoir un bénéfice)
    ws.append([1, 100, 2500, 3000, 2, 10, '2026-06-30'])  # prix_vente = 3000 (bénéfice de 500)
    ws.append([2, 50, 1500, 1800, 2, 5, ''])  # prix_vente = 1800 (bénéfice de 300)
    ws.append([3, 200, 500, 600, 3, 20, ''])  # prix_vente = 600 (bénéfice de 100)

    # Feuille de référence des articles
    ws2 = wb.create_sheet('Articles')
    ws2.append(['CODE PRODUIT', 'Nom scientifique', 'Nom commercial'])
    for col in range(1, 4):
        cell = ws2.cell(row=1, column=col)
        cell.fill = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws2.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22
    tenant_id = request.user.get_entreprise_id() if request.user.is_authenticated else None
    articles_qs = Article.objects.filter(entreprise_id=tenant_id) if tenant_id else Article.objects.all()
    for article in articles_qs:
        ws2.append([article.article_id, article.nom_scientifique, article.nom_commercial or ''])

    # Feuille de référence des devises
    ws3 = wb.create_sheet('Devises')
    ws3.append(['ID', 'Sigle', 'Nom', 'Symbole'])
    for col in range(1, 5):
        cell = ws3.cell(row=1, column=col)
        cell.fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws3.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18
    devises_qs = Devise.objects.filter(entreprise_id=tenant_id) if tenant_id else Devise.objects.all()
    for devise in devises_qs:
        ws3.append([devise.id, devise.sigle, devise.nom, devise.symbole])

    # Feuille "Référence complète" : tous les articles (code) et devises en un seul endroit
    ws_ref = wb.create_sheet('Reference_Complete', 1)
    ref_title_fill = PatternFill(start_color='5C6BC0', end_color='5C6BC0', fill_type='solid')
    ref_title_font = Font(bold=True, color='FFFFFF', size=12)
    ref_section_fill = PatternFill(start_color='7986CB', end_color='7986CB', fill_type='solid')
    ref_section_font = Font(bold=True, color='FFFFFF')

    ws_ref.append(['RÉFÉRENCE COMPLÈTE — Utilisez UNIQUEMENT les codes/ID ci-dessous dans la feuille "Approvisionnement"'])
    ws_ref.merge_cells('A1:G1')
    ws_ref.cell(row=1, column=1).fill = ref_title_fill
    ws_ref.cell(row=1, column=1).font = ref_title_font
    ws_ref.cell(row=1, column=1).alignment = header_align
    ws_ref.row_dimensions[1].height = 22

    ws_ref.append([])
    ws_ref.append(['ARTICLE_ID (CODE) — Colonne 1 de la feuille Approvisionnement (tous les articles)'])
    ws_ref.merge_cells('A3:G3')
    ws_ref.cell(row=3, column=1).fill = ref_section_fill
    ws_ref.cell(row=3, column=1).font = ref_section_font
    ws_ref.append(['CODE PRODUIT (article_id)', 'Nom scientifique', 'Nom commercial'])
    for col in range(1, 4):
        cell = ws_ref.cell(row=4, column=col)
        cell.fill = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_art = 5
    for article in articles_qs.order_by('article_id'):
        ws_ref.append([
            article.article_id,
            article.nom_scientifique,
            article.nom_commercial or '',
        ])
        for col in range(1, 4):
            ws_ref.cell(row=row_art, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_art += 1

    ws_ref.append([])
    ws_ref.append(['DEVISE_ID — Colonne 5 de la feuille Approvisionnement (toutes les devises)'])
    ws_ref.merge_cells(f'A{row_art + 1}:G{row_art + 1}')
    ws_ref.cell(row=row_art + 1, column=1).fill = ref_section_fill
    ws_ref.cell(row=row_art + 1, column=1).font = ref_section_font
    row_art += 2
    ws_ref.append(['ID', 'Sigle', 'Nom', 'Symbole'])
    for col in range(1, 5):
        cell = ws_ref.cell(row=row_art, column=col)
        cell.fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_art += 1
    for devise in devises_qs.order_by('id'):
        ws_ref.append([devise.id, devise.sigle, devise.nom, devise.symbole])
        for col in range(1, 5):
            ws_ref.cell(row=row_art, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_art += 1

    for c in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        ws_ref.column_dimensions[c].width = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="modele_approvisionnement.xlsx"'
    return response

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_approvisionnement(request):
    """Importe un fichier Excel d'approvisionnement et crée une Entree avec ses lignes."""
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': _('Aucun fichier envoyé.')}, status=400)
    wb = openpyxl.load_workbook(file)
    ws = wb['Approvisionnement']
    lignes = []
    from datetime import datetime
    from stock.views import _get_tenant_ids
    from stock.models import Devise
    tenant_id, branch_id = _get_tenant_ids(request)
    if not tenant_id:
        return JsonResponse({'error': _('Contexte entreprise manquant. Connectez-vous et sélectionnez une entreprise.')}, status=400)
    devise_principale = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Ignore les lignes vides (toutes les valeurs nulles ou vides)
            if not row or all(cell is None or (isinstance(cell, str) and not cell.strip()) for cell in row):
                continue
            # Nouvelle structure avec prix_vente
            if len(row) < 6:
                return JsonResponse({'error': f'Ligne {row_idx}: Format invalide. Colonnes attendues: article_id, quantite, prix_unitaire, prix_vente, devise_id, seuil_alerte, date_expiration'}, status=400)
            
            article_id_raw, quantite_raw, prix_unitaire_raw, prix_vente_raw, devise_id, seuil_alerte_raw, date_expiration = row[:7]

            # Normaliser l'ID article
            article_id = str(article_id_raw).strip() if article_id_raw is not None else None

            # Helper: parser de nombres (gère les chaînes avec ',' comme séparateur décimal)
            def _parse_number(cell):
                if cell is None:
                    return None
                if isinstance(cell, str):
                    s = cell.strip()
                    if not s:
                        return None
                    s = s.replace(',', '.')
                    try:
                        return float(s)
                    except Exception:
                        return None
                if isinstance(cell, (int, float)):
                    return float(cell)
                return None

            quantite = _parse_number(quantite_raw)
            prix_unitaire = _parse_number(prix_unitaire_raw)
            prix_vente = _parse_number(prix_vente_raw)
            seuil_alerte = _parse_number(seuil_alerte_raw)
            
            # Validation du prix_vente (obligatoire et doit être > 0)
            if prix_vente is None:
                return JsonResponse({'error': f'Prix de vente manquant ou invalide à la ligne {row_idx} (article {article_id}). Le prix de vente est obligatoire pour chaque ligne d\'entrée.'}, status=400)
            
            if prix_vente <= 0:
                return JsonResponse({'error': f'Prix de vente invalide à la ligne {row_idx} (article {article_id}). Le prix de vente doit être supérieur à 0.'}, status=400)
            # Toujours extraire l'id numérique de la devise, peu importe le type
            devise_id_val = None
            # LOG TEMPORAIRE POUR DEBUG
            # print('DEBUG devise_id:', devise_id, type(devise_id))
            # On ne doit JAMAIS transmettre un objet Devise, ni aucun objet non convertible en int
            devise_id_val = None
            # Si devise_id est vide ou None, on prend la devise principale de l'entreprise
            if devise_id is None or (isinstance(devise_id, str) and not devise_id.strip()):
                devise_id_val = devise_principale.id if devise_principale else None
            else:
                if hasattr(devise_id, 'id'):
                    devise_id_val = getattr(devise_id, 'id', None)
                elif isinstance(devise_id, (int, float)):
                    devise_id_val = int(devise_id)
                elif isinstance(devise_id, str):
                    try:
                        devise_id_val = int(float(devise_id))
                    except Exception:
                        devise_id_val = None
                else:
                    devise_id_val = None
            # Si la devise n'existe pas dans la base, on force à None pour utiliser la devise principale
            if devise_id_val is not None:
                if not Devise.objects.filter(pk=devise_id_val).exists():
                    devise_id_val = None

            # Validation minimale des valeurs numériques
            if quantite is None:
                return JsonResponse({'error': f'Quantité manquante ou invalide à la ligne {row_idx} (article {article_id}).'}, status=400)

            # Conversion automatique des formats de date
            date_str = None
            if date_expiration:
                if isinstance(date_expiration, str):
                    # Essaye AAAA-MM-JJ
                    try:
                        date_str = datetime.strptime(date_expiration, "%Y-%m-%d").strftime("%Y-%m-%d")
                    except ValueError:
                        # Essaye JJ/MM/AAAA
                        try:
                            date_str = datetime.strptime(date_expiration, "%d/%m/%Y").strftime("%Y-%m-%d")
                        except ValueError:
                            date_str = None
                elif isinstance(date_expiration, datetime):
                    date_str = date_expiration.strftime("%Y-%m-%d")
                elif isinstance(date_expiration, (int, float)):
                    # Excel peut stocker les dates comme float (numéro de série)
                    try:
                        from openpyxl.utils.datetime import from_excel
                        date_obj = from_excel(date_expiration)
                        date_str = date_obj.strftime("%Y-%m-%d")
                    except Exception:
                        date_str = None
            ligne = {
                'article_id': article_id,  # Le serializer attend 'article_id' (PrimaryKeyRelatedField avec source='article')
                'quantite': int(quantite) if quantite is not None else None,
                'prix_unitaire': float(prix_unitaire) if prix_unitaire is not None else 0.0,
                'prix_vente': float(prix_vente),  # Prix de vente obligatoire
                'seuil_alerte': int(seuil_alerte) if seuil_alerte is not None else 0,
                'date_expiration': date_str if date_str else None,
                'devise_id': devise_id_val if devise_id_val is not None else None
            }
            lignes.append(ligne)
    # Vérification du solde de caisse par devise avant création
    from decimal import Decimal
    from stock.models import MouvementCaisse
    from django.db.models import Sum
    erreurs_solde = []
    totaux_par_devise = {}
    for ligne in lignes:
        devise_id = ligne.get('devise_id')
        quantite = Decimal(str(ligne.get('quantite') or 0))
        prix_unitaire = Decimal(str(ligne.get('prix_unitaire') or 0))
        montant = (quantite * prix_unitaire).quantize(Decimal('0.01'))
        if not devise_id:
            devise_id = devise_principale.id if devise_principale else None
        if not devise_id:
            continue
        if devise_id not in totaux_par_devise:
            totaux_par_devise[devise_id] = Decimal('0.00')
        totaux_par_devise[devise_id] += montant

    for devise_id, total in totaux_par_devise.items():
        devise_obj = Devise.objects.filter(pk=devise_id).first()
        if not devise_obj:
            continue
        qs = MouvementCaisse.objects.filter(devise=devise_obj, entreprise_id=tenant_id)
        entrees = qs.filter(type='ENTREE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        sorties = qs.filter(type='SORTIE').aggregate(s=Sum('montant'))['s'] or Decimal('0')
        solde = entrees - sorties
        if total > solde:
            erreurs_solde.append(f"Solde insuffisant en {devise_obj.nom} ({devise_obj.sigle}): Requis {total} {devise_obj.symbole}, Disponible {solde} {devise_obj.symbole}. Veuillez d'abord effectuer une entrée en caisse dans cette devise.")

    if erreurs_solde:
        return JsonResponse({
            'soldes_insuffisants': erreurs_solde,
            'message': 'Approvisionnement impossible: soldes insuffisants dans certaines devises.'
        }, status=400)

    data = {
        'libele': request.POST.get('libele', 'Import Excel'),
        'description': request.POST.get('description', ''),
        'lignes': lignes
    }
    serializer = EntreeSerializer(data=data, context={'request': request})
    if serializer.is_valid():
        entree = serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)
        from stock.models import MouvementCaisse
        for devise_id, total in totaux_par_devise.items():
            if total <= 0:
                continue
            devise_obj = Devise.objects.filter(pk=devise_id).first()
            if not devise_obj:
                continue
            MouvementCaisse.objects.create(
                montant=total,
                devise=devise_obj,
                type='SORTIE',
                motif=f"Approvisionnement entrée #{entree.pk} (Import Excel)",
                moyen='Cash',
                entree=entree,
                entreprise_id=tenant_id,
                succursale_id=branch_id,
            )
        return JsonResponse(serializer.data, status=201)
    else:
        return JsonResponse(serializer.errors, status=400)


# --- Import Articles (même logique que l'import approvisionnement) ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_template_articles(request):
    """Télécharge un fichier Excel modèle pour l'import d'articles."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Articles'
    entetes = ['nom_scientifique', 'nom_commercial', 'sous_type_article_id', 'unite_id', 'emplacement']
    ws.append(entetes)
    header_fill = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    header_align = Alignment(horizontal='center', vertical='center')
    thin = Side(border_style="thin", color="000000")
    for col in range(1, len(entetes) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22

    # Exemples (nom_commercial et emplacement optionnels)
    ws.append(['Paracétamol 500mg', 'Doliprane', 1, 1, 'Rayon A1'])
    ws.append(['Ibuprofène 400mg', 'Advil', 1, 1, ''])
    ws.append(['Vitamine C 1g', '', 2, 2, 'Rayon B2'])

    # Feuille de référence des sous-types d'articles
    ws2 = wb.create_sheet('SousTypes')
    ws2.append(['ID', 'Libellé', 'Type article ID'])
    for col in range(1, 4):
        cell = ws2.cell(row=1, column=col)
        cell.fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws2.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18
    for st in SousTypeArticle.objects.select_related('type_article').all():
        ws2.append([st.id, st.libelle, st.type_article_id])

    # Feuille de référence des unités
    ws3 = wb.create_sheet('Unites')
    ws3.append(['ID', 'Libellé', 'Description'])
    for col in range(1, 4):
        cell = ws3.cell(row=1, column=col)
        cell.fill = PatternFill(start_color='FFB300', end_color='FFB300', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws3.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 22
    for u in Unite.objects.all():
        ws3.append([u.id, u.libelle, (u.description or '')[:50]])

    # Feuille "Référence complète" : tous les ID valides en un seul endroit (aucune confusion)
    ws_ref = wb.create_sheet('Reference_Complete', 1)  # en 2e position pour être visible
    ref_title_fill = PatternFill(start_color='5C6BC0', end_color='5C6BC0', fill_type='solid')
    ref_title_font = Font(bold=True, color='FFFFFF', size=12)
    ref_section_fill = PatternFill(start_color='7986CB', end_color='7986CB', fill_type='solid')
    ref_section_font = Font(bold=True, color='FFFFFF')

    ws_ref.append(['RÉFÉRENCE COMPLÈTE — Utilisez UNIQUEMENT les ID ci-dessous dans la feuille "Articles"'])
    ws_ref.merge_cells('A1:E1')
    ws_ref.cell(row=1, column=1).fill = ref_title_fill
    ws_ref.cell(row=1, column=1).font = ref_title_font
    ws_ref.cell(row=1, column=1).alignment = header_align
    ws_ref.row_dimensions[1].height = 22

    ws_ref.append([])
    ws_ref.append(['SOUS_TYPE_ARTICLE_ID — Colonne 3 de la feuille Articles (tous les ID existants)'])
    ws_ref.merge_cells('A3:E3')
    ws_ref.cell(row=3, column=1).fill = ref_section_fill
    ws_ref.cell(row=3, column=1).font = ref_section_font
    ws_ref.append(['ID', 'Libellé sous-type', 'Type article (parent)', 'Type article ID'])
    for col in range(1, 5):
        cell = ws_ref.cell(row=4, column=col)
        cell.fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_sous = 5
    for st in SousTypeArticle.objects.select_related('type_article').order_by('type_article_id', 'id'):
        ws_ref.append([
            st.id,
            st.libelle,
            st.type_article.libelle if st.type_article else '',
            st.type_article_id,
        ])
        for col in range(1, 5):
            ws_ref.cell(row=row_sous, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_sous += 1

    ws_ref.append([])
    ws_ref.append(['UNITE_ID — Colonne 4 de la feuille Articles (tous les ID existants)'])
    ws_ref.merge_cells(f'A{row_sous + 1}:E{row_sous + 1}')
    ws_ref.cell(row=row_sous + 1, column=1).fill = ref_section_fill
    ws_ref.cell(row=row_sous + 1, column=1).font = ref_section_font
    row_sous += 2
    ws_ref.append(['ID', 'Libellé', 'Description'])
    for col in range(1, 4):
        cell = ws_ref.cell(row=row_sous, column=col)
        cell.fill = PatternFill(start_color='FFB300', end_color='FFB300', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_sous += 1
    for u in Unite.objects.order_by('id'):
        ws_ref.append([u.id, u.libelle, (u.description or '')])
        for col in range(1, 4):
            ws_ref.cell(row=row_sous, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_sous += 1

    for c in ['A', 'B', 'C', 'D', 'E']:
        ws_ref.column_dimensions[c].width = 24

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="modele_articles.xlsx"'
    return response


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_articles(request):
    """Importe un fichier Excel d'articles et crée les articles + un Stock à 0 pour chacun."""
    from stock.views import _get_tenant_ids
    tenant_id, branch_id = _get_tenant_ids(request)
    if not tenant_id:
        return JsonResponse(
            {'error': _('Contexte entreprise manquant. Connectez-vous et sélectionnez une entreprise.')},
            status=400
        )

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': _('Aucun fichier envoyé.')}, status=400)

    wb = openpyxl.load_workbook(file)
    if 'Articles' not in wb.sheetnames:
        return JsonResponse(
            {'error': 'Le fichier doit contenir une feuille nommée "Articles".'},
            status=400,
        )
    ws = wb['Articles']
    created = []
    errors = []

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(
            c is None or (isinstance(c, str) and not c.strip()) for c in row
        ):
            continue

        if len(row) < 4:
            errors.append(
                f'Ligne {row_idx}: au moins nom_scientifique, sous_type_article_id, unite_id requis.'
            )
            continue

        nom_scientifique_raw = row[0]
        nom_commercial_raw = row[1] if len(row) > 1 else None
        sous_type_id_raw = row[2] if len(row) > 2 else None
        unite_id_raw = row[3] if len(row) > 3 else None
        emplacement_raw = row[4] if len(row) > 4 else None

        nom_scientifique = (
            str(nom_scientifique_raw).strip()
            if nom_scientifique_raw is not None
            else ''
        )
        if not nom_scientifique:
            errors.append(f'Ligne {row_idx}: nom_scientifique obligatoire.')
            continue

        nom_commercial = None
        if nom_commercial_raw is not None and str(nom_commercial_raw).strip():
            nom_commercial = str(nom_commercial_raw).strip()

        def _int_or_none(val):
            if val is None:
                return None
            if isinstance(val, (int, float)):
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return None
            s = str(val).strip()
            if not s:
                return None
            try:
                return int(float(s))
            except (ValueError, TypeError):
                return None

        sous_type_id = _int_or_none(sous_type_id_raw)
        unite_id = _int_or_none(unite_id_raw)

        if not sous_type_id or not SousTypeArticle.objects.filter(pk=sous_type_id).exists():
            errors.append(
                f'Ligne {row_idx}: sous_type_article_id invalide ou inconnu ({sous_type_id_raw}).'
            )
            continue
        if not unite_id or not Unite.objects.filter(pk=unite_id).exists():
            errors.append(
                f'Ligne {row_idx}: unite_id invalide ou inconnu ({unite_id_raw}).'
            )
            continue

        emplacement = '1'
        if emplacement_raw is not None and str(emplacement_raw).strip():
            emplacement = str(emplacement_raw).strip()[:200]

        data = {
            'nom_scientifique': nom_scientifique,
            'nom_commercial': nom_commercial,
            'sous_type_article_id': sous_type_id,
            'unite_id': unite_id,
        }
        serializer = ArticleSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            errors.append(f'Ligne {row_idx}: {serializer.errors}')
            continue

        try:
            article = serializer.save(entreprise_id=tenant_id, succursale_id=branch_id)
            if emplacement != '1':
                article.emplacement = emplacement
                article.save(update_fields=['emplacement'])
            # Créer le Stock pour le nouvel article (comme ArticleViewSet.perform_create)
            Stock.objects.get_or_create(
                article=article,
                defaults={'Qte': 0, 'seuilAlert': 0},
            )
            created.append({
                'article_id': article.article_id,
                'nom_scientifique': article.nom_scientifique,
                'nom_commercial': article.nom_commercial,
            })
        except Exception as e:
            errors.append(f'Ligne {row_idx}: {str(e)}')

    if errors and not created:
        return JsonResponse({'error': 'Import échoué.', 'details': errors}, status=400)

    return JsonResponse(
        {
            'message': f'{len(created)} article(s) importé(s).',
            'crees': created,
            'erreurs': errors if errors else None,
        },
        status=201,
    )


# --- Import Sortie / Vente (même structure que approvisionnement et articles) ---

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_template_sortie(request):
    """Télécharge un fichier Excel modèle pour l'import de sorties (ventes)."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    tenant_id = request.user.get_entreprise_id() if request.user.is_authenticated else None
    articles_qs = Article.objects.filter(entreprise_id=tenant_id) if tenant_id else Article.objects.all()
    devises_qs = Devise.objects.filter(entreprise_id=tenant_id) if tenant_id else Devise.objects.all()
    clients_qs = Client.objects.filter(entreprise_id=tenant_id) if tenant_id else Client.objects.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Sortie'
    entetes = ['statut', 'motif', 'client_id', 'article_id', 'quantite', 'prix_unitaire', 'devise_id']
    ws.append(entetes)
    header_fill = PatternFill(start_color='E64A19', end_color='E64A19', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    header_align = Alignment(horizontal='center', vertical='center')
    thin = Side(border_style="thin", color="000000")
    for col in range(1, len(entetes) + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 18

    # Exemples : PAYEE (payée) ou EN_CREDIT (vente à crédit — client_id obligatoire)
    ws.append(['PAYEE', 'Vente du jour', '', 'MED001', 5, 1200, 1])
    ws.append(['', '', '', 'VIT001', 2, 500, 1])
    ws.append(['EN_CREDIT', 'Vente à crédit', 'CLI0001', 'MED001', 3, 1200, 1])

    # Feuille Reference_Complete : tous les articles (code) + devises + clients
    ws_ref = wb.create_sheet('Reference_Complete', 1)
    ref_title_fill = PatternFill(start_color='5C6BC0', end_color='5C6BC0', fill_type='solid')
    ref_title_font = Font(bold=True, color='FFFFFF', size=12)
    ref_section_fill = PatternFill(start_color='7986CB', end_color='7986CB', fill_type='solid')
    ref_section_font = Font(bold=True, color='FFFFFF')

    ws_ref.append(['RÉFÉRENCE COMPLÈTE — Utilisez UNIQUEMENT les codes/ID ci-dessous dans la feuille "Sortie"'])
    ws_ref.merge_cells('A1:G1')
    ws_ref.cell(row=1, column=1).fill = ref_title_fill
    ws_ref.cell(row=1, column=1).font = ref_title_font
    ws_ref.cell(row=1, column=1).alignment = header_align
    ws_ref.row_dimensions[1].height = 22

    ws_ref.append([])
    ws_ref.append(['STATUT — Colonne 1 : PAYEE (payée) ou EN_CREDIT (vente à crédit/dette). Si EN_CREDIT, client_id (col. 3) OBLIGATOIRE.'])
    ws_ref.merge_cells('A3:G3')
    ws_ref.cell(row=3, column=1).fill = ref_section_fill
    ws_ref.cell(row=3, column=1).font = ref_section_font
    ws_ref.append([])
    ws_ref.append(['ARTICLE_ID (CODE) — Colonne 4 de la feuille Sortie (tous les articles)'])
    ws_ref.merge_cells('A5:G5')
    ws_ref.cell(row=5, column=1).fill = ref_section_fill
    ws_ref.cell(row=5, column=1).font = ref_section_font
    ws_ref.append(['CODE PRODUIT (article_id)', 'Nom scientifique', 'Nom commercial'])
    for col in range(1, 4):
        cell = ws_ref.cell(row=6, column=col)
        cell.fill = PatternFill(start_color='1976D2', end_color='1976D2', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_cur = 7
    for article in articles_qs.order_by('article_id'):
        ws_ref.append([article.article_id, article.nom_scientifique, article.nom_commercial or ''])
        for col in range(1, 4):
            ws_ref.cell(row=row_cur, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_cur += 1

    ws_ref.append([])
    ws_ref.append(['DEVISE_ID — Colonne 7 de la feuille Sortie (toutes les devises)'])
    ws_ref.merge_cells(f'A{row_cur + 1}:G{row_cur + 1}')
    ws_ref.cell(row=row_cur + 1, column=1).fill = ref_section_fill
    ws_ref.cell(row=row_cur + 1, column=1).font = ref_section_font
    row_cur += 2
    ws_ref.append(['ID', 'Sigle', 'Nom', 'Symbole'])
    for col in range(1, 5):
        cell = ws_ref.cell(row=row_cur, column=col)
        cell.fill = PatternFill(start_color='388E3C', end_color='388E3C', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_cur += 1
    for devise in devises_qs.order_by('id'):
        ws_ref.append([devise.id, devise.sigle, devise.nom, devise.symbole])
        for col in range(1, 5):
            ws_ref.cell(row=row_cur, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_cur += 1

    ws_ref.append([])
    ws_ref.append(['CLIENT_ID — Colonne 3 de la feuille Sortie (OBLIGATOIRE si statut=EN_CREDIT, sinon optionnel)'])
    ws_ref.merge_cells(f'A{row_cur + 1}:G{row_cur + 1}')
    ws_ref.cell(row=row_cur + 1, column=1).fill = ref_section_fill
    ws_ref.cell(row=row_cur + 1, column=1).font = ref_section_font
    row_cur += 2
    ws_ref.append(['ID', 'Nom', 'Téléphone'])
    for col in range(1, 4):
        cell = ws_ref.cell(row=row_cur, column=col)
        cell.fill = PatternFill(start_color='7B1FA2', end_color='7B1FA2', fill_type='solid')
        cell.font = Font(bold=True, color='FFFFFF')
        cell.alignment = header_align
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
    row_cur += 1
    for client in clients_qs.order_by('nom'):
        ws_ref.append([client.id, client.nom, (client.telephone or '')])
        for col in range(1, 4):
            ws_ref.cell(row=row_cur, column=col).border = Border(top=thin, left=thin, right=thin, bottom=thin)
        row_cur += 1

    for c in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        ws_ref.column_dimensions[c].width = 22

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="modele_sortie_vente.xlsx"'
    return response


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_sortie(request):
    """Importe un fichier Excel de sortie (vente) et crée une Sortie avec ses lignes (FIFO, caisse, etc.)."""
    from stock.views import _get_tenant_ids
    tenant_id, branch_id = _get_tenant_ids(request)
    if not tenant_id:
        return JsonResponse({'error': _('Contexte entreprise manquant. Connectez-vous et sélectionnez une entreprise.')}, status=400)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': _('Aucun fichier envoyé.')}, status=400)

    wb = openpyxl.load_workbook(file)
    if 'Sortie' not in wb.sheetnames:
        return JsonResponse(
            {'error': 'Le fichier doit contenir une feuille nommée "Sortie".'},
            status=400,
        )

    ws = wb['Sortie']
    lignes = []
    statut_global = 'PAYEE'
    motif_global = request.POST.get('motif', 'Import Excel')
    client_id_global = None

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(c is None or (isinstance(c, str) and not str(c).strip()) for c in row):
            continue

        # Colonnes : statut, motif, client_id, article_id, quantite, prix_unitaire, devise_id (min 5 pour article_id + quantite)
        if len(row) < 5:
            return JsonResponse(
                {'error': f'Ligne {row_idx}: colonnes requises statut, motif, client_id, article_id, quantite (prix_unitaire et devise_id optionnels).'},
                status=400,
            )

        statut_raw = row[0] if len(row) > 0 else None
        motif_raw = row[1] if len(row) > 1 else None
        client_id_raw = row[2] if len(row) > 2 else None
        article_id_raw = row[3] if len(row) > 3 else None
        quantite_raw = row[4] if len(row) > 4 else None
        prix_unitaire_raw = row[5] if len(row) > 5 else None
        devise_id_raw = row[6] if len(row) > 6 else None

        if row_idx == 2:
            if statut_raw is not None and str(statut_raw).strip().upper() in ('EN_CREDIT', 'EN CREDIT', 'CREDIT'):
                statut_global = 'EN_CREDIT'
            elif statut_raw is not None and str(statut_raw).strip().upper() in ('PAYEE', 'PAYÉ', 'PAYEE'):
                statut_global = 'PAYEE'
            if motif_raw is not None and str(motif_raw).strip():
                motif_global = str(motif_raw).strip()
            if client_id_raw is not None and str(client_id_raw).strip():
                try:
                    cid = str(client_id_raw).strip()
                    if Client.objects.filter(id=cid).exists():
                        client_id_global = cid
                except Exception:
                    pass

        article_id = str(article_id_raw).strip() if article_id_raw is not None else None
        if not article_id:
            continue

        def _num(val):
            if val is None:
                return None
            if isinstance(val, (int, float)):
                try:
                    return int(val) if isinstance(val, float) and val == int(val) else float(val)
                except (ValueError, TypeError):
                    return None
            s = str(val).strip().replace(',', '.')
            if not s:
                return None
            try:
                return int(float(s)) if float(s) == int(float(s)) else float(s)
            except (ValueError, TypeError):
                return None

        qte = _num(quantite_raw)
        if qte is None or (isinstance(qte, (int, float)) and (qte <= 0 or (isinstance(qte, float) and qte != int(qte)))):
            return JsonResponse({'error': f'Ligne {row_idx}: quantité invalide (entier > 0).'}, status=400)
        qte = int(qte)

        prix_u = _num(prix_unitaire_raw)
        if prix_u is not None and prix_u < 0:
            return JsonResponse({'error': f'Ligne {row_idx}: prix_unitaire ne peut pas être négatif.'}, status=400)
        prix_final = float(prix_u) if prix_u is not None else 0.0

        devise_id = None
        if devise_id_raw is not None:
            if isinstance(devise_id_raw, (int, float)):
                try:
                    devise_id = int(devise_id_raw)
                except (ValueError, TypeError):
                    pass
            elif isinstance(devise_id_raw, str) and devise_id_raw.strip():
                try:
                    devise_id = int(float(devise_id_raw))
                except (ValueError, TypeError):
                    pass
        if not devise_id or not Devise.objects.filter(pk=devise_id).exists():
            default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
            devise_id = default_dev.id if default_dev else None
        if not devise_id:
            return JsonResponse({'error': f'Ligne {row_idx}: devise_id invalide et aucune devise principale.'}, status=400)

        lignes.append({
            'article_id': article_id,
            'quantite': qte,
            'prix_unitaire': prix_final,
            'devise_id': devise_id,
        })

    if not lignes:
        return JsonResponse({'error': 'Aucune ligne de sortie valide dans le fichier.'}, status=400)

    # Vente en crédit (dette) : le client est obligatoire
    if statut_global == 'EN_CREDIT':
        if not client_id_global:
            return JsonResponse({
                'error': 'Pour une vente en crédit (statut EN_CREDIT), le client_id est obligatoire. Renseignez la colonne client_id sur la première ligne de la feuille Sortie.'
            }, status=400)
        try:
            client_obj = Client.objects.get(id=client_id_global)
        except Client.DoesNotExist:
            return JsonResponse({
                'error': f'Client avec ID "{client_id_global}" introuvable. Vente en crédit impossible.'
            }, status=400)

    # Appeler la même logique que SortieViewSet.create (FIFO, LigneSortieLot, Stock, MouvementCaisse)
    from rest_framework.request import Request
    from stock.views import SortieViewSet
    from stock.models import Sortie as SortieModel, DetteClient
    from decimal import Decimal

    payload = {
        'motif': motif_global,
        'statut': statut_global,
        'client_id': client_id_global,
        'lignes': lignes,
    }
    old_data = getattr(request, '_full_data', None)
    request._full_data = payload
    try:
        viewset = SortieViewSet()
        viewset.request = request
        viewset.action = 'create'
        viewset.format_kwarg = None
        viewset.kwargs = {}
        response = viewset.create(request)
    except Exception as e:
        request._full_data = old_data
        return JsonResponse({'error': f'Erreur lors de la création de la sortie: {str(e)}'}, status=400)
    request._full_data = old_data

    if response.status_code != 201:
        try:
            err_detail = response.data if hasattr(response, 'data') else str(response)
            return JsonResponse({'error': 'Création sortie refusée.', 'details': err_detail}, status=400)
        except Exception:
            return JsonResponse({'error': 'Création sortie refusée.'}, status=400)

    # Si vente en crédit : créer la DetteClient (une dette par sortie)
    if statut_global == 'EN_CREDIT' and client_id_global:
        sortie_id = response.data.get('id')
        sortie = SortieModel.objects.filter(pk=sortie_id).select_related('client').prefetch_related('lignes').first()
        if sortie and not DetteClient.objects.filter(sortie=sortie).exists():
            total_dette = Decimal('0.00')
            devise_dette = None
            for ligne in sortie.lignes.all():
                total_dette += Decimal(str(ligne.quantite)) * Decimal(str(ligne.prix_unitaire))
                if ligne.devise_id and devise_dette is None:
                    devise_dette = ligne.devise
            if devise_dette is None:
                devise_dette = Devise.objects.filter(entreprise_id=sortie.entreprise_id, est_principal=True).first()
            client_obj = Client.objects.get(id=client_id_global)
            DetteClient.objects.create(
                sortie=sortie,
                client=client_obj,
                montant_total=total_dette.quantize(Decimal('0.01')),
                devise=devise_dette,
                entreprise_id=sortie.entreprise_id,
                succursale_id=sortie.succursale_id,
            )

    return JsonResponse(response.data, status=201)
