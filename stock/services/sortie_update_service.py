"""Mise à jour d'une vente (Sortie) avec impact stock, caisse et dette cohérent."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django.db import transaction
from rest_framework import serializers

from stock.models import (
    Article,
    Client,
    ConditionnementArticle,
    Devise,
    LigneSortie,
    PrixConditionnementEntree,
    Sortie,
)
from stock.services.credit_sale_adjustment_service import sync_dette_for_credit_sortie
from stock.services.currency import build_conversion_snapshot
from stock.services.sale_cash_adjustment_service import sync_sortie_cash_movements
from stock.services.stock_adjustment import (
    apply_stock_delta,
    consume_fifo_lots,
    create_sortie_lot_traces,
    quantize_qty,
    rollback_sortie_ligne,
)


def _parse_decimal_quantity(raw_value) -> Decimal:
    if raw_value is None:
        return Decimal('0')
    return Decimal(str(raw_value).replace(',', '.')).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _resolve_conditionnement(article: Article, ligne_payload: dict) -> ConditionnementArticle | None:
    cid = ligne_payload.get('conditionnement_id') or ligne_payload.get('conditionnement')
    if not cid:
        return None
    try:
        return ConditionnementArticle.objects.get(pk=cid, article=article)
    except ConditionnementArticle.DoesNotExist as exc:
        raise serializers.ValidationError(
            {'conditionnement_id': f'Conditionnement {cid} introuvable pour {article.article_id}.'}
        ) from exc


def _compute_prix_moyen_depuis_lots(
    lots_utilises_data: list[dict],
    conditionnement: ConditionnementArticle | None,
) -> Decimal:
    total = Decimal('0')
    total_qte = Decimal('0')
    for lot_data in lots_utilises_data:
        lot = lot_data['lot']
        qte = Decimal(str(lot_data['quantite']))
        unit_base_price = lot.prix_vente_unitaire_base or lot.prix_vente
        if conditionnement is not None:
            prix_specifique = PrixConditionnementEntree.objects.filter(
                ligne_entree=lot,
                conditionnement=conditionnement,
            ).order_by('-est_prix_principal', 'id').first()
            if prix_specifique is not None:
                mult = Decimal(str(conditionnement.multiplicateur_base or '1'))
                if mult > 0:
                    unit_base_price = (prix_specifique.prix_vente / mult).quantize(
                        Decimal('0.00001'), rounding=ROUND_DOWN
                    )
        total += unit_base_price * qte
        total_qte += qte
    if total_qte <= 0:
        return Decimal('0')
    return (total / total_qte).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _parse_prix_unitaire(raw) -> Decimal | None:
    if raw is None:
        return None
    try:
        val = Decimal(str(raw))
    except (ValueError, TypeError, InvalidOperation):
        raise serializers.ValidationError({'prix_unitaire': 'Le prix unitaire doit être un nombre valide.'})
    if val < 0:
        raise serializers.ValidationError({'prix_unitaire': 'Le prix unitaire ne peut pas être négatif.'})
    return val.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _process_sortie_ligne(sortie: Sortie, ligne_payload: dict, *, default_dev: Devise | None, tenant_id: int) -> dict:
    """Crée une ligne de sortie avec FIFO. Retourne les données devise/total."""
    article_id = ligne_payload.get('article_id') or ligne_payload.get('article')
    try:
        article_obj = Article.objects.get(article_id=article_id, entreprise_id=tenant_id)
    except Article.DoesNotExist:
        raise serializers.ValidationError({'article': f"Article avec ID {article_id} non trouvé."})

    qte_saisie = _parse_decimal_quantity(ligne_payload.get('quantite', 0))
    if qte_saisie <= 0:
        raise serializers.ValidationError({'quantite': 'La quantité doit être supérieure à 0.'})
    conditionnement = _resolve_conditionnement(article_obj, ligne_payload)
    if conditionnement is not None:
        multiplicateur = Decimal(str(conditionnement.multiplicateur_base or '1'))
        if multiplicateur <= 0:
            raise serializers.ValidationError({'conditionnement_id': 'Multiplicateur conditionnement invalide.'})
        qte = (qte_saisie * multiplicateur).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    else:
        qte = qte_saisie

    prix_unitaire_encaisse = _parse_prix_unitaire(ligne_payload.get('prix_unitaire'))

    devise_id = ligne_payload.get('devise_id') or ligne_payload.get('devise')
    if devise_id:
        try:
            devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id)
        except Devise.DoesNotExist:
            devise_obj = default_dev
    else:
        devise_obj = default_dev

    lots_utilises_data, total_prix_vente = consume_fifo_lots(article_obj, qte)

    prix_vente_moyen_lots = _compute_prix_moyen_depuis_lots(lots_utilises_data, conditionnement)

    prix_unitaire_final = prix_unitaire_encaisse if prix_unitaire_encaisse is not None else prix_vente_moyen_lots
    prix_unitaire_final = prix_unitaire_final.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

    montant_ligne = (prix_unitaire_final * qte).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    snapshot_ligne = build_conversion_snapshot(
        entreprise_id=sortie.entreprise_id,
        amount=montant_ligne,
        devise_source=devise_obj or default_dev,
    )
    ligne_sortie = LigneSortie.objects.create(
        sortie=sortie,
        article=article_obj,
        quantite=qte,
        prix_unitaire=prix_unitaire_final,
        devise=devise_obj,
        devise_reference=snapshot_ligne['devise_reference'],
        taux_change=snapshot_ligne['taux_change'],
        montant_reference=snapshot_ligne['montant_reference'],
    )
    create_sortie_lot_traces(ligne_sortie, lots_utilises_data, prix_unitaire_final)
    apply_stock_delta(article_obj, -qte)

    devise_key = devise_obj.sigle if devise_obj else 'DEFAULT'
    return {
        'devise_key': devise_key,
        'devise_obj': devise_obj,
        'montant_ligne': montant_ligne,
    }


@transaction.atomic
def update_sortie_from_payload(
    sortie: Sortie,
    data: dict,
    *,
    utilisateur=None,
    type_caisse_id: int | None = None,
) -> Sortie:
    """
    Met à jour une sortie complète : rollback FIFO, nouvelles lignes, caisse, dette.

    ``data`` attend ``lignes`` (liste), champs entête optionnels (motif, client_id, statut).
    """
    sortie = Sortie.objects.select_for_update().get(pk=sortie.pk)
    old_statut = sortie.statut
    tenant_id = sortie.entreprise_id

    lignes_data = data.get('lignes')
    if lignes_data is not None and not lignes_data:
        raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})

    default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
    if default_dev is None:
        default_dev = Devise.objects.filter(est_principal=True).first()

    if lignes_data is not None:
        for ancienne_ligne in list(sortie.lignes.select_for_update().all()):
            rollback_sortie_ligne(ancienne_ligne)

    if 'motif' in data:
        sortie.motif = data['motif']
    if 'client_id' in data:
        client_id = data.get('client_id')
        if client_id:
            try:
                sortie.client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                raise serializers.ValidationError({'client_id': f"Client {client_id} non trouvé."})
        else:
            sortie.client = None

    new_statut = data.get('statut', sortie.statut)
    if new_statut == 'EN_CREDIT' and not (sortie.client_id or data.get('client_id')):
        raise serializers.ValidationError({'client_id': 'Client obligatoire pour une vente à crédit.'})
    sortie.statut = new_statut
    sortie.save()

    totaux_par_devise = {}
    if lignes_data is not None:
        for ligne_payload in lignes_data:
            result = _process_sortie_ligne(sortie, ligne_payload, default_dev=default_dev, tenant_id=tenant_id)
            key = result['devise_key']
            if key not in totaux_par_devise:
                totaux_par_devise[key] = {'devise_obj': result['devise_obj'], 'total': Decimal('0')}
            totaux_par_devise[key]['total'] += result['montant_ligne']
    else:
        for ligne in sortie.lignes.select_related('devise').all():
            key = ligne.devise.sigle if ligne.devise else 'DEFAULT'
            montant = (ligne.prix_unitaire or Decimal('0')) * quantize_qty(ligne.quantite)
            if key not in totaux_par_devise:
                totaux_par_devise[key] = {'devise_obj': ligne.devise, 'total': Decimal('0')}
            totaux_par_devise[key]['total'] += montant

    if not sortie.lignes.exists():
        raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})

    sync_sortie_cash_movements(
        sortie,
        totaux_par_devise,
        utilisateur=utilisateur,
        type_caisse_id=type_caisse_id,
        old_statut=old_statut,
        new_statut=new_statut,
    )
    sync_dette_for_credit_sortie(
        sortie,
        default_devise=default_dev,
        old_statut=old_statut,
        new_statut=new_statut,
    )
    return sortie
