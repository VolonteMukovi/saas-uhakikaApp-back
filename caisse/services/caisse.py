"""
Création des mouvements de caisse : un enregistrement = montant + motif + moyen
(comme avant la ventilation « multicaisse » sur plusieurs lignes Detail).

Les anciennes lignes ``DetailMouvementCaisse`` en base restent lisibles pour l'historique.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN
from typing import Any, List, Optional, Union

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from caisse.models import MouvementCaisse, TypeCaisse
from caisse.services.caisse_defaut import CaisseError, valider_caisse_pour_operation
from caisse.services.session_caisse import SessionCaisseError, get_session_ouverte_for_caisse
from stock.models import DetteClient


def _merge_details_into_motif(details: List[dict], entreprise_id: int, motif_base: str) -> str:
    """Ancien format API ``details_write`` : fusionne en un seul texte (sans lignes Detail)."""
    parts = []
    for row in details:
        tid = row.get("type_caisse_id")
        tc = None
        if tid:
            tc = TypeCaisse.objects.filter(pk=tid, entreprise_id=entreprise_id).first()
        lm = Decimal(str(row.get("montant", 0))).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        if tc:
            parts.append(f"{tc.libelle_affiche}: {lm}")
        else:
            me = (row.get("motif_explicite") or "").strip()
            parts.append(me if me else str(lm))
    suffix = " | ".join(parts)
    base = (motif_base or "").strip()
    if base and suffix:
        return f"{base} — {suffix}"
    return suffix or base


def _resolve_type_caisse(
    type_caisse: Optional[TypeCaisse],
    type_caisse_id: Optional[int],
) -> tuple[Optional[TypeCaisse], Optional[int]]:
    if type_caisse is not None:
        return type_caisse, type_caisse.pk
    if type_caisse_id:
        return None, int(type_caisse_id)
    return None, None


@transaction.atomic
def creer_mouvement_caisse(
    *,
    montant: Optional[Decimal],
    devise,
    type_mouvement: str,
    entreprise_id: int,
    succursale_id: Optional[int],
    content_object: Optional[Any] = None,
    utilisateur=None,
    reference_piece: str = "",
    details: Optional[List[dict]] = None,
    sortie=None,
    entree=None,
    motif: str = "",
    moyen: Optional[str] = None,
    session_caisse=None,
    type_caisse=None,
    type_caisse_id: Optional[int] = None,
    categorie: str = "AUTRE",
    skip_session_check: bool = False,
) -> MouvementCaisse:
    """
    Crée un ``MouvementCaisse`` unique (pas de lignes ``DetailMouvementCaisse``).

    - ``type_caisse`` ou ``type_caisse_id`` obligatoire sauf ``skip_session_check`` ou montant nul.
    - Vérifie caisse active ; session ouverte uniquement pour la caisse cash par défaut.
    """
    details = details or []
    lines_total = sum(Decimal(str(d.get("montant", 0) or 0)) for d in details)

    if details:
        if montant is not None:
            if lines_total.quantize(Decimal('0.00001'), rounding=ROUND_DOWN) != Decimal(str(montant)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN):
                raise CaisseError(
                    f"La somme des lignes ({lines_total}) ne correspond pas au montant ({montant})."
                )
        else:
            montant = lines_total
    else:
        if montant is None:
            raise CaisseError("Montant requis si aucune ligne détaillée.")
        montant = Decimal(str(montant)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        if montant < 0:
            raise CaisseError("Le montant ne peut pas être négatif.")

    if details:
        montant = Decimal(str(montant)).quantize(Decimal('0.00001'), rounding=ROUND_DOWN)

    montant_zero = montant == 0

    ct = None
    oid = None
    if content_object is not None:
        ct = ContentType.objects.get_for_model(content_object.__class__)
        oid = content_object.pk

    motif = (motif or "").strip()
    moyen = (moyen or "").strip() or None

    if details:
        motif = _merge_details_into_motif(details, entreprise_id, motif)

    if not motif:
        if sortie:
            motif = f"Vente sortie #{sortie.pk} — {montant}"
        elif entree:
            motif = f"Approvisionnement entrée #{entree.pk} — {montant}"
        elif content_object is not None and isinstance(content_object, DetteClient):
            motif = f"Paiement dette #{content_object.pk} — {montant}"
        else:
            motif = f"Mouvement — {montant}"

    type_caisse, type_caisse_id = _resolve_type_caisse(type_caisse, type_caisse_id)
    if type_caisse_id is None and session_caisse is not None and session_caisse.type_caisse_id:
        type_caisse_id = session_caisse.type_caisse_id
        type_caisse = session_caisse.type_caisse

    devise_id = devise.pk if devise else None

    if not skip_session_check and not montant_zero:
        if not devise_id:
            raise CaisseError("Devise requise pour un mouvement de caisse.")
        type_caisse = valider_caisse_pour_operation(
            type_caisse=type_caisse,
            type_caisse_id=type_caisse_id,
            entreprise_id=entreprise_id,
            succursale_id=succursale_id,
            devise_id=devise_id,
            montant_zero=montant_zero,
        )
        session = session_caisse
        if session is None:
            session = get_session_ouverte_for_caisse(
                type_caisse,
                succursale_id,
                devise_id,
            )
        if session is not None:
            session_caisse = session
    elif not montant_zero and type_caisse is None and type_caisse_id:
        type_caisse = TypeCaisse.objects.filter(pk=type_caisse_id, entreprise_id=entreprise_id).first()

    if sortie and categorie == "AUTRE":
        categorie = "VENTE"
    elif entree and categorie == "AUTRE":
        categorie = "APPROVISIONNEMENT"
    elif content_object is not None and isinstance(content_object, DetteClient) and categorie == "AUTRE":
        categorie = "PAIEMENT_DETTE"
    elif type_mouvement == "ENTREE" and categorie == "AUTRE":
        categorie = "ENTREE_MANUELLE"
    elif type_mouvement == "SORTIE" and categorie == "AUTRE":
        categorie = "SORTIE_MANUELLE"

    mc = MouvementCaisse(
        montant=montant,
        devise=devise,
        type=type_mouvement,
        motif=motif,
        moyen=moyen,
        content_type=ct,
        object_id=oid,
        entreprise_id=entreprise_id,
        succursale_id=succursale_id,
        utilisateur=utilisateur,
        reference_piece=reference_piece or "",
        sortie=sortie,
        entree=entree,
        session_caisse=session_caisse,
        type_caisse=type_caisse,
        categorie=categorie,
    )
    mc.save()
    return mc


def motif_mouvement_concatene(mouvement: MouvementCaisse) -> str:
    """Texte affiché : ``motif`` du mouvement, sinon ancienne ventilation en base."""
    m = (mouvement.motif or "").strip()
    if m:
        return m
    parts = []
    for d in mouvement.details.all().order_by("id"):
        if d.type_caisse_id:
            parts.append(f"{d.type_caisse.libelle_affiche}: {d.montant}")
        elif d.motif_explicite:
            parts.append(d.motif_explicite)
        else:
            parts.append(str(d.montant))
    return " | ".join(parts) if parts else ""


def mouvement_moyen_affiche(mouvement: MouvementCaisse) -> str:
    """Champ ``moyen``, sinon libellé issu d'un ancien détail multicaisse."""
    s = (getattr(mouvement, "moyen", None) or "").strip()
    if s:
        return s
    if mouvement.type_caisse_id:
        return mouvement.type_caisse.libelle_affiche
    first = mouvement.details.select_related("type_caisse").first()
    if first and first.type_caisse:
        return first.type_caisse.libelle_affiche
    if first and first.motif_explicite:
        return (first.motif_explicite or "")[:80]
    return ""
