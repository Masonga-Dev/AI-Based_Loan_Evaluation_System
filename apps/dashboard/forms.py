from django import forms
from apps.authentication.models import User

class ApplicantProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'address', 'city', 'country',
            'account_number', 'profile_picture'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.TextInput(attrs={'maxlength': 100, 'style': 'max-width: 300px;'}),
        }
