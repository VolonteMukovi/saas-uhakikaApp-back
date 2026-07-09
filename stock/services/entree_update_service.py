"""Mise à jour d'un approvisionnement (Entree) avec impact stock/lots cohérent."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from rest_framework import serializers

from stock.models import Article, Devise, Entree, LigneEntree
from stock.services.conditionnement_pricing import (
    build_ligne_entree_values,
    upsert_prix_conditionnement_entree,
)
from stock.services.currency import build_conversion_snapshot
from stock.services.stock_adjustment import (
    apply_stock_delta,
    quantize_qty,
    quantite_vendue_ligne_entree,
    remove_ligne_entree_from_stock,
    validate_ligne_entree_can_delete,
    validate_ligne_entree_can_reduce,
)


def _parse_decimal(raw, default=Decimal('0')) -> Decimal:
    if raw is None:
        return default
    return Decimal(str(raw)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _resolve_article(article_id, entreprise_id) -> Article:
    try:
        return Article.objects.get(article_id=article_id, entreprise_id=entreprise_id)
    except Article.DoesNotExist:
        raise serializers.ValidationError({'article_id': f"Article {article_id} introuvable."})


def _resolve_devise(devise_id, entreprise_id, default_dev: Devise | None) -> Devise | None:
    if not devise_id:
        return default_dev
    try:
        return Devise.objects.get(pk=devise_id, entreprise_id=entreprise_id)
    except Devise.DoesNotExist:
        return default_dev


def _build_ligne_snapshot(entreprise_id, montant, devise_obj, devise_principale):
    return build_conversion_snapshot(
        entreprise_id=entreprise_id,
        amount=montant,
        devise_source=devise_obj,
        devise_reference=devise_principale,
    )


@transaction.atomic
def _create_ligne_entree(entree: Entree, payload: dict, *, default_dev: Devise | None, devise_principale: Devise | None) -> LigneEntree:
    article_id = payload.get('article_id') or payload.get('article')
    if not article_id:
        raise serializers.ValidationError({'lignes': 'Chaque ligne doit avoir un article.'})

    article = _resolve_article(article_id, entree.entreprise_id)
    ligne_values = build_ligne_entree_values(article, payload)
    quantite = ligne_values['quantite']
    prix_unitaire = ligne_values['prix_unitaire']
    prix_vente = ligne_values['prix_vente']

    seuil_alerte = _parse_decimal(payload.get('seuil_alerte', 0))
    devise_obj = _resolve_devise(
        payload.get('devise_id') or payload.get('devise'),
        entree.entreprise_id,
        default_dev,
    )
    montant_ligne = (prix_unitaire * quantite).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    snapshot = _build_ligne_snapshot(entree.entreprise_id, montant_ligne, devise_obj, devise_principale)

    ligne = LigneEntree.objects.create(
        entree=entree,
        article=article,
        conditionnement=ligne_values['conditionnement'],
        quantite_saisie=ligne_values['quantite_saisie'],
        quantite_base=ligne_values['quantite_base'],
        quantite=ligne_values['quantite'],
        quantite_restante=ligne_values['quantite_restante'],
        prix_achat_conditionnement=ligne_values['prix_achat_conditionnement'],
        prix_vente_conditionnement=ligne_values['prix_vente_conditionnement'],
        prix_achat_unitaire_base=ligne_values['prix_achat_unitaire_base'],
        prix_vente_unitaire_base=ligne_values['prix_vente_unitaire_base'],
        prix_unitaire=ligne_values['prix_unitaire'],
        prix_vente=ligne_values['prix_vente'],
        date_expiration=payload.get('date_expiration'),
        devise=devise_obj,
        devise_reference=snapshot['devise_reference'],
        taux_change=snapshot['taux_change'],
        montant_reference=snapshot['montant_reference'],
        seuil_alerte=seuil_alerte,
    )
    upsert_prix_conditionnement_entree(
        ligne,
        payload.get('prix_conditionnements'),
        devise_obj or devise_principale,
    )
    apply_stock_delta(article, quantite, seuil_alerte=seuil_alerte)
    return ligne


@transaction.atomic
def _update_ligne_entree(entree: Entree, ligne: LigneEntree, payload: dict, *, default_dev: Devise | None, devise_principale: Devise | None) -> LigneEntree:
    ligne = LigneEntree.objects.select_for_update().get(pk=ligne.pk, entree=entree)
    old_article = ligne.article
    old_quantite = quantize_qty(ligne.quantite)
    vendue = quantite_vendue_ligne_entree(ligne)

    new_article_id = payload.get('article_id') or payload.get('article')
    if new_article_id:
        new_article = _resolve_article(new_article_id, entree.entreprise_id)
    else:
        new_article = old_article

    ligne_values = build_ligne_entree_values(new_article, payload | {
        'conditionnement_id': payload.get('conditionnement_id') or payload.get('conditionnement') or getattr(ligne, 'conditionnement_id', None),
        'quantite': payload.get('quantite', ligne.quantite),
        'quantite_saisie': payload.get('quantite_saisie', ligne.quantite_saisie),
        'quantite_base': payload.get('quantite_base', ligne.quantite_base),
        'prix_unitaire': payload.get('prix_unitaire', ligne.prix_unitaire),
        'prix_vente': payload.get('prix_vente', ligne.prix_vente),
        'prix_achat_conditionnement': payload.get('prix_achat_conditionnement', ligne.prix_achat_conditionnement),
        'prix_vente_conditionnement': payload.get('prix_vente_conditionnement', ligne.prix_vente_conditionnement),
        'prix_achat_unitaire_base': payload.get('prix_achat_unitaire_base', ligne.prix_achat_unitaire_base),
        'prix_vente_unitaire_base': payload.get('prix_vente_unitaire_base', ligne.prix_vente_unitaire_base),
    })
    new_quantite = ligne_values['quantite']

    if new_article.pk != old_article.pk:
        if vendue > 0:
            raise serializers.ValidationError({
                'article_id': (
                    f"Impossible de changer l'article : {vendue} unité(s) ont déjà été vendues "
                    f"depuis cet approvisionnement."
                ),
            })
        apply_stock_delta(old_article, -old_quantite)
        ligne.article = new_article
        ligne.quantite = ligne_values['quantite']
        ligne.quantite_restante = new_quantite
        apply_stock_delta(new_article, new_quantite)
    else:
        validate_ligne_entree_can_reduce(ligne, new_quantite)
        delta = new_quantite - old_quantite
        ligne.quantite = new_quantite
        ligne.quantite_restante = quantize_qty(ligne.quantite_restante) + delta
        if delta != 0:
            apply_stock_delta(old_article, delta)

    prix_unitaire = ligne_values['prix_unitaire']
    prix_vente = ligne_values['prix_vente']

    seuil_alerte = _parse_decimal(payload.get('seuil_alerte', ligne.seuil_alerte))
    devise_obj = _resolve_devise(
        payload.get('devise_id') or payload.get('devise'),
        entree.entreprise_id,
        ligne.devise or default_dev,
    )
    if payload.get('date_expiration') is not None:
        ligne.date_expiration = payload.get('date_expiration')

    montant_ligne = (prix_unitaire * new_quantite).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    snapshot = _build_ligne_snapshot(entree.entreprise_id, montant_ligne, devise_obj, devise_principale)

    ligne.prix_unitaire = prix_unitaire
    ligne.prix_vente = prix_vente
    ligne.conditionnement = ligne_values['conditionnement']
    ligne.quantite_saisie = ligne_values['quantite_saisie']
    ligne.quantite_base = ligne_values['quantite_base']
    ligne.prix_achat_conditionnement = ligne_values['prix_achat_conditionnement']
    ligne.prix_vente_conditionnement = ligne_values['prix_vente_conditionnement']
    ligne.prix_achat_unitaire_base = ligne_values['prix_achat_unitaire_base']
    ligne.prix_vente_unitaire_base = ligne_values['prix_vente_unitaire_base']
    ligne.devise = devise_obj
    ligne.devise_reference = snapshot['devise_reference']
    ligne.taux_change = snapshot['taux_change']
    ligne.montant_reference = snapshot['montant_reference']
    ligne.seuil_alerte = seuil_alerte
    ligne.save()
    upsert_prix_conditionnement_entree(
        ligne,
        payload.get('prix_conditionnements'),
        devise_obj or devise_principale,
    )

    from stock.models import Stock
    stock_obj, _ = Stock.objects.get_or_create(
        article=ligne.article,
        defaults={'Qte': Decimal('0'), 'seuilAlert': seuil_alerte},
    )
    stock_obj.seuilAlert = seuil_alerte
    stock_obj.save(update_fields=['seuilAlert'])
    return ligne


@transaction.atomic
def update_entree_from_payload(entree: Entree, data: dict) -> Entree:
    """
    Met à jour une entrée et ses lignes.

    Payload attendu (extrait de ``data``) :
    - libele, description (optionnels)
    - lignes : liste avec ``id`` pour modifier, sans ``id`` pour créer
    - lignes_supprimees : liste d'IDs à supprimer
    """
    entree = Entree.objects.select_for_update().get(pk=entree.pk)

    default_dev = Devise.objects.filter(entreprise_id=entree.entreprise_id, est_principal=True).first()
    if default_dev is None:
        default_dev = Devise.objects.filter(est_principal=True).first()
    devise_principale = default_dev

    if 'libele' in data:
        entree.libele = data['libele']
    if 'description' in data:
        entree.description = data.get('description', '')
    entree.save()

    lignes_supprimees = data.get('lignes_supprimees') or []
    for lid in lignes_supprimees:
        try:
            ligne = LigneEntree.objects.select_for_update().get(pk=lid, entree=entree)
        except LigneEntree.DoesNotExist:
            raise serializers.ValidationError({'lignes_supprimees': f"Ligne {lid} introuvable."})
        validate_ligne_entree_can_delete(ligne)
        remove_ligne_entree_from_stock(ligne)

    lignes_data = data.get('lignes')
    if lignes_data is not None:
        if not lignes_data and not entree.lignes.exists():
            raise serializers.ValidationError({'lignes': "Au moins une ligne d'entrée est requise."})

        for payload in lignes_data:
            lid = payload.get('id')
            if lid:
                try:
                    ligne = LigneEntree.objects.get(pk=lid, entree=entree)
                except LigneEntree.DoesNotExist:
                    raise serializers.ValidationError({'lignes': f"Ligne {lid} introuvable pour cette entrée."})
                _update_ligne_entree(entree, ligne, payload, default_dev=default_dev, devise_principale=devise_principale)
            else:
                _create_ligne_entree(entree, payload, default_dev=default_dev, devise_principale=devise_principale)

    if not entree.lignes.exists():
        raise serializers.ValidationError({'lignes': "Au moins une ligne d'entrée est requise."})

    return entree
