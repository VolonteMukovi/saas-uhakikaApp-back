from django.urls import path

from chatbot.views import ChatbotAskView

urlpatterns = [
    path('chatbot/ask/', ChatbotAskView.as_view(), name='chatbot-ask'),
]
