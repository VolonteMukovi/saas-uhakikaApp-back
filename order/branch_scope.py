"""
Périmètre **succursale** pour le module commandes et le portail client.
Aligné sur `TenantFilterMixin` / `filter_by_tenant` (entreprise + succursale JWT).
"""
from django.db.models import Q
from stock.models import Succursale


def branch_q_for_membership(membership):
    """
    Restreint dettes / sorties / commandes au périmètre succursale du **lien**
    `ClientEntreprise` actif (JWT portail), avec lignes sans succursale (historique).
    """
    if membership.succursale_id is None:
        return Q(succursale__isnull=True)
    return Q(succursale_id=membership.succursale_id) | Q(succursale__isnull=True)


def apply_admin_commande_branch_filter(qs, request, tenant_id, branch_id):
    """
    Filtre les commandes pour un **administrateur** connecté en JWT staff.

    - Toujours : ``entreprise_id = tenant_id``.
    - Si ``?succursale_id=`` est fourni : filtre cette succursale (doit appartenir
      à l’entreprise). Si le JWT fixe déjà une succursale, le paramètre doit être
      identique (sinon queryset vide).
    - Sinon, si le contexte JWT (ou membership) fournit une succursale : filtre cette succursale.
    - Sinon : toutes les succursales de l’entreprise.
    """
    if tenant_id is None:
        return qs.none()

    qs = qs.filter(entreprise_id=tenant_id)

    raw_sid = request.query_params.get("succursale_id")
    if raw_sid is not None and str(raw_sid).strip() != "":
        try:
            sid = int(raw_sid)
        except (TypeError, ValueError):
            return qs.none()
        if not Succursale.objects.filter(pk=sid, entreprise_id=tenant_id).exists():
            return qs.none()
        if branch_id is not None and sid != branch_id:
            return qs.none()
        return qs.filter(succursale_id=sid)

    if branch_id is not None:
        return qs.filter(succursale_id=branch_id)
    return qs
