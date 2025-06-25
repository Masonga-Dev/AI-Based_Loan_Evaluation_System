from django.shortcuts import render, redirect
from django.views import View
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from apps.dashboard.utils import create_notification
from apps.loan_application.models import LoanApplication, ApplicationDocument
from .forms import LoanApplicationForm

class ApplicationListView(View):
    def get(self, request):
        return HttpResponse('Application List View')

@login_required
def apply_for_loan(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save LoanApplication (core fields)
            loan_app = form.save(commit=False)
            loan_app.applicant = request.user
            loan_app.status = 'submitted'
            loan_app.save()

            # Save uploaded documents
            ApplicationDocument.objects.create(
                application=loan_app,
                document_type='identity',
                document_name=form.cleaned_data['national_id_upload'].name,
                document_file=form.cleaned_data['national_id_upload'],
                file_size=form.cleaned_data['national_id_upload'].size,
                mime_type=form.cleaned_data['national_id_upload'].content_type
            )
            ApplicationDocument.objects.create(
                application=loan_app,
                document_type='income_proof',
                document_name=form.cleaned_data['payslip_upload'].name,
                document_file=form.cleaned_data['payslip_upload'],
                file_size=form.cleaned_data['payslip_upload'].size,
                mime_type=form.cleaned_data['payslip_upload'].content_type
            )
            ApplicationDocument.objects.create(
                application=loan_app,
                document_type='bank_statement',
                document_name=form.cleaned_data['bank_statement_upload'].name,
                document_file=form.cleaned_data['bank_statement_upload'],
                file_size=form.cleaned_data['bank_statement_upload'].size,
                mime_type=form.cleaned_data['bank_statement_upload'].content_type
            )
            if form.cleaned_data.get('business_license_upload'):
                ApplicationDocument.objects.create(
                    application=loan_app,
                    document_type='business_license',
                    document_name=form.cleaned_data['business_license_upload'].name,
                    document_file=form.cleaned_data['business_license_upload'],
                    file_size=form.cleaned_data['business_license_upload'].size,
                    mime_type=form.cleaned_data['business_license_upload'].content_type
                )
            # Save up to two additional documents
            for i in range(1, 3):
                doc_field = f'additional_document_{i}'
                file = form.cleaned_data.get(doc_field)
                if file:
                    ApplicationDocument.objects.create(
                        application=loan_app,
                        document_type='other',
                        document_name=file.name,
                        document_file=file,
                        file_size=file.size,
                        mime_type=file.content_type
                    )
            messages.success(request, 'Loan application submitted successfully!')
            return redirect('dashboard:applicant_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoanApplicationForm()
    return render(request, 'loan_application/apply_for_loan.html', {'form': form})

@login_required
def my_applications(request):
    loan_applications = LoanApplication.objects.filter(applicant=request.user)
    return render(request, 'loan_application/my_applications.html', {'loan_applications': loan_applications})

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
    # Simulate approval logic
    application = LoanApplication.objects.get(pk=pk)
    application.status = 'approved'
    application.save()
    create_notification(
        application.applicant,
        f'Your loan application {application.application_number} has been approved.',
        link=f'/loan_application/{application.pk}/detail/'
    )
    return HttpResponse(f'Approve Application {pk}')

def reject_application(request, pk):
    # Simulate rejection logic
    application = LoanApplication.objects.get(pk=pk)
    application.status = 'rejected'
    application.save()
    create_notification(
        application.applicant,
        f'Your loan application {application.application_number} has been rejected.',
        link=f'/loan_application/{application.pk}/detail/'
    )
    return HttpResponse(f'Reject Application {pk}')

def upload_document(request, pk):
    return HttpResponse(f'Upload Document for Application {pk}')
