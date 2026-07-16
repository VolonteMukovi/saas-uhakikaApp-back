"""
Transformation Réquisition → Approvisionnement (Entree).

Réutilise la logique métier existante de création d'entrée (stock, lots, prix).
La réquisition exprime le besoin ; l'Entree matérialise la réception.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from stock.models import (
    ConditionnementArticle,
    Devise,
    Entree,
    LigneEntree,
    Requisition,
    RequisitionLigne,
    Stock,
)
from stock.services import requisition as requisition_service
from stock.services.conditionnement_pricing import (
    build_ligne_entree_values,
    get_or_create_conditionnement_defaut,
    upsert_prix_conditionnement_entree,
)
from stock.services.currency import build_conversion_snapshot


def resolve_conditionnement_for_ligne(
    ligne: RequisitionLigne,
) -> ConditionnementArticle | None:
    if ligne.type_ligne != RequisitionLigne.TYPE_ARTICLE or not ligne.article_id:
        return None
    if ligne.conditionnement_id:
        return ligne.conditionnement
    return get_or_create_conditionnement_defaut(ligne.article)


def build_entree_prefill_from_requisition(requisition: Requisition) -> dict[str, Any]:
    """
    Construit le payload JSON compatible POST /api/entrees/ (pré-remplissage FE).
    Les lignes LIBRE sans article sont listées dans ``lignes_ignorees``.
    """
    lignes_payload: list[dict] = []
    lignes_ignorees: list[dict] = []

    for ligne in requisition.lignes.select_related(
        'article', 'article__unite', 'conditionnement',
    ).order_by('ordre', 'id'):
        if ligne.type_ligne == RequisitionLigne.TYPE_LIBRE or not ligne.article_id:
            lignes_ignorees.append({
                'ligne_id': ligne.pk,
                'designation': ligne.designation,
                'raison': 'Ligne libre : créer l\'article avant l\'approvisionnement.',
            })
            continue

        cond = resolve_conditionnement_for_ligne(ligne)
        prix_achat = requisition_service.dernier_prix_achat_conditionnement(ligne.article, cond)
        if prix_achat is None and ligne.prix_estime is not None:
            prix_achat = Decimal(str(ligne.prix_estime))
        prix_vente = requisition_service.dernier_prix_vente_conditionnement(ligne.article, cond)
        if prix_vente is None or prix_vente <= 0:
            # Obligatoire côté Entree : fallback sur prix d'achat packing ou 0.00001
            prix_vente = prix_achat if prix_achat and prix_achat > 0 else Decimal('0.00001')

        seuil = ligne.seuil_alerte
        if seuil is None:
            stock = Stock.objects.filter(article=ligne.article).first()
            seuil = getattr(stock, 'seuilAlert', 0) if stock else 0

        lignes_payload.append({
            'article_id': ligne.article_id,
            'conditionnement_id': cond.pk if cond else None,
            'conditionnement_nom': cond.nom if cond else None,
            'quantite_saisie': str(ligne.quantite),
            'prix_achat_conditionnement': str(prix_achat) if prix_achat is not None else '0',
            'prix_vente_conditionnement': str(prix_vente),
            'seuil_alerte': str(seuil or 0),
            'remarque_source': ligne.remarque or '',
            'requisition_ligne_id': ligne.pk,
        })

    libele = f"Approvisionnement — {requisition.numero}"
    if requisition.titre:
        libele = f"{libele} — {requisition.titre}"[:100]
    description_parts = [
        f"Issu de la réquisition {requisition.numero}.",
    ]
    if requisition.description:
        description_parts.append(requisition.description)
    if requisition.observations:
        description_parts.append(f"Observations : {requisition.observations}")

    return {
        'libele': libele,
        'description': '\n'.join(description_parts),
        'source_requisition_id': requisition.pk,
        'source_requisition_numero': requisition.numero,
        'succursale_id': requisition.succursale_id,
        'lignes': lignes_payload,
        'lignes_ignorees': lignes_ignorees,
    }


def transform_requisition_to_approvisionnement(
    requisition: Requisition,
    *,
    utilisateur=None,
    force: bool = False,
    creer: bool = True,
) -> dict[str, Any]:
    """
    Transforme une réquisition VALIDEE en approvisionnement.

    ``creer=True`` (défaut) : crée l'Entree via la même logique que POST /api/entrees/
    (lots, stock, prix). L'utilisateur peut ensuite modifier via le flux Entree existant.

    ``creer=False`` : retourne uniquement le payload de pré-remplissage (preview).
    """
    if requisition.statut != Requisition.STATUT_VALIDEE:
        raise ValidationError({
            'detail': (
                'Seule une réquisition validée peut être transformée '
                'en approvisionnement.'
            ),
        })
    if (
        requisition.transformation_status == Requisition.TRANSFO_OUI
        and not force
        and creer
    ):
        existing = list(
            requisition.approvisionnements.order_by('-id').values('id', 'libele', 'date_op')
        )
        raise ValidationError({
            'detail': 'Cette réquisition a déjà été transformée.',
            'approvisionnements': [
                {
                    'id': e['id'],
                    'libele': e['libele'],
                    'date_op': e['date_op'].isoformat() if e['date_op'] else None,
                }
                for e in existing
            ],
            'hint': 'Passez force=true pour créer un nouvel approvisionnement lié.',
        })

    prefill = build_entree_prefill_from_requisition(requisition)
    if not prefill['lignes']:
        raise ValidationError({
            'detail': (
                'Aucune ligne article transformable. '
                'Les lignes libres doivent d\'abord être créées comme articles.'
            ),
            'lignes_ignorees': prefill['lignes_ignorees'],
        })

    if not creer:
        return {
            'cree': False,
            'prefill': prefill,
            'requisition_id': requisition.pk,
            'requisition_numero': requisition.numero,
        }

    with transaction.atomic():
        entree = _create_entree_from_prefill(requisition, prefill)
        requisition.transformation_status = Requisition.TRANSFO_OUI
        requisition.transformed_at = timezone.now()
        requisition.save(update_fields=['transformation_status', 'transformed_at', 'date_modification'])
        requisition_service.log_historique(
            requisition,
            action='TRANSFORMATION_APPROVISIONNEMENT',
            utilisateur=utilisateur,
            detail=f'Approvisionnement #{entree.pk} créé depuis {requisition.numero}',
            metadata={
                'entree_id': entree.pk,
                'lignes': len(prefill['lignes']),
                'lignes_ignorees': len(prefill['lignes_ignorees']),
                'force': force,
            },
        )

    return {
        'cree': True,
        'entree_id': entree.pk,
        'entree': {
            'id': entree.pk,
            'libele': entree.libele,
            'description': entree.description,
            'date_op': entree.date_op.isoformat() if entree.date_op else None,
            'source_requisition_id': requisition.pk,
            'source_requisition_numero': requisition.numero,
        },
        'prefill': prefill,
        'requisition_id': requisition.pk,
        'requisition_numero': requisition.numero,
        'message': (
            'Approvisionnement créé. Vous pouvez encore modifier les quantités '
            'reçues via le module Approvisionnements avant / après correction.'
        ),
    }


def _create_entree_from_prefill(requisition: Requisition, prefill: dict) -> Entree:
    """Crée l'Entree en réutilisant build_ligne_entree_values (même pipeline que serializers)."""
    entreprise_id = requisition.entreprise_id
    succursale_id = requisition.succursale_id
    devise_principale = Devise.objects.filter(
        entreprise_id=entreprise_id, est_principal=True,
    ).first() or Devise.objects.filter(est_principal=True).first()

    entree = Entree.objects.create(
        libele=prefill['libele'],
        description=prefill['description'],
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        source_requisition=requisition,
        source_requisition_numero=requisition.numero,
    )

    for ligne_data in prefill['lignes']:
        from stock.models import Article
        article = Article.objects.get(article_id=ligne_data['article_id'])
        ligne_values = build_ligne_entree_values(
            article,
            {
                'conditionnement_id': ligne_data.get('conditionnement_id'),
                'quantite_saisie': ligne_data.get('quantite_saisie'),
                'prix_achat_conditionnement': ligne_data.get('prix_achat_conditionnement'),
                'prix_vente_conditionnement': ligne_data.get('prix_vente_conditionnement'),
            },
        )
        quantite = ligne_values['quantite']
        montant_ligne = (
            Decimal(str(ligne_values['prix_unitaire'])) * Decimal(str(quantite))
        ).quantize(Decimal('0.00001'))
        snapshot_ligne = build_conversion_snapshot(
            entreprise_id=entreprise_id,
            amount=montant_ligne,
            devise_source=devise_principale,
            devise_reference=devise_principale,
        )
        le = LigneEntree.objects.create(
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
            devise=devise_principale,
            devise_reference=snapshot_ligne['devise_reference'],
            taux_change=snapshot_ligne['taux_change'],
            montant_reference=snapshot_ligne['montant_reference'],
            seuil_alerte=Decimal(str(ligne_data.get('seuil_alerte') or 0)),
        )
        upsert_prix_conditionnement_entree(le, None, devise_principale)
        stock_obj, _ = Stock.objects.get_or_create(
            article=article,
            defaults={'Qte': 0, 'seuilAlert': Decimal(str(ligne_data.get('seuil_alerte') or 0))},
        )
        stock_obj.Qte += quantite
        stock_obj.seuilAlert = Decimal(str(ligne_data.get('seuil_alerte') or stock_obj.seuilAlert or 0))
        stock_obj.save(update_fields=['Qte', 'seuilAlert'])

    return entree
