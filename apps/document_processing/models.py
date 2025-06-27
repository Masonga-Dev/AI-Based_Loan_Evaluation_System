from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class DocumentTemplate(models.Model):
    """
    Templates for different document types with expected fields
    """
    DOCUMENT_TYPE_CHOICES = [
        ('identity', 'Identity Document'),
        ('income_proof', 'Income Proof'),
        ('bank_statement', 'Bank Statement'),
        ('employment_letter', 'Employment Letter'),
        ('tax_return', 'Tax Return'),
        ('property_document', 'Property Document'),
    ]

    name = models.CharField(max_length=100)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    expected_fields = models.JSONField(default=list)  # List of expected field names
    validation_rules = models.JSONField(default=dict)  # Validation rules for fields
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_template'
        verbose_name = 'Document Template'
        verbose_name_plural = 'Document Templates'

    def __str__(self):
        return f"{self.name} ({self.document_type})"


class OCRResult(models.Model):
    """
    Store OCR processing results
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(
        'loan_application.ApplicationDocument',
        on_delete=models.CASCADE,
        related_name='ocr_result'
    )

    # OCR processing details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_text = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Extracted structured data
    extracted_data = models.JSONField(default=dict)

    # Processing metadata
    processing_time = models.DurationField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ocr_result'
        verbose_name = 'OCR Result'
        verbose_name_plural = 'OCR Results'

    def __str__(self):
        return f"OCR for {self.document.document_name}"

    @property
    def is_high_confidence(self):
        """Check if OCR result has high confidence"""
        return self.confidence_score and self.confidence_score >= 80

    @property
    def needs_manual_review(self):
        """Check if OCR result needs manual review"""
        return not self.confidence_score or self.confidence_score < 60


class ExtractedField(models.Model):
    """
    Individual fields extracted from documents
    """
    ocr_result = models.ForeignKey(OCRResult, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=100)
    field_value = models.TextField()
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Field validation
    is_validated = models.BooleanField(default=False)
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),
            ('needs_review', 'Needs Review'),
        ],
        blank=True
    )
    validation_notes = models.TextField(blank=True)

    # Field coordinates in the document (for highlighting)
    x_coordinate = models.IntegerField(null=True, blank=True)
    y_coordinate = models.IntegerField(null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'extracted_field'
        verbose_name = 'Extracted Field'
        verbose_name_plural = 'Extracted Fields'

    def __str__(self):
        return f"{self.field_name}: {self.field_value[:50]}"


class DocumentVerification(models.Model):
    """
    Document verification status and admin review
    """
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('needs_correction', 'Needs Correction'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged for Review'),
    ]

    document = models.OneToOneField(
        'loan_application.ApplicationDocument',
        on_delete=models.CASCADE,
        related_name='verification'
    )

    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')

    # Verification details
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_documents')
    verification_notes = models.TextField(blank=True)

    # OCR vs Manual comparison
    ocr_manual_match = models.BooleanField(null=True, blank=True)  # True if OCR matches manual entry
    discrepancies = models.JSONField(default=list, blank=True)  # List of field discrepancies

    # Quality assessment
    image_quality_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    readability_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'document_verification'
        verbose_name = 'Document Verification'
        verbose_name_plural = 'Document Verifications'

    def __str__(self):
        return f"Verification for {self.document.document_name} - {self.status}"


class OCRComparison(models.Model):
    """
    Compare OCR extracted data with manually entered data
    """
    COMPARISON_STATUS_CHOICES = [
        ('pending', 'Pending Comparison'),
        ('match', 'Data Matches'),
        ('mismatch', 'Data Mismatch'),
        ('partial_match', 'Partial Match'),
        ('no_manual_data', 'No Manual Data Available'),
    ]

    ocr_result = models.OneToOneField(OCRResult, on_delete=models.CASCADE, related_name='comparison')
    application = models.ForeignKey('loan_application.LoanApplication', on_delete=models.CASCADE)

    status = models.CharField(max_length=20, choices=COMPARISON_STATUS_CHOICES, default='pending')

    # Comparison results
    matched_fields = models.JSONField(default=list, blank=True)
    mismatched_fields = models.JSONField(default=list, blank=True)
    missing_fields = models.JSONField(default=list, blank=True)

    # Scores
    match_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Review status
    requires_admin_review = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ocr_comparison'
        verbose_name = 'OCR Comparison'
        verbose_name_plural = 'OCR Comparisons'

    def __str__(self):
        return f"Comparison for {self.ocr_result.document.document_name} - {self.status}"


class DocumentValidation(models.Model):
    """
    Document validation results
    """
    VALIDATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('needs_review', 'Needs Manual Review'),
    ]

    document = models.OneToOneField(
        'loan_application.ApplicationDocument',
        on_delete=models.CASCADE,
        related_name='validation'
    )

    status = models.CharField(max_length=20, choices=VALIDATION_STATUS_CHOICES, default='pending')
    validation_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Validation checks
    format_valid = models.BooleanField(default=False)
    content_valid = models.BooleanField(default=False)
    authenticity_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Validation details
    validation_errors = models.JSONField(default=list)
    validation_warnings = models.JSONField(default=list)
    validation_notes = models.TextField(blank=True)

    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_validation'
        verbose_name = 'Document Validation'
        verbose_name_plural = 'Document Validations'

    def __str__(self):
        return f"Validation for {self.document.document_name}"
