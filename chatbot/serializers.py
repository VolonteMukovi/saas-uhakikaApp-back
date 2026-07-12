from rest_framework import serializers


class ChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'model'])
    content = serializers.CharField(max_length=1000)


class ChatAskSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    history = ChatHistoryItemSerializer(many=True, required=False, max_length=6)

    def validate_history(self, value):
        if value and len(value) > 6:
            raise serializers.ValidationError('Maximum 6 messages d’historique.')
        return value
