"""
Champs de relation DRF limités à l'entreprise courante (isolation multi-tenant).

Sans ces champs, un `PrimaryKeyRelatedField(queryset=Model.objects.all())` accepte
l'identifiant d'un objet appartenant à une autre entreprise.
"""
from rest_framework import serializers

from stock.services.tenant_context import get_tenant_ids


def resolve_request_tenant_id(request):
    """Entreprise courante : portail client (JWT client) ou utilisateur interne."""
    if request is None:
        return None
    if getattr(request, 'client', None) is not None:
        membership = getattr(request, 'client_membership', None)
        return getattr(membership, 'entreprise_id', None)
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    tenant_id, _branch_id = get_tenant_ids(request)
    return tenant_id


class TenantScopedFieldMixin:
    """
    Restreint le queryset du champ à `tenant_lookup == entreprise courante`.
    Sans requête dans le contexte (usage interne), le queryset n'est pas filtré.
    """

    default_tenant_lookup = 'entreprise_id'

    def __init__(self, *args, tenant_lookup=None, **kwargs):
        self.tenant_lookup = tenant_lookup or self.default_tenant_lookup
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'request' not in self.context:
            return queryset
        tenant_id = resolve_request_tenant_id(self.context['request'])
        if tenant_id is None:
            return queryset.none()
        return queryset.filter(**{self.tenant_lookup: tenant_id})


class TenantPrimaryKeyRelatedField(TenantScopedFieldMixin, serializers.PrimaryKeyRelatedField):
    pass


class TenantSlugRelatedField(TenantScopedFieldMixin, serializers.SlugRelatedField):
    pass
