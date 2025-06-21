"""
Document Validation Utilities
This module handles document validation and authenticity checks
"""

import re
import os
import magic
from datetime import datetime, timedelta
from django.core.files.storage import default_storage
from .models import DocumentValidation, DocumentTemplate
import logging

logger = logging.getLogger(__name__)


class DocumentValidator:
    """
    Main document validation class
    """
    
    def __init__(self):
        self.validation_rules = {
            'identity': self.validate_identity_document,
            'income_proof': self.validate_income_document,
            'bank_statement': self.validate_bank_statement,
            'employment_letter': self.validate_employment_letter,
            'tax_return': self.validate_tax_return,
            'property_document': self.validate_property_document,
        }
    
    def validate_document(self, document):
        """
        Main validation method for documents
        """
        try:
            # Create or get validation record
            validation, created = DocumentValidation.objects.get_or_create(
                document=document,
                defaults={'status': 'pending'}
            )
            
            validation.status = 'pending'
            validation.validation_errors = []
            validation.validation_warnings = []
            validation.save()
            
            # Perform basic file validation
            format_valid = self.validate_file_format(document)
            validation.format_valid = format_valid
            
            # Perform content validation
            content_valid = self.validate_content(document)
            validation.content_valid = content_valid
            
            # Calculate authenticity score
            authenticity_score = self.calculate_authenticity_score(document)
            validation.authenticity_score = authenticity_score
            
            # Calculate overall validation score
            validation_score = self.calculate_validation_score(
                format_valid, content_valid, authenticity_score
            )
            validation.validation_score = validation_score
            
            # Determine final status
            if validation_score >= 80:
                validation.status = 'valid'
            elif validation_score >= 60:
                validation.status = 'needs_review'
            else:
                validation.status = 'invalid'
            
            validation.validated_at = datetime.now()
            validation.save()
            
            logger.info(f"Document validation completed for document {document.id}")
            return validation
            
        except Exception as e:
            logger.error(f"Document validation failed for document {document.id}: {str(e)}")
            
            if 'validation' in locals():
                validation.status = 'invalid'
                validation.validation_errors.append(f"Validation error: {str(e)}")
                validation.save()
            
            raise e
    
    def validate_file_format(self, document):
        """
        Validate file format and basic properties
        """
        try:
            file_path = document.document_file.path
            
            # Check if file exists
            if not os.path.exists(file_path):
                return False
            
            # Check file size (not empty, not too large)
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return False
            
            # Check MIME type using python-magic
            try:
                mime_type = magic.from_file(file_path, mime=True)
                allowed_types = [
                    'application/pdf',
                    'image/jpeg',
                    'image/png',
                    'image/tiff',
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                ]
                
                if mime_type not in allowed_types:
                    return False
                    
            except Exception as e:
                logger.warning(f"MIME type check failed: {str(e)}")
                # Fall back to file extension check
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.doc', '.docx']
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension not in allowed_extensions:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"File format validation failed: {str(e)}")
            return False
    
    def validate_content(self, document):
        """
        Validate document content based on type
        """
        try:
            document_type = document.document_type
            
            if document_type in self.validation_rules:
                return self.validation_rules[document_type](document)
            else:
                # Generic content validation
                return self.validate_generic_content(document)
                
        except Exception as e:
            logger.error(f"Content validation failed: {str(e)}")
            return False
    
    def validate_identity_document(self, document):
        """
        Validate identity documents
        """
        try:
            # Get OCR result if available
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                extracted_data = ocr_result.extracted_data
                
                # Check for required fields
                required_fields = ['name', 'date_of_birth', 'id_number']
                missing_fields = []
                
                for field in required_fields:
                    if field not in extracted_data or not extracted_data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    logger.warning(f"Missing required fields in identity document: {missing_fields}")
                    return False
                
                # Validate date of birth format
                if 'date_of_birth' in extracted_data:
                    dob = extracted_data['date_of_birth']
                    if not self.validate_date_format(dob):
                        logger.warning(f"Invalid date of birth format: {dob}")
                        return False
                
                return True
            
            return True  # If no OCR result, assume valid for now
            
        except Exception as e:
            logger.error(f"Identity document validation failed: {str(e)}")
            return False
    
    def validate_income_document(self, document):
        """
        Validate income documents
        """
        try:
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                extracted_data = ocr_result.extracted_data
                
                # Check for income amount
                if 'income_amount' not in extracted_data:
                    logger.warning("No income amount found in income document")
                    return False
                
                # Validate income amount is reasonable
                try:
                    income = float(extracted_data['income_amount'].replace(',', ''))
                    if income <= 0 or income > 10000000:  # Reasonable range
                        logger.warning(f"Income amount out of reasonable range: {income}")
                        return False
                except ValueError:
                    logger.warning(f"Invalid income amount format: {extracted_data['income_amount']}")
                    return False
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Income document validation failed: {str(e)}")
            return False
    
    def validate_bank_statement(self, document):
        """
        Validate bank statements
        """
        try:
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                extracted_data = ocr_result.extracted_data
                
                # Check for account number
                if 'account_number' not in extracted_data:
                    logger.warning("No account number found in bank statement")
                    return False
                
                # Check for balance
                if 'balance' in extracted_data:
                    try:
                        balance = float(extracted_data['balance'].replace(',', ''))
                        # Balance can be negative, so just check it's a valid number
                    except ValueError:
                        logger.warning(f"Invalid balance format: {extracted_data['balance']}")
                        return False
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Bank statement validation failed: {str(e)}")
            return False
    
    def validate_employment_letter(self, document):
        """
        Validate employment letters
        """
        try:
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                extracted_data = ocr_result.extracted_data
                
                # Check for job title
                if 'job_title' not in extracted_data:
                    logger.warning("No job title found in employment letter")
                    return False
                
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Employment letter validation failed: {str(e)}")
            return False
    
    def validate_tax_return(self, document):
        """
        Validate tax returns
        """
        try:
            # Basic validation for tax returns
            # In production, this would include more sophisticated checks
            return True
            
        except Exception as e:
            logger.error(f"Tax return validation failed: {str(e)}")
            return False
    
    def validate_property_document(self, document):
        """
        Validate property documents
        """
        try:
            # Basic validation for property documents
            # In production, this would include more sophisticated checks
            return True
            
        except Exception as e:
            logger.error(f"Property document validation failed: {str(e)}")
            return False
    
    def validate_generic_content(self, document):
        """
        Generic content validation
        """
        try:
            # Check if document has any readable text
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                if not ocr_result.raw_text or len(ocr_result.raw_text.strip()) < 10:
                    logger.warning("Document contains insufficient readable text")
                    return False
                
                # Check OCR confidence
                if ocr_result.confidence_score and ocr_result.confidence_score < 50:
                    logger.warning(f"Low OCR confidence: {ocr_result.confidence_score}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Generic content validation failed: {str(e)}")
            return False
    
    def calculate_authenticity_score(self, document):
        """
        Calculate document authenticity score
        """
        try:
            score = 100.0
            
            # Check OCR confidence
            if hasattr(document, 'ocr_result'):
                ocr_result = document.ocr_result
                if ocr_result.confidence_score:
                    # Lower confidence reduces authenticity score
                    if ocr_result.confidence_score < 70:
                        score -= (70 - ocr_result.confidence_score) * 0.5
            
            # Check file properties
            file_size = document.file_size
            if file_size < 1024:  # Very small files are suspicious
                score -= 20
            
            # Check document age (very recent uploads might be suspicious)
            upload_time = document.uploaded_at
            if upload_time and (datetime.now() - upload_time.replace(tzinfo=None)).total_seconds() < 60:
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Authenticity score calculation failed: {str(e)}")
            return 50.0  # Default neutral score
    
    def calculate_validation_score(self, format_valid, content_valid, authenticity_score):
        """
        Calculate overall validation score
        """
        score = 0
        
        if format_valid:
            score += 30
        
        if content_valid:
            score += 40
        
        # Authenticity contributes 30% of the score
        score += (authenticity_score / 100) * 30
        
        return min(100, max(0, score))
    
    def validate_date_format(self, date_string):
        """
        Validate date format
        """
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2}'
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, date_string.strip()):
                return True
        
        return False
