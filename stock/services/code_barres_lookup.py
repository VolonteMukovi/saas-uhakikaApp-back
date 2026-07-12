"""Recherche article + conditionnement + prix/stock à partir d'un code-barres scanné."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db.models import Sum

from stock.models import (
    Article,
    CodeBarresArticle,
    ConditionnementArticle,
    Devise,
    LigneEntree,
    PrixConditionnementEntree,
    Stock,
)

MONEY_QUANT = Decimal('0.00001')
QTY_QUANT = Decimal('0.00001')


def normalize_code_barres(raw: str | None) -> str:
    return ''.join(str(raw or '').strip().split())


def infer_type_code(code: str) -> str:
    digits = ''.join(ch for ch in code if ch.isdigit())
    if len(digits) == len(code):
        if len(code) == 13:
            return CodeBarresArticle.TYPE_EAN13
        if len(code) == 8:
            return CodeBarresArticle.TYPE_EAN8
        if len(code) == 12:
            return CodeBarresArticle.TYPE_UPC
    if code.upper().startswith('QR') or len(code) > 20:
        return CodeBarresArticle.TYPE_QR
    return CodeBarresArticle.TYPE_INTERNE


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_DOWN)


def _quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_QUANT, rounding=ROUND_DOWN)


def _stock_quantite_base(article: Article, *, tenant_id: int) -> Decimal:
    agg = (
        LigneEntree.objects.filter(
            article=article,
            quantite_restante__gt=0,
            entree__entreprise_id=tenant_id,
        ).aggregate(total=Sum('quantite_restante'))
    )
    total = agg.get('total')
    if total is not None:
        return _quantize_qty(Decimal(str(total)))
    stock = Stock.objects.filter(article=article).first()
    if stock is not None:
        return _quantize_qty(Decimal(str(stock.Qte or '0')))
    return Decimal('0')


def _prix_conditionnement_lot(
    lot: LigneEntree,
    conditionnement: ConditionnementArticle,
) -> tuple[Decimal, Devise | None, str]:
    mult = Decimal(str(conditionnement.multiplicateur_base or '1'))
    prix_spec = (
        PrixConditionnementEntree.objects.filter(
            ligne_entree=lot,
            conditionnement=conditionnement,
        )
        .select_related('devise')
        .order_by('-est_prix_principal', 'id')
        .first()
    )
    if prix_spec is not None:
        return _quantize_money(prix_spec.prix_vente), prix_spec.devise, 'prix_conditionnement_entree'

    if lot.conditionnement_id == conditionnement.pk and lot.prix_vente_conditionnement is not None:
        return (
            _quantize_money(lot.prix_vente_conditionnement),
            lot.devise,
            'prix_conditionnement_ligne',
        )

    base = lot.prix_vente_unitaire_base or lot.prix_vente
    if mult <= 0:
        mult = Decimal('1')
    return _quantize_money(base * mult), lot.devise, 'prix_unitaire_base_fifo'


def compute_prix_fifo_conditionnement(
    article: Article,
    conditionnement: ConditionnementArticle,
    *,
    tenant_id: int,
) -> dict | None:
    """
    Prix moyen pondéré (FIFO) pour 1 unité du conditionnement scanné.
    Retourne None si aucun lot en stock.
    """
    mult = Decimal(str(conditionnement.multiplicateur_base or '1'))
    if mult <= 0:
        mult = Decimal('1')

    lots = (
        LigneEntree.objects.filter(
            article=article,
            quantite_restante__gt=0,
            entree__entreprise_id=tenant_id,
        )
        .select_related('devise', 'conditionnement')
        .order_by('date_entree', 'id')
    )

    total_cond_units = Decimal('0')
    weighted_sum = Decimal('0')
    devise: Devise | None = None
    source = 'prix_unitaire_base_fifo'

    for lot in lots:
        qte_base = Decimal(str(lot.quantite_restante))
        cond_units = qte_base / mult
        if cond_units <= 0:
            continue
        prix_cond, lot_devise, lot_source = _prix_conditionnement_lot(lot, conditionnement)
        weighted_sum += prix_cond * cond_units
        total_cond_units += cond_units
        if devise is None and lot_devise is not None:
            devise = lot_devise
        if lot_source == 'prix_conditionnement_entree':
            source = 'prix_conditionnement_fifo'
        elif lot_source == 'prix_conditionnement_ligne' and source != 'prix_conditionnement_fifo':
            source = 'prix_conditionnement_ligne'

    if total_cond_units <= 0:
        return None

    montant = _quantize_money(weighted_sum / total_cond_units)
    prix_unitaire_base = _quantize_money(montant / mult)
    return {
        'montant': montant,
        'prix_unitaire_base': prix_unitaire_base,
        'devise': devise,
        'source': source,
    }


def lookup_code_barres(
    code: str,
    *,
    tenant_id: int,
    branch_id: int | None = None,
) -> dict:
    normalized = normalize_code_barres(code)
    if not normalized:
        return {
            'found': False,
            'message': 'Aucun article n’est associé à ce code-barres.',
        }

    qs = (
        CodeBarresArticle.objects.filter(
            entreprise_id=tenant_id,
            code=normalized,
            est_actif=True,
        )
        .select_related(
            'article',
            'article__unite',
            'conditionnement',
        )
    )
    if branch_id is not None:
        qs = qs.filter(succursale_id__in=[branch_id, None])

    barcode = qs.order_by('-est_principal', '-updated_at', '-id').first()
    if barcode is None:
        return {
            'found': False,
            'message': 'Aucun article n’est associé à ce code-barres.',
        }

    article = barcode.article
    conditionnement = barcode.conditionnement
    mult = Decimal(str(conditionnement.multiplicateur_base or '1'))
    stock_base = _stock_quantite_base(article, tenant_id=tenant_id)
    stock_cond_units = _quantize_qty(stock_base / mult) if mult > 0 else stock_base

    prix_info = compute_prix_fifo_conditionnement(
        article,
        conditionnement,
        tenant_id=tenant_id,
    )

    devise_obj = prix_info['devise'] if prix_info else None
    if devise_obj is None:
        devise_obj = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()

    unite_base = article.unite.libelle if article.unite_id and article.unite else 'Unité'

    payload: dict = {
        'found': True,
        'code_barres': {
            'uuid': str(barcode.uuid),
            'code': barcode.code,
            'type_code': barcode.type_code,
            'est_principal': barcode.est_principal,
        },
        'article': {
            'id': article.article_id,
            'nom': article.nom_commercial or article.nom_scientifique,
            'nom_scientifique': article.nom_scientifique,
            'nom_commercial': article.nom_commercial,
        },
        'conditionnement': {
            'id': conditionnement.id,
            'nom': conditionnement.nom,
            'multiplicateur_base': str(_quantize_qty(mult)),
            'quantite_base': str(_quantize_qty(mult)),
            'est_defaut': conditionnement.est_defaut,
        },
        'stock': {
            'quantite_base': str(stock_base),
            'quantite_conditionnement': str(stock_cond_units),
            'unite_base': unite_base,
            'disponible': stock_base > 0,
        },
    }

    if prix_info:
        payload['prix'] = {
            'montant': str(prix_info['montant']),
            'prix_unitaire_base': str(prix_info['prix_unitaire_base']),
            'devise': devise_obj.sigle if devise_obj else None,
            'devise_id': devise_obj.pk if devise_obj else None,
            'symbole': devise_obj.symbole if devise_obj else None,
            'source': prix_info['source'],
        }
    else:
        payload['prix'] = {
            'montant': None,
            'prix_unitaire_base': None,
            'devise': devise_obj.sigle if devise_obj else None,
            'devise_id': devise_obj.pk if devise_obj else None,
            'symbole': devise_obj.symbole if devise_obj else None,
            'source': 'stock_insuffisant',
        }

    return payload
