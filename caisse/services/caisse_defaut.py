"""
Création et résolution des caisses (dont caisse cash par défaut).
"""
from __future__ import annotations

from typing import Optional, Union

from django.db import transaction
from django.utils.translation import gettext as _

from caisse.constants import CAISSE_DEFAUT_CODE, CAISSE_DEFAUT_LIBELLE, CAISSE_DEFAUT_NOM
from caisse.models import TypeCaisse
from stock.models import Devise, Entreprise, Succursale


class CaisseError(ValueError):
    """Erreur métier liée à une caisse."""


MSG_CAISSE_REQUISE = _(
    'Veuillez sélectionner une caisse avant de valider cette opération.'
)
MSG_CAISSE_INACTIVE = _(
    'Cette opération financière exige une caisse active.'
)
MSG_CAISSE_INTRouvable = _('Caisse introuvable pour cette entreprise.')
MSG_CAISSE_DEVISE = _(
    'La devise de l\'opération ne correspond pas à la devise de la caisse sélectionnée.'
)
MSG_CAISSE_CASH_FERMEE = _(
    'La caisse cash est fermée. Veuillez ouvrir la caisse avant d\'effectuer cette opération.'
)
MSG_SESSION_UNIQUEMENT_CASH_DEFAUT = _(
    'Seule la caisse cash physique par défaut peut être ouverte ou fermée.'
)


def caisse_necessite_session(type_caisse: TypeCaisse) -> bool:
    """
    True uniquement pour la caisse cash physique par défaut (ouverture / clôture / mouvements).
    Banque, mobile money, etc. : pas de session requise.
    """
    return type_caisse.code_type == CAISSE_DEFAUT_CODE and type_caisse.est_defaut


def get_caisse_defaut_session_scope(
    entreprise_id: int,
    succursale_id: Optional[int] = None,
) -> Optional[TypeCaisse]:
    """Caisse cash par défaut du contexte (sans création automatique)."""
    qs = TypeCaisse.objects.filter(
        entreprise_id=entreprise_id,
        est_defaut=True,
        code_type=CAISSE_DEFAUT_CODE,
    )
    if succursale_id is not None:
        branch_caisse = qs.filter(succursale_id=succursale_id).first()
        if branch_caisse:
            return branch_caisse
    return qs.filter(succursale_id__isnull=True).first()


def _devise_principale(entreprise_id: int):
    return Devise.objects.filter(entreprise_id=entreprise_id, est_principal=True).first()


def parse_type_caisse_id_from_payload(data) -> Optional[int]:
    """Extrait l'id caisse depuis les clés API courantes."""
    if data is None:
        return None
    if hasattr(data, 'get'):
        raw = (
            data.get('type_caisse_id')
            or data.get('caisse_id')
            or data.get('caisse')
        )
    else:
        raw = data
    if raw is None or raw == '':
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise CaisseError(_('Identifiant de caisse invalide.')) from None


@transaction.atomic
def get_or_create_caisse_defaut(
    entreprise_id: int,
    succursale_id: Optional[int] = None,
) -> TypeCaisse:
    """
    Retourne la caisse cash par défaut pour l'entreprise (et l'agence si précisée).
    La crée si elle n'existe pas.
    """
    qs = TypeCaisse.objects.filter(
        entreprise_id=entreprise_id,
        est_defaut=True,
        code_type=CAISSE_DEFAUT_CODE,
    )
    if succursale_id is not None:
        qs = qs.filter(succursale_id=succursale_id)
    else:
        qs = qs.filter(succursale_id__isnull=True)

    existing = qs.first()
    if existing:
        return existing

    # Une seule caisse défaut par entreprise sans agence : réutiliser si déjà créée globalement
    if succursale_id is not None:
        global_default = TypeCaisse.objects.filter(
            entreprise_id=entreprise_id,
            est_defaut=True,
            succursale_id__isnull=True,
        ).first()
        if global_default and not Entreprise.objects.filter(
            pk=entreprise_id, has_branches=True,
        ).exists():
            return global_default

    devise = _devise_principale(entreprise_id)
    return TypeCaisse.objects.create(
        nom=CAISSE_DEFAUT_NOM,
        libelle=CAISSE_DEFAUT_LIBELLE,
        code_type=CAISSE_DEFAUT_CODE,
        description='Caisse cash physique créée automatiquement.',
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        devise=devise,
        is_active=True,
        est_defaut=True,
    )


def ensure_caisse_defaut_entreprise(entreprise: Union[Entreprise, int]) -> TypeCaisse:
    """Assure la caisse par défaut au niveau entreprise (sans agence)."""
    eid = entreprise.pk if isinstance(entreprise, Entreprise) else entreprise
    return get_or_create_caisse_defaut(eid, None)


def ensure_caisse_defaut_succursale(succursale: Succursale) -> TypeCaisse:
    """Assure une caisse par défaut pour une succursale."""
    return get_or_create_caisse_defaut(succursale.entreprise_id, succursale.pk)


def valider_caisse_pour_operation(
    *,
    type_caisse: Optional[TypeCaisse],
    type_caisse_id: Optional[int],
    entreprise_id: int,
    succursale_id: Optional[int],
    devise_id: Optional[int] = None,
    montant_zero: bool = False,
) -> TypeCaisse:
    """
    Résout et valide la caisse pour une opération financière.
    Lève CaisseError si la caisse est absente, inactive ou incompatible.
    """
    if montant_zero:
        if type_caisse is None and type_caisse_id:
            type_caisse = TypeCaisse.objects.filter(
                pk=type_caisse_id, entreprise_id=entreprise_id,
            ).first()
        return type_caisse

    if type_caisse is None:
        if type_caisse_id:
            type_caisse = TypeCaisse.objects.filter(
                pk=type_caisse_id, entreprise_id=entreprise_id,
            ).first()
        if type_caisse is None:
            raise CaisseError(str(MSG_CAISSE_REQUISE))

    if not type_caisse.is_active:
        raise CaisseError(str(MSG_CAISSE_INACTIVE))

    if type_caisse.entreprise_id != entreprise_id:
        raise CaisseError(str(MSG_CAISSE_INTRouvable))

    if succursale_id is not None and type_caisse.succursale_id not in (None, succursale_id):
        raise CaisseError(str(MSG_CAISSE_INTRouvable))

    if devise_id and type_caisse.devise_id and type_caisse.devise_id != devise_id:
        raise CaisseError(str(MSG_CAISSE_DEVISE))

    return type_caisse
