"""
Contexte multi-tenant (entreprise / succursale) depuis la requête.
Centralisé pour éviter les imports circulaires serializers ↔ views.
"""


def get_tenant_ids(request):
    """
    Retourne (entreprise_id, succursale_id) depuis le contexte JWT ou le user.
    Utilisé pour isolation stricte multi-tenant sur les ViewSets et serializers.
    """
    tenant_id = getattr(request, 'tenant_id', None) or (
        request.user.get_entreprise_id(request) if request.user.is_authenticated else None
    )
    branch_id = getattr(request, 'branch_id', None)
    if branch_id is None and request.user.is_authenticated:
        m = request.user.get_current_membership(request)
        if m and m.default_succursale_id:
            branch_id = m.default_succursale_id
    return tenant_id, branch_id
