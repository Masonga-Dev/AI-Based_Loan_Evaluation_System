from django import forms
from .models import LoanApplication

class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = LoanApplication
        exclude = ['id', 'applicant', 'application_number', 'status', 'assigned_officer', 'ai_score', 'created_at', 'updated_at', 'decision_date']
