"""Conversion conditionnement <-> unité de base pour approvisionnement/vente."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from rest_framework import serializers

from stock.models import Article, ConditionnementArticle, Devise, LigneEntree, PrixConditionnementEntree

QTY_QUANT = Decimal('0.00001')
MONEY_QUANT = Decimal('0.00001')


def _to_decimal(raw, *, label: str, default: Decimal | None = None) -> Decimal:
    if raw is None:
        if default is not None:
            return default
        raise serializers.ValidationError({label: f'{label} est requis.'})
    try:
        return Decimal(str(raw).replace(',', '.'))
    except Exception as exc:  # noqa: BLE001
        raise serializers.ValidationError({label: f'{label} invalide.'}) from exc


def quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_QUANT, rounding=ROUND_DOWN)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_DOWN)


def get_or_create_conditionnement_defaut(article: Article) -> ConditionnementArticle:
    cond = article.conditionnements.filter(est_defaut=True).first()
    if cond:
        return cond
    # fallback: 1 unité de base de l'article
    nom = (article.unite.libelle if article.unite_id and article.unite else 'Unité').strip() or 'Unité'
    cond = article.conditionnements.filter(nom__iexact=nom).first()
    if cond:
        if not cond.est_defaut:
            cond.est_defaut = True
            cond.save(update_fields=['est_defaut', 'updated_at'])
        return cond
    return ConditionnementArticle.objects.create(
        article=article,
        nom=nom,
        multiplicateur_base=Decimal('1'),
        est_defaut=True,
    )


def resolve_conditionnement(article: Article, payload: dict) -> ConditionnementArticle:
    cid = payload.get('conditionnement_id') or payload.get('conditionnement')
    if cid:
        try:
            cond = ConditionnementArticle.objects.get(pk=cid, article=article)
        except ConditionnementArticle.DoesNotExist as exc:
            raise serializers.ValidationError(
                {'conditionnement_id': f'Conditionnement {cid} introuvable pour cet article.'}
            ) from exc
        return cond
    return get_or_create_conditionnement_defaut(article)


def build_ligne_entree_values(article: Article, payload: dict) -> dict:
    """
    Construit les valeurs legacy + conditionnement pour LigneEntree.
    Garde la logique historique: quantite/prix_* restent en unité de base.
    """
    cond = resolve_conditionnement(article, payload)
    multiplicateur = _to_decimal(cond.multiplicateur_base, label='multiplicateur_base', default=Decimal('1'))
    if multiplicateur <= 0:
        raise serializers.ValidationError({'conditionnement_id': 'Le multiplicateur doit être strictement positif.'})

    qte_saisie_raw = payload.get('quantite_saisie')
    qte_base_raw = payload.get('quantite_base')
    qte_legacy_raw = payload.get('quantite')
    if qte_saisie_raw is None and qte_base_raw is None and qte_legacy_raw is None:
        raise serializers.ValidationError({'quantite': 'La quantité est obligatoire.'})

    if qte_saisie_raw is not None:
        quantite_saisie = quantize_qty(_to_decimal(qte_saisie_raw, label='quantite_saisie'))
    elif qte_legacy_raw is not None:
        quantite_saisie = quantize_qty(_to_decimal(qte_legacy_raw, label='quantite'))
    else:
        quantite_saisie = quantize_qty(_to_decimal(qte_base_raw, label='quantite_base') / multiplicateur)

    if qte_base_raw is not None:
        quantite_base = quantize_qty(_to_decimal(qte_base_raw, label='quantite_base'))
    else:
        quantite_base = quantize_qty(quantite_saisie * multiplicateur)

    if quantite_saisie <= 0 or quantite_base <= 0:
        raise serializers.ValidationError({'quantite': 'La quantité doit être supérieure à 0.'})

    pac_raw = payload.get('prix_achat_conditionnement')
    pvc_raw = payload.get('prix_vente_conditionnement')
    pub_raw = payload.get('prix_unitaire') or payload.get('prix_achat_unitaire_base')
    pvb_raw = payload.get('prix_vente') or payload.get('prix_vente_unitaire_base')

    if pac_raw is None and pub_raw is not None:
        prix_achat_unitaire_base = quantize_money(_to_decimal(pub_raw, label='prix_unitaire', default=Decimal('0')))
        prix_achat_conditionnement = quantize_money(prix_achat_unitaire_base * multiplicateur)
    else:
        prix_achat_conditionnement = quantize_money(
            _to_decimal(pac_raw, label='prix_achat_conditionnement', default=Decimal('0'))
        )
        prix_achat_unitaire_base = quantize_money(prix_achat_conditionnement / multiplicateur)

    if pvc_raw is None and pvb_raw is not None:
        prix_vente_unitaire_base = quantize_money(_to_decimal(pvb_raw, label='prix_vente'))
        prix_vente_conditionnement = quantize_money(prix_vente_unitaire_base * multiplicateur)
    else:
        prix_vente_conditionnement = quantize_money(_to_decimal(pvc_raw, label='prix_vente_conditionnement'))
        prix_vente_unitaire_base = quantize_money(prix_vente_conditionnement / multiplicateur)

    if prix_vente_unitaire_base <= 0:
        raise serializers.ValidationError({'prix_vente': 'Le prix de vente doit être supérieur à 0.'})

    return {
        'conditionnement': cond,
        'quantite_saisie': quantite_saisie,
        'quantite_base': quantite_base,
        'prix_achat_conditionnement': prix_achat_conditionnement,
        'prix_vente_conditionnement': prix_vente_conditionnement,
        'prix_achat_unitaire_base': prix_achat_unitaire_base,
        'prix_vente_unitaire_base': prix_vente_unitaire_base,
        # champs legacy conservés pour FIFO / stock
        'quantite': quantite_base,
        'quantite_restante': quantite_base,
        'prix_unitaire': prix_achat_unitaire_base,
        'prix_vente': prix_vente_unitaire_base,
    }


def upsert_prix_conditionnement_entree(
    ligne_entree: LigneEntree, prix_items: list[dict] | None, devise_fallback: Devise | None
) -> None:
    if prix_items is None:
        return
    seen: set[int] = set()
    for item in prix_items:
        cid = item.get('conditionnement_id') or item.get('conditionnement')
        if not cid:
            raise serializers.ValidationError({'prix_conditionnements': 'conditionnement_id est obligatoire.'})
        try:
            cond = ConditionnementArticle.objects.get(pk=cid, article=ligne_entree.article)
        except ConditionnementArticle.DoesNotExist as exc:
            raise serializers.ValidationError({'prix_conditionnements': f'Conditionnement {cid} introuvable.'}) from exc
        if cond.pk in seen:
            raise serializers.ValidationError({'prix_conditionnements': f'Conditionnement {cid} en doublon.'})
        seen.add(cond.pk)
        pv = quantize_money(_to_decimal(item.get('prix_vente'), label='prix_vente'))
        if pv <= 0:
            raise serializers.ValidationError({'prix_conditionnements': 'prix_vente doit être > 0.'})
        did = item.get('devise_id') or item.get('devise')
        if did:
            try:
                devise = Devise.objects.get(pk=did, entreprise_id=ligne_entree.entree.entreprise_id)
            except Devise.DoesNotExist as exc:
                raise serializers.ValidationError({'prix_conditionnements': f'Devise {did} introuvable.'}) from exc
        else:
            devise = devise_fallback
        if devise is None:
            raise serializers.ValidationError({'prix_conditionnements': 'Aucune devise disponible.'})
        obj, _ = PrixConditionnementEntree.objects.update_or_create(
            ligne_entree=ligne_entree,
            conditionnement=cond,
            defaults={
                'prix_vente': pv,
                'devise': devise,
                'est_prix_principal': bool(item.get('est_prix_principal', False)),
            },
        )
        if obj.est_prix_principal:
            PrixConditionnementEntree.objects.filter(
                ligne_entree=ligne_entree,
                est_prix_principal=True,
            ).exclude(pk=obj.pk).update(est_prix_principal=False)

