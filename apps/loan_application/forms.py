from django import forms
from .models import LoanApplication

class LoanApplicationForm(forms.ModelForm):
    # Section A: Personal Information
    full_name = forms.CharField(label='Full Name', max_length=100)
    national_id = forms.CharField(label='National ID Number (NIDA)', max_length=20)
    date_of_birth = forms.DateField(label='Date of Birth', widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    phone_number = forms.CharField(label='Phone Number', max_length=20)
    email = forms.EmailField(label='Email Address')
    residential_address = forms.CharField(label='Residential Address', max_length=255)
    district = forms.CharField(label='District', max_length=50)
    sector = forms.CharField(label='Sector', max_length=50)
    village = forms.CharField(label='Village', max_length=50)
    marital_status = forms.ChoiceField(choices=[('single', 'Single'), ('married', 'Married'), ('divorced', 'Divorced'), ('widowed', 'Widowed')])

    # Section B: Employment & Income Details
    employment_status = forms.ChoiceField(choices=[('employed', 'Employed'), ('self_employed', 'Self-employed'), ('unemployed', 'Unemployed'), ('retired', 'Retired')])
    employer_name = forms.CharField(label="Employer's Name", max_length=100, required=False)
    job_title = forms.CharField(label='Job Title / Occupation', max_length=100, required=False)
    monthly_income = forms.DecimalField(label='Monthly Income (RWF)', max_digits=12, decimal_places=2)
    other_monthly_income = forms.DecimalField(label='Other Monthly Income (optional)', max_digits=12, decimal_places=2, required=False)
    source_of_other_income = forms.CharField(label='Source of Other Income', max_length=100, required=False)

    # Section C: Loan Details
    LOAN_TYPE_CHOICES = [
        ('personal', 'Personal Loan'),
        ('education', 'Education Loan'),
        ('mortgage', 'Mortgage Loan'),
        ('agriculture', 'Agriculture Loan'),
        ('business', 'Business Loan'),
    ]
    loan_type = forms.ChoiceField(
        choices=LOAN_TYPE_CHOICES,
        label='Loan Type',
        widget=forms.Select(attrs={'class': 'form-select required-field'})
    )
    loan_amount = forms.DecimalField(
        label='Loan Amount Requested (RWF)',
        max_digits=12,
        decimal_places=2,
        min_value=1000,
        help_text=None
    )
    loan_purpose = forms.CharField(label='Loan Purpose / Description', widget=forms.Textarea)
    repayment_period = forms.IntegerField(label='Repayment Period (Months)')
    repayment_frequency = forms.ChoiceField(choices=[('monthly', 'Monthly'), ('biweekly', 'Bi-Weekly')])
    proposed_start_date = forms.DateField(label='Proposed Start Date for Repayment', widget=forms.DateInput(attrs={'type': 'date'}))

    # Section D: Financial History
    has_existing_loans = forms.ChoiceField(label='Do you have existing loans?', choices=[('yes', 'Yes'), ('no', 'No')])
    existing_loans_details = forms.CharField(label='If yes, provide: Lender, Outstanding Amount, Monthly Repayment', widget=forms.Textarea, required=False)
    has_defaulted = forms.ChoiceField(label='Have you defaulted on any loan before?', choices=[('yes', 'Yes'), ('no', 'No')])
    bank_account_number = forms.CharField(label='Bank Account Number (at Equity Bank)', max_length=30)
    bank_branch = forms.CharField(label='Bank Branch', max_length=100)

    # Section E: Guarantor Information
    guarantor_full_name = forms.CharField(label='Guarantor Full Name', max_length=100)
    guarantor_national_id = forms.CharField(label='Guarantor National ID', max_length=20)
    guarantor_phone = forms.CharField(label='Guarantor Phone Number', max_length=20)
    guarantor_relationship = forms.CharField(label='Guarantor Relationship to Applicant', max_length=50)
    guarantor_employment_info = forms.CharField(label='Guarantor Employment Info (optional)', max_length=100, required=False)

    # Section F: Document Uploads
    national_id_upload = forms.FileField(label='National ID (PDF/JPG)')
    payslip_upload = forms.FileField(label='Recent Payslip or Income Proof')
    bank_statement_upload = forms.FileField(label='Bank Statement (last 3–6 months)')
    business_license_upload = forms.FileField(label='Business License (if applicable)', required=False)
    additional_document_1 = forms.FileField(label='Additional Document 1 (optional)', required=False)
    additional_document_2 = forms.FileField(label='Additional Document 2 (optional)', required=False)
    number_of_dependents = forms.IntegerField(label='Number of Dependents', min_value=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            # Only add styling, not a custom asterisk
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
        self.fields['loan_type'].widget.attrs['class'] = 'form-select required-field'
        self.fields['loan_amount'].help_text = None

    class Meta:
        model = LoanApplication
        fields = ['full_name', 'national_id', 'date_of_birth', 'gender', 'phone_number', 'email', 'residential_address', 'district', 'sector', 'village', 'marital_status', 'loan_type', 'loan_amount', 'loan_purpose', 'repayment_period', 'number_of_dependents', 'employment_status', 'employer_name', 'job_title', 'monthly_income', 'other_monthly_income', 'source_of_other_income', 'proposed_start_date', 'repayment_frequency', 'has_existing_loans', 'existing_loans_details', 'has_defaulted', 'bank_account_number', 'bank_branch', 'guarantor_full_name', 'guarantor_national_id', 'guarantor_phone', 'guarantor_relationship', 'guarantor_employment_info', 'national_id_upload', 'payslip_upload', 'bank_statement_upload', 'business_license_upload', 'additional_document_1', 'additional_document_2']
