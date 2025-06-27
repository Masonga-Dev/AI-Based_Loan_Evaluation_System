"""
Enhanced OCR Service with real-time validation and comparison features
"""
import logging
from datetime import datetime
from django.utils import timezone
from django.db import transaction

from .models import OCRResult, DocumentVerification, OCRComparison
from .ocr_utils import OCRProcessor
from apps.admin_dashboard.models import AdminNotification

logger = logging.getLogger(__name__)


class EnhancedOCRService:
    """
    Service class for enhanced OCR processing with validation and comparison
    """
    
    def __init__(self):
        self.ocr_processor = OCRProcessor()
        self.confidence_threshold = 70  # Minimum confidence for auto-approval
        self.match_threshold = 80  # Minimum match percentage for auto-approval
    
    def process_document_with_validation(self, document):
        """
        Process document with OCR and perform real-time validation
        """
        try:
            with transaction.atomic():
                # Process OCR
                ocr_result = self.ocr_processor.process_document(document)
                
                # Perform quality assessment
                quality_score = self.assess_document_quality(document, ocr_result)
                
                # Create verification record
                verification = self.create_verification_record(document, ocr_result, quality_score)
                
                # Check if manual review is required
                if self.requires_manual_review(ocr_result, verification):
                    self.create_review_notification(document, ocr_result)
                
                # Update document processing status
                document.is_processed = True
                document.processing_status = 'completed'
                document.processed_at = timezone.now()
                document.save()
                
                return {
                    'success': True,
                    'ocr_result': ocr_result,
                    'verification': verification,
                    'requires_review': self.requires_manual_review(ocr_result, verification)
                }
                
        except Exception as e:
            logger.error(f"Enhanced OCR processing failed for document {document.id}: {str(e)}")
            
            # Update document status to failed
            document.processing_status = 'failed'
            document.save()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def assess_document_quality(self, document, ocr_result):
        """
        Assess the quality of the document and OCR results
        """
        quality_factors = []
        
        # OCR confidence score
        if ocr_result.confidence_score:
            quality_factors.append(float(ocr_result.confidence_score))
        
        # Text length (longer text usually indicates better extraction)
        text_length_score = min(len(ocr_result.raw_text) / 500 * 100, 100) if ocr_result.raw_text else 0
        quality_factors.append(text_length_score)
        
        # Structured data extraction success
        structured_data_score = len(ocr_result.extracted_data) * 20 if ocr_result.extracted_data else 0
        quality_factors.append(min(structured_data_score, 100))
        
        # Calculate overall quality score
        overall_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0
        
        return round(overall_score, 2)
    
    def create_verification_record(self, document, ocr_result, quality_score):
        """
        Create document verification record with initial assessment
        """
        # Determine initial verification status
        if quality_score >= 90 and ocr_result.confidence_score and ocr_result.confidence_score >= 85:
            status = 'verified'
        elif quality_score >= 70 and ocr_result.confidence_score and ocr_result.confidence_score >= 70:
            status = 'pending'
        else:
            status = 'needs_correction'
        
        # Check for OCR comparison results
        ocr_manual_match = None
        if hasattr(ocr_result, 'comparison'):
            comparison = ocr_result.comparison
            ocr_manual_match = comparison.match_percentage >= self.match_threshold
        
        verification = DocumentVerification.objects.create(
            document=document,
            status=status,
            ocr_manual_match=ocr_manual_match,
            image_quality_score=quality_score,
            readability_score=ocr_result.confidence_score
        )
        
        return verification
    
    def requires_manual_review(self, ocr_result, verification):
        """
        Determine if document requires manual review
        """
        # Low confidence score
        if ocr_result.confidence_score and ocr_result.confidence_score < self.confidence_threshold:
            return True
        
        # Poor quality assessment
        if verification.image_quality_score < 60:
            return True
        
        # OCR-manual data mismatch
        if verification.ocr_manual_match is False:
            return True
        
        # Verification status indicates issues
        if verification.status in ['needs_correction', 'flagged']:
            return True
        
        # Check comparison results if available
        if hasattr(ocr_result, 'comparison'):
            comparison = ocr_result.comparison
            if comparison.requires_admin_review:
                return True
        
        return False
    
    def create_review_notification(self, document, ocr_result):
        """
        Create notification for admin review
        """
        # Determine notification priority
        priority = 'high'
        if ocr_result.confidence_score and ocr_result.confidence_score < 50:
            priority = 'urgent'
        elif ocr_result.confidence_score and ocr_result.confidence_score >= 60:
            priority = 'medium'
        
        # Create notification for admin users
        from apps.authentication.models import User
        admin_users = User.objects.filter(role__in=['admin', 'manager', 'officer'])
        
        for admin_user in admin_users:
            AdminNotification.objects.create(
                recipient=admin_user,
                notification_type='manual_review_required',
                priority=priority,
                title='Document Requires Manual Review',
                message=f'Document "{document.document_name}" from application {document.application.application_number} requires manual review due to quality or accuracy concerns.',
                related_document=document,
                related_application=document.application,
                action_required=True,
                link_url=f'/admin-dashboard/ocr-data/?document_id={document.id}'
            )
    
    def bulk_process_documents(self, documents):
        """
        Process multiple documents in bulk
        """
        results = []
        
        for document in documents:
            try:
                result = self.process_document_with_validation(document)
                results.append({
                    'document_id': document.id,
                    'document_name': document.document_name,
                    'success': result['success'],
                    'requires_review': result.get('requires_review', False),
                    'error': result.get('error')
                })
            except Exception as e:
                results.append({
                    'document_id': document.id,
                    'document_name': document.document_name,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def reprocess_document(self, document):
        """
        Reprocess a document (useful for failed or low-quality extractions)
        """
        # Delete existing OCR results
        try:
            if hasattr(document, 'ocr_result'):
                document.ocr_result.delete()
        except:
            pass
        
        try:
            if hasattr(document, 'verification'):
                document.verification.delete()
        except:
            pass
        
        # Reset document status
        document.is_processed = False
        document.processing_status = 'pending'
        document.processed_at = None
        document.save()
        
        # Process again
        return self.process_document_with_validation(document)
