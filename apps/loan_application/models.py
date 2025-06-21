from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()


class LoanApplication(models.Model):
    """
    Main loan application model
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    LOAN_TYPE_CHOICES = [
        ('personal', 'Personal Loan'),
        ('home', 'Home Loan'),
        ('auto', 'Auto Loan'),
        ('business', 'Business Loan'),
        ('education', 'Education Loan'),
    ]

    LOAN_PURPOSE_CHOICES = [
        ('home_purchase', 'Home Purchase'),
        ('home_refinance', 'Home Refinance'),
        ('debt_consolidation', 'Debt Consolidation'),
        ('business_expansion', 'Business Expansion'),
        ('education', 'Education'),
        ('medical', 'Medical Expenses'),
        ('other', 'Other'),
    ]

    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_applications')
    application_number = models.CharField(max_length=20, unique=True, editable=False)

    # Loan details
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPE_CHOICES)
    loan_purpose = models.CharField(max_length=30, choices=LOAN_PURPOSE_CHOICES)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(1000)])
    loan_term_months = models.IntegerField(validators=[MinValueValidator(6), MaxValueValidator(360)])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Property information (for secured loans)
    property_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(
        max_length=20,
        choices=[
            ('single_family', 'Single Family Home'),
            ('condo', 'Condominium'),
            ('townhouse', 'Townhouse'),
            ('multi_family', 'Multi-Family'),
            ('commercial', 'Commercial Property'),
        ],
        blank=True
    )
    property_address = models.TextField(blank=True)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Application status and workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    assigned_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications',
        limit_choices_to={'role__in': ['officer', 'manager']}
    )

    # AI evaluation results
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_recommendation = models.CharField(
        max_length=20,
        choices=[
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('manual_review', 'Manual Review Required'),
        ],
        blank=True
    )
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('very_high', 'Very High Risk'),
        ],
        blank=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)

    # Additional information
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'loan_application'
        verbose_name = 'Loan Application'
        verbose_name_plural = 'Loan Applications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Application {self.application_number} - {self.applicant.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.application_number:
            # Generate application number
            import datetime
            today = datetime.date.today()
            count = LoanApplication.objects.filter(created_at__date=today).count() + 1
            self.application_number = f"LA{today.strftime('%Y%m%d')}{count:04d}"
        super().save(*args, **kwargs)

    @property
    def loan_to_value_ratio(self):
        """Calculate loan-to-value ratio for secured loans"""
        if self.property_value and self.loan_amount:
            return (self.loan_amount / self.property_value) * 100
        return 0

    @property
    def monthly_payment_estimate(self):
        """Calculate estimated monthly payment"""
        if self.loan_amount and self.loan_term_months and self.interest_rate:
            principal = float(self.loan_amount)
            rate = float(self.interest_rate) / 100 / 12
            term = self.loan_term_months

            if rate > 0:
                payment = principal * (rate * (1 + rate) ** term) / ((1 + rate) ** term - 1)
            else:
                payment = principal / term

            return round(payment, 2)
        return 0


class ApplicationDocument(models.Model):
    """
    Documents uploaded for loan applications
    """
    DOCUMENT_TYPE_CHOICES = [
        ('identity', 'Identity Document'),
        ('income_proof', 'Income Proof'),
        ('bank_statement', 'Bank Statement'),
        ('employment_letter', 'Employment Letter'),
        ('tax_return', 'Tax Return'),
        ('property_document', 'Property Document'),
        ('other', 'Other'),
    ]

    application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    document_name = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='documents/')
    file_size = models.IntegerField()
    mime_type = models.CharField(max_length=100)

    # OCR and processing results
    extracted_text = models.TextField(blank=True)
    is_processed = models.BooleanField(default=False)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'application_document'
        verbose_name = 'Application Document'
        verbose_name_plural = 'Application Documents'

    def __str__(self):
        return f"{self.document_name} - {self.application.application_number}"


class ApplicationHistory(models.Model):
    """
    Track changes and history of loan applications
    """
    ACTION_CHOICES = [
        ('created', 'Application Created'),
        ('submitted', 'Application Submitted'),
        ('assigned', 'Assigned to Officer'),
        ('reviewed', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('document_uploaded', 'Document Uploaded'),
        ('ai_evaluated', 'AI Evaluation Completed'),
    ]

    application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'application_history'
        verbose_name = 'Application History'
        verbose_name_plural = 'Application Histories'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.application.application_number} - {self.action}"


class LoanOffer(models.Model):
    """
    Loan offers generated for approved applications
    """
    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, related_name='offer')
    offered_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_term_months = models.IntegerField()
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)

    # Offer conditions
    conditions = models.TextField(blank=True)
    expiry_date = models.DateTimeField()

    # Offer status
    is_accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loan_offer'
        verbose_name = 'Loan Offer'
        verbose_name_plural = 'Loan Offers'

    def __str__(self):
        return f"Offer for {self.application.application_number}"
