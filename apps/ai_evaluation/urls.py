from django.urls import path
from . import views

app_name = 'ai_evaluation'

urlpatterns = [
    path('models/', views.ModelListView.as_view(), name='model_list'),
    path('models/<int:pk>/', views.ModelDetailView.as_view(), name='model_detail'),
    path('models/<int:pk>/performance/', views.model_performance, name='model_performance'),
    path('models/train/', views.train_model, name='train_model'),
    path('evaluate/<uuid:application_id>/', views.evaluate_application, name='evaluate_application'),
    path('batch-evaluate/', views.batch_evaluate_applications, name='batch_evaluate'),
    path('predictions/', views.prediction_history, name='prediction_history'),
    path('model-management/', views.model_management, name='model_management'),
]
