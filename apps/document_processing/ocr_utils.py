"""
OCR Utilities for Document Processing
This module handles OCR processing using pytesseract
"""

import pytesseract
import cv2
import numpy as np
from PIL import Image
import os
import re
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from .models import OCRResult, ExtractedField, DocumentTemplate
import logging

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Main OCR processing class using pytesseract
    """
    
    def __init__(self):
        # Set tesseract command path if specified in settings
        if hasattr(settings, 'TESSERACT_CMD'):
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        
        self.supported_formats = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        self.confidence_threshold = 60  # Minimum confidence score
        
    def process_document(self, document):
        """
        Process a document and extract text using OCR
        """
        start_time = datetime.now()
        
        try:
            # Create or get OCR result record
            ocr_result, created = OCRResult.objects.get_or_create(
                document=document,
                defaults={'status': 'processing'}
            )
            
            if not created:
                ocr_result.status = 'processing'
                ocr_result.save()
            
            # Get file path
            file_path = document.document_file.path
            
            # Preprocess image if needed
            processed_image = self.preprocess_image(file_path)
            
            # Extract text using OCR
            extracted_text, confidence = self.extract_text_with_confidence(processed_image)
            
            # Update OCR result
            ocr_result.raw_text = extracted_text
            ocr_result.confidence_score = confidence
            ocr_result.status = 'completed'
            ocr_result.processing_time = datetime.now() - start_time
            ocr_result.completed_at = datetime.now()
            ocr_result.save()
            
            # Extract structured data based on document type
            structured_data = self.extract_structured_data(
                extracted_text, 
                document.document_type
            )
            ocr_result.extracted_data = structured_data
            ocr_result.save()
            
            # Create extracted field records
            self.create_extracted_fields(ocr_result, structured_data)

            # Create comparison with manual data if available
            self.create_ocr_comparison(ocr_result, document.application)

            logger.info(f"OCR processing completed for document {document.id}")
            return ocr_result
            
        except Exception as e:
            logger.error(f"OCR processing failed for document {document.id}: {str(e)}")
            
            # Update OCR result with error
            if 'ocr_result' in locals():
                ocr_result.status = 'failed'
                ocr_result.error_message = str(e)
                ocr_result.processing_time = datetime.now() - start_time
                ocr_result.save()
            
            raise e
    
    def preprocess_image(self, image_path):
        """
        Preprocess image to improve OCR accuracy
        """
        try:
            # Read image
            if image_path.lower().endswith('.pdf'):
                # For PDF files, convert first page to image
                # This would require pdf2image library in production
                return image_path
            
            # Read image using OpenCV
            image = cv2.imread(image_path)
            
            if image is None:
                raise ValueError(f"Could not read image from {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply noise reduction
            denoised = cv2.medianBlur(gray, 3)
            
            # Apply thresholding to get binary image
            _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Deskew image if needed
            deskewed = self.deskew_image(thresh)
            
            return deskewed
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
            return image_path
    
    def deskew_image(self, image):
        """
        Deskew image to improve OCR accuracy
        """
        try:
            # Find contours
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest contour (assuming it's the document)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get minimum area rectangle
                rect = cv2.minAreaRect(largest_contour)
                angle = rect[2]
                
                # Correct angle
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                
                # Rotate image
                if abs(angle) > 0.5:  # Only rotate if angle is significant
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                    return rotated
            
            return image
            
        except Exception as e:
            logger.warning(f"Image deskewing failed: {str(e)}")
            return image
    
    def extract_text_with_confidence(self, image):
        """
        Extract text from image with confidence scores
        """
        try:
            # Configure tesseract
            config = '--oem 3 --psm 6'  # Use LSTM OCR Engine Mode with uniform text block
            
            if isinstance(image, str):
                # If image is a file path
                text = pytesseract.image_to_string(image, config=config)
                
                # Get detailed data for confidence calculation
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config)
            else:
                # If image is a numpy array
                text = pytesseract.image_to_string(image, config=config)
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config)
            
            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return "", 0
    
    def extract_structured_data(self, text, document_type):
        """
        Extract structured data based on document type
        """
        structured_data = {}
        
        try:
            if document_type == 'identity':
                structured_data = self.extract_identity_data(text)
            elif document_type == 'income_proof':
                structured_data = self.extract_income_data(text)
            elif document_type == 'bank_statement':
                structured_data = self.extract_bank_statement_data(text)
            elif document_type == 'employment_letter':
                structured_data = self.extract_employment_data(text)
            else:
                # Generic extraction for other document types
                structured_data = self.extract_generic_data(text)
                
        except Exception as e:
            logger.error(f"Structured data extraction failed: {str(e)}")
            structured_data = {'error': str(e)}
        
        return structured_data

    def create_ocr_comparison(self, ocr_result, application):
        """
        Compare OCR extracted data with manually entered application data
        """
        from .models import OCRComparison

        try:
            # Get manual data from application
            manual_data = self.get_manual_application_data(application, ocr_result.document.document_type)
            ocr_data = ocr_result.extracted_data

            # Perform comparison
            comparison_result = self.compare_data_fields(manual_data, ocr_data)

            # Create comparison record
            comparison = OCRComparison.objects.create(
                ocr_result=ocr_result,
                application=application,
                status=comparison_result['status'],
                matched_fields=comparison_result['matched_fields'],
                mismatched_fields=comparison_result['mismatched_fields'],
                missing_fields=comparison_result['missing_fields'],
                match_percentage=comparison_result['match_percentage'],
                confidence_score=comparison_result['confidence_score'],
                requires_admin_review=comparison_result['requires_review']
            )

            logger.info(f"OCR comparison created for document {ocr_result.document.id}")
            return comparison

        except Exception as e:
            logger.error(f"OCR comparison failed: {str(e)}")
            return None

    def get_manual_application_data(self, application, document_type):
        """
        Extract relevant manual data from application based on document type
        """
        manual_data = {}

        if document_type == 'income_proof':
            manual_data.update({
                'monthly_income': str(application.applicant.monthly_income) if application.applicant.monthly_income else '',
                'annual_income': str(application.applicant.annual_income) if application.applicant.annual_income else '',
                'employer': application.applicant.employer or '',
                'employment_status': application.applicant.employment_status or '',
            })

        elif document_type == 'identity':
            manual_data.update({
                'full_name': application.applicant.get_full_name(),
                'first_name': application.applicant.first_name,
                'last_name': application.applicant.last_name,
                'date_of_birth': str(application.applicant.date_of_birth) if application.applicant.date_of_birth else '',
                'address': application.applicant.address or '',
            })

        elif document_type == 'bank_statement':
            manual_data.update({
                'account_number': application.applicant.account_number or '',
                'monthly_income': str(application.applicant.monthly_income) if application.applicant.monthly_income else '',
            })

        elif document_type == 'employment_letter':
            manual_data.update({
                'employer': application.applicant.employer or '',
                'employment_status': application.applicant.employment_status or '',
                'monthly_income': str(application.applicant.monthly_income) if application.applicant.monthly_income else '',
            })

        return manual_data

    def compare_data_fields(self, manual_data, ocr_data):
        """
        Compare manual and OCR data fields
        """
        matched_fields = []
        mismatched_fields = []
        missing_fields = []

        # Check each manual field against OCR data
        for field_name, manual_value in manual_data.items():
            if not manual_value:  # Skip empty manual values
                continue

            ocr_value = ocr_data.get(field_name, '')

            if not ocr_value:
                missing_fields.append({
                    'field': field_name,
                    'manual_value': manual_value,
                    'ocr_value': ''
                })
            else:
                # Normalize values for comparison
                manual_normalized = self.normalize_value(manual_value)
                ocr_normalized = self.normalize_value(ocr_value)

                similarity = self.calculate_similarity(manual_normalized, ocr_normalized)

                if similarity >= 0.8:  # 80% similarity threshold
                    matched_fields.append({
                        'field': field_name,
                        'manual_value': manual_value,
                        'ocr_value': ocr_value,
                        'similarity': similarity
                    })
                else:
                    mismatched_fields.append({
                        'field': field_name,
                        'manual_value': manual_value,
                        'ocr_value': ocr_value,
                        'similarity': similarity
                    })

        # Calculate overall match percentage
        total_fields = len(matched_fields) + len(mismatched_fields) + len(missing_fields)
        match_percentage = (len(matched_fields) / total_fields * 100) if total_fields > 0 else 0

        # Calculate confidence score
        confidence_score = sum([field['similarity'] for field in matched_fields]) / len(matched_fields) * 100 if matched_fields else 0

        # Determine status
        if match_percentage >= 90:
            status = 'match'
        elif match_percentage >= 70:
            status = 'partial_match'
        elif total_fields == 0:
            status = 'no_manual_data'
        else:
            status = 'mismatch'

        # Determine if admin review is required
        requires_review = (
            match_percentage < 80 or
            len(mismatched_fields) > 0 or
            confidence_score < 70
        )

        return {
            'status': status,
            'matched_fields': matched_fields,
            'mismatched_fields': mismatched_fields,
            'missing_fields': missing_fields,
            'match_percentage': round(match_percentage, 2),
            'confidence_score': round(confidence_score, 2),
            'requires_review': requires_review
        }

    def normalize_value(self, value):
        """
        Normalize value for comparison
        """
        if not value:
            return ''

        # Convert to string and lowercase
        normalized = str(value).lower().strip()

        # Remove common punctuation and extra spaces
        import re
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def calculate_similarity(self, str1, str2):
        """
        Calculate similarity between two strings using Levenshtein distance
        """
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0

        # Simple similarity calculation
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
    
    def extract_identity_data(self, text):
        """
        Extract identity document data with enhanced patterns
        """
        data = {}

        # Enhanced name patterns
        name_patterns = [
            r'(?:full\s+)?name[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'surname[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'given\s+name[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'first\s+name[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'last\s+name[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
        ]

        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:  # Valid name should be longer than 2 chars
                    if 'first_name' not in data and 'first' in pattern:
                        data['first_name'] = name
                    elif 'last_name' not in data and 'last' in pattern:
                        data['last_name'] = name
                    elif 'full_name' not in data:
                        data['full_name'] = name

        # Enhanced date of birth patterns
        dob_patterns = [
            r'(?:date\s+of\s+birth|dob|born)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(?:date\s+of\s+birth|dob|born)[:\s]+(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # Generic date pattern
        ]

        for pattern in dob_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Validate date format
                if self.is_valid_date(match):
                    data['date_of_birth'] = match
                    break
            if 'date_of_birth' in data:
                break

        # Enhanced ID number patterns
        id_patterns = [
            r'(?:national\s+)?id(?:\s+number)?[:\s]+(\d{10,20})',
            r'identification[:\s]+(\d{10,20})',
            r'passport[:\s]+([A-Z0-9]{6,12})',
            r'license[:\s]+([A-Z0-9]{6,15})',
        ]

        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                id_num = match.group(1).strip()
                if len(id_num) >= 6:  # Valid ID should be at least 6 characters
                    data['id_number'] = id_num
                    break

        # Extract address
        address_patterns = [
            r'address[:\s]+([^\n]+(?:\n[^\n]+)*?)(?:\n\n|\n[A-Z]|$)',
            r'residence[:\s]+([^\n]+)',
            r'location[:\s]+([^\n]+)',
        ]

        for pattern in address_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                address = match.group(1).strip()
                if len(address) > 5:  # Valid address should be longer
                    data['address'] = address
                    break

        return data

    def is_valid_date(self, date_str):
        """
        Validate if a date string is a valid date
        """
        try:
            from datetime import datetime
            # Try different date formats
            formats = ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y', '%Y/%m/%d', '%Y-%m-%d']
            for fmt in formats:
                try:
                    datetime.strptime(date_str, fmt)
                    return True
                except ValueError:
                    continue
            return False
        except:
            return False

    def extract_income_data(self, text):
        """
        Extract data from income proof documents with enhanced patterns
        """
        data = {}

        # Enhanced salary patterns with currency support
        salary_patterns = [
            r'(?:gross\s+)?(?:monthly\s+)?salary[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'(?:monthly\s+)?income[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'(?:gross\s+)?pay[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'earnings[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'net\s+salary[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'basic\s+salary[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                salary_str = match.group(1).replace(',', '')
                try:
                    salary_value = float(salary_str)
                    if salary_value > 0:  # Valid salary should be positive
                        data['monthly_income'] = salary_str
                        break
                except ValueError:
                    continue

        # Enhanced employer patterns
        employer_patterns = [
            r'employer[:\s]+([a-zA-Z\s&.,]+?)(?:\n|$)',
            r'company[:\s]+([a-zA-Z\s&.,]+?)(?:\n|$)',
            r'organization[:\s]+([a-zA-Z\s&.,]+?)(?:\n|$)',
            r'institution[:\s]+([a-zA-Z\s&.,]+?)(?:\n|$)',
            r'workplace[:\s]+([a-zA-Z\s&.,]+?)(?:\n|$)',
        ]

        for pattern in employer_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                employer = match.group(1).strip()
                if len(employer) > 2 and not employer.isdigit():
                    data['employer'] = employer
                    break

        # Extract employment status
        status_patterns = [
            r'employment\s+status[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'position[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'job\s+title[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
            r'designation[:\s]+([a-zA-Z\s]+?)(?:\n|$)',
        ]

        for pattern in status_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                status = match.group(1).strip()
                if len(status) > 2:
                    data['employment_status'] = status
                    break

        # Extract annual income if available
        annual_patterns = [
            r'annual\s+(?:salary|income)[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
            r'yearly\s+(?:salary|income)[:\s]+(?:rwf\s*)?([0-9,]+(?:\.\d{2})?)',
        ]

        for pattern in annual_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                annual_str = match.group(1).replace(',', '')
                try:
                    annual_value = float(annual_str)
                    if annual_value > 0:
                        data['annual_income'] = annual_str
                        break
                except ValueError:
                    continue

        return data
    
    def extract_bank_statement_data(self, text):
        """
        Extract data from bank statements
        """
        data = {}
        
        # Extract account number
        account_patterns = [
            r'Account[:\s]+([0-9-]+)',
            r'A/C[:\s]+([0-9-]+)'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['account_number'] = match.group(1).strip()
                break
        
        # Extract balance
        balance_patterns = [
            r'Balance[:\s]+\$?([0-9,]+\.?\d*)',
            r'Current Balance[:\s]+\$?([0-9,]+\.?\d*)'
        ]
        
        for pattern in balance_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                data['balance'] = amount
                break
        
        return data
    
    def extract_employment_data(self, text):
        """
        Extract data from employment letters
        """
        data = {}
        
        # Extract job title
        title_patterns = [
            r'Position[:\s]+([A-Za-z\s]+)',
            r'Title[:\s]+([A-Za-z\s]+)',
            r'Role[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['job_title'] = match.group(1).strip()
                break
        
        return data
    
    def extract_generic_data(self, text):
        """
        Generic data extraction for unknown document types
        """
        data = {
            'text_length': len(text),
            'word_count': len(text.split()),
            'has_numbers': bool(re.search(r'\d', text)),
            'has_currency': bool(re.search(r'\$|USD|dollar', text, re.IGNORECASE))
        }
        
        return data
    
    def create_extracted_fields(self, ocr_result, structured_data):
        """
        Create ExtractedField records from structured data
        """
        for field_name, field_value in structured_data.items():
            if field_value and str(field_value).strip():
                ExtractedField.objects.create(
                    ocr_result=ocr_result,
                    field_name=field_name,
                    field_value=str(field_value),
                    confidence_score=ocr_result.confidence_score
                )
