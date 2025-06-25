from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('loan-applications/', views.loan_applications, name='loan_applications'),
    path('uploaded-documents/', views.uploaded_documents, name='uploaded_documents'),
    path('ocr-data/', views.ocr_data, name='ocr_data'),
    path('ai-predictions/', views.ai_predictions, name='ai_predictions'),
    path('approve-reject/', views.approve_reject, name='approve_reject'),
    path('flag-documents/', views.flag_documents, name='flag_documents'),
]
