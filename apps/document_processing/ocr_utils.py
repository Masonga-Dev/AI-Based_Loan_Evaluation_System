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
    
    def extract_identity_data(self, text):
        """
        Extract data from identity documents
        """
        data = {}
        
        # Extract name patterns
        name_patterns = [
            r'Name[:\s]+([A-Za-z\s]+)',
            r'Full Name[:\s]+([A-Za-z\s]+)',
            r'Given Name[:\s]+([A-Za-z\s]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['name'] = match.group(1).strip()
                break
        
        # Extract date of birth
        dob_patterns = [
            r'Date of Birth[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'DOB[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Born[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
        ]
        
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['date_of_birth'] = match.group(1).strip()
                break
        
        # Extract ID number
        id_patterns = [
            r'ID[:\s]+([A-Za-z0-9]+)',
            r'License[:\s]+([A-Za-z0-9]+)',
            r'Number[:\s]+([A-Za-z0-9]+)'
        ]
        
        for pattern in id_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['id_number'] = match.group(1).strip()
                break
        
        return data
    
    def extract_income_data(self, text):
        """
        Extract data from income documents
        """
        data = {}
        
        # Extract salary/income amounts
        income_patterns = [
            r'Salary[:\s]+\$?([0-9,]+\.?\d*)',
            r'Income[:\s]+\$?([0-9,]+\.?\d*)',
            r'Gross[:\s]+\$?([0-9,]+\.?\d*)',
            r'Annual[:\s]+\$?([0-9,]+\.?\d*)'
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                data['income_amount'] = amount
                break
        
        # Extract employer name
        employer_patterns = [
            r'Employer[:\s]+([A-Za-z\s&.,]+)',
            r'Company[:\s]+([A-Za-z\s&.,]+)'
        ]
        
        for pattern in employer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['employer'] = match.group(1).strip()
                break
        
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
