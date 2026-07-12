"""Génération de codes-barres internes Code128 par conditionnement."""
from __future__ import annotations

import io
import re
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from stock.models import Article, CodeBarresArticle, ConditionnementArticle, Entreprise

NUMERIC_CODE_PATTERN = re.compile(r'^(\d+)$')
STRUCTURED_CODE_PREFIX = 'UH-'


def _prefix() -> str:
    return str(getattr(settings, 'CODE_BARRES_INTERNE_PREFIX', '20')).strip() or '20'


def _total_digits() -> int:
    return int(getattr(settings, 'CODE_BARRES_INTERNE_DIGITS', 12))


def normalize_format(raw: str | None) -> str:
    value = (raw or 'numerique').strip().lower()
    if value in ('numerique', 'numeric', 'num'):
        return 'numerique'
    if value in ('structure', 'structuree', 'struct', 'uh'):
        return 'structure'
    raise serializers.ValidationError({
        'format': _('Format invalide. Valeurs acceptées : numerique, structure.'),
    })


def _conditionnement_has_active_code(conditionnement_id: int) -> bool:
    return CodeBarresArticle.objects.filter(
        conditionnement_id=conditionnement_id,
        est_actif=True,
    ).exists()


def _next_numeric_code(entreprise_id: int) -> str:
    prefix = _prefix()
    total_digits = _total_digits()
    if len(prefix) >= total_digits:
        raise serializers.ValidationError({
            'non_field_errors': _('Configuration CODE_BARRES_INTERNE_DIGITS invalide.'),
        })

    suffix_len = total_digits - len(prefix)
    min_val = int(prefix + '0' * suffix_len)
    max_val = int(prefix + '9' * suffix_len)

    existing = CodeBarresArticle.objects.filter(
        entreprise_id=entreprise_id,
        code__startswith=prefix,
    ).values_list('code', flat=True)

    max_num = min_val - 1
    for raw in existing:
        if not NUMERIC_CODE_PATTERN.match(raw):
            continue
        if len(raw) != total_digits:
            continue
        try:
            num = int(raw)
        except (TypeError, ValueError):
            continue
        if min_val <= num <= max_val:
            max_num = max(max_num, num)

    next_num = max_num + 1
    if next_num > max_val:
        raise serializers.ValidationError({
            'non_field_errors': _(
                'Limite de codes-barres internes numériques atteinte pour cette entreprise.'
            ),
        })
    return str(next_num).zfill(total_digits)


def _structured_code(entreprise_id: int, article: Article, conditionnement: ConditionnementArticle) -> str:
    base = f'{STRUCTURED_CODE_PREFIX}{entreprise_id}-{article.article_id}-{conditionnement.pk}'
    if CodeBarresArticle.objects.filter(entreprise_id=entreprise_id, code=base).exists():
        seq = 1
        while CodeBarresArticle.objects.filter(
            entreprise_id=entreprise_id,
            code=f'{base}-{seq}',
        ).exists():
            seq += 1
            if seq > 999:
                raise serializers.ValidationError({
                    'non_field_errors': _('Impossible de générer un code structure unique.'),
                })
        return f'{base}-{seq}'
    return base


def generate_internal_code_value(
    *,
    entreprise_id: int,
    article: Article,
    conditionnement: ConditionnementArticle,
    format_code: str = 'numerique',
) -> str:
    fmt = normalize_format(format_code)
    if fmt == 'numerique':
        return _next_numeric_code(entreprise_id)
    return _structured_code(entreprise_id, article, conditionnement)


def _deactivate_codes_conditionnement(conditionnement_id: int) -> None:
    CodeBarresArticle.objects.filter(
        conditionnement_id=conditionnement_id,
        est_actif=True,
    ).update(est_actif=False)


@transaction.atomic
def generer_code_barres_interne(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    article: Article,
    conditionnement: ConditionnementArticle,
    utilisateur=None,
    format_code: str = 'numerique',
    remplacer: bool = False,
) -> CodeBarresArticle:
    if article.entreprise_id != entreprise_id:
        raise serializers.ValidationError({'article_id': _('Article hors entreprise courante.')})
    if conditionnement.article_id != article.article_id:
        raise serializers.ValidationError({
            'conditionnement_id': _('Le conditionnement ne correspond pas à l’article.'),
        })

    has_active = _conditionnement_has_active_code(conditionnement.pk)
    if has_active and not remplacer:
        raise serializers.ValidationError({
            'conditionnement_id': _(
                'Ce conditionnement possède déjà un code-barres actif. '
                'Utilisez remplacer=true pour en générer un nouveau.'
            ),
        })
    if has_active and remplacer:
        _deactivate_codes_conditionnement(conditionnement.pk)

    code_value = generate_internal_code_value(
        entreprise_id=entreprise_id,
        article=article,
        conditionnement=conditionnement,
        format_code=format_code,
    )

    return CodeBarresArticle.objects.create(
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        article=article,
        conditionnement=conditionnement,
        code=code_value,
        type_code=CodeBarresArticle.TYPE_CODE128,
        est_principal=True,
        est_actif=True,
        cree_par=utilisateur if utilisateur and getattr(utilisateur, 'is_authenticated', False) else None,
    )


def generer_codes_manquants_article(
    *,
    entreprise_id: int,
    succursale_id: int | None,
    article: Article,
    utilisateur=None,
    format_code: str = 'numerique',
) -> list[CodeBarresArticle]:
    created: list[CodeBarresArticle] = []
    for cond in article.conditionnements.all().order_by('-est_defaut', 'nom', 'id'):
        if _conditionnement_has_active_code(cond.pk):
            continue
        created.append(
            generer_code_barres_interne(
                entreprise_id=entreprise_id,
                succursale_id=succursale_id,
                article=article,
                conditionnement=cond,
                utilisateur=utilisateur,
                format_code=format_code,
                remplacer=False,
            )
        )
    return created


def build_etiquette_pdf(
    code_barres: CodeBarresArticle,
    *,
    entreprise: Entreprise | None = None,
) -> bytes:
    from reportlab.graphics.barcode import code128 as rl_code128
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A6
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

    class Code128Flowable(Flowable):
        def __init__(self, value: str, bar_height):
            super().__init__()
            self.barcode = rl_code128.Code128(
                value,
                barHeight=bar_height,
                barWidth=0.45,
                humanReadable=True,
            )
            self.width, self.height = self.barcode.wrap(0, 0)

        def draw(self):
            self.barcode.drawOn(self.canv, 0, 0)

    article = code_barres.article
    cond = code_barres.conditionnement
    ent = entreprise or code_barres.entreprise
    mult = Decimal(str(cond.multiplicateur_base or '1'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A6,
        leftMargin=6 * mm,
        rightMargin=6 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle('LabelTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, alignment=TA_CENTER)
    normal = ParagraphStyle('LabelNormal', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER)
    small = ParagraphStyle('LabelSmall', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey)

    nom = article.nom_commercial or article.nom_scientifique
    unite = article.unite.libelle if article.unite_id and article.unite else 'Unité'
    mult_display = format(mult.normalize(), 'f').rstrip('0').rstrip('.') or '1'
    cond_label = f'{cond.nom} ×{mult_display} {unite}'

    elements = [
        Paragraph(ent.nom if ent else 'UHAKIKAAPP', title),
        Spacer(1, 2 * mm),
        Paragraph(nom, normal),
        Paragraph(cond_label, normal),
        Spacer(1, 2 * mm),
        Paragraph(_('Code : %(code)s') % {'code': code_barres.code}, small),
        Spacer(1, 3 * mm),
        Code128Flowable(code_barres.code, 14 * mm),
    ]

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
