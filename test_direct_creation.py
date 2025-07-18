#!/usr/bin/env python
"""
Test script to directly test loan application creation logic
"""
import os
import sys
import django
from datetime import date
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loan_evaluation_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.loan_application.models import LoanApplication

User = get_user_model()

def test_direct_application_creation():
    """Test creating a loan application directly"""
    print("Testing direct loan application creation...")
    
    # Get or create a test user
    try:
        user = User.objects.first()
        if not user:
            user = User.objects.create_user(username='testuser4', email='test4@example.com', password='testpass')
    except Exception as e:
        print(f"Error with user: {e}")
        return False
    
    # Count existing applications
    initial_count = LoanApplication.objects.count()
    print(f"Initial loan applications count: {initial_count}")
    
    # Test session data (same as what would be in session)
    session_data = {
        'personal': {
            'full_name': 'John Doe',
            'national_id': '1234567890123456',
            'date_of_birth': '1990-01-01',
            'gender': 'male',
            'phone_number': '+250788123456',
            'email': 'john@example.com',
            'residential_address': '123 Main St',
            'district': 'Kigali',
            'sector': 'Nyarugenge',
            'village': 'Kimisagara',
            'marital_status': 'single',
            'number_of_dependents': 0,
        },
        'financial': {
            'employment_status': 'employed',
            'employment_contract_type': 'permanent',
            'employer_name': 'Test Company',
            'job_title': 'Developer',
            'employment_years': 5,
            'monthly_income': '500000',
            'annual_income': '6000000',
            'other_monthly_income': '100000',
            'source_of_other_income': 'Freelancing',
            'credit_score': '750',
            'monthly_debt_payments': '50000',
            'has_existing_loans': 'no',
            'existing_loans_amount': '0',
            'savings_account_balance': '1000000',
            'loan_collateral': 'Property',
            'guarantor_available': 'no',
        },
        'loan': {
            'loan_type': 'personal',
            'loan_amount': '2000000',
            'loan_purpose': 'business_expansion',
            'loan_purpose_description': 'Start a small business',
            'loan_term_months': 24,
            'repayment_frequency': 'monthly',
            'proposed_start_date': '2025-08-01',
            'bank_account_number': '1234567890',
            'bank_branch': 'Kigali Branch',
            'has_defaulted': 'no',
        }
    }
    
    try:
        # Replicate the exact logic from the view
        # Convert date strings back to date objects
        date_of_birth = session_data['personal']['date_of_birth']
        if isinstance(date_of_birth, str):
            from datetime import datetime
            date_of_birth = datetime.fromisoformat(date_of_birth).date()

        proposed_start_date = session_data['loan']['proposed_start_date']
        if isinstance(proposed_start_date, str):
            proposed_start_date = datetime.fromisoformat(proposed_start_date).date()

        # Convert Decimal strings back to Decimal objects
        def convert_to_decimal(value):
            if isinstance(value, str) and value:
                try:
                    return Decimal(value)
                except:
                    return None
            return value

        print("Creating loan application...")
        loan_application = LoanApplication.objects.create(
            applicant=user,
            # Personal Information
            full_name=session_data['personal']['full_name'],
            national_id=session_data['personal']['national_id'],
            date_of_birth=date_of_birth,
            gender=session_data['personal']['gender'],
            phone_number=session_data['personal']['phone_number'],
            email=session_data['personal']['email'],
            residential_address=session_data['personal']['residential_address'],
            district=session_data['personal']['district'],
            sector=session_data['personal']['sector'],
            village=session_data['personal']['village'],
            marital_status=session_data['personal']['marital_status'],
            number_of_dependents=session_data['personal']['number_of_dependents'],

            # Financial Information
            employment_status=session_data['financial']['employment_status'],
            employment_contract_type=session_data['financial'].get('employment_contract_type', ''),
            employer_name=session_data['financial'].get('employer_name', ''),
            job_title=session_data['financial'].get('job_title', ''),
            employment_years=session_data['financial'].get('employment_years'),
            monthly_income=convert_to_decimal(session_data['financial']['monthly_income']),
            annual_income=convert_to_decimal(session_data['financial'].get('annual_income')),
            other_monthly_income=convert_to_decimal(session_data['financial'].get('other_monthly_income')),
            source_of_other_income=session_data['financial'].get('source_of_other_income', ''),
            credit_score=convert_to_decimal(session_data['financial'].get('credit_score')),
            monthly_debt_payments=convert_to_decimal(session_data['financial'].get('monthly_debt_payments')),
            has_existing_loans=session_data['financial']['has_existing_loans'],
            existing_loans_amount=convert_to_decimal(session_data['financial'].get('existing_loans_amount')),
            savings_account_balance=convert_to_decimal(session_data['financial'].get('savings_account_balance')),
            loan_collateral=session_data['financial'].get('loan_collateral', ''),
            guarantor_available=session_data['financial']['guarantor_available'],
            guarantor_full_name=session_data['financial'].get('guarantor_full_name', ''),
            guarantor_national_id=session_data['financial'].get('guarantor_national_id', ''),
            guarantor_phone_number=session_data['financial'].get('guarantor_phone_number', ''),
            guarantor_address=session_data['financial'].get('guarantor_address', ''),
            guarantor_monthly_income=convert_to_decimal(session_data['financial'].get('guarantor_monthly_income')),
            guarantor_relationship=session_data['financial'].get('guarantor_relationship', ''),

            # Loan Details
            loan_type=session_data['loan']['loan_type'],
            loan_amount=convert_to_decimal(session_data['loan']['loan_amount']),
            loan_purpose=session_data['loan']['loan_purpose'],
            loan_purpose_description=session_data['loan']['loan_purpose_description'],
            loan_term_months=session_data['loan']['loan_term_months'],
            repayment_frequency=session_data['loan']['repayment_frequency'],
            proposed_start_date=proposed_start_date,
            bank_account_number=session_data['loan']['bank_account_number'],
            bank_branch=session_data['loan']['bank_branch'],
            has_defaulted=session_data['loan']['has_defaulted'],

            # Status
            status='submitted',
            submitted_at=timezone.now()
        )
        
        # Check if application was created
        final_count = LoanApplication.objects.count()
        print(f"Final loan applications count: {final_count}")
        
        if final_count > initial_count:
            print("✓ Loan application created successfully!")
            print(f"  Application ID: {loan_application.id}")
            print(f"  Application Number: {loan_application.application_number}")
            print(f"  Applicant: {loan_application.full_name}")
            print(f"  Loan Amount: {loan_application.loan_amount}")
            print(f"  Status: {loan_application.status}")
            return True
        else:
            print("✗ No new loan application was created")
            return False
            
    except Exception as e:
        print(f"✗ Direct creation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting direct loan application creation test...\n")
    
    success = test_direct_application_creation()
    
    if success:
        print("\n🎉 Direct creation test passed! The application creation logic works.")
        print("The issue might be in the view logic or form validation.")
    else:
        print("\n❌ Direct creation test failed. There's an issue with the application creation logic.")
