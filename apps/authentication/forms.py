from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from .models import User, UserProfile

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form with Bootstrap styling
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email',
            'autofocus': True
        }),
        label='Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class UserRegistrationForm(UserCreationForm):
    """
    User registration form with additional fields
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    account_number = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Equity Account Number'
        }),
        label='Account Number'
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I agree to the Terms and Conditions'
    )

    from django_countries.fields import CountryField
    gender = forms.ChoiceField(
        choices=[('', 'Select a gender'), ('male', 'Male'), ('female', 'Female')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    nationality = forms.ChoiceField(
        choices=[('', 'Select nationality'), ('rwandan', 'Rwandan'), ('burundian', 'Burundian'), ('ugandan', 'Ugandan'), ('kenyan', 'Kenyan'), ('tanzanian', 'Tanzanian'), ('congolese', 'Congolese'), ('other', 'Other')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    country_of_residence = CountryField(blank_label='Select a country').formfield(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    national_id = forms.CharField(
        max_length=16,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'National ID Number'
        })
    )
    physical_address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Physical Address'
        })
    )

    class Meta:
        model = User
        fields = (
            'email', 'first_name', 'last_name', 'gender', 'nationality', 'country_of_residence',
            'national_id', 'physical_address', 'account_number', 'phone_number',
            'password1', 'password2', 'terms_accepted'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ == 'CheckboxInput':
                field.widget.attrs['class'] = 'form-check-input'
            elif field.widget.__class__.__name__ == 'Select':
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
        # Customize password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create New Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        # Remove role and confirm_email fields if present
        self.fields.pop('role', None)
        self.fields.pop('confirm_email', None)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_account_number(self):
        account_number = self.cleaned_data.get('account_number')
        if not account_number.isdigit() or len(account_number) != 10:
            raise forms.ValidationError('Equity Bank account number must be exactly 10 digits.')
        if User.objects.filter(account_number=account_number).exists():
            raise forms.ValidationError('This Equity Bank account number is already registered.')
        return account_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.role = 'applicant'  # Always set to applicant
        user.account_number = self.cleaned_data['account_number']
        user.gender = self.cleaned_data['gender']
        user.nationality = self.cleaned_data['nationality']
        user.country_of_residence = self.cleaned_data['country_of_residence']
        user.national_id = self.cleaned_data['national_id']
        user.physical_address = self.cleaned_data['physical_address']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """
    User profile form for updating user information
    """
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 
            'date_of_birth', 'address', 'city', 'state', 'zip_code', 'country',
            'employment_status', 'employer_name', 'job_title', 'annual_income',
            'employment_years', 'credit_score', 'monthly_debt_payments',
            'profile_picture'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'employer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'employment_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'credit_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'monthly_debt_payments': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }


class UserProfileExtendedForm(forms.ModelForm):
    """
    Extended user profile form for additional information
    """
    class Meta:
        model = UserProfile
        fields = [
            'marital_status', 'dependents', 'education_level',
            'emergency_contact_name', 'emergency_contact_phone', 
            'emergency_contact_relationship', 'preferred_language'
        ]
        widgets = {
            'marital_status': forms.Select(attrs={'class': 'form-select'}),
            'dependents': forms.NumberInput(attrs={'class': 'form-control'}),
            'education_level': forms.Select(attrs={'class': 'form-select'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relationship': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_language': forms.TextInput(attrs={'class': 'form-control'}),
        }


class PasswordResetRequestForm(forms.Form):
    """
    Password reset request form
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('No user found with this email address.')
        return email
