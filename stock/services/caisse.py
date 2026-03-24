"""
Création des mouvements de caisse : un enregistrement = montant + motif + moyen
(comme avant la ventilation « multicaisse » sur plusieurs lignes Detail).

Les anciennes lignes ``DetailMouvementCaisse`` en base restent lisibles pour l'historique.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from stock.models import DetteClient, MouvementCaisse, TypeCaisse


def _merge_details_into_motif(details: List[dict], entreprise_id: int, motif_base: str) -> str:
    """Ancien format API ``details_write`` : fusionne en un seul texte (sans lignes Detail)."""
    parts = []
    for row in details:
        tid = row.get("type_caisse_id")
        tc = None
        if tid:
            tc = TypeCaisse.objects.filter(pk=tid, entreprise_id=entreprise_id).first()
        lm = Decimal(str(row.get("montant", 0))).quantize(Decimal("0.01"))
        if tc:
            parts.append(f"{tc.libelle}: {lm}")
        else:
            me = (row.get("motif_explicite") or "").strip()
            parts.append(me if me else str(lm))
    suffix = " | ".join(parts)
    base = (motif_base or "").strip()
    if base and suffix:
        return f"{base} — {suffix}"
    return suffix or base


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
) -> MouvementCaisse:
    """
    Crée un ``MouvementCaisse`` unique (pas de lignes ``DetailMouvementCaisse``).

    - Si ``details`` (format legacy) est fourni : les montants doivent sommer au total ;
      le texte est fusionné dans ``motif``.
    - Sinon : ``montant`` obligatoire ; ``motif`` / ``moyen`` remplis comme avant.
    """
    details = details or []
    lines_total = sum(Decimal(str(d.get("montant", 0) or 0)) for d in details)

    if details:
        if montant is not None:
            if lines_total.quantize(Decimal("0.01")) != Decimal(str(montant)).quantize(Decimal("0.01")):
                raise ValueError(
                    f"La somme des lignes ({lines_total}) ne correspond pas au montant ({montant})."
                )
        else:
            montant = lines_total
    else:
        if montant is None:
            raise ValueError("Montant requis si aucune ligne détaillée.")
        montant = Decimal(str(montant)).quantize(Decimal("0.01"))
        if montant < 0:
            raise ValueError("Le montant ne peut pas être négatif.")

    if details:
        montant = Decimal(str(montant)).quantize(Decimal("0.01"))

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
            parts.append(f"{d.type_caisse.libelle}: {d.montant}")
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
    first = mouvement.details.select_related("type_caisse").first()
    if first and first.type_caisse:
        return first.type_caisse.libelle
    if first and first.motif_explicite:
        return (first.motif_explicite or "")[:80]
    return ""
