"""Client Gemini — génération de réponse à partir du contexte filtré."""
from __future__ import annotations

import json
import logging

from django.conf import settings

from chatbot.knowledge import DOCUMENTATION_UHAKIKAAPP, SYSTEM_RULES
from chatbot.services.business_answer_formatter import format_business_answer

logger = logging.getLogger(__name__)

_GENAI_IMPORT_ERROR: str | None = None


def _client():
    global _GENAI_IMPORT_ERROR  # noqa: PLW0603

    api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    if not api_key:
        return None
    try:
        from google import genai
    except ImportError as exc:
        _GENAI_IMPORT_ERROR = str(exc)
        logger.warning(
            'google-genai non installé — réponses métier en mode local. '
            'Installez : pip install google-genai'
        )
        return None

    return genai.Client(api_key=api_key)


def build_system_instruction(*, include_documentation: bool) -> str:
    parts = [SYSTEM_RULES]
    if include_documentation:
        parts.append('\nDOCUMENTATION :\n')
        parts.append(DOCUMENTATION_UHAKIKAAPP)
    return '\n'.join(parts)


def generate_answer(
    *,
    question: str,
    context_payload: dict,
    history: list[dict] | None = None,
    include_documentation: bool = False,
) -> str:
    try:
        client = _client()
    except Exception as exc:  # noqa: BLE001
        logger.exception('Gemini client init error: %s', exc)
        return _fallback_answer(question, context_payload)

    if client is None:
        return _fallback_answer(question, context_payload)

    try:
        from google.genai import types
    except ImportError as exc:
        logger.warning('google.genai.types unavailable: %s', exc)
        return _fallback_answer(question, context_payload)

    model = getattr(settings, 'CHATBOT_GEMINI_MODEL', 'gemini-2.5-flash')
    user_content = (
        'Contexte JSON (données autorisées, ne rien inventer hors de ce JSON) :\n'
        f'{json.dumps(context_payload, ensure_ascii=False, indent=2)}\n\n'
        f'Question utilisateur : {question}'
    )

    contents = []
    for item in (history or [])[-4:]:
        role = item.get('role', 'user')
        text = str(item.get('content', ''))[:500]
        if text:
            contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
    contents.append(types.Content(role='user', parts=[types.Part(text=user_content)]))

    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=build_system_instruction(include_documentation=include_documentation),
                temperature=0.1,
            ),
        )
        text = getattr(response, 'text', None) or ''
        return text.strip() or _fallback_answer(question, context_payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception('Gemini chatbot error: %s', exc)
        return _fallback_answer(question, context_payload)


def _fallback_answer(question: str, context_payload: dict) -> str:
    intent = context_payload.get('intent')
    formatted = format_business_answer(intent or '', context_payload)
    if formatted:
        return formatted

    data = context_payload.get('donnees_autorisees') or {}
    if not data:
        if intent in ('hors_sujet', 'hors_sujet_sensible', 'question_interdite'):
            return (
                'Je suis surtout là pour UHAKIKAAPP 😊\n'
                'Vous voulez qu’on vérifie vos ventes, votre stock, vos clients ou votre caisse ?'
            )
        if intent == 'aide':
            return (
                'Je peux vous guider sur les modules UHAKIKAAPP (articles, stock, ventes, caisse, dettes). '
                'Précisez ce que vous souhaitez faire.'
            )
        if _GENAI_IMPORT_ERROR and getattr(settings, 'GEMINI_API_KEY', ''):
            return (
                'Je peux consulter vos données, mais le module Gemini n’est pas disponible sur ce serveur. '
                'Contactez l’administrateur pour installer le paquet `google-genai`.'
            )
        return 'Je ne peux pas consulter cette information pour le moment.'

    lines = ['Voici les informations disponibles :']
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            lines.append(f'- {key} : {json.dumps(value, ensure_ascii=False)}')
        else:
            lines.append(f'- {key} : {value}')
    return '\n'.join(lines)
