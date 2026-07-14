"""Orchestration principale du chatbot."""
from __future__ import annotations

import logging

from django.conf import settings
from django.utils.translation import gettext as _

from chatbot.context import ChatbotContext
from chatbot.services.conversation_responses import build_conversation_answer
from chatbot.services.gemini_client import generate_answer
from chatbot.services.intent_classifier import INTENT_DOMAIN, classify_intent
from chatbot.services.permission_checker import CONVERSATIONAL_INTENTS, check_domain_permission
from chatbot.services.rate_limiter import check_rate_limit
from chatbot.services.response_builder import build_response
from chatbot.services.tools import fetch_for_intent

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000

LOCAL_FIRST_INTENTS = frozenset(
    k for k, v in INTENT_DOMAIN.items()
    if v in ('stock', 'caisse', 'ventes', 'dettes', 'clients', 'rapports', 'abonnement')
    or k in ('subscription_plans_list', 'platform', 'clients_with_debts')
)


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
    selected_entity: dict | None = None,
    conversation_context: dict | None = None,
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
    intent_result = classify_intent(
        message,
        history=history,
        conversation_context=conversation_context,
    )

    if selected_entity:
        etype = selected_entity.get('type')
        eid = selected_entity.get('id') or selected_entity.get('value')
        if etype == 'client' and eid:
            intent_result.client_hint = str(
                selected_entity.get('label') or intent_result.client_hint or ''
            )
            if not intent_result.intent.startswith('client') and intent_result.intent not in (
                'client_debt_detail', 'client_debt_pdf', 'dettes', 'debt_summary',
                'clients_with_debts',
            ):
                intent_result.intent = 'client_situation'
            intent_result.last_entities['client_id'] = eid
        if etype == 'article' and eid:
            intent_result.last_entities['article_id'] = eid
            if intent_result.intent not in ('stock_sheet_pdf', 'stock_article_detail'):
                intent_result.intent = 'stock_article_detail'

    intent = intent_result.intent
    perm = check_domain_permission(ctx, intent)
    if not perm.allowed:
        raise ChatbotError(
            title=perm.title or _('Accès refusé'),
            detail=perm.detail or _('Accès refusé.'),
            status_code=403,
        )

    if intent in CONVERSATIONAL_INTENTS:
        answer = build_conversation_answer(intent, message, ctx)
        if intent_result.preface and answer:
            answer = intent_result.preface + answer
        if answer:
            return _success_payload(
                answer=answer,
                intent=intent,
                ctx=ctx,
                sources=[],
                actions=[],
                entities=_build_entities_out(intent_result),
                conversation_context_out=_build_context_out(intent_result),
            )

    donnees = fetch_for_intent(ctx, intent_result)

    if selected_entity and selected_entity.get('type') == 'client' and selected_entity.get('id'):
        from chatbot.services.tools import _client_debts_summary, _client_sales_summary
        from stock.models import Client

        cid = int(selected_entity['id'])
        client = Client.objects.filter(pk=cid).first()
        if client and donnees is not None:
            sales = _client_sales_summary(ctx, cid, period=intent_result.period or 'all_time')
            debts = _client_debts_summary(ctx, cid)
            if intent in (
                'client_debt_detail', 'client_debt_pdf', 'dettes', 'debt_summary',
            ):
                donnees = {
                    'mode': 'client',
                    'client': {'id': client.pk, 'nom': client.nom, 'telephone': client.telephone or ''},
                    'dettes_client': debts,
                    'clients_candidats': [],
                }
            else:
                donnees = {
                    'mode': 'detail',
                    'client': {'id': client.pk, 'nom': client.nom, 'telephone': client.telephone or ''},
                    'ventes': sales,
                    'dettes': debts,
                    'existe': True,
                }

    context_payload = {
        'entreprise': ctx.entreprise_nom,
        'succursale': ctx.succursale_nom,
        'role': ctx.role,
        'intent': intent,
        'question': message,
        'donnees_autorisees': donnees,
    }

    business_intents = LOCAL_FIRST_INTENTS | {
        'stock_sheet_pdf', 'stock_requisition_pdf', 'client_invoice_pdf',
        'client_debt_pdf', 'debt_clients_pdf', 'subscription_plans_list',
        'credit_sales_today', 'top_selling_products', 'approvisionnement_list',
        'approvisionnement_today', 'client_situation', 'client_purchase_history',
        'client_search', 'client_list', 'client_count', 'stock_expiration_30_days',
        'stock_expiration_90_days', 'stock_rupture_list', 'stock_alert_list',
        'stock_article_count', 'stock_article_detail', 'stock_summary',
        'vente_today_summary', 'caisse_balance', 'debt_summary', 'client_debt_detail',
        'clients_with_debts',
    }

    if intent in business_intents:
        built = build_response(intent, context_payload)
        if built:
            answer = built['answer']
            if intent_result.preface:
                answer = intent_result.preface + answer
            entities_out = built.get('entities') or _build_entities_out(intent_result)
            logger.info(
                'chatbot ask user=%s tenant=%s intent=%s mode=local',
                request.user.pk, ctx.tenant_id, intent,
            )
            return _success_payload(
                answer=answer,
                intent=intent,
                ctx=ctx,
                sources=list(dict.fromkeys(ctx.sources)),
                actions=built.get('actions') or [],
                file=built.get('file'),
                entities=entities_out,
                conversation_context_out=_build_context_out(intent_result, entities_out),
            )

    include_doc = intent == 'aide'
    answer = generate_answer(
        question=message,
        context_payload=context_payload,
        history=history,
        include_documentation=include_doc,
    )
    return _success_payload(
        answer=answer,
        intent=intent,
        ctx=ctx,
        sources=list(dict.fromkeys(ctx.sources)),
        actions=[],
        entities=_build_entities_out(intent_result),
        conversation_context_out=_build_context_out(intent_result),
    )


def _build_entities_out(intent_result, extra: dict | None = None) -> dict:
    out = {
        'client': intent_result.client_hint or intent_result.last_entities.get('client'),
        'article': intent_result.product_hint or intent_result.last_entities.get('article'),
        'period': intent_result.period,
        'limit': intent_result.top_n,
    }
    if extra:
        out.update({k: v for k, v in extra.items() if v is not None})
    return {k: v for k, v in out.items() if v is not None}


def _build_context_out(intent_result, entities: dict | None = None) -> dict:
    ent = entities or _build_entities_out(intent_result)
    domain = INTENT_DOMAIN.get(intent_result.intent)
    return {
        'last_intent': intent_result.intent,
        'last_domain': domain,
        'last_entities': ent,
    }


def _success_payload(
    *,
    answer: str,
    intent: str,
    ctx: ChatbotContext,
    sources: list[str],
    actions: list | None = None,
    file: dict | None = None,
    entities: dict | None = None,
    conversation_context_out: dict | None = None,
) -> dict:
    payload = {
        'answer': answer,
        'type': 'success',
        'sources': sources,
        'context': ctx.public_dict(),
        'actions': actions or [],
        'metadata': {
            'intent': intent,
            'entreprise_id': ctx.tenant_id,
            'succursale_id': ctx.branch_id,
            'model': getattr(settings, 'CHATBOT_GEMINI_MODEL', 'gemini-2.5-flash'),
        },
    }
    if file:
        payload['file'] = file
    if entities:
        payload['entities'] = entities
    if conversation_context_out:
        payload['conversation_context'] = conversation_context_out
    return payload
