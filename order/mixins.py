from stock.services.tenant_context import get_tenant_ids


def filter_by_tenant(qs, request):
    """Filtre le queryset par `entreprise` / `succursale` selon le contexte JWT."""
    tenant_id, branch_id = get_tenant_ids(request)
    if tenant_id is None:
        return qs.none()

    model = qs.model
    if hasattr(model, "entreprise_id"):
        qs = qs.filter(entreprise_id=tenant_id)

    # Si l'utilisateur est rattaché à une succursale, filtrer aussi.
    if branch_id is not None and hasattr(model, "succursale_id"):
        qs = qs.filter(succursale_id=branch_id)

    return qs

