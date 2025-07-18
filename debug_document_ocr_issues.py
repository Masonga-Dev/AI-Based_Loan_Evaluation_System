#!/usr/bin/env python
"""
Debug document upload and OCR processing issues
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loan_evaluation_system.settings')
django.setup()

from apps.loan_application.models import LoanApplication, ApplicationDocument
from apps.document_processing.ocr_utils import OCRProcessor
from apps.document_processing.ocr_service import EnhancedOCRService

def debug_document_issues():
    print("🔍 Debugging Document Upload & OCR Issues")
    print("=" * 60)
    
    # Check recent applications and their documents
    applications = LoanApplication.objects.all().order_by('-created_at')[:5]
    
    if not applications:
        print("❌ No applications found")
        return
    
    print(f"📊 Found {applications.count()} recent applications")
    
    for i, app in enumerate(applications, 1):
        print(f"\n📋 Application {i}: {app.application_number}")
        print(f"   Status: {app.status}")
        print(f"   Created: {app.created_at}")
        
        # Check documents
        documents = ApplicationDocument.objects.filter(application=app)
        print(f"   📎 Documents: {documents.count()}")
        
        if documents.count() == 0:
            print(f"   ⚠️  NO DOCUMENTS FOUND!")
            continue
        
        for j, doc in enumerate(documents, 1):
            print(f"\n      📄 Document {j}: {doc.document_name}")
            print(f"         Type: {doc.get_document_type_display()}")
            print(f"         Size: {doc.file_size:,} bytes")
            print(f"         MIME: {doc.mime_type}")
            print(f"         Uploaded: {doc.uploaded_at}")
            
            # Check OCR processing status
            print(f"         🤖 OCR Status:")
            print(f"            Processed: {'✅' if doc.is_processed else '❌'}")
            print(f"            Status: {doc.processing_status}")
            print(f"            Processed At: {doc.processed_at or 'Never'}")
            
            # Check extracted text
            if doc.extracted_text:
                text_preview = doc.extracted_text[:100] + "..." if len(doc.extracted_text) > 100 else doc.extracted_text
                print(f"            Extracted Text: {text_preview}")
            else:
                print(f"            Extracted Text: ❌ None")
            
            # Check file existence
            if doc.document_file:
                file_exists = os.path.exists(doc.document_file.path)
                print(f"            File Exists: {'✅' if file_exists else '❌'}")
                if file_exists:
                    print(f"            File Path: {doc.document_file.path}")
            else:
                print(f"            File: ❌ No file attached")

def test_ocr_processing():
    print(f"\n🧪 Testing OCR Processing")
    print("=" * 60)
    
    # Get a document that hasn't been processed
    unprocessed_docs = ApplicationDocument.objects.filter(
        is_processed=False,
        document_file__isnull=False
    )
    
    if not unprocessed_docs.exists():
        print("❌ No unprocessed documents found")
        return
    
    doc = unprocessed_docs.first()
    print(f"📄 Testing with document: {doc.document_name}")
    print(f"   Application: {doc.application.application_number}")
    print(f"   Type: {doc.get_document_type_display()}")
    
    # Test OCR processor
    try:
        print(f"\n🔧 Testing OCR Processor...")
        processor = OCRProcessor()
        
        # Test simple text extraction
        if doc.document_file and os.path.exists(doc.document_file.path):
            extracted_text = processor.extract_text_from_image(doc.document_file.path)
            print(f"   ✅ OCR Processor working")
            print(f"   📝 Extracted text preview: {extracted_text[:200]}...")
            
            # Update document with extracted text
            doc.extracted_text = extracted_text
            doc.is_processed = True
            doc.processing_status = 'completed'
            doc.processed_at = django.utils.timezone.now()
            doc.save()
            print(f"   ✅ Document updated with OCR results")
            
        else:
            print(f"   ❌ Document file not found")
            
    except Exception as e:
        print(f"   ❌ OCR processing failed: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_ocr_service():
    print(f"\n🚀 Testing Enhanced OCR Service")
    print("=" * 60)
    
    # Get another unprocessed document
    unprocessed_docs = ApplicationDocument.objects.filter(
        is_processed=False,
        document_file__isnull=False
    )
    
    if not unprocessed_docs.exists():
        print("❌ No unprocessed documents found")
        return
    
    doc = unprocessed_docs.first()
    print(f"📄 Testing with document: {doc.document_name}")
    
    try:
        print(f"\n🔧 Testing Enhanced OCR Service...")
        ocr_service = EnhancedOCRService()
        
        result = ocr_service.process_document_with_validation(doc)
        
        if result['success']:
            print(f"   ✅ Enhanced OCR Service working")
            print(f"   📊 Requires Review: {result.get('requires_review', False)}")
            
            if 'ocr_result' in result:
                ocr_result = result['ocr_result']
                print(f"   📝 OCR Result ID: {ocr_result.id}")
                print(f"   📊 Confidence: {ocr_result.confidence_score}")
        else:
            print(f"   ❌ Enhanced OCR Service failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Enhanced OCR Service failed: {e}")
        import traceback
        traceback.print_exc()

def check_ocr_configuration():
    print(f"\n⚙️  Checking OCR Configuration")
    print("=" * 60)
    
    try:
        from django.conf import settings
        print(f"📊 OCR Settings:")
        print(f"   TESSERACT_CMD: {settings.TESSERACT_CMD}")
        print(f"   OCR_LANGUAGES: {settings.OCR_LANGUAGES}")
        
        # Check if Tesseract is accessible
        tesseract_exists = os.path.exists(settings.TESSERACT_CMD)
        print(f"   Tesseract Exists: {'✅' if tesseract_exists else '❌'}")
        
        # Test basic OCR functionality
        import pytesseract
        from PIL import Image, ImageDraw
        
        # Create test image
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 30), "TEST DOCUMENT OCR", fill='black')
        
        # Test OCR
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        text = pytesseract.image_to_string(img)
        
        if "TEST" in text.upper():
            print(f"   OCR Functionality: ✅ Working")
        else:
            print(f"   OCR Functionality: ⚠️  Partial (got: '{text.strip()}')")
            
    except Exception as e:
        print(f"   ❌ OCR Configuration Error: {e}")

def identify_root_causes():
    print(f"\n🎯 Root Cause Analysis")
    print("=" * 60)
    
    issues = []
    
    # Check if documents are being created during application submission
    recent_apps = LoanApplication.objects.filter(status='submitted').order_by('-created_at')[:3]
    
    for app in recent_apps:
        docs = ApplicationDocument.objects.filter(application=app)
        if docs.count() == 0:
            issues.append(f"Application {app.application_number} has no documents")
        else:
            unprocessed = docs.filter(is_processed=False).count()
            if unprocessed > 0:
                issues.append(f"Application {app.application_number} has {unprocessed} unprocessed documents")
    
    # Check OCR processing workflow
    try:
        processor = OCRProcessor()
        issues.append("OCR Processor can be instantiated ✅")
    except Exception as e:
        issues.append(f"OCR Processor instantiation failed: {e}")
    
    try:
        ocr_service = EnhancedOCRService()
        issues.append("Enhanced OCR Service can be instantiated ✅")
    except Exception as e:
        issues.append(f"Enhanced OCR Service instantiation failed: {e}")
    
    print(f"📋 Issues Identified:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print(f"\n💡 Likely Root Causes:")
    print(f"   1. 🔧 Documents uploaded during application submission don't trigger OCR")
    print(f"   2. 📝 OCR processing only happens through separate upload endpoint")
    print(f"   3. ⚙️  Missing automatic OCR trigger in application submission workflow")
    print(f"   4. 🔄 No background task processing for submitted documents")

if __name__ == "__main__":
    debug_document_issues()
    test_ocr_processing()
    test_enhanced_ocr_service()
    check_ocr_configuration()
    identify_root_causes()
    
    print(f"\n🔧 Recommended Fixes:")
    print(f"   1. Add OCR processing trigger to application submission")
    print(f"   2. Process all uploaded documents automatically")
    print(f"   3. Add background task for OCR processing")
    print(f"   4. Update document processing status properly")
