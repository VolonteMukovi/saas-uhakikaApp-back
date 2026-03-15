from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RapportsViewSet

router = DefaultRouter()
router.register(r'rapports', RapportsViewSet, basename='rapports')

urlpatterns = [
    path('', include(router.urls)),
]
