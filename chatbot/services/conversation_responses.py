"""Réponses conversationnelles chaleureuses (sans appel données métier)."""
from __future__ import annotations

import re
import unicodedata

from chatbot.context import ChatbotContext

UHAKIKA_SIGNIFICATION = (
    'Uhakika est un mot swahili qui signifie certitude, fiabilité, assurance ou garantie.\n\n'
    'Dans UHAKIKAAPP, ce nom représente l’objectif du logiciel : aider les entreprises à travailler '
    'avec des données fiables, un stock maîtrisé, une caisse suivie et des rapports clairs.'
)

_SUGGESTION_SUITE = (
    'Vous voulez qu’on vérifie vos ventes, votre stock, vos clients ou votre caisse ?'
)


def _norm(text: str) -> str:
    text = unicodedata.normalize('NFKD', (text or '').lower().strip())
    return ''.join(c for c in text if not unicodedata.combining(c))


def _is_evening_greeting(text: str) -> bool:
    return any(w in text for w in ('bonsoir', 'bonne soiree', 'bonne soirée'))


def _is_morning_greeting(text: str) -> bool:
    return any(w in text for w in ('bonjour', 'bonne journee', 'bonne journée'))


def build_conversation_answer(intent: str, message: str, ctx: ChatbotContext) -> str | None:
    text = _norm(message)

    if intent == 'salutation':
        if _is_evening_greeting(text):
            return (
                'Bonsoir 👋\n'
                'J’espère que votre journée s’est bien passée. '
                'Je suis là pour vous aider avec UHAKIKAAPP.'
            )
        if _is_morning_greeting(text):
            return (
                'Bonjour 👋\n'
                'Je suis ravi de vous retrouver sur UHAKIKAAPP. '
                'Comment puis-je vous aider aujourd’hui ?'
            )
        return (
            'Salut 😊\n'
            'Je suis là pour vous accompagner dans UHAKIKAAPP. '
            'Que voulez-vous vérifier ou comprendre ?'
        )

    if intent == 'remerciement':
        if 'beaucoup' in text or 'bcp' in text:
            return (
                'Merci à vous aussi 🙏\n'
                'Je suis là pour rendre l’utilisation de UHAKIKAAPP plus simple.'
            )
        return (
            'Avec plaisir 😊\n'
            'Je reste disponible si vous voulez vérifier autre chose dans UHAKIKAAPP.'
        )

    if intent == 'compliment':
        if any(w in text for w in ('mechant', 'méchant', 'dur', 'froid', 'agressif')):
            return (
                'Oh non 😅 je ne veux surtout pas paraître méchant.\n'
                'Je suis simplement configuré pour rester concentré sur UHAKIKAAPP, '
                'mais je peux répondre avec plus de douceur. Merci de me l’avoir fait remarquer.'
            )
        return (
            'Merci beaucoup 😊\n'
            'Je fais de mon mieux pour vous accompagner clairement dans UHAKIKAAPP.'
        )

    if intent == 'comprehension':
        if any(w in text for w in ('parfait', 'tres bien', 'très bien', 'super', 'genial', 'génial')):
            return (
                'Parfait 👍\n'
                'Vous pouvez me poser une autre question sur vos ventes, votre stock, '
                'vos clients, votre caisse ou vos rapports.'
            )
        return (
            'Très bien 😊\n'
            'Je reste disponible si vous voulez continuer.'
        )

    if intent == 'petite_conversation':
        if any(w in text for w in ('parle', 'parler', 'discut')):
            return (
                'Bien sûr 😊\n'
                'Je vous écoute. On peut parler de votre entreprise, de vos ventes, '
                'de votre stock, de vos clients, de votre caisse ou de ce que vous voulez '
                'comprendre dans UHAKIKAAPP.'
            )
        if any(w in text for w in ('comment ca va', 'comment ça va', 'allez vous bien', 'allez-vous bien', 'ca va')):
            return (
                'Je vais très bien, merci 😊\n'
                f'{_SUGGESTION_SUITE}'
            )
        return (
            'Je suis là pour vous 😊\n'
            f'{_SUGGESTION_SUITE}'
        )

    if intent == 'contexte_utilisateur':
        ent = ctx.entreprise_nom or 'votre entreprise'
        if ctx.succursale_nom:
            return (
                f'Vous êtes actuellement connecté à l’entreprise **{ent}**, '
                f'succursale **{ctx.succursale_nom}**.'
            ).replace('**', '')
        if ctx.tenant_id:
            return f'Vous êtes actuellement connecté à l’entreprise {ent}.'
        return (
            'Je ne vois pas encore d’entreprise active sur votre session. '
            'Vérifiez que vous êtes bien connecté avec le bon contexte entreprise.'
        )

    if intent == 'uhakika_info':
        return UHAKIKA_SIGNIFICATION

    if intent == 'question_interdite':
        return (
            'Je ne peux pas vous aider avec ce type de demande.\n'
            'Par contre, je peux vous accompagner sur l’utilisation de UHAKIKAAPP '
            'et la sécurité de votre espace.'
        )

    if intent == 'hors_sujet_sensible':
        if any(w in text for w in ('president', 'président', 'politique', 'election', 'élection')):
            return (
                'Haha 😄 là, on sort un peu du terrain UHAKIKAAPP.\n'
                'Je suis spécialisé dans votre logiciel de gestion : ventes, stock, caisse, '
                'clients, dettes, rapports et abonnements.\n'
                'Je peux vous aider sur l’un de ces sujets ?'
            )
        if any(w in text for w in ('amour', 'recette', 'cuisine', 'meteo', 'météo')):
            return (
                'Belle question 😊, mais là on est un peu hors du périmètre UHAKIKAAPP.\n'
                'Moi, je suis surtout là pour vous aider à gérer votre entreprise, '
                'vos ventes, votre stock, votre caisse et vos clients.'
            )
        return (
            'Cette question sort du périmètre UHAKIKAAPP 😊\n'
            f'{_SUGGESTION_SUITE}'
        )

    if intent == 'hors_sujet':
        return (
            'Je suis surtout là pour UHAKIKAAPP 😊\n'
            f'{_SUGGESTION_SUITE}'
        )

    return None
