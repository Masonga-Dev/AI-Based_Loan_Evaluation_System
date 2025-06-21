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
