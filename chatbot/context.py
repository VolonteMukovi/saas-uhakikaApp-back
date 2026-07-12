"""Contexte utilisateur sécurisé pour le chatbot."""
from __future__ import annotations

from dataclasses import dataclass, field

from django.contrib.auth import get_user_model

User = get_user_model()


@dataclass
class ChatbotContext:
    user: User
    tenant_id: int | None
    branch_id: int | None
    entreprise_nom: str | None
    succursale_nom: str | None
    role: str | None
    is_superadmin: bool
    is_admin: bool
    is_agent: bool
    onboarding_ok: bool
    operations_metier_ok: bool
    chatbot_plan_ok: bool
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, request) -> ChatbotContext:
        from abonnements.services.licence import fonctionnalite_autorisee
        from inscription.services.onboarding_status import onboarding_metier_autorise
        from stock.models import Entreprise, Succursale
        from stock.services.tenant_context import get_tenant_ids

        user = request.user
        tenant_id, branch_id = get_tenant_ids(request)
        ent = user.get_entreprise(request) if user.is_authenticated else None
        if tenant_id is None and ent is not None:
            tenant_id = ent.pk

        membership = user.get_current_membership(request) if user.is_authenticated else None
        role = membership.role if membership else None

        succursale_nom = None
        if branch_id:
            succursale_nom = Succursale.objects.filter(pk=branch_id).values_list('nom', flat=True).first()
        elif ent and not getattr(ent, 'has_branches', False):
            succursale_nom = None

        entreprise_nom = ent.nom if ent else None
        if not entreprise_nom and tenant_id:
            entreprise_nom = Entreprise.objects.filter(pk=tenant_id).values_list('nom', flat=True).first()

        ops_ok = onboarding_metier_autorise(user, request) if user.is_authenticated else False
        chatbot_ok = True
        if tenant_id and user.is_authenticated and not user.is_superuser:
            chatbot_ok = fonctionnalite_autorisee(tenant_id, 'chatbot')

        return cls(
            user=user,
            tenant_id=tenant_id,
            branch_id=branch_id,
            entreprise_nom=entreprise_nom,
            succursale_nom=succursale_nom,
            role=role,
            is_superadmin=bool(user.is_authenticated and user.is_superadmin()),
            is_admin=bool(user.is_authenticated and user.is_admin(request)),
            is_agent=bool(user.is_authenticated and user.is_agent(request)),
            onboarding_ok=bool(user.is_authenticated and getattr(user, 'onboarding_complete', False)),
            operations_metier_ok=ops_ok,
            chatbot_plan_ok=chatbot_ok,
        )

    def public_dict(self) -> dict:
        return {
            'entreprise': self.entreprise_nom,
            'succursale': self.succursale_nom,
            'role': self.role,
        }

    def has_business_scope(self) -> bool:
        return self.tenant_id is not None and not self.is_superadmin

    def can_read_business_data(self) -> bool:
        if not self.user.is_authenticated:
            return False
        if self.is_superadmin:
            return self.tenant_id is not None
        if not self.tenant_id:
            return False
        if not self.chatbot_plan_ok:
            return False
        if not self.operations_metier_ok:
            return False
        return self.is_admin or self.is_agent or self.user.get_current_membership() is not None
