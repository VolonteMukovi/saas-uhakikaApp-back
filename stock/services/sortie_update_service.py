"""Mise à jour d'une vente (Sortie) avec impact stock et caisse cohérent."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django.db import transaction
from django.utils.translation import gettext as _
from rest_framework import serializers

from stock.models import (
    Article,
    Client,
    ConditionnementArticle,
    Devise,
    LigneSortie,
    Sortie,
)
from stock.services.currency import build_conversion_snapshot
from stock.services.sale_cash_adjustment_service import sync_sortie_cash_movements
from stock.services.sortie_motif import MSG_SORTIE_NON_COMMERCIALE_CREDIT, est_sortie_commerciale
from stock.services.stock_adjustment import (
    apply_stock_delta,
    consume_fifo_lots,
    create_sortie_lot_traces,
    quantize_qty,
    rollback_sortie_ligne,
)
from stock.services.sortie_pricing import (
    normalize_fifo_lot_prices,
    validate_sale_price_policy,
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


def _parse_prix_unitaire(raw, field_name: str = 'prix_unitaire') -> Decimal | None:
    if raw is None:
        return None
    try:
        val = Decimal(str(raw).replace(',', '.'))
    except (ValueError, TypeError, InvalidOperation):
        raise serializers.ValidationError({field_name: 'Le prix de vente doit être un nombre valide.'})
    if val < 0:
        raise serializers.ValidationError({field_name: 'Le prix de vente ne peut pas être négatif.'})
    return val.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)


def _process_sortie_ligne(
    sortie: Sortie,
    ligne_payload: dict,
    *,
    default_dev: Devise | None,
    tenant_id: int,
    utilisateur,
    request=None,
) -> dict:
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

    prix_conditionnement = _parse_prix_unitaire(
        ligne_payload.get('prix_conditionnement'),
        'prix_conditionnement',
    )
    prix_unitaire_encaisse = (
        _parse_prix_unitaire(ligne_payload.get('prix_unitaire'))
        if prix_conditionnement is None
        else None
    )

    devise_id = ligne_payload.get('devise_id') or ligne_payload.get('devise')
    if devise_id:
        try:
            devise_obj = Devise.objects.get(pk=devise_id, entreprise_id=tenant_id)
        except Devise.DoesNotExist:
            raise serializers.ValidationError({'devise_id': f'Devise {devise_id} non trouvée dans votre entreprise.'})
    else:
        devise_obj = default_dev
    if devise_obj is None:
        raise serializers.ValidationError({'devise_id': 'Aucune devise principale n’est configurée.'})

    lots_utilises_data, _ = consume_fifo_lots(article_obj, qte)
    lots_utilises_data = normalize_fifo_lot_prices(
        lots_utilises_data,
        conditionnement,
        devise_obj,
        entreprise_id=tenant_id,
    )
    if prix_conditionnement is not None:
        multiplicateur = Decimal(str(conditionnement.multiplicateur_base)) if conditionnement else Decimal('1')
        prix_unitaire_final = prix_conditionnement / multiplicateur
    elif prix_unitaire_encaisse is not None:
        prix_unitaire_final = prix_unitaire_encaisse
    else:
        prix_unitaire_final = lots_utilises_data[0]['prix_vente']
    prix_unitaire_final = prix_unitaire_final.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    montant_ligne = (
        (prix_conditionnement * qte_saisie).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        if prix_conditionnement is not None
        else (prix_unitaire_final * qte).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
    )
    # Le contrôle « vente gratuite / sous le coût » ne concerne que les ventes.
    motif_exception = validate_sale_price_policy(
        prix_unitaire_final,
        qte,
        lots_utilises_data,
        utilisateur,
        ligne_payload.get('motif_prix_exception', ''),
        montant_total=montant_ligne,
        request=request,
    ) if sortie.est_commerciale else str(ligne_payload.get('motif_prix_exception') or '').strip()[:500]
    snapshot_ligne = build_conversion_snapshot(
        entreprise_id=sortie.entreprise_id,
        amount=montant_ligne,
        devise_source=devise_obj or default_dev,
    )
    ligne_sortie = LigneSortie.objects.create(
        sortie=sortie,
        article=article_obj,
        conditionnement=conditionnement,
        quantite_conditionnement=qte_saisie if conditionnement is not None else None,
        prix_conditionnement=prix_conditionnement,
        quantite=qte,
        prix_unitaire=prix_unitaire_final,
        montant_total=montant_ligne,
        motif_prix_exception=motif_exception,
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


def _verifier_sortie_modifiable(sortie: Sortie) -> None:
    from order.models import Commande
    from stock.models import InventaireSession

    commande = Commande.objects.filter(sortie_livraison=sortie).first()
    if commande is not None:
        raise serializers.ValidationError({'detail': (
            "Cette sortie a été générée par la livraison d'une commande "
            f"({(commande.reference or '').strip() or '#' + str(commande.pk)}) : modifiez-la depuis le module Commandes."
        )})
    if InventaireSession.objects.filter(sortie_ajustement=sortie).exists():
        raise serializers.ValidationError({'detail': (
            "Cette sortie est un ajustement d'inventaire : elle ne peut pas être modifiée "
            "(annulez l'inventaire si nécessaire)."
        )})


def _resoudre_client(sortie: Sortie, client_id):
    if not client_id:
        return None
    client = Client.objects.filter(pk=client_id, liens_entreprise__entreprise_id=sortie.entreprise_id).first()
    if client is None:
        raise serializers.ValidationError({'client_id': f"Client {client_id} introuvable dans votre entreprise."})
    return client


@transaction.atomic
def update_sortie_from_payload(
    sortie: Sortie,
    data: dict,
    *,
    utilisateur=None,
    request=None,
    type_caisse_id: int | None = None,
) -> Sortie:
    """
    Met à jour une sortie complète : rollback FIFO, nouvelles lignes, caisse, dette, journal.

    ``data`` attend ``lignes`` (liste), champs entête optionnels (motif, client_id, statut).
    Les dates d'origine de la vente (lignes, bénéfices) sont conservées : une modification
    ne déplace pas la vente dans le temps.
    """
    from stock.models import BeneficeLot, DettesClients, LogSuppression
    from stock.services.log_suppression import journaliser_lignes_supprimees
    from stock.services.annulation_mouvement import inventaires_posterieurs, libelle_sortie
    from stock.services.dettes_clients import synchroniser_dette_sortie
    from stock.services.journal_modification import changements_sortie, journaliser, photo_sortie
    from stock.services.retrait_marchandise import nettoyer_retire_par

    sortie = Sortie.objects.select_for_update().get(pk=sortie.pk)
    _verifier_sortie_modifiable(sortie)
    old_statut = sortie.statut
    tenant_id = sortie.entreprise_id
    avant = photo_sortie(sortie)
    dette = DettesClients.objects.filter(sortie=sortie).first()
    paiements_recus = dette is not None and dette.paiements.exists()

    lignes_data = data.get('lignes')
    if lignes_data is not None and not lignes_data:
        raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})

    if lignes_data is not None:
        articles = {ligne['article_id'] for ligne in avant['lignes']} | {
            str(p.get('article_id') or p.get('article')) for p in lignes_data
        }
        raisons = inventaires_posterieurs(tenant_id, sortie.date_creation, articles)
        if raisons:
            raise serializers.ValidationError({'detail': 'Modification des lignes impossible : ' + ' '.join(raisons)})

    default_dev = Devise.objects.filter(entreprise_id=tenant_id, est_principal=True).first()
    if default_dev is None:
        default_dev = Devise.objects.filter(est_principal=True).first()

    # --- Entête : motif / nature, client, type de vente ---------------------------------
    if 'motif' in data:
        nouveau_motif = str(data.get('motif') or '').strip()
        if nouveau_motif != (sortie.motif or '').strip():
            sortie.motif = nouveau_motif
            sortie.est_commerciale = est_sortie_commerciale(nouveau_motif)
    if 'client_id' in data:
        nouveau_client = _resoudre_client(sortie, data.get('client_id'))
        if (nouveau_client.pk if nouveau_client else None) != sortie.client_id and paiements_recus:
            raise serializers.ValidationError({'client_id': (
                "Impossible de changer le client : des paiements ont déjà été reçus sur la dette de cette vente."
            )})
        sortie.client = nouveau_client

    new_statut = str(data.get('statut', sortie.statut) or 'PAYEE').upper()
    if new_statut not in ('PAYEE', 'EN_CREDIT'):
        raise serializers.ValidationError({'statut': 'Statut invalide (PAYEE ou EN_CREDIT).'})
    if new_statut == 'EN_CREDIT' and not sortie.client_id:
        raise serializers.ValidationError({
            'client': _('Un client est obligatoire pour une vente à crédit.'),
        })
    if new_statut == 'EN_CREDIT' and not sortie.est_commerciale:
        raise serializers.ValidationError({'statut': MSG_SORTIE_NON_COMMERCIALE_CREDIT})
    if old_statut == 'EN_CREDIT' and new_statut != 'EN_CREDIT' and paiements_recus:
        raise serializers.ValidationError({'statut': (
            "Impossible de passer cette vente au comptant : des paiements ont déjà été reçus sur sa dette. "
            "Encaissez le reste dû depuis la dette du client."
        )})

    if new_statut != 'EN_CREDIT':
        if str(data.get('retire_par') or '').strip():
            nettoyer_retire_par(data.get('retire_par'), new_statut)
        sortie.retire_par = ''
    elif 'retire_par' in data:
        sortie.retire_par = nettoyer_retire_par(data.get('retire_par', ''), new_statut)
    sortie.statut = new_statut
    sortie.save()

    # --- Lignes : retour des lots puis nouvelle consommation FIFO -------------------------
    totaux_par_devise = {}
    if lignes_data is not None:
        premiere = sortie.lignes.order_by('id').first()
        date_vente = premiere.date_sortie if premiere else sortie.date_creation
        date_benefice = (
            BeneficeLot.objects.filter(ligne_sortie__sortie=sortie).order_by('id')
            .values_list('date_calcul', flat=True).first()
        ) or date_vente
        anciennes_lignes = list(sortie.lignes.select_for_update().select_related('article', 'devise'))
        articles_gardes = {str(p.get('article_id') or p.get('article')) for p in lignes_data}
        retirees = [ligne for ligne in anciennes_lignes if str(ligne.article_id) not in articles_gardes]
        if retirees:
            # Articles retirés de la vente : visibles dans « Stock supprimé » et l'audit.
            journaliser_lignes_supprimees(
                sortie, retirees, utilisateur, motif=LogSuppression.MOTIF_LIGNE, entreprise_id=tenant_id,
            )
        for ancienne_ligne in anciennes_lignes:
            rollback_sortie_ligne(ancienne_ligne)
        for ligne_payload in lignes_data:
            result = _process_sortie_ligne(
                sortie,
                ligne_payload,
                default_dev=default_dev,
                tenant_id=tenant_id,
                utilisateur=utilisateur,
                request=request,
            )
            key = result['devise_key']
            if key not in totaux_par_devise:
                totaux_par_devise[key] = {'devise_obj': result['devise_obj'], 'total': Decimal('0')}
            totaux_par_devise[key]['total'] += result['montant_ligne']
        LigneSortie.objects.filter(sortie=sortie).update(date_sortie=date_vente)
        BeneficeLot.objects.filter(ligne_sortie__sortie=sortie).update(date_calcul=date_benefice)
    else:
        for ligne in sortie.lignes.select_related('devise').all():
            key = ligne.devise.sigle if ligne.devise else 'DEFAULT'
            montant = ligne.get_montant_total()
            if key not in totaux_par_devise:
                totaux_par_devise[key] = {'devise_obj': ligne.devise or default_dev, 'total': Decimal('0')}
            totaux_par_devise[key]['total'] += montant

    if not sortie.lignes.exists():
        raise serializers.ValidationError({'lignes': 'Au moins une ligne de sortie est requise.'})

    if new_statut == 'EN_CREDIT' and not sortie.devise_id:
        from stock.services.sortie_devise import resolve_sortie_primary_devise

        sortie.devise = resolve_sortie_primary_devise(sortie, default_devise=default_dev)
        sortie.save(update_fields=['devise'])

    # --- Dette puis caisse ----------------------------------------------------------------
    synchroniser_dette_sortie(sortie)
    impact_caisse = sync_sortie_cash_movements(
        sortie,
        totaux_par_devise,
        utilisateur=utilisateur,
        type_caisse_id=type_caisse_id,
        old_statut=old_statut,
        new_statut=new_statut,
        motif_ajustement=f'modification {libelle_sortie(sortie)}',
    )

    sortie.refresh_from_db()
    apres = photo_sortie(sortie)
    changements, sensible = changements_sortie(avant, apres)
    journaliser(
        type_mouvement='SORTIE',
        piece=sortie,
        libelle=libelle_sortie(sortie),
        utilisateur=utilisateur,
        avant=avant,
        apres=apres,
        changements=changements,
        sensible=sensible,
        impact_caisse=impact_caisse,
    )
    return sortie

