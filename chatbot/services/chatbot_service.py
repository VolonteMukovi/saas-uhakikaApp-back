"""Orchestration principale du chatbot."""
from __future__ import annotations

import logging

from django.conf import settings
from django.utils.translation import gettext as _

from chatbot.context import ChatbotContext
from chatbot.services.conversation_responses import build_conversation_answer
from chatbot.services.business_answer_formatter import format_business_answer
from chatbot.services.gemini_client import generate_answer
from chatbot.services.intent_classifier import classify_intent
from chatbot.services.permission_checker import CONVERSATIONAL_INTENTS, check_domain_permission
from chatbot.services.rate_limiter import check_rate_limit
from chatbot.services.tools import fetch_for_intent

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000

# Intents où les données backend suffisent — évite Gemini (lenteur / timeouts réseau).
LOCAL_FIRST_INTENTS = frozenset({
    'stock', 'caisse', 'ventes', 'dettes', 'clients', 'rapports', 'abonnement', 'platform',
})


class ChatbotError(Exception):
    def __init__(self, *, title: str, detail: str, status_code: int = 400):
        self.title = title
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def ask_chatbot(
    *,
    request,
    message: str,
    history: list[dict] | None = None,
) -> dict:
    message = (message or '').strip()
    if not message:
        raise ChatbotError(
            title=_('Message vide'),
            detail=_('Veuillez saisir une question.'),
            status_code=400,
        )
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ChatbotError(
            title=_('Message trop long'),
            detail=_('La question ne peut pas dépasser %(max)s caractères.') % {
                'max': MAX_MESSAGE_LENGTH,
            },
            status_code=400,
        )

    if not request.user.is_authenticated:
        raise ChatbotError(
            title=_('Authentification requise'),
            detail=_('Vous devez être connecté pour utiliser l’assistant UHAKIKAAPP.'),
            status_code=401,
        )

    ok, rl_msg = check_rate_limit(request.user.pk)
    if not ok:
        raise ChatbotError(
            title=_('Limite atteinte'),
            detail=rl_msg or _('Réessayez plus tard.'),
            status_code=429,
        )

    ctx = ChatbotContext.from_request(request)
    intent = classify_intent(message)
    perm = check_domain_permission(ctx, intent)
    if not perm.allowed:
        raise ChatbotError(
            title=perm.title or _('Accès refusé'),
            detail=perm.detail or _('Accès refusé.'),
            status_code=403,
        )

    if intent in CONVERSATIONAL_INTENTS:
        answer = build_conversation_answer(intent, message, ctx)
        if answer:
            return _success_payload(
                answer=answer,
                intent=intent,
                ctx=ctx,
                sources=[],
            )

    donnees = fetch_for_intent(ctx, intent, message)

    context_payload = {
        'entreprise': ctx.entreprise_nom,
        'succursale': ctx.succursale_nom,
        'role': ctx.role,
        'intent': intent,
        'question': message,
        'donnees_autorisees': donnees,
    }

    # Réponses métier structurées : formateur local d’abord (rapide, fiable hors ligne Gemini).
    if intent in LOCAL_FIRST_INTENTS:
        local = format_business_answer(intent, context_payload)
        if local:
            logger.info(
                'chatbot ask user=%s tenant=%s intent=%s mode=local sources=%s',
                request.user.pk,
                ctx.tenant_id,
                intent,
                ctx.sources,
            )
            return _success_payload(
                answer=local,
                intent=intent,
                ctx=ctx,
                sources=list(dict.fromkeys(ctx.sources)),
            )

    include_doc = intent == 'aide'
    answer = generate_answer(
        question=message,
        context_payload=context_payload,
        history=history,
        include_documentation=include_doc,
    )

    logger.info(
        'chatbot ask user=%s tenant=%s intent=%s sources=%s',
        request.user.pk,
        ctx.tenant_id,
        intent,
        ctx.sources,
    )

    return _success_payload(
        answer=answer,
        intent=intent,
        ctx=ctx,
        sources=list(dict.fromkeys(ctx.sources)),
    )


def _success_payload(*, answer: str, intent: str, ctx: ChatbotContext, sources: list[str]) -> dict:
    return {
        'answer': answer,
        'type': 'success',
        'sources': sources,
        'context': ctx.public_dict(),
        'metadata': {
            'intent': intent,
            'entreprise_id': ctx.tenant_id,
            'succursale_id': ctx.branch_id,
            'model': getattr(settings, 'CHATBOT_GEMINI_MODEL', 'gemini-2.5-flash'),
        },
    }
