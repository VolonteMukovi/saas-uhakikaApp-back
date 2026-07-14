from rest_framework import serializers

HISTORY_MAX_ITEMS = 6
HISTORY_CONTENT_MAX = 1000


class ChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'model', 'assistant'])
    content = serializers.CharField(required=True, allow_blank=True)

    def validate_role(self, value):
        if value == 'assistant':
            return 'model'
        return value

    def validate_content(self, value):
        text = (value or '').strip()
        if len(text) > HISTORY_CONTENT_MAX:
            text = text[: HISTORY_CONTENT_MAX - 1] + '…'
        return text


class ChatAskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    history = ChatHistoryItemSerializer(many=True, required=False)
    selected_entity = serializers.DictField(required=False, allow_null=True)
    # Contexte structuré frontend (évite de renvoyer tout l'historique)
    conversation_context = serializers.DictField(required=False, allow_null=True)

    def validate_history(self, value):
        if not value:
            return []
        cleaned = []
        for item in value[-HISTORY_MAX_ITEMS:]:
            content = (item.get('content') or '').strip()
            if not content:
                continue
            if 'ErrorDetail' in content or ('max_length' in content and 'history' in content):
                continue
            cleaned.append(item)
        return cleaned[-HISTORY_MAX_ITEMS:]

    def validate_message(self, value):
        return (value or '').strip()

    def validate_conversation_context(self, value):
        if not value:
            return {}
        # Garder seulement les clés utiles
        last_entities = value.get('last_entities') or {}
        return {
            'last_intent': value.get('last_intent'),
            'last_domain': value.get('last_domain'),
            'last_entities': {
                k: last_entities.get(k)
                for k in ('client', 'article', 'period', 'limit', 'intent')
                if last_entities.get(k) is not None
            },
        }
