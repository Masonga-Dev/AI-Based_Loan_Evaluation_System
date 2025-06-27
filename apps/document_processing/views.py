from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.conf import settings
import os
import json
import time
from datetime import datetime, timedelta

from .models import OCRResult, ExtractedField, DocumentValidation, DocumentTemplate
from .ocr_utils import OCRProcessor
from .document_validators import DocumentValidator
from apps.loan_application.models import ApplicationDocument
from apps.dashboard.utils import create_notification


class DocumentListView(LoginRequiredMixin, ListView):
    """
    List view for user's documents
    """
    model = ApplicationDocument
    template_name = 'document_processing/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.role == 'applicant':
            return ApplicationDocument.objects.filter(
                application__applicant=self.request.user
            ).order_by('-uploaded_at')
        else:
            return ApplicationDocument.objects.all().order_by('-uploaded_at')


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for a specific document
    """
    model = ApplicationDocument
    template_name = 'document_processing/document_detail.html'
    context_object_name = 'document'

    def get_object(self):
        document = get_object_or_404(ApplicationDocument, pk=self.kwargs['pk'])

        # Check permissions
        if (self.request.user.role == 'applicant' and
            document.application.applicant != self.request.user):
            raise PermissionError("You don't have permission to view this document.")

        return document

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()

        # Get OCR results if available
        try:
            context['ocr_result'] = document.ocr_result
            context['extracted_fields'] = document.ocr_result.fields.all()
        except OCRResult.DoesNotExist:
            context['ocr_result'] = None
            context['extracted_fields'] = []

        # Get validation results if available
        try:
            context['validation'] = document.validation
        except DocumentValidation.DoesNotExist:
            context['validation'] = None

        return context


@login_required
def upload_document(request, application_id):
    """
    Handle document upload for a loan application
    """
    from apps.loan_application.models import LoanApplication

    application = get_object_or_404(LoanApplication, pk=application_id)

    # Check permissions
    if (request.user.role == 'applicant' and
        application.applicant != request.user):
        messages.error(request, "You don't have permission to upload documents for this application.")
        return redirect('loan_application:detail', pk=application_id)

    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        uploaded_file = request.FILES.get('document_file')

        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
            # Notify applicant of failed upload
            create_notification(
                application.applicant,
                f'Failed to upload document for application {application.application_number}: No file selected.',
                link=f'/loan_application/{application.pk}/detail/'
            )
            return redirect('loan_application:detail', pk=application_id)

        # Validate file
        if not validate_uploaded_file(uploaded_file):
            messages.error(request, 'Invalid file type or size. Please upload PDF, JPG, or PNG files under 10MB.')
            # Notify applicant of invalid file
            create_notification(
                application.applicant,
                f'Failed to upload document for application {application.application_number}: Invalid file type or size.',
                link=f'/loan_application/{application.pk}/detail/'
            )
            return redirect('loan_application:detail', pk=application_id)

        # Create document record
        document = ApplicationDocument.objects.create(
            application=application,
            document_type=document_type,
            document_name=uploaded_file.name,
            document_file=uploaded_file,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type
        )

        # Start enhanced OCR processing
        from .ocr_service import EnhancedOCRService
        ocr_service = EnhancedOCRService()

        try:
            # Process with enhanced validation
            result = ocr_service.process_document_with_validation(document)

            if result['success']:
                if result['requires_review']:
                    messages.warning(request, f'Document "{uploaded_file.name}" uploaded and processed, but requires manual review.')
                else:
                    messages.success(request, f'Document "{uploaded_file.name}" uploaded and processed successfully.')
            else:
                messages.error(request, f'Document uploaded but OCR processing failed: {result.get("error", "Unknown error")}')
        except Exception as e:
            # Fallback to basic OCR processing
            process_document_ocr.delay(document.id)
            messages.success(request, f'Document "{uploaded_file.name}" uploaded successfully. OCR processing started.')

        messages.success(request, f'Document "{uploaded_file.name}" uploaded successfully. OCR processing started.')
        return redirect('loan_application:detail', pk=application_id)

    return redirect('loan_application:detail', pk=application_id)


@csrf_exempt
def process_document_ocr_view(request, document_id):
    """
    Process OCR for a specific document
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    document = get_object_or_404(ApplicationDocument, pk=document_id)

    try:
        # Initialize OCR processor
        ocr_processor = OCRProcessor()

        # Process the document
        result = ocr_processor.process_document(document)

        return JsonResponse({
            'success': True,
            'message': 'OCR processing completed successfully',
            'result': {
                'confidence_score': float(result.confidence_score) if result.confidence_score else 0,
                'extracted_fields_count': result.fields.count(),
                'status': result.status
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def validate_document(request, document_id):
    """
    Validate a document
    """
    document = get_object_or_404(ApplicationDocument, pk=document_id)

    # Check permissions
    if request.user.role not in ['officer', 'manager', 'admin']:
        messages.error(request, "You don't have permission to validate documents.")
        return redirect('document_processing:detail', pk=document_id)

    try:
        validator = DocumentValidator()
        validation_result = validator.validate_document(document)
        messages.success(request, 'Document validation completed successfully.')
    except Exception as e:
        messages.error(request, f'Document validation failed: {str(e)}')
        # Notify applicant of validation failure
        create_notification(
            document.application.applicant,
            f'Document validation failed for {document.document_name}: {str(e)}',
            link=f'/document_processing/{document.pk}/detail/'
        )
    return redirect('document_processing:detail', pk=document_id)


def validate_uploaded_file(uploaded_file):
    """
    Validate uploaded file type and size
    """
    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if uploaded_file.size > max_size:
        return False

    # Check file type
    allowed_types = [
        'application/pdf',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]

    if uploaded_file.content_type not in allowed_types:
        return False

    return True


# Celery task (would normally be in tasks.py)
def process_document_ocr(document_id):
    """
    Celery task to process OCR for a document
    This is a placeholder - in production, this would be in tasks.py
    """
    try:
        document = ApplicationDocument.objects.get(pk=document_id)
        ocr_processor = OCRProcessor()
        result = ocr_processor.process_document(document)

        # Update document processing status
        document.is_processed = True
        document.processing_status = 'completed'
        document.processed_at = datetime.now()
        document.save()

        return True

    except Exception as e:
        # Update document processing status to failed
        try:
            document = ApplicationDocument.objects.get(pk=document_id)
            document.processing_status = 'failed'
            document.save()
        except:
            pass

        return False


@login_required
def ocr_comparison_view(request, document_id):
    """
    View OCR comparison results with manual data
    """
    document = get_object_or_404(ApplicationDocument, pk=document_id)

    # Check permissions
    if (request.user.role == 'applicant' and
        document.application.applicant != request.user):
        messages.error(request, "You don't have permission to view this document.")
        return redirect('dashboard:home')

    try:
        ocr_result = document.ocr_result
        comparison = getattr(ocr_result, 'comparison', None)
        verification = getattr(document, 'verification', None)
    except:
        ocr_result = None
        comparison = None
        verification = None

    context = {
        'document': document,
        'application': document.application,
        'ocr_result': ocr_result,
        'comparison': comparison,
        'verification': verification,
    }

    return render(request, 'document_processing/ocr_comparison.html', context)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def reprocess_document_ocr(request, document_id):
    """
    Reprocess document OCR (for failed or low-quality extractions)
    """
    if request.user.role not in ['admin', 'manager', 'officer']:
        return JsonResponse({'success': False, 'error': 'Insufficient permissions'})

    document = get_object_or_404(ApplicationDocument, pk=document_id)

    try:
        from .ocr_service import EnhancedOCRService
        ocr_service = EnhancedOCRService()

        result = ocr_service.reprocess_document(document)

        return JsonResponse({
            'success': result['success'],
            'requires_review': result.get('requires_review', False),
            'error': result.get('error'),
            'message': 'Document reprocessed successfully' if result['success'] else 'Reprocessing failed'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def bulk_process_documents(request):
    """
    Bulk process multiple documents with enhanced OCR
    """
    if request.user.role not in ['admin', 'manager', 'officer']:
        return JsonResponse({'success': False, 'error': 'Insufficient permissions'})

    try:
        data = json.loads(request.body)
        document_ids = data.get('document_ids', [])

        if not document_ids:
            return JsonResponse({'success': False, 'error': 'No documents selected'})

        documents = ApplicationDocument.objects.filter(id__in=document_ids)

        from .ocr_service import EnhancedOCRService
        ocr_service = EnhancedOCRService()

        results = ocr_service.bulk_process_documents(documents)

        return JsonResponse({
            'success': True,
            'results': results,
            'processed_count': len(results),
            'success_count': len([r for r in results if r['success']]),
            'review_required_count': len([r for r in results if r.get('requires_review', False)])
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def document_verification_status(request, document_id):
    """
    Get document verification status and details
    """
    document = get_object_or_404(ApplicationDocument, pk=document_id)

    # Check permissions
    if (request.user.role == 'applicant' and
        document.application.applicant != request.user and
        request.user.role not in ['admin', 'manager', 'officer']):
        return JsonResponse({'success': False, 'error': 'Insufficient permissions'})

    try:
        verification = getattr(document, 'verification', None)
        ocr_result = getattr(document, 'ocr_result', None)
        comparison = getattr(ocr_result, 'comparison', None) if ocr_result else None

        data = {
            'document_id': document.id,
            'document_name': document.document_name,
            'processing_status': document.processing_status,
            'is_processed': document.is_processed,
            'verification': {
                'status': verification.status if verification else 'pending',
                'image_quality_score': float(verification.image_quality_score) if verification and verification.image_quality_score else None,
                'readability_score': float(verification.readability_score) if verification and verification.readability_score else None,
                'ocr_manual_match': verification.ocr_manual_match if verification else None,
                'verified_at': verification.verified_at.isoformat() if verification and verification.verified_at else None,
                'verified_by': verification.verified_by.get_full_name() if verification and verification.verified_by else None,
            } if verification else None,
            'ocr_result': {
                'confidence_score': float(ocr_result.confidence_score) if ocr_result and ocr_result.confidence_score else None,
                'status': ocr_result.status if ocr_result else None,
                'extracted_fields_count': len(ocr_result.extracted_data) if ocr_result and ocr_result.extracted_data else 0,
            } if ocr_result else None,
            'comparison': {
                'status': comparison.status if comparison else None,
                'match_percentage': float(comparison.match_percentage) if comparison and comparison.match_percentage else None,
                'requires_review': comparison.requires_admin_review if comparison else None,
            } if comparison else None,
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
