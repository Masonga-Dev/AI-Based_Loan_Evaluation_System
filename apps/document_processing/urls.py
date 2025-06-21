from django.urls import path
from . import views

app_name = 'document_processing'

urlpatterns = [
    path('', views.DocumentListView.as_view(), name='list'),
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='detail'),
    path('<int:pk>/process-ocr/', views.process_document_ocr_view, name='process_ocr'),
    path('<int:pk>/validate/', views.validate_document, name='validate'),
    path('upload/<uuid:application_id>/', views.upload_document, name='upload'),
]
