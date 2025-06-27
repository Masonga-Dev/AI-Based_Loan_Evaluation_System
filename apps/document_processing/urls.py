from django.urls import path
from . import views

app_name = 'document_processing'

urlpatterns = [
    # Document management
    path('', views.DocumentListView.as_view(), name='list'),
    path('<int:pk>/', views.DocumentDetailView.as_view(), name='detail'),
    path('upload/<uuid:application_id>/', views.upload_document, name='upload'),

    # OCR processing
    path('<int:pk>/process-ocr/', views.process_document_ocr_view, name='process_ocr'),
    path('<int:document_id>/reprocess-ocr/', views.reprocess_document_ocr, name='reprocess_ocr'),
    path('bulk-process/', views.bulk_process_documents, name='bulk_process_documents'),

    # OCR comparison and verification
    path('<int:document_id>/ocr-comparison/', views.ocr_comparison_view, name='ocr_comparison'),
    path('<int:document_id>/verification-status/', views.document_verification_status, name='verification_status'),

    # Document validation
    path('<int:pk>/validate/', views.validate_document, name='validate'),
]
