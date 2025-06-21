from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

router = DefaultRouter()
# Add API viewsets here when implemented

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.health_check, name='health_check'),
    path('applications/', views.ApplicationAPIView.as_view(), name='applications'),
    path('predictions/', views.PredictionAPIView.as_view(), name='predictions'),
]
