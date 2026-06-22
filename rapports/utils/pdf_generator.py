"""
Utilitaires PDF pour documents POS (tickets, bons caisse).
Les rapports métier sont exposés en JSON uniquement ; le frontend gère l'export PDF.
"""
from decimal import Decimal
from django.utils.translation import gettext as _
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class PDFGenerator:
    """En-têtes et helpers visuels pour les tickets PDF POS."""

    def __init__(self):
        self.page_width = 210 * mm
        self.page_height = 297 * mm
        self.margin = 20 * mm
        self.usable_width = self.page_width - (2 * self.margin)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='EntrepriseNom',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold',
        ))
        self.styles.add(ParagraphStyle(
            name='EntrepriseInfo',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=3,
            alignment=TA_LEFT,
        ))
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
        self.styles.add(ParagraphStyle(
            name='EntrepriseNomCompact',
            parent=self.styles['EntrepriseNom'],
            spaceAfter=1,
        ))
        self.styles.add(ParagraphStyle(
            name='EntrepriseInfoCompact',
            parent=self.styles['EntrepriseInfo'],
            spaceAfter=1,
        ))

    def _create_entete(self, entete_data, compact=False, centered=True, logo_size_mm=None):
        """Logo, nom, slogan et téléphone de l'entreprise (tickets POS / petits PDF)."""
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
        space_after_block = 4 if compact else 12

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

        elements.append(Paragraph(entreprise.get('nom', ''), style_nom))

        slogan = (entreprise.get('slogan') or '').strip()
        if slogan:
            elements.append(Paragraph(slogan, style_info))

        telephone = (entreprise.get('telephone') or '').strip()
        if telephone:
            elements.append(Paragraph(f"{_('Tél')}: {telephone}", style_info))

        elements.append(Spacer(1, space_after_block))
        return elements
