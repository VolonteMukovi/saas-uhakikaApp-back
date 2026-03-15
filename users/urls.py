from rest_framework import routers
from django.urls import path, include
from .views import UserViewSet, CustomTokenObtainPairView

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='custom_token_obtain_pair'),
    path('', include(router.urls)),
]