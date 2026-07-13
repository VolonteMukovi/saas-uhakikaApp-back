"""Classification d'intention par mots-clés (sans ML)."""
from __future__ import annotations

import re
import unicodedata


def _norm(text: str) -> str:
    text = unicodedata.normalize('NFKD', text.lower().strip())
    text = text.replace("'", ' ').replace('’', ' ')
    return ''.join(c for c in text if not unicodedata.combining(c))


def _is_short_message(text: str, max_words: int = 4) -> bool:
    return len(text.split()) <= max_words


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

FORBIDDEN_PATTERNS = [
    r'hack',
    r'pirat',
    r'cracker',
    r'voler\s+un\s+compte',
    r'programme\s+python\s+pour\s+hack',
]

CONTEXT_ENTREPRISE_PATTERNS = [
    r'je\s+suis\s+(dans\s+)?quelle\s+entreprise',
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
    r'^bonjour\b',
    r'^bonsoir\b',
    r'^salut\b',
    r'^hello\b',
    r'^coucou\b',
    r'^bonne\s+(journee|soiree)\b',
]

REMERCIEMENT_PATTERNS = [
    r'^merci\b',
    r'^thanks\b',
    r'^je\s+vous\s+remercie',
    r'^c.est\s+gentil',
]

COMPREHENSION_PATTERNS = [
    r'^(ok|d.accord|dac|dacord)\.?$',
    r'^je\s+(comprends|vois)\.?$',
    r'^(tres\s+bien|très\s+bien|parfait|ca\s+marche|ça\s+marche|c.est\s+bon)\.?$',
    r'^super\.?$',
    r'^genial\.?$',
    r'^génial\.?$',
]

COMPLIMENT_PATTERNS = [
    r'vous\s+etes\s+gentil',
    r'tu\s+es\s+gentil',
    r'vous\s+etes\s+sympa',
    r'bravo',
    r'bien\s+joue',
]

PETITE_CONVERSATION_PATTERNS = [
    r'comment\s+ca\s+va',
    r'comment\s+allez\s+vous',
    r'vous\s+allez\s+bien',
    r'ca\s+va\s*\?',
]

NEGATIVE_COMPLIMENT_PATTERNS = [
    r'pourquoi\s+vous\s+etes\s+mechant',
    r'pourquoi\s+tu\s+es\s+mechant',
    r'vous\s+etes\s+mechant',
    r'tu\s+es\s+mechant',
]

HORS_SUJET_SENSIBLE_KEYWORDS = [
    'president', 'président', 'politique', 'election', 'élection',
    'amour', 'recette de', 'tarte aux', 'meteo', 'météo', 'football match',
]

INTENT_KEYWORDS: dict[str, list[str]] = {
    'platform': [
        'superadmin', 'plateforme', 'toutes les entreprises saas', 'abonnements en attente',
        'licences actives', 'entreprises inscrites',
    ],
    'stock': [
        'stock', 'rupture', 'alerte', 'inventaire', 'expiration', 'expire', 'dlc',
        'approvisionnement', 'entree en stock', 'quantite restante', 'articles en',
    ],
    'caisse': [
        'caisse', 'solde caisse', 'encaisse', 'mouvement caisse', 'session caisse',
        'ouverture caisse', 'cloture caisse',
    ],
    'ventes': [
        'vente', 'vendu', 'chiffre d affaires', 'ca du jour', 'produits les plus vendus',
        'meilleures ventes', 'sorties du jour',
    ],
    'dettes': [
        'dette', 'doit encore', 'impaye', 'solde restant', 'credit client', 'en retard',
        'recouvrement',
    ],
    'clients': [
        'combien de clients', 'nombre de clients', 'j ai combien de clients',
        'jai combien de clients', 'clients enregistres', 'nos clients',
        'mes clients', 'liste des clients', 'quels sont nos clients',
        'quel sont nos clients', 'quels sont mes clients', 'nos client',
    ],
    'rapports': [
        'rapport', 'synthese', 'resume activite', 'resume du jour', 'bilan', 'point a surveiller',
        'activite du jour', 'activite du mois',
    ],
    'abonnement': [
        'abonnement', 'licence', 'formule', 'essai gratuit', 'plan tarifaire',
    ],
    'aide': [
        'comment ', 'comment creer', 'comment enregistrer', 'comment fonctionne',
        'procedure', 'etapes pour', 'tutoriel',
    ],
}


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify_intent(message: str) -> str:
    text = _norm(message)
    if not text:
        return 'hors_sujet'

    for pattern in SECURITY_PATTERNS:
        if re.search(pattern, text):
            return 'security_bypass'

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text):
            return 'question_interdite'

    if _matches_any(text, NEGATIVE_COMPLIMENT_PATTERNS):
        return 'compliment'

    if _matches_any(text, CONTEXT_ENTREPRISE_PATTERNS):
        return 'contexte_utilisateur'

    if _matches_any(text, UHAKIKA_INFO_PATTERNS):
        return 'uhakika_info'

    if _matches_any(text, SALUTATION_PATTERNS) or (
        _is_short_message(text) and text in ('bonjour', 'bonsoir', 'salut', 'hello', 'coucou')
    ):
        return 'salutation'

    if _matches_any(text, REMERCIEMENT_PATTERNS) or text in ('merci', 'thanks'):
        return 'remerciement'

    if _matches_any(text, COMPREHENSION_PATTERNS):
        return 'comprehension'

    if _matches_any(text, COMPLIMENT_PATTERNS):
        return 'compliment'

    if _matches_any(text, PETITE_CONVERSATION_PATTERNS):
        return 'petite_conversation'

    if any(kw in text for kw in HORS_SUJET_SENSIBLE_KEYWORDS):
        return 'hors_sujet_sensible'

    scores: dict[str, int] = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score:
            scores[intent] = score

    if scores:
        if scores.get('dettes', 0) >= scores.get('clients', 0) and 'dettes' in scores:
            return 'dettes'
        if 'clients' in scores and any(w in text for w in ('client', 'clients')):
            if 'dette' not in text and 'doit' not in text:
                return 'clients'
        if 'rapports' in scores and scores['rapports'] >= 2:
            return 'rapports'
        if 'platform' in scores:
            return 'platform'
        return max(scores, key=scores.get)

    if 'client' in text and not any(w in text for w in ('dette', 'doit', 'impaye')):
        return 'clients'

    if any(w in text for w in ('uhakika', 'comment', 'aide')):
        return 'aide'

    if _is_short_message(text, max_words=6):
        return 'petite_conversation'

    return 'hors_sujet'


def extract_client_hint(message: str) -> str | None:
    text = message.strip()
    patterns = [
        r'client\s+([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 \-\']{1,60})',
        r'(?:doit|doivent)\s+(?:le|la)?\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \-\']{1,60})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            hint = m.group(1).strip(' ?.,!')
            if hint.lower() not in ('encore', 'combien', 'quel', 'quelle'):
                return hint
    return None


def extract_product_hint(message: str) -> str | None:
    patterns = [
        r'produit\s+([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 \-\']{1,60})',
        r'article\s+([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 \-\']{1,60})',
        r'stock\s+(?:du|de|d)\s+([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 \-\']{1,60})',
    ]
    for pat in patterns:
        m = re.search(pat, message, re.IGNORECASE)
        if m:
            return m.group(1).strip(' ?.,!')
    return None


def is_expiration_question(message: str) -> bool:
    text = _norm(message)
    return any(w in text for w in ('expir', 'dlc', 'perime', 'périmé', 'proche de l expiration'))
