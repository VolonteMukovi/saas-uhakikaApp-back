"""Classification d'intention fine + extraction d'entités (sans ML).

Ordre imposé :
1. Normaliser le message (fautes / synonymes)
2. Détecter les suivis de conversation (non en général, en PDF…)
3. Classifier l'intention métier
4. Extraire les entités seulement après (et jamais depuis des mots-filtres)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

TYPO_REPLACEMENTS: list[tuple[str, str]] = [
    (r'\bapprovision+e?ments?\b', 'approvisionnements'),
    (r'\bapprovision+e?ment\b', 'approvisionnement'),
    (r'\bapprovisonn?ements?\b', 'approvisionnements'),
    (r'\brecquisiti?oi?ns?\b', 'requisition'),
    (r'\brequisitions?\b', 'requisition'),
    (r'\baujourdhui+t?\b', 'aujourd hui'),
    (r'\baujour.?hui+t?\b', 'aujourd hui'),
    (r'\bqui\s+au\s+des\b', 'qui ont des'),
    (r'\bqui\s+on\s+des\b', 'qui ont des'),
    (r'\bquel\s+sont\b', 'quels sont'),
    (r'\ben\s+general\b', 'en general'),
    (r'\bfoction\b', 'fonction'),
    (r'\bvenduss?\b', 'vendus'),
    (r'\bdettes?\s+en\s+cours\b', 'dettes en cours'),
]


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in text if not unicodedata.combining(c))


def normalize_user_message(message: str) -> str:
    text = (message or '').lower().strip()
    text = text.replace("'", ' ').replace('’', ' ').replace('`', ' ')
    text = _strip_accents(text)
    text = re.sub(r'[?!…]{2,}', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    for pattern, repl in TYPO_REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return text


def _norm(text: str) -> str:
    return normalize_user_message(text)


def _is_short_message(text: str, max_words: int = 4) -> bool:
    return len(text.split()) <= max_words


def strip_polite_prefix(text: str) -> str:
    """
    Retire un préfixe de politesse (merci, bonjour…) si le message contient
    encore une vraie demande métier ensuite.
    Ex. « merci, quels produits puis-je approvisionner » → partie métier.
    """
    stripped = re.sub(
        r'^(merci(\s+beaucoup)?|bonjour|bonsoir|salut|hello|coucou|'
        r'd.accord|ok|parfait|tres bien)\s*[,;:.\-!]+\s*',
        '',
        text,
        count=1,
    )
    stripped = re.sub(
        r'^(merci(\s+beaucoup)?|bonjour|bonsoir|salut)\s+',
        '',
        stripped,
        count=1,
    )
    # Ne retirer le préfixe que s'il reste une question substantielle
    if stripped != text and len(stripped.split()) >= 3:
        return stripped.strip()
    return text


def _is_pure_politeness(text: str) -> bool:
    """True si le message n'est qu'une salutation / remerciement isolé."""
    t = text.strip()
    if not t:
        return True
    if re.fullmatch(
        r'(merci(\s+beaucoup)?|bonjour|bonsoir|salut|hello|coucou|'
        r'd.accord|ok|parfait|tres bien|je comprends|je vois|ca marche)[.!?]*',
        t,
    ):
        return True
    # « merci » suivi d'à peine 1-2 mots sans demande
    if t.startswith('merci') and len(t.split()) <= 3 and not any(
        w in t for w in (
            'stock', 'vente', 'client', 'dette', 'caisse', 'article', 'produit',
            'approvision', 'requisition', 'facture', 'rapport', 'combien', 'quel',
        )
    ):
        return True
    return False


# ---------------------------------------------------------------------------
# Patterns conversationnels
# ---------------------------------------------------------------------------

SECURITY_PATTERNS = [
    r'ignore(r)?\s+les?\s+permissions',
    r'contourn',
    r'mot\s+de\s+passe',
    r'\bpassword\b',
    r'\btoken\b',
    r'\bsql\b',
    r'toutes\s+les\s+entreprises',
    r'donnees?\s+globales',
    r'sans\s+filtr',
]

FORBIDDEN_PATTERNS = [r'hack', r'pirat', r'cracker', r'voler\s+un\s+compte']

CONTEXT_ENTREPRISE_PATTERNS = [
    r'je\s+suis\s+(dans\s+)?quelle?\s+entreprise',
    r'je\s+suis\s+quel\s+entreprise',
    r'mon\s+entreprise\s+c.est\s+quoi',
    r'je\s+travaille\s+(sur|dans)\s+quelle\s+entreprise',
    r'je\s+suis\s+connecte\s+ou',
    r'quelle\s+entreprise\s+suis',
    r'entreprise\s+active',
]

UHAKIKA_INFO_PATTERNS = [
    r'que\s+signifie\s+uhakika',
    r'qu.est.ce\s+que\s+uhakika',
    r'signification\s+de\s+uhakika',
    r'uhakika\s+c.est\s+quoi',
    r'veut\s+dire\s+uhakika',
]

SALUTATION_PATTERNS = [
    r'^bonjour\b', r'^bonsoir\b', r'^salut\b', r'^hello\b', r'^coucou\b',
]

REMERCIEMENT_PATTERNS = [
    r'^merci\b', r'^thanks\b', r'^je\s+vous\s+remercie', r'^merci\s+beaucoup',
]

COMPREHENSION_PATTERNS = [
    r'^(ok|d.accord|dac|dacord)\.?$',
    r'^je\s+(comprends|vois)\.?$',
    r'^(tres\s+bien|parfait|ca\s+marche|c.est\s+bon|super|genial)\.?$',
]

COMPLIMENT_PATTERNS = [
    r'vous\s+etes\s+gentil', r'tu\s+es\s+gentil', r'vous\s+etes\s+sympa', r'bravo',
]

NEGATIVE_COMPLIMENT_PATTERNS = [
    r'pourquoi\s+vous\s+etes\s+mechant', r'pourquoi\s+tu\s+es\s+mechant',
    r'vous\s+etes\s+mechant', r'tu\s+es\s+mechant',
]

PETITE_CONVERSATION_PATTERNS = [
    r'comment\s+ca\s+va', r'comment\s+allez\s+vous', r'vous\s+allez\s+bien',
    r'ca\s+va\s*\?', r'je\s+veux\s+qu.?on\s+parle', r'on\s+peut\s+parler',
    r'parlons', r'je\s+veux\s+parler',
]

# Corrections de période / suivi (pas de petite conversation)
PERIOD_FOLLOWUP_PATTERNS = [
    r'^non\s+(en\s+)?general\.?$',
    r'^pas\s+aujourd.?hui\.?$',
    r'^en\s+general\.?$',
    r'^globalement\.?$',
    r'^toutes?\s+periodes?\.?$',
    r'^depuis\s+le\s+debut\.?$',
    r'^tout\s+le\s+temps\.?$',
    r'^sur\s+toute\s+la\s+periode\.?$',
    r'^au\s+global\.?$',
    r'^non\s*,?\s*en\s+general\.?$',
]

PDF_FOLLOWUP_PATTERNS = [
    r'^en\s+pdf(\s+maintenant)?\.?$',
    r'^genere?\s+(le\s+)?pdf\.?$',
    r'^pdf\s+maintenant\.?$',
]

HORS_SUJET_SENSIBLE_KEYWORDS = [
    'president', 'politique', 'election', 'amour', 'recette de', 'tarte aux',
    'meteo', 'football match',
]

# Mots qui ne sont JAMAIS un nom de client
CLIENT_HINT_STOPWORDS = frozenset({
    'encore', 'combien', 'quel', 'quelle', 'quels', 'quelles', 'quoi', 'aujourd',
    'hui', 'tous', 'toutes', 'mes', 'nos', 'les', 'des', 'une', 'un', 'cet', 'cette',
    'systeme', 'uhakikaapp', 'de', 'ce', 'parmi', 'en', 'cours', 'retard', 'payee',
    'payees', 'impaye', 'impayees', 'dettes', 'dette', 'solde', 'soldes', 'clients',
    'client', 'qui', 'ont', 'au', 'avec', 'credit', 'credits', 'pdf', 'pour',
    'facture', 'situation', 'fiche', 'etat', 'historique', 'quelques', 'quelque',
    'premier', 'premiers', 'plus', 'vendus', 'vendu', 'articles', 'article',
    'produits', 'produit', 'stock', 'caisse', 'ventes', 'vente', 'general',
    'ou', 'ce', 'qu', 'il', 'elle', 'a', 'achete', 'achat', 'achats',
})

INTENT_DOMAIN: dict[str, str | None] = {
    'salutation': None,
    'remerciement': None,
    'compliment': None,
    'comprehension': None,
    'petite_conversation': None,
    'contexte_utilisateur': None,
    'uhakika_info': None,
    'hors_sujet': None,
    'hors_sujet_sensible': None,
    'question_interdite': None,
    'security_bypass': None,
    'aide': None,
    'platform': None,
    'abonnement': 'abonnement',
    'subscription_plans_list': 'abonnement',
    'stock': 'stock',
    'stock_summary': 'stock',
    'stock_article_count': 'stock',
    'stock_rupture_list': 'stock',
    'stock_alert_list': 'stock',
    'stock_expiration_30_days': 'stock',
    'stock_expiration_90_days': 'stock',
    'stock_article_detail': 'stock',
    'stock_sheet_pdf': 'stock',
    'stock_requisition_pdf': 'stock',
    'approvisionnement_list': 'stock',
    'approvisionnement_today': 'stock',
    'clients': 'clients',
    'client_count': 'clients',
    'client_list': 'clients',
    'client_search': 'clients',
    'client_situation': 'clients',
    'client_purchase_history': 'clients',
    'client_invoice_pdf': 'clients',
    'clients_with_debts': 'dettes',
    'client_debt_detail': 'dettes',
    'client_debt_pdf': 'dettes',
    'debt_clients_pdf': 'dettes',
    'dettes': 'dettes',
    'debt_summary': 'dettes',
    'ventes': 'ventes',
    'vente_today_summary': 'ventes',
    'credit_sales_today': 'ventes',
    'top_selling_products': 'ventes',
    'caisse': 'caisse',
    'caisse_balance': 'caisse',
    'rapports': 'rapports',
}


@dataclass
class IntentResult:
    intent: str
    client_hint: str | None = None
    product_hint: str | None = None
    period: str = 'today'
    top_n: int = 5
    wants_pdf: bool = False
    last_entities: dict = field(default_factory=dict)
    follow_up: bool = False
    preface: str | None = None  # ex. "D'accord, période générale."


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def _is_valid_client_hint(hint: str | None) -> bool:
    if not hint:
        return False
    cleaned = normalize_user_message(hint)
    words = [w for w in cleaned.split() if w]
    if not words or len(cleaned) < 2:
        return False
    if all(w in CLIENT_HINT_STOPWORDS for w in words):
        return False
    if cleaned in CLIENT_HINT_STOPWORDS:
        return False
    # Trop de mots-outils → faux positif (ex. "qui ont des dettes")
    stop_ratio = sum(1 for w in words if w in CLIENT_HINT_STOPWORDS) / len(words)
    if stop_ratio >= 0.6 and len(words) >= 2:
        return False
    if any(w in cleaned for w in (
        'en cours', 'ont des', 'au des', 'des dettes', 'qui ont', 'plus vendu',
    )):
        return False
    return True


def extract_period(text: str, *, default: str = 'today') -> str:
    if any(w in text for w in (
        'en general', 'toutes periodes', 'depuis le debut', 'tout temps',
        'tout le temps', 'pas aujourd', 'globalement', 'au global',
        'sur toute la periode',
    )):
        return 'all_time'
    if any(w in text for w in ('3 mois', 'trois mois', '90 jour', 'prochain mois')):
        return 'days_90'
    if '30 jour' in text or (('bientot' in text or 'proche' in text) and 'expir' in text):
        return 'days_30'
    if 'semaine' in text:
        return 'week'
    if 'mois' in text and '3' not in text and 'trois' not in text:
        return 'month'
    if 'aujourd' in text or 'du jour' in text:
        return 'today'
    return default


def extract_top_n(text: str, default: int = 5) -> int:
    m = re.search(r'top\s*(\d+)', text)
    if m:
        return min(max(int(m.group(1)), 1), 50)
    m = re.search(r'(\d+)\s*(premiers?|produits?|articles?|clients?)', text)
    if m:
        return min(max(int(m.group(1)), 1), 50)
    m = re.search(r'(?:les|mes|nos)\s+(\d+)\s+(?:premiers?|meilleurs?)', text)
    if m:
        return min(max(int(m.group(1)), 1), 50)
    return default


def wants_pdf(text: str) -> bool:
    return any(w in text for w in ('pdf', 'imprime', 'imprimer', 'telecharger'))


def extract_client_hint(message: str) -> str | None:
    """N'extrait un client QUE via des motifs explicites sûrs."""
    raw = message.strip()
    text = normalize_user_message(raw)

    # Interdit : phrases dettes / listes génériques
    if any(p in text for p in (
        'dettes en cours', 'clients qui ont', 'client qui ont', 'qui ont des dettes',
        'qui au des dettes', 'clients debiteurs', 'clients endettes',
        'quelque client qui', 'quelques client', 'combien de dettes',
    )):
        # sauf si un vrai nom apparaît après "client X" / "pour X"
        pass

    patterns = [
        r'(?:situation|fiche|etat)\s+(?:du\s+)?client\s+([a-z0-9][a-z0-9 \-]{1,40})',
        r'client\s+([a-z0-9][a-z0-9\-]{1,40})(?!\s+qui)',
        r'facture(?:\s+pdf)?\s+(?:pour|de|du)\s+([a-z0-9][a-z0-9\-]{1,40})',
        r'(?:achats?|achete|historique)\s+(?:de\s+|du\s+)?([a-z0-9][a-z0-9\-]{2,40})',
        r'(?:dettes?|solde)\s+(?:pour|de|du)\s+([a-z0-9][a-z0-9\-]{2,40})',
        r'aujourd.?hui\s+([a-z0-9][a-z0-9\-]{2,40})\s+a\s+',
        r'([a-z0-9][a-z0-9\-]{2,40})\s+a\s+achete',
        r'pour\s+([a-z0-9][a-z0-9\-]{2,40})(?:\s+ou|\s*$|\s*\?)',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        hint = m.group(1).strip(' ?.,!')
        # Couper aux mots-outils
        words = []
        for w in hint.split():
            if w in CLIENT_HINT_STOPWORDS and words:
                break
            if w in CLIENT_HINT_STOPWORDS:
                continue
            words.append(w)
        hint = ' '.join(words).strip()
        if _is_valid_client_hint(hint):
            return hint
    return None


def extract_product_hint(message: str) -> str | None:
    text = normalize_user_message(message)
    patterns = [
        r'(?:produit|article)\s+([a-z0-9][a-z0-9 \-]{1,60})',
        r'stock\s+(?:du|de|d)\s+(?:l.?article\s+)?([a-z0-9][a-z0-9 \-]{1,60})',
        r'fiche\s+de\s+stock\s+(?:de\s+(?:l.?article\s+)?)?([a-z0-9][a-z0-9 \-]{1,60})',
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            hint = m.group(1).strip(' ?.,!')
            words = []
            for w in hint.split():
                if w in ('stock', 'pdf', 'en', 'la', 'le', 'les', 'plus', 'vendus'):
                    break
                words.append(w)
            hint = ' '.join(words)
            if hint and hint not in ('stock', 'pdf'):
                return hint
    return None


def extract_last_entities_from_history(history: list[dict] | None) -> dict:
    entities: dict = {'client': None, 'article': None, 'intent': None, 'period': None, 'limit': None}
    if not history:
        return entities
    for item in reversed(history[-6:]):
        content = str(item.get('content') or '')
        # Prefer structured metadata if frontend starts sending it in content markers — skip
        m = re.search(
            r'(?:client|situation du client|achats? de|aucun achat de|facture)\s+[«"]?([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\-]{1,40})',
            content,
            re.IGNORECASE,
        )
        if m and not entities['client']:
            cand = m.group(1).strip(' «»".,')
            if _is_valid_client_hint(cand):
                entities['client'] = cand
        hint = extract_client_hint(content)
        if hint and not entities['client']:
            entities['client'] = hint
        ph = extract_product_hint(content)
        if ph and not entities['article']:
            entities['article'] = ph
    return entities


def apply_conversation_context(
    result: IntentResult,
    conversation_context: dict | None,
) -> IntentResult:
    """Applique le contexte structuré envoyé par le frontend."""
    if not conversation_context:
        return result
    last_intent = conversation_context.get('last_intent')
    last_entities = conversation_context.get('last_entities') or {}
    if last_entities.get('client') and _is_valid_client_hint(str(last_entities['client'])):
        result.last_entities['client'] = last_entities['client']
    if last_entities.get('article'):
        result.last_entities['article'] = last_entities['article']
    if last_entities.get('period'):
        result.last_entities['period'] = last_entities['period']
    if last_entities.get('limit'):
        result.last_entities['limit'] = last_entities['limit']
    if last_intent:
        result.last_entities['intent'] = last_intent
    return result


def is_expiration_question(message: str) -> bool:
    text = normalize_user_message(message)
    return any(w in text for w in ('expir', 'dlc', 'perime', 'proche de l expiration'))


def classify_intent(
    message: str,
    history: list[dict] | None = None,
    conversation_context: dict | None = None,
) -> IntentResult:
    text = normalize_user_message(message)
    text = strip_polite_prefix(text)
    result = IntentResult(intent='hors_sujet')
    result.last_entities = extract_last_entities_from_history(history)
    result = apply_conversation_context(result, conversation_context)

    # top_n : depuis message OU contexte
    result.top_n = extract_top_n(text, default=int(result.last_entities.get('limit') or 5))
    result.wants_pdf = wants_pdf(text)

    if not text:
        return result

    # --- Sécurité ---
    for pattern in SECURITY_PATTERNS:
        if re.search(pattern, text):
            result.intent = 'security_bypass'
            return result
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text):
            result.intent = 'question_interdite'
            return result

    # --- Suivi de conversation (AVANT petite_conversation) ---
    last_intent = (
        (conversation_context or {}).get('last_intent')
        or result.last_entities.get('intent')
    )
    if _matches_any(text, PERIOD_FOLLOWUP_PATTERNS) and last_intent:
        result.intent = str(last_intent)
        result.period = 'all_time'
        result.follow_up = True
        result.preface = (
            'D’accord 😊 je prends la période générale (toutes périodes confondues).\n\n'
        )
        if result.last_entities.get('limit'):
            result.top_n = int(result.last_entities['limit'])
        if result.last_entities.get('client') and not result.client_hint:
            result.client_hint = result.last_entities['client']
        return result

    if _matches_any(text, PDF_FOLLOWUP_PATTERNS) and last_intent:
        result.intent = str(last_intent)
        result.wants_pdf = True
        result.follow_up = True
        if 'client' in str(last_intent) or last_intent in (
            'client_purchase_history', 'client_situation', 'clients_with_debts',
        ):
            result.intent = 'client_invoice_pdf' if last_intent != 'clients_with_debts' else 'debt_clients_pdf'
        if 'requisition' in str(last_intent) or last_intent == 'stock_summary':
            result.intent = 'stock_requisition_pdf'
        if result.last_entities.get('client'):
            result.client_hint = result.last_entities['client']
        return result

    # --- Conversationnels (UNIQUEMENT si message purement poli) ---
    if _matches_any(text, NEGATIVE_COMPLIMENT_PATTERNS):
        result.intent = 'compliment'
        return result
    if _matches_any(text, CONTEXT_ENTREPRISE_PATTERNS):
        result.intent = 'contexte_utilisateur'
        return result
    if _matches_any(text, UHAKIKA_INFO_PATTERNS):
        result.intent = 'uhakika_info'
        return result
    if _is_pure_politeness(text):
        if _matches_any(text, SALUTATION_PATTERNS) or text in (
            'bonjour', 'bonsoir', 'salut', 'hello', 'coucou',
        ):
            result.intent = 'salutation'
            return result
        if text.startswith('merci') or _matches_any(text, REMERCIEMENT_PATTERNS):
            result.intent = 'remerciement'
            return result
        if _matches_any(text, COMPREHENSION_PATTERNS):
            result.intent = 'comprehension'
            return result
    if _matches_any(text, COMPLIMENT_PATTERNS) and _is_short_message(text, 8):
        result.intent = 'compliment'
        return result
    if _matches_any(text, PETITE_CONVERSATION_PATTERNS) and not any(
        w in text for w in ('stock', 'vente', 'client', 'dette', 'approvision', 'requisition')
    ):
        result.intent = 'petite_conversation'
        return result
    if any(kw in text for kw in HORS_SUJET_SENSIBLE_KEYWORDS):
        result.intent = 'hors_sujet_sensible'
        return result

    # --- Dettes (AVANT extraction client) ---
    if any(w in text for w in (
        'clients qui ont des dettes', 'client qui ont des dettes', 'clients debiteurs',
        'clients endettes', 'quelque client qui', 'quelques client', 'clients avec solde',
        'qui n a pas encore paye', 'ceux qui ont des credits', 'clients qui doivent',
    )) or (re.search(r'client[s].{0,30}dettes?', text) and 'combien' not in text):
        result.intent = 'clients_with_debts'
        result.client_hint = None
        result.period = extract_period(text, default='all_time')
        return result

    if any(w in text for w in (
        'combien de dettes', 'nombre de dettes', 'dettes en cours', 'dettes en retard',
        'solde total restant', 'recouvrement',
    )) or (re.search(r'\bdettes?\b', text) and not re.search(r'client\s+[a-z0-9]', text)):
        # "dettes pour MANDEFU" → client debt
        named = re.search(r'dettes?\s+(?:pour|de|du)\s+([a-z0-9][a-z0-9\-]{2,40})', text)
        if named and _is_valid_client_hint(named.group(1)):
            result.client_hint = named.group(1)
            result.intent = 'client_debt_detail' if not wants_pdf(text) else 'client_debt_pdf'
            return result
        if wants_pdf(text) and 'client' in text:
            result.intent = 'debt_clients_pdf'
            result.client_hint = None
            return result
        result.intent = 'debt_summary'
        result.client_hint = None
        return result

    # --- Extraction entités (après filtre dettes) ---
    result.client_hint = extract_client_hint(message)
    result.product_hint = extract_product_hint(message)
    result.period = extract_period(text, default='today')

    # Pronom → dernier client UNIQUEMENT si pas de nouveau nom explicite
    if not result.client_hint and re.search(r'\b(il|elle|lui|celui|celle)\b', text):
        prev = result.last_entities.get('client')
        if _is_valid_client_hint(prev):
            result.client_hint = prev

    # --- Réquisition stock / produits à approvisionner ---
    if any(w in text for w in (
        'requisition', 'bon d entree', 'bon d entree',
        'produits que je peux approvisionner', 'articles que je peux approvisionner',
        'que je peux approvisionner', 'quoi approvisionner', 'a commander',
        'a reapprovisionner', 'a reapprovisionner', 'besoin d approvisionnement',
        'produits a commander', 'articles a commander',
    )) or (
        'fais' in text and 'stock' in text and any(w in text for w in ('statut', 'rupture', 'alerte'))
    ) or (
        'approvisionner' in text and any(w in text for w in ('produit', 'article', 'requisition', 'stock'))
    ):
        result.intent = 'stock_requisition_pdf'
        return result

    # --- PDF / facture client ---
    if result.wants_pdf or 'facture' in text or 'recu' in text:
        if result.client_hint or re.search(r'facture.{0,40}(?:pour|de)\s+[a-z0-9]', text):
            if not result.client_hint:
                # re-try pour "facture ... pour Name"
                m = re.search(r'(?:facture|recu).{0,30}(?:pour|de)\s+([a-z0-9][a-z0-9\-]{2,40})', text)
                if m and _is_valid_client_hint(m.group(1)):
                    result.client_hint = m.group(1)
            if result.client_hint:
                result.intent = 'client_invoice_pdf'
                # période : si pas précisée → all_time pour facture
                if result.period == 'today' and 'aujourd' not in text:
                    result.period = 'all_time'
                return result
        if 'dettes' in text and ('tous' in text or 'clients' in text):
            result.intent = 'debt_clients_pdf'
            return result
        if 'fiche de stock' in text or (result.product_hint and 'stock' in text):
            result.intent = 'stock_sheet_pdf'
            return result

    # --- Abonnements ---
    if any(w in text for w in ('autres abonnements', 'autres plans', 'formules', 'plans disponibles')):
        result.intent = 'subscription_plans_list'
        return result
    if any(w in text for w in ('abonnement', 'licence', 'mon plan', 'jours restants')):
        result.intent = 'abonnement'
        return result

    # --- Approvisionnements ---
    if any(w in text for w in (
        'approvisionn', 'entrees d', 'entree stock', 'entrees de stock',
        'produits entres', 'achat fournisseur',
    )):
        if 'aujourd' in text or 'du jour' in text:
            result.intent = 'approvisionnement_today'
            result.period = 'today'
        else:
            result.intent = 'approvisionnement_list'
        return result

    # --- Expiration ---
    if is_expiration_question(message) or 'expire' in text:
        if '3 mois' in text or 'trois mois' in text or result.period == 'days_90':
            result.intent = 'stock_expiration_90_days'
            result.period = 'days_90'
        else:
            result.intent = 'stock_expiration_30_days'
            result.period = 'days_30'
        return result

    # --- Top produits (défaut = all_time) ---
    if any(w in text for w in (
        'plus vendu', 'top ', 'meilleures ventes', 'produits populaires',
        'produit le plus', 'articles les plus vendus', 'articles plus vendus',
    )):
        result.intent = 'top_selling_products'
        if 'aujourd' in text or 'du jour' in text:
            result.period = 'today'
        elif 'semaine' in text:
            result.period = 'week'
        elif 'mois' in text:
            result.period = 'month'
        else:
            result.period = 'all_time'
        result.last_entities['limit'] = result.top_n
        result.last_entities['period'] = result.period
        return result

    # --- Ventes crédit ---
    if any(w in text for w in ('credit', 'a credit', 'en credit')) and any(
        w in text for w in ('vend', 'vente', 'aujourd', 'jour')
    ):
        result.intent = 'credit_sales_today'
        result.period = 'today'
        return result

    # --- Client nommé ---
    if result.client_hint:
        if any(w in text for w in ('achete', 'achat', 'vendu', 'facture', 'recu')):
            result.intent = 'client_purchase_history'
            if 'aujourd' not in text and result.period == 'today':
                result.period = 'all_time'
            return result
        if any(w in text for w in ('dette', 'doit', 'impaye', 'solde')):
            result.intent = 'client_debt_detail'
            return result
        if any(w in text for w in ('parmi', 'fait partie', 'est client')):
            result.intent = 'client_search'
            return result
        if any(w in text for w in ('situation', 'fiche', 'etat', 'historique', 'voir')):
            result.intent = 'client_situation'
            return result
        # nom seul dans une phrase type "situation blessing" déjà couvert
        result.intent = 'client_situation'
        return result

    if re.search(r'\b(il|elle)\b.{0,40}(client|systeme|uhakika)', text):
        if result.last_entities.get('client'):
            result.client_hint = result.last_entities['client']
            result.intent = 'client_search'
            return result

    # --- Clients génériques ---
    if any(w in text for w in (
        'nos clients', 'mes clients', 'liste des clients', 'quels sont nos client',
        'quels sont mes client',
    )):
        result.intent = 'client_list'
        return result
    if any(w in text for w in ('combien de clients', 'nombre de clients', 'j ai combien de clients')):
        result.intent = 'client_count'
        return result

    # --- Stock ---
    if 'rupture' in text:
        result.intent = 'stock_rupture_list'
        return result
    if 'alerte' in text or ('seuil' in text and 'stock' in text):
        result.intent = 'stock_alert_list'
        return result
    if any(w in text for w in ('combien d article', 'combien darticles', 'nombre d article', 'j ai combien d article')):
        result.intent = 'stock_article_count'
        return result
    if result.product_hint and 'stock' in text:
        result.intent = 'stock_article_detail'
        return result
    if any(w in text for w in ('stock', 'inventaire', 'consulter le stock', 'etat du stock', 'statuts de stock')):
        result.intent = 'stock_summary'
        return result

    # --- Ventes ---
    if any(w in text for w in ('vente', 'vendu', 'chiffre d affaires', 'ca du jour')):
        result.intent = 'vente_today_summary'
        return result

    # --- Caisse ---
    if any(w in text for w in ('caisse', 'encaisse', 'solde usd', 'mouvement caisse')):
        result.intent = 'caisse_balance'
        return result

    if any(w in text for w in ('comment ', 'aide', 'tutoriel', 'comment creer')):
        result.intent = 'aide'
        return result

    if any(w in text for w in ('superadmin', 'plateforme', 'entreprises inscrites')):
        result.intent = 'platform'
        return result

    # Ne PAS classer les suivis orphelin comme petite conversation métier
    if _matches_any(text, PERIOD_FOLLOWUP_PATTERNS):
        result.intent = 'petite_conversation'
        result.preface = (
            'D’accord 😊 précisez ce que vous voulez en période générale '
            '(ventes, top produits, clients…).'
        )
        return result

    if _is_short_message(text, max_words=4):
        result.intent = 'petite_conversation'
        return result

    result.intent = 'hors_sujet'
    return result
