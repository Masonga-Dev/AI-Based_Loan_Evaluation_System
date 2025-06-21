from django.urls import path
from . import views

app_name = 'loan_application'

urlpatterns = [
    path('', views.ApplicationListView.as_view(), name='list'),
    path('apply/', views.apply_for_loan, name='apply'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('review/', views.review_applications, name='review_applications'),
    path('<uuid:pk>/', views.ApplicationDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.edit_application, name='edit'),
    path('<uuid:pk>/submit/', views.submit_application, name='submit'),
    path('<uuid:pk>/approve/', views.approve_application, name='approve'),
    path('<uuid:pk>/reject/', views.reject_application, name='reject'),
    path('<uuid:pk>/upload-document/', views.upload_document, name='upload_document'),
]
