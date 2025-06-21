from django.shortcuts import render
from django.views import View
from django.http import HttpResponse

class ApplicationListView(View):
    def get(self, request):
        return HttpResponse('Application List View')

def apply_for_loan(request):
    return HttpResponse('Apply for Loan')

def my_applications(request):
    return HttpResponse('My Applications')

def review_applications(request):
    return HttpResponse('Review Applications')

class ApplicationDetailView(View):
    def get(self, request, pk):
        return HttpResponse(f'Application Detail View for {pk}')

def edit_application(request, pk):
    return HttpResponse(f'Edit Application {pk}')

def submit_application(request, pk):
    return HttpResponse(f'Submit Application {pk}')

def approve_application(request, pk):
    return HttpResponse(f'Approve Application {pk}')

def reject_application(request, pk):
    return HttpResponse(f'Reject Application {pk}')

def upload_document(request, pk):
    return HttpResponse(f'Upload Document for Application {pk}')
