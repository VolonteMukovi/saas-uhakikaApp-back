from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatbot.serializers import ChatAskSerializer
from chatbot.services.chatbot_service import ChatbotError, ask_chatbot
from config.http.problem_details import problem_response


class ChatbotAskView(APIView):
    """
    POST /api/chatbot/ask/

    Assistant métier UHAKIKAAPP : contexte JWT, permissions, données filtrées, Gemini.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChatAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = ask_chatbot(
                request=request,
                message=serializer.validated_data['message'],
                history=serializer.validated_data.get('history'),
                selected_entity=serializer.validated_data.get('selected_entity'),
                conversation_context=serializer.validated_data.get('conversation_context'),
            )
        except ChatbotError as exc:
            return problem_response(
                request=request,
                status_code=exc.status_code,
                title=exc.title,
                detail=exc.detail,
                type_uri='urn:uhakika:problem:chatbot-error',
            )

        return Response(payload)
