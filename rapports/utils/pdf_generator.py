"""
Générateur de PDF pour les rapports
Format A4 (210mm x 297mm)
Marges: 20mm de chaque côté
"""
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from django.utils.translation import gettext as _
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


class PDFGenerator:
    """Classe pour générer des PDF de rapports au format A4"""
    
    def __init__(self):
        # Format A4: 210mm x 297mm
        self.page_width = 210 * mm
        self.page_height = 297 * mm
        self.margin = 20 * mm
        
        # Largeur utilisable (avec marges)
        self.usable_width = self.page_width - (2 * self.margin)
        
        # Styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Créer des styles personnalisés"""
        # Style pour le titre principal
        self.styles.add(ParagraphStyle(
            name='TitrePrincipal',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Style pour l'en-tête entreprise — taille proche du titre facture, aligné à gauche
        self.styles.add(ParagraphStyle(
            name='EntrepriseNom',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='EntrepriseInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=3,
            alignment=TA_LEFT
        ))
        # Même rendu que EntrepriseNom / EntrepriseInfo mais centré (rapports A4)
        self.styles.add(ParagraphStyle(
            name='EntrepriseNomCenter',
            parent=self.styles['EntrepriseNom'],
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            name='EntrepriseInfoCenter',
            parent=self.styles['EntrepriseInfo'],
            alignment=TA_CENTER,
        ))
        # Variantes compactes (facture POS : nom + tél serrés, moins d'espace)
        self.styles.add(ParagraphStyle(
            name='EntrepriseNomCompact',
            parent=self.styles['EntrepriseNom'],
            spaceAfter=1
        ))
        self.styles.add(ParagraphStyle(
            name='EntrepriseInfoCompact',
            parent=self.styles['EntrepriseInfo'],
            spaceAfter=1
        ))
        
        # Style pour les sous-titres
        self.styles.add(ParagraphStyle(
            name='SousTitre',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Style pour le texte normal
        self.styles.add(ParagraphStyle(
            name='TexteNormal',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=6
        ))

    @staticmethod
    def _format_quantity(value, max_decimals=3):
        """Affiche une quantité sans zéros inutiles (41.00 -> 41, 41.50 -> 41.5)."""
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
    
    def _create_entete(self, entete_data, compact=False, centered=True, logo_size_mm=None):
        """Créer l'en-tête simplifié : logo (si présent), nom, slogan, téléphone uniquement.
        compact=True : espacements réduits (nom/tél serrés, peu d'espace avant le titre) pour facture POS.
        centered=True : bloc centré sur la largeur utile (rapports A4). Les tickets POS passent compact=True
        ou centered=False pour conserver l'alignement à gauche."""
        if compact:
            centered = False
        elements = []
        entreprise = entete_data.get('entreprise', {})
        if compact:
            style_nom = self.styles['EntrepriseNomCompact']
            style_info = self.styles['EntrepriseInfoCompact']
        elif centered:
            style_nom = self.styles['EntrepriseNomCenter']
            style_info = self.styles['EntrepriseInfoCenter']
        else:
            style_nom = self.styles['EntrepriseNom']
            style_info = self.styles['EntrepriseInfo']
        space_after_block = 4 if compact else 12  # points
        
        # Logo (si disponible) — gauche (tickets) ou centré (A4)
        logo_path = entreprise.get('logo_path')
        if logo_path:
            try:
                if logo_size_mm is None:
                    logo_size_mm = 24 if compact else 30
                max_w = logo_size_mm * mm
                max_h = logo_size_mm * mm
                img = Image(logo_path)
                if getattr(img, 'imageWidth', None) and getattr(img, 'imageHeight', None):
                    scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
                    img.drawWidth = img.imageWidth * scale
                    img.drawHeight = img.imageHeight * scale
                else:
                    img.drawWidth = max_w
                    img.drawHeight = max_h
                img.hAlign = 'CENTER' if centered else 'LEFT'
                elements.append(img)
                elements.append(Spacer(1, 4))
            except Exception:
                pass
        
        # Nom de l'entreprise
        elements.append(Paragraph(
            entreprise.get('nom', ''),
            style_nom
        ))
        
        # Slogan / devise (si disponible)
        slogan = (entreprise.get('slogan') or '').strip()
        if slogan:
            elements.append(Paragraph(slogan, style_info))
        
        # Téléphone (tout juste après le nom en mode compact)
        telephone = (entreprise.get('telephone') or '').strip()
        if telephone:
            elements.append(Paragraph(
                f"{_('Tél')}: {telephone}",
                style_info
            ))
        
        elements.append(Spacer(1, space_after_block))
        
        return elements

    def _append_generation_meta(self, elements, data):
        """
        Ajoute les métadonnées d'impression/génération si présentes:
        - Date impression
        - Imprimé par
        """
        meta = (data or {}).get('meta_generation') or {}
        printed_at = (meta.get('printed_at') or '').strip()
        printed_by = (meta.get('printed_by') or '').strip()
        if not printed_at:
            printed_at = timezone.now().strftime('%d/%m/%Y %H:%M')
        if printed_by:
            elements.append(Paragraph(f"{_('Imprimé par')}: {printed_by}", self.styles['TexteNormal']))
        elements.append(Paragraph(f"{_('Date impression')}: {printed_at}", self.styles['TexteNormal']))
        elements.append(Spacer(1, 8))

    @staticmethod
    def _get_generation_meta(data):
        meta = (data or {}).get('meta_generation') or {}
        printed_at = (meta.get('printed_at') or '').strip() or timezone.now().strftime('%d/%m/%Y %H:%M')
        printed_by = (meta.get('printed_by') or '').strip()
        return printed_at, printed_by

    def _draw_footer(self, canv, doc, data):
        """
        Pied de page commun :
        - Imprimé par (si disponible)
        - Date impression
        - Pagination (Page X)
        """
        printed_at, printed_by = self._get_generation_meta(data)
        y = 10 * mm

        canv.saveState()
        canv.setFont('Helvetica', 8)
        canv.setFillColor(colors.HexColor('#555555'))

        left_text = f"{_('Date impression')}: {printed_at}"
        if printed_by:
            left_text = f"{left_text}  |  {_('Imprimé par')}: {printed_by}"
        canv.drawString(doc.leftMargin, y, left_text)

        page_text = f"{_('Page')} {canv.getPageNumber()}"
        canv.drawRightString(doc.pagesize[0] - doc.rightMargin, y, page_text)
        canv.restoreState()

    def _build_with_footer(self, doc, elements, data):
        def _on_page(canv, _doc):
            self._draw_footer(canv, _doc, data)
        doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    
    # Libellés des statistiques (clé → msgid français pour traduction)
    _STATS_LABELS = {
        'total_articles': "Total articles",
        'en_alerte': "En alerte",
        'en_rupture': "En rupture",
        'normaux': "Normaux",
    }

    def _create_statistiques_table(self, stats_data, title=None):
        if title is None:
            title = _("Statistiques")
        """Créer un tableau de statistiques"""
        elements = []
        
        # Titre
        elements.append(Paragraph(title, self.styles['SousTitre']))
        
        # Données du tableau
        data = []
        for key, value in stats_data.items():
            label = _(self._STATS_LABELS.get(key, key.replace('_', ' ').title()))
            data.append([label, str(value)])
        
        # Créer le tableau
        table = Table(data, colWidths=[self.usable_width * 0.7, self.usable_width * 0.3])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7'))
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
        
        return elements
    
    def generate_inventaire_pdf(self, data):
        """Générer le PDF du rapport d'inventaire"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        elements = []
        
        # En-tête
        elements.extend(self._create_entete(data['entete'], logo_size_mm=30))
        
        # Titre du rapport
        elements.append(Paragraph(data['titre'], self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 12))
        
        # Période
        if 'periode' in data:
            periode_text = _("Période: du %(debut)s au %(fin)s") % {'debut': data['periode']['date_debut'], 'fin': data['periode']['date_fin']}
            elements.append(Paragraph(periode_text, self.styles['TexteNormal']))
            elements.append(Spacer(1, 8))
        
        # Statistiques
        elements.extend(self._create_statistiques_table(data['statistiques']))
        
        # Tableau des articles
        elements.append(Paragraph(_("Liste des Articles"), self.styles['SousTitre']))
        
        # En-têtes du tableau (sans colonne Type : type/sous-type affichés sous le nom)
        table_data = [[
            _('Article ID'),
            _('Nom'),
            _('Unité'),
            _('Stock'),
            _('P.U.'),
            _('Prix total'),
            _('Seuil'),
            _('Statut')
        ]]
        
        # Données : dans Nom on met le nom puis en dessous type et sous_type, texte aligné à gauche
        total_prix_total = Decimal('0.00')
        for article in data['articles']:
            pu = article.get('prix_unitaire', 0)
            pt = article.get('prix_total', 0)
            try:
                total_prix_total += Decimal(str(pt)) if pt is not None else Decimal('0.00')
            except (TypeError, ValueError, ArithmeticError):
                pass
            if not isinstance(pu, str):
                pu = f"{Decimal(str(pu)).quantize(Decimal('0.01')):.2f}" if pu is not None else "0.00"
            if not isinstance(pt, str):
                pt = f"{Decimal(str(pt)).quantize(Decimal('0.01')):.2f}" if pt is not None else "0.00"
            nom_affichage = article['nom_scientifique']
            if article.get('nom_commercial'):
                nom_affichage += f" ({article['nom_commercial']})"
            nom_affichage += f"<br/><font size='7' color='#555'>{article['type_article']} / {article['sous_type']}</font>"
            style_nom = ParagraphStyle('InventaireNom', parent=self.styles['Normal'], fontSize=8, alignment=TA_LEFT, wordWrap='CJK')
            table_data.append([
                article['article_id'],
                Paragraph(nom_affichage, style_nom),
                article['unite'],
                self._format_quantity(article['quantite_stock']),
                pu,
                pt,
                self._format_quantity(article['seuil_alerte']),
                article['statut']
            ])

        # Ligne de total général (Prix total = somme de tous les prix total)
        total_pt_str = f"{total_prix_total.quantize(Decimal('0.01')):.2f}"
        table_data.append([
            '',
            _('TOTAL GÉNÉRAL'),
            '',
            '',
            '',
            total_pt_str,
            '',
            ''
        ])
        last_row_idx = len(table_data) - 1

        # Créer le tableau (8 colonnes)
        col_widths = [
            self.usable_width * 0.10,  # Article ID
            self.usable_width * 0.28,  # Nom (type/sous-type en dessous)
            self.usable_width * 0.08,  # Unité
            self.usable_width * 0.08,  # Stock
            self.usable_width * 0.10,  # P.U.
            self.usable_width * 0.12,  # Prix total
            self.usable_width * 0.08,  # Seuil
            self.usable_width * 0.14   # Statut
        ]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style du tableau (texte du corps aligné à gauche pour les colonnes texte)
        table_style = [
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Corps : colonnes 0 (Article ID), 1 (Nom) alignées à gauche
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),   # Unité
            ('ALIGN', (3, 1), (5, -1), 'RIGHT'),  # Stock, P.U., Prix total
            ('ALIGN', (6, 1), (-1, -1), 'CENTER'), # Seuil, Statut
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]
        
        # Alternance de couleurs pour les lignes (sauf la ligne total)
        for i in range(1, last_row_idx):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))
            # Coloration selon le statut (dernière colonne = Statut, index 7)
            statut = data['articles'][i-1]['statut']
            if statut == 'RUPTURE':
                table_style.append(('BACKGROUND', (7, i), (7, i), colors.HexColor('#e74c3c')))
                table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.whitesmoke))
            elif statut == 'ALERTE':
                table_style.append(('BACKGROUND', (7, i), (7, i), colors.HexColor('#f39c12')))
                table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.whitesmoke))
            elif statut == 'NORMAL':
                table_style.append(('BACKGROUND', (7, i), (7, i), colors.HexColor('#27ae60')))
                table_style.append(('TEXTCOLOR', (7, i), (7, i), colors.whitesmoke))

        # Ligne total général : fond et police en gras
        table_style.append(('BACKGROUND', (0, last_row_idx), (-1, last_row_idx), colors.HexColor('#2c3e50')))
        table_style.append(('TEXTCOLOR', (0, last_row_idx), (-1, last_row_idx), colors.whitesmoke))
        table_style.append(('FONTNAME', (0, last_row_idx), (-1, last_row_idx), 'Helvetica-Bold'))
        table_style.append(('ALIGN', (0, last_row_idx), (1, last_row_idx), 'LEFT'))
        table_style.append(('ALIGN', (5, last_row_idx), (5, last_row_idx), 'RIGHT'))
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        # Construire le PDF
        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer
    
    def generate_bon_entree_pdf(self, data):
        """Générer le PDF du rapport de réquisition"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        elements = []
        
        # En-tête
        elements.extend(self._create_entete(data['entete'], logo_size_mm=26))
        
        # Titre
        elements.append(Paragraph(data['titre'], self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 12))
        
        # Instructions
        instruction_style = ParagraphStyle(
            name='Instruction',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#e67e22'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph(data['instructions'], instruction_style))
        
        # Statistiques
        elements.extend(self._create_statistiques_table(data['statistiques']))
        
        # Tableau des articles à réapprovisionner (sous-titre du rapport de réquisition)
        elements.append(Paragraph(_("Articles à réapprovisionner"), self.styles['SousTitre']))
        
        # En-têtes : Article, Unité, Dernier prix, Quantité, Prix Total, Statut
        table_data = [[
            _('Article'),
            _('Unité'),
            _('Dernier prix'),
            _('Quantité'),
            _('Prix Total'),
            _('Statut')
        ]]
        
        # Données
        for article in data['articles']:
            table_data.append([
                article['designation'],
                article['unite'],
                article.get('dernier_prix', '') or '',
                '___________',  # À remplir
                '___________',  # À remplir
                article['statut_stock']
            ])
        
        # Largeurs de colonnes
        col_widths = [
            self.usable_width * 0.28,  # Article
            self.usable_width * 0.10,   # Unité
            self.usable_width * 0.12,   # Dernier prix
            self.usable_width * 0.12,   # Quantité
            self.usable_width * 0.13,   # Prix Total
            self.usable_width * 0.25    # Statut
        ]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Style
        table_style = [
            # En-tête
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Corps
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (4, -1), 'RIGHT'),  # Dernier prix, Quantité, Prix Total
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            
            # Grille
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]
        
        # Alternance et coloration selon statut
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))
            
            # Coloration du statut
            statut = data['articles'][i-1]['statut_stock']
            if 'RUPTURE' in statut:
                table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#e74c3c')))
                table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.whitesmoke))
                table_style.append(('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'))
            elif 'ALERTE' in statut:
                table_style.append(('BACKGROUND', (4, i), (4, i), colors.HexColor('#f39c12')))
                table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.whitesmoke))
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        # Construire le PDF
        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer
    
    def generate_bon_achat_pdf(self, data):
        """Générer le PDF du bon d'achat.
        - Intervalle (dates) en haut.
        - Zone commentaire en haut.
        - Tableau sans colonnes Date ni Devise.
        - Ligne total général en bas du tableau.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        elements = []
        
        # En-tête
        elements.extend(self._create_entete(data['entete'], logo_size_mm=26))
        
        # Titre
        elements.append(Paragraph(data['titre'], self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 8))
        
        # Intervalle en haut (période)
        if 'periode' in data:
            p = data.get('periode') or {}
            d0 = p.get('date_debut')
            d1 = p.get('date_fin')
            if d0 and d1:
                periode_text = _("<b>Intervalle :</b> du %(debut)s au %(fin)s") % {'debut': d0, 'fin': d1}
                elements.append(Paragraph(periode_text, self.styles['TexteNormal']))
                elements.append(Spacer(1, 8))

        # Détail complet d'une entrée (si filtre entree_id utilisé)
        entree_details = data.get('entree_details') or {}
        if entree_details:
            elements.append(Paragraph(_("<b>Détails de l'entrée sélectionnée</b>"), self.styles['SousTitre']))
            details_rows = []
            details_rows.append([_("N° Entrée"), str(entree_details.get('id') or '')])
            if entree_details.get('date_op'):
                details_rows.append([_("Date opération"), str(entree_details.get('date_op'))])
            if entree_details.get('libele'):
                details_rows.append([_("Libellé"), str(entree_details.get('libele'))])
            if entree_details.get('description'):
                details_rows.append([_("Description"), str(entree_details.get('description'))])
            if entree_details.get('entreprise'):
                details_rows.append([_("Entreprise"), str(entree_details.get('entreprise'))])
            if entree_details.get('succursale'):
                details_rows.append([_("Succursale"), str(entree_details.get('succursale'))])

            details_table = Table(
                details_rows,
                colWidths=[self.usable_width * 0.28, self.usable_width * 0.72],
            )
            details_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d0d0d0')),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
            ]))
            elements.append(details_table)
            elements.append(Spacer(1, 8))
        
        # Zone commentaire (à remplir)
        comment_style = ParagraphStyle(
            name='Commentaire',
            parent=self.styles['Normal'],
            fontSize=9,
            leftIndent=0,
            borderPadding=5,
            backColor=colors.HexColor('#f8f9fa'),
        )
        elements.append(Paragraph(f"<b>{_('Commentaire')}:</b>", self.styles['TexteNormal']))
        elements.append(Paragraph("_ " * 40, comment_style))  # Ligne pour écrire
        elements.append(Spacer(1, 12))
        
        # Tableau des achats (sans Date, sans Devise)
        elements.append(Paragraph(_("Détail des Achats"), self.styles['SousTitre']))
        
        table_data = [[
            _('N° Entrée'),
            _('Article'),
            _('Qté'),
            _('P.U.'),
            _('Total')
        ]]
        
        total_general = Decimal('0.00')
        for achat in data['achats']:
            try:
                total_general += Decimal(str(achat['prix_total']))
            except (TypeError, ValueError, ArithmeticError):
                pass
            table_data.append([
                str(achat['numero_entree']),
                achat['designation'],
                self._format_quantity(achat['quantite']),
                str(achat['prix_unitaire']),
                str(achat['prix_total'])
            ])
        
        # Ligne total général
        table_data.append([
            '',
            _('TOTAL GÉNÉRAL'),
            '',
            '',
            f"{total_general.quantize(Decimal('0.01')):.2f}"
        ])
        last_row_idx = len(table_data) - 1
        
        col_widths = [
            self.usable_width * 0.12,  # N° Entrée
            self.usable_width * 0.38,  # Article
            self.usable_width * 0.12,  # Qté
            self.usable_width * 0.18,  # P.U.
            self.usable_width * 0.20   # Total
        ]
        
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]
        
        for i in range(1, last_row_idx):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))
        
        # Ligne total général
        table_style.append(('BACKGROUND', (0, last_row_idx), (-1, last_row_idx), colors.HexColor('#2c3e50')))
        table_style.append(('TEXTCOLOR', (0, last_row_idx), (-1, last_row_idx), colors.whitesmoke))
        table_style.append(('FONTNAME', (0, last_row_idx), (-1, last_row_idx), 'Helvetica-Bold'))
        table_style.append(('ALIGN', (1, last_row_idx), (1, last_row_idx), 'RIGHT'))
        table_style.append(('ALIGN', (4, last_row_idx), (4, last_row_idx), 'RIGHT'))
        
        table.setStyle(TableStyle(table_style))
        elements.append(table)
        
        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer

    def generate_ventes_pdf(self, data):
        """
        Rapport des ventes au même style visuel que le bon d'achat.
        Attendu `data` : entete, titre, periode, lignes_ventes, total_quantite, total_montant_vente.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )
        elements = []
        elements.extend(self._create_entete(data['entete'], logo_size_mm=24))
        elements.append(Paragraph(data['titre'], self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 8))
        if 'periode' in data:
            periode_text = _('<b>Période :</b> du %(debut)s au %(fin)s') % {
                'debut': data['periode']['date_debut'],
                'fin': data['periode']['date_fin'],
            }
            elements.append(Paragraph(periode_text, self.styles['TexteNormal']))
            elements.append(Spacer(1, 8))
        filtres = data.get('filtres') or {}
        filtres_lines = []
        if filtres.get('date_jour'):
            filtres_lines.append(_("Date jour: %(d)s") % {'d': filtres['date_jour']})
        if filtres.get('mois') and filtres.get('annee'):
            filtres_lines.append(_("Mois: %(m)s/%(y)s") % {'m': filtres['mois'], 'y': filtres['annee']})
        if filtres.get('client_id'):
            filtres_lines.append(_("Client ID: %(v)s") % {'v': filtres['client_id']})
        if filtres.get('client_nom'):
            filtres_lines.append(_("Client: %(v)s") % {'v': filtres['client_nom']})
        if filtres.get('statut_paiement'):
            filtres_lines.append(_("Statut paiement: %(v)s") % {'v': filtres['statut_paiement']})
        if filtres.get('montant_min') or filtres.get('montant_max'):
            filtres_lines.append(_("Montant: %(min)s -> %(max)s") % {
                'min': filtres.get('montant_min') or '-',
                'max': filtres.get('montant_max') or '-',
            })
        if filtres.get('reference'):
            filtres_lines.append(_("Référence: %(v)s") % {'v': filtres['reference']})
        if filtres_lines:
            elements.append(Paragraph("<b>%s</b>" % _("Filtres actifs"), self.styles['TexteNormal']))
            for line in filtres_lines:
                elements.append(Paragraph(line, self.styles['TexteNormal']))
            elements.append(Spacer(1, 6))

        resume = data.get('resume_global') or {}
        if resume:
            elements.append(Paragraph("<b>%s</b>" % _("Résumé global"), self.styles['SousTitre']))
            resume_rows = [
                [_("Total sorties"), str(resume.get('total_sorties', 0))],
                [_("Total clients"), str(resume.get('total_clients', 0))],
                [_("Sorties comptant"), str(resume.get('sorties_comptant', 0))],
                [_("Sorties crédit"), str(resume.get('sorties_credit', 0))],
                [_("Total quantité"), str(resume.get('total_quantite', '0'))],
                [_("Total montant ventes"), str(resume.get('total_montant_vente', '0.00'))],
                [_("Bénéfice total"), str(resume.get('total_benefice', '0.00'))],
            ]
            resume_table = Table(
                resume_rows,
                colWidths=[self.usable_width * 0.52, self.usable_width * 0.48],
            )
            resume_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d0d0d0')),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
            ]))
            elements.append(resume_table)
            elements.append(Spacer(1, 8))

        rows = data.get('lignes_ventes') or []
        elements.append(Paragraph(_("Détail des Ventes"), self.styles['SousTitre']))

        table_data = [
            [
                _('N° Sortie'),
                _('Date'),
                _('Client'),
                _('Article'),
                _('PU achat'),
                _('PU vente'),
                _('Qté'),
                _('Total'),
                _('Bénéfice'),
                _('Statut'),
                _('Référence'),
            ]
        ]

        total_general = Decimal('0.00')
        for row in rows:
            art = row.get('article') or row.get('nom_scientifique') or '—'
            q = row.get('quantite')
            q_s = self._format_quantity(q) if q is not None else '—'
            pua = Decimal(str(row.get('pu_achat') or row.get('prix_achat_unitaire') or '0'))
            puv = Decimal(str(row.get('pu_vente') or row.get('prix_vente_unitaire') or '0'))
            qd = Decimal(str(q or 0))
            line_total = (qd * puv).quantize(Decimal('0.01'))
            total_general += line_total
            benefice_line = Decimal(str(row.get('benefice') or '0')).quantize(Decimal('0.01'))
            ref = str(row.get('reference', ''))[:36]
            date_s = str(row.get('date') or '')[:16]
            client_s = str(row.get('client') or '—')[:28]
            statut_s = str(row.get('statut_paiement') or '—')
            table_data.append(
                [
                    str(row.get('sortie_id') or '—'),
                    date_s,
                    client_s,
                    str(art)[:40] + ('...' if len(str(art)) > 40 else ''),
                    f"{pua.quantize(Decimal('0.01')):.2f}",
                    f"{puv.quantize(Decimal('0.01')):.2f}",
                    q_s,
                    f"{line_total:.2f}",
                    f"{benefice_line:.2f}",
                    statut_s,
                    ref,
                ]
            )

        tot_q = data.get('total_quantite') if data.get('total_quantite') is not None else Decimal('0')
        tot_mv = data.get('total_montant_vente') if data.get('total_montant_vente') is not None else str(total_general)
        table_data.append(
            [
                '',
                '',
                Paragraph(f"<b>{_('TOTAL GÉNÉRAL')}</b>", self.styles['Normal']),
                '—',
                '—',
                '—',
                self._format_quantity(tot_q),
                str(Decimal(str(tot_mv)).quantize(Decimal('0.01'))),
                str(Decimal(str((data.get('resume_global') or {}).get('total_benefice', '0'))).quantize(Decimal('0.01'))),
                '—',
                '—',
            ]
        )

        col_widths = [
            self.usable_width * 0.07,  # N° sortie
            self.usable_width * 0.11,  # Date
            self.usable_width * 0.10,  # Client
            self.usable_width * 0.15,  # Article
            self.usable_width * 0.09,  # PU achat
            self.usable_width * 0.09,  # PU vente
            self.usable_width * 0.07,  # Qté
            self.usable_width * 0.09,  # Total
            self.usable_width * 0.09,  # Bénéfice
            self.usable_width * 0.07,  # Statut
            self.usable_width * 0.07,  # Réf
        ]
        last_row_idx = len(table_data) - 1
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (3, -1), 'LEFT'),
            ('ALIGN', (4, 1), (8, -1), 'RIGHT'),
            ('ALIGN', (9, 1), (10, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]

        for i in range(1, last_row_idx):
            if i % 2 == 0:
                table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))

        table_style.append(('BACKGROUND', (0, last_row_idx), (-1, last_row_idx), colors.HexColor('#2c3e50')))
        table_style.append(('TEXTCOLOR', (0, last_row_idx), (-1, last_row_idx), colors.whitesmoke))
        table_style.append(('FONTNAME', (0, last_row_idx), (-1, last_row_idx), 'Helvetica-Bold'))
        table_style.append(('ALIGN', (2, last_row_idx), (2, last_row_idx), 'RIGHT'))
        table_style.append(('ALIGN', (6, last_row_idx), (8, last_row_idx), 'RIGHT'))

        table.setStyle(TableStyle(table_style))
        elements.append(table)
        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer

    def generate_journal_operations_pdf(self, data):
        """Générer le PDF du journal complet des opérations avec style harmonisé."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        elements = []
        elements.extend(self._create_entete(data['entete'], logo_size_mm=24))
        elements.append(Paragraph(data.get('titre', _('JOURNAL COMPLET DES OPÉRATIONS')), self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 8))

        periode = data.get('periode') or {}
        periode_label = periode.get('label')
        if not periode_label and periode.get('date_debut') and periode.get('date_fin'):
            periode_label = _("Du %(debut)s au %(fin)s") % {
                'debut': periode['date_debut'],
                'fin': periode['date_fin'],
            }
        if periode_label:
            elements.append(Paragraph(f"<b>{_('Période')}:</b> {periode_label}", self.styles['TexteNormal']))
            elements.append(Spacer(1, 6))

        filtres = data.get('filtres') or {}
        filtres_lines = []
        if filtres.get('month') and filtres.get('year'):
            filtres_lines.append(_("Mois/Année: %(m)s/%(y)s") % {'m': filtres['month'], 'y': filtres['year']})
        if filtres.get('date_min') or filtres.get('date_max'):
            filtres_lines.append(_("Dates: %(d0)s -> %(d1)s") % {
                'd0': filtres.get('date_min') or '-',
                'd1': filtres.get('date_max') or '-',
            })
        if filtres_lines:
            elements.append(Paragraph("<b>%s</b>" % _("Filtres actifs"), self.styles['TexteNormal']))
            for line in filtres_lines:
                elements.append(Paragraph(line, self.styles['TexteNormal']))
            elements.append(Spacer(1, 6))

        resume = data.get('resume_global') or {}
        if resume:
            elements.append(Paragraph("<b>%s</b>" % _("Résumé global"), self.styles['SousTitre']))
            resume_rows = [
                [_("Total opérations"), str(resume.get('total_operations', 0))],
                [_("Approvisionnements"), str(resume.get('approvisionnements', 0))],
                [_("Ventes"), str(resume.get('ventes', 0))],
                [_("Caisse entrées"), str(resume.get('caisse_entrees', 0))],
                [_("Caisse sorties"), str(resume.get('caisse_sorties', 0))],
                [_("Paiements dettes"), str(resume.get('paiements_dettes', 0))],
            ]
            resume_table = Table(
                resume_rows,
                colWidths=[self.usable_width * 0.52, self.usable_width * 0.48],
            )
            resume_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d0d0d0')),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(resume_table)
            elements.append(Spacer(1, 8))

        elements.append(Paragraph(_("Détail des opérations"), self.styles['SousTitre']))
        table_data = [[
            _('Date/Heure'),
            _('Type'),
            _('Désignation / Motif'),
            _('Montant'),
            _('Référence'),
        ]]
        for op in data.get('operations') or []:
            dt = op.get('date')
            if hasattr(dt, 'strftime'):
                dt_txt = dt.strftime('%d/%m/%Y %H:%M')
            else:
                dt_txt = str(dt or '')
            table_data.append([
                dt_txt,
                str(op.get('type_display') or op.get('type') or ''),
                str(op.get('designation') or '')[:90],
                str(op.get('montant_texte') or '-'),
                str(op.get('ref') or '')[:36],
            ])

        if len(table_data) == 1:
            elements.append(Paragraph(_('Aucune opération pour la période.'), self.styles['TexteNormal']))
        else:
            col_widths = [
                self.usable_width * 0.18,
                self.usable_width * 0.16,
                self.usable_width * 0.40,
                self.usable_width * 0.14,
                self.usable_width * 0.12,
            ]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
            ]
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))
            table.setStyle(TableStyle(table_style))
            elements.append(table)

        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer

    def generate_etat_caisse_pdf(self, data):
        """Générer le PDF de l'état de caisse (soldes par devise)."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        elements = []
        elements.extend(self._create_entete(data['entete'], logo_size_mm=24))
        elements.append(Paragraph(data.get('titre', _("ÉTAT DE LA CAISSE")), self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 8))

        filtres = data.get('filtres') or {}
        filtres_txt = []
        if filtres.get('date_min') or filtres.get('date_max'):
            filtres_txt.append(
                _("Période: %(d0)s -> %(d1)s") % {
                    'd0': filtres.get('date_min') or '-',
                    'd1': filtres.get('date_max') or '-',
                }
            )
        if filtres.get('type'):
            filtres_txt.append(_("Type mouvement: %(t)s") % {'t': filtres.get('type')})
        if filtres_txt:
            elements.append(Paragraph("<b>%s</b>" % _("Filtres actifs"), self.styles['TexteNormal']))
            for line in filtres_txt:
                elements.append(Paragraph(line, self.styles['TexteNormal']))
            elements.append(Spacer(1, 6))

        summary = data.get('resume_global') or {}
        resume_rows = [
            [_("Nombre devises actives"), str(summary.get('nb_devises_actives', 0))],
            [_("Total mouvements"), str(summary.get('total_mouvements_global', 0))],
            [_("Devise principale"), str(summary.get('devise_principale') or '-')],
        ]
        resume_table = Table(resume_rows, colWidths=[self.usable_width * 0.55, self.usable_width * 0.45])
        resume_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#d0d0d0')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(resume_table)
        elements.append(Spacer(1, 8))

        elements.append(Paragraph(_("Soldes par devise"), self.styles['SousTitre']))
        table_data = [[
            _('Devise'),
            _('Total Entrées'),
            _('Total Sorties'),
            _('Solde'),
            _('Nb mouvements'),
            _('Statut'),
        ]]
        for d in data.get('soldes_par_devise') or []:
            devise_label = f"{d.get('devise_sigle', '')} ({d.get('devise_symbole', '')})".strip()
            statut = 'POSITIF' if Decimal(str(d.get('solde') or '0')) > 0 else ('NEGATIF' if Decimal(str(d.get('solde') or '0')) < 0 else 'EQUILIBRE')
            table_data.append([
                devise_label,
                str(d.get('total_entrees', '0.00')),
                str(d.get('total_sorties', '0.00')),
                str(d.get('solde', '0.00')),
                str(d.get('nb_mouvements', 0)),
                statut,
            ])

        if len(table_data) == 1:
            elements.append(Paragraph(_('Aucune donnée caisse pour cette sélection.'), self.styles['TexteNormal']))
        else:
            col_widths = [
                self.usable_width * 0.20,
                self.usable_width * 0.18,
                self.usable_width * 0.18,
                self.usable_width * 0.18,
                self.usable_width * 0.13,
                self.usable_width * 0.13,
            ]
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (4, -1), 'RIGHT'),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ecf0f1')))
            table.setStyle(TableStyle(style))
            elements.append(table)

        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer

    def generate_clients_dettes_pdf(self, data):
        """Générer le PDF listant les clients et leurs dettes détaillées.

        Attendu `data`:
        {
            'entete': {...},
            'titre': 'Liste des clients et dettes',
            'clients': [
                {
                    'id': 'CLI0001', 'nom': 'Nom', 'telephone': '...', 'adresse': '...', 'email': '...',
                    'dettes': [ { 'id': 1, 'montant_total': '...', 'montant_paye': '...', 'solde_restant': '...', 'devise': {...}, 'date_creation': '...', 'date_echeance': '...', 'statut': '...','sortie_id': ... }, ... ]
                }, ...]
        }
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        elements = []
        # En-tête
        elements.extend(self._create_entete(data['entete'], logo_size_mm=22))

        # Titre
        elements.append(Paragraph(data.get('titre', _('Clients et Dettes')), self.styles['TitrePrincipal']))
        elements.append(Spacer(1, 12))

        # Global totals removed — per-client totals are rendered per client below

        # Pour chaque client, ajouter un bloc avec ses dettes (table)
        for client in data.get('clients', []):
            client_title = f"{client.get('id', '')} - {client.get('nom', '')}"
            elements.append(Paragraph(client_title, self.styles['SousTitre']))
            info_lines = []
            if client.get('telephone'):
                info_lines.append(f"{_('Tél')}: {client.get('telephone')}")
            if client.get('email'):
                info_lines.append(f"{_('Email')}: {client.get('email')}")
            if client.get('adresse'):
                info_lines.append(f"{_('Adresse')}: {client.get('adresse')}")
            if info_lines:
                elements.append(Paragraph(' | '.join(info_lines), self.styles['TexteNormal']))

            # Tableau des dettes pour ce client
            dettes = client.get('dettes', [])
            if not dettes:
                elements.append(Paragraph(_('Aucune dette enregistrée.'), self.styles['TexteNormal']))
                elements.append(Spacer(1, 6))
                continue

            table_data = [[
                _('Sortie / Produits'), _('Montant Total'), _('Montant Payé'), _('Solde'), _('Date création'), _('Échéance'), _('Statut')
            ]]

            for d in dettes:
                devise = d.get('devise') or {}
                sigle = devise.get('sigle') if isinstance(devise, dict) else ''

                # Build sortie / products description — only product names kept to reduce width
                sortie = d.get('sortie') or {}
                produits = sortie.get('produits') if isinstance(sortie, dict) else []
                prod_names = []
                for p in produits or []:
                    ns = (p.get('nom_scientifique') or '').strip()
                    nc = (p.get('nom_commercial') or '').strip()
                    name = ns
                    if nc:
                        name = f"{ns} ({nc})"
                    # Truncate long names
                    if len(name) > 40:
                        name = name[:37] + '...'
                    prod_names.append(name)

                # Join using line breaks so each product is on its own line in the cell
                sortie_text = '<br/>'.join(prod_names) if prod_names else ''
                sortie_paragraph = Paragraph(sortie_text, self.styles['TexteNormal']) if sortie_text else ''

                # Format date_creation to YYYY-MM-DD (remove time)
                date_creation_val = d.get('date_creation') or ''
                date_creation_display = date_creation_val[:10] if isinstance(date_creation_val, str) else str(date_creation_val)[:10]

                table_data.append([
                    sortie_paragraph,
                    str(d.get('montant_total', '0')),
                    str(d.get('montant_paye', '0')),
                    str(d.get('solde_restant', '0')),
                    date_creation_display,
                    str(d.get('date_echeance', '')),
                    str(d.get('statut', ''))
                ])

            # Adjust column widths for portrait: wider products column, remove Dette ID and Devise
            col_widths = [
                self.usable_width * 0.30,  # Sortie / Produits
                self.usable_width * 0.14,  # Montant Total
                self.usable_width * 0.14,  # Montant Payé
                self.usable_width * 0.14,  # Solde
                self.usable_width * 0.12,  # Date création
                self.usable_width * 0.12,  # Échéance
                self.usable_width * 0.04,  # Statut
            ]

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ]))

            elements.append(table)
            # Per-client totals (if provided in the JSON)
            client_totaux = client.get('totaux_encours') or {}
            if client_totaux:
                client_summary = [
                    [_('Tot. Montant (EN_COURS)'), _('Tot. Payé (EN_COURS)'), _('Solde (EN_COURS)')],
                    [
                        client_totaux.get('montant_total', '0'),
                        client_totaux.get('montant_paye', '0'),
                        client_totaux.get('solde_restant', '0')
                    ]
                ]
                client_table = Table(client_summary, colWidths=[self.usable_width / 3] * 3)
                client_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#95a5a6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elements.append(client_table)
            elements.append(Spacer(1, 12))

        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer

    def generate_clients_dettes_general_pdf(self, data):
        """Générer le PDF synthétique du rapport général des dettes clients.
        
        Attendu `data`:
        {
            'entete': {...},
            'titre': 'Rapport général des dettes clients',
            'clients': [
                {
                    'id': 'CLI0001', 'nom': 'Nom', 'telephone': '...', 'adresse': '...', 'email': '...',
                    'totaux_encours': {
                        'montant_total': '...',
                        'montant_paye': '...',
                        'solde_restant': '...'
                    }
                }, ...
            ],
            'totaux_globaux': {
                'montant_total': '...',
                'montant_paye': '...',
                'solde_restant': '...',
                'nombre_clients': ...
            }
        }
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        elements = []
        # En-tête
        elements.extend(self._create_entete(data['entete'], logo_size_mm=22))

        # Titre
        elements.append(Paragraph(data.get('titre', _('Rapport général des dettes clients')), self.styles['TitrePrincipal']))
        
        # Afficher la période si elle est fournie
        periode = data.get('periode')
        if periode:
            periode_text = []
            if periode.get('date_debut'):
                periode_text.append(_("Du %(date)s") % {'date': periode['date_debut']})
            if periode.get('date_fin'):
                periode_text.append(_("au %(date)s") % {'date': periode['date_fin']})
            if periode_text:
                elements.append(Paragraph(' | '.join(periode_text), self.styles['TexteNormal']))
        
        elements.append(Spacer(1, 12))

        # Tableau synthétique des clients avec dettes
        clients = data.get('clients', [])
        if not clients:
            elements.append(Paragraph(_('Aucun client avec des dettes en cours.'), self.styles['TexteNormal']))
        else:
            # En-têtes du tableau
            table_data = [[
                _('ID Client'),
                _('Nom'),
                _('Téléphone'),
                _('Montant Total'),
                _('Montant Payé'),
                _('Solde Restant')
            ]]

            # Données des clients
            for client in clients:
                totaux = client.get('totaux_encours', {})
                table_data.append([
                    client.get('id', ''),
                    client.get('nom', ''),
                    client.get('telephone', '') or '-',
                    totaux.get('montant_total', '0.00'),
                    totaux.get('montant_paye', '0.00'),
                    totaux.get('solde_restant', '0.00')
                ])

            # Ligne des totaux globaux
            totaux_globaux = data.get('totaux_globaux', {})
            table_data.append([
                '',
                Paragraph(f'<b>{_("TOTAL GÉNÉRAL")}</b>', self.styles['TexteNormal']),
                '',
                Paragraph(f"<b>{totaux_globaux.get('montant_total', '0.00')}</b>", self.styles['TexteNormal']),
                Paragraph(f"<b>{totaux_globaux.get('montant_paye', '0.00')}</b>", self.styles['TexteNormal']),
                Paragraph(f"<b>{totaux_globaux.get('solde_restant', '0.00')}</b>", self.styles['TexteNormal'])
            ])

            # Largeurs des colonnes
            col_widths = [
                self.usable_width * 0.12,  # ID Client
                self.usable_width * 0.25,  # Nom
                self.usable_width * 0.15,  # Téléphone
                self.usable_width * 0.16,  # Montant Total
                self.usable_width * 0.16,  # Montant Payé
                self.usable_width * 0.16,  # Solde Restant
            ]

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Aligner les montants à droite
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.whitesmoke, None]),  # Alternance de couleurs (sauf dernière ligne)
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#95a5a6')),  # Ligne des totaux
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, -1), (-1, -1), 9),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 12))

            # Statistiques
            nombre_clients = totaux_globaux.get('nombre_clients', 0)
            stats_text = f"<b>{_('Nombre de clients avec dettes')}:</b> {nombre_clients}"
            elements.append(Paragraph(stats_text, self.styles['TexteNormal']))

        self._build_with_footer(doc, elements, data)
        buffer.seek(0)
        return buffer