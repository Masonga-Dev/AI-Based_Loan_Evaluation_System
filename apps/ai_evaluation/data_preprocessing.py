"""
Data Preprocessing for AI/ML Models
This module handles data preparation and feature engineering
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from sklearn.preprocessing import StandardScaler, LabelEncoder
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class DataPreprocessor:
    """
    Data preprocessing class for loan applications
    """
    
    def __init__(self):
        self.feature_columns = [
            'age', 'income', 'loan_amount', 'credit_score', 
            'employment_years', 'debt_to_income_ratio',
            'loan_term', 'property_value', 'down_payment'
        ]
        
        self.categorical_columns = [
            'employment_type', 'education_level', 'marital_status',
            'property_type', 'loan_purpose', 'loan_type'
        ]
        
        self.scaler = StandardScaler()
        self.label_encoders = {}
    
    def prepare_training_data(self):
        """
        Prepare training data from historical loan applications
        """
        try:
            from apps.loan_application.models import LoanApplication
            
            # Get completed applications (approved or rejected)
            applications = LoanApplication.objects.filter(
                status__in=['approved', 'rejected']
            ).select_related('applicant', 'applicant__profile')
            
            if not applications.exists():
                logger.warning("No training data available")
                return pd.DataFrame()
            
            # Convert to DataFrame
            data = []
            for app in applications:
                row = self.extract_features_from_application(app)
                if row:
                    # Add target variable
                    row['loan_approved'] = 1 if app.status == 'approved' else 0
                    data.append(row)
            
            if not data:
                logger.warning("No valid training data extracted")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Clean and preprocess data
            df = self.clean_data(df)
            df = self.engineer_features(df)
            
            logger.info(f"Prepared training data with {len(df)} samples")
            return df
            
        except Exception as e:
            logger.error(f"Failed to prepare training data: {str(e)}")
            return pd.DataFrame()
    
    def prepare_application_data(self, application):
        """
        Prepare data for a single application prediction
        """
        try:
            # Extract features
            features = self.extract_features_from_application(application)
            
            if not features:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame([features])
            
            # Clean and engineer features
            df = self.clean_data(df)
            df = self.engineer_features(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to prepare application data: {str(e)}")
            return None
    
    def extract_features_from_application(self, application):
        """
        Extract features from a loan application
        """
        try:
            applicant = application.applicant
            
            # Calculate age
            age = None
            if applicant.date_of_birth:
                age = (datetime.now().date() - applicant.date_of_birth).days / 365.25
            
            # Calculate debt-to-income ratio
            debt_to_income_ratio = 0
            if applicant.annual_income and applicant.monthly_debt_payments:
                monthly_income = float(applicant.annual_income) / 12
                debt_to_income_ratio = (float(applicant.monthly_debt_payments) / monthly_income) * 100
            
            # Extract features
            features = {
                # Applicant features
                'age': age or 35,  # Default age if not provided
                'income': float(applicant.annual_income) if applicant.annual_income else 0,
                'credit_score': applicant.credit_score or 650,  # Default credit score
                'employment_years': applicant.employment_years or 0,
                'debt_to_income_ratio': debt_to_income_ratio,
                
                # Loan features
                'loan_amount': float(application.loan_amount),
                'loan_term': application.loan_term_months,
                'property_value': float(application.property_value) if application.property_value else 0,
                'down_payment': float(application.down_payment) if application.down_payment else 0,
                
                # Categorical features
                'employment_type': applicant.employment_status or 'employed',
                'education_level': getattr(applicant.profile, 'education_level', 'bachelor') if hasattr(applicant, 'profile') else 'bachelor',
                'marital_status': getattr(applicant.profile, 'marital_status', 'single') if hasattr(applicant, 'profile') else 'single',
                'property_type': application.property_type or 'single_family',
                'loan_purpose': application.loan_purpose,
                'loan_type': application.loan_type,
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract features from application {application.id}: {str(e)}")
            return None
    
    def clean_data(self, df):
        """
        Clean and validate data
        """
        try:
            # Handle missing values
            numeric_columns = ['age', 'income', 'loan_amount', 'credit_score', 
                             'employment_years', 'debt_to_income_ratio', 'loan_term',
                             'property_value', 'down_payment']
            
            for col in numeric_columns:
                if col in df.columns:
                    # Fill missing values with median
                    df[col] = df[col].fillna(df[col].median())
                    
                    # Ensure positive values where appropriate
                    if col in ['income', 'loan_amount', 'credit_score', 'employment_years', 'loan_term']:
                        df[col] = df[col].abs()
            
            # Handle categorical missing values
            categorical_columns = ['employment_type', 'education_level', 'marital_status',
                                 'property_type', 'loan_purpose', 'loan_type']
            
            for col in categorical_columns:
                if col in df.columns:
                    df[col] = df[col].fillna('unknown')
            
            # Remove outliers (optional)
            df = self.remove_outliers(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Data cleaning failed: {str(e)}")
            return df
    
    def engineer_features(self, df):
        """
        Create new features from existing ones
        """
        try:
            # Loan-to-income ratio
            if 'loan_amount' in df.columns and 'income' in df.columns:
                df['loan_to_income_ratio'] = df['loan_amount'] / (df['income'] + 1)  # +1 to avoid division by zero
            
            # Loan-to-value ratio (for secured loans)
            if 'loan_amount' in df.columns and 'property_value' in df.columns:
                df['loan_to_value_ratio'] = df['loan_amount'] / (df['property_value'] + 1)
            
            # Monthly payment estimate
            if all(col in df.columns for col in ['loan_amount', 'loan_term']):
                # Assume 5% interest rate for estimation
                interest_rate = 0.05 / 12  # Monthly rate
                df['estimated_monthly_payment'] = (
                    df['loan_amount'] * interest_rate * (1 + interest_rate) ** df['loan_term']
                ) / ((1 + interest_rate) ** df['loan_term'] - 1)
            
            # Payment-to-income ratio
            if 'estimated_monthly_payment' in df.columns and 'income' in df.columns:
                monthly_income = df['income'] / 12
                df['payment_to_income_ratio'] = df['estimated_monthly_payment'] / (monthly_income + 1)
            
            # Credit score categories
            if 'credit_score' in df.columns:
                df['credit_score_category'] = pd.cut(
                    df['credit_score'],
                    bins=[0, 580, 670, 740, 800, 850],
                    labels=['poor', 'fair', 'good', 'very_good', 'excellent']
                )
            
            # Age categories
            if 'age' in df.columns:
                df['age_category'] = pd.cut(
                    df['age'],
                    bins=[0, 25, 35, 45, 55, 100],
                    labels=['young', 'young_adult', 'middle_aged', 'mature', 'senior']
                )
            
            # Employment stability score
            if 'employment_years' in df.columns:
                df['employment_stability'] = np.where(
                    df['employment_years'] >= 2, 'stable',
                    np.where(df['employment_years'] >= 1, 'moderate', 'unstable')
                )
            
            return df
            
        except Exception as e:
            logger.error(f"Feature engineering failed: {str(e)}")
            return df
    
    def remove_outliers(self, df, method='iqr'):
        """
        Remove outliers from numerical columns
        """
        try:
            if method == 'iqr':
                numeric_columns = df.select_dtypes(include=[np.number]).columns
                
                for col in numeric_columns:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    # Cap outliers instead of removing them
                    df[col] = np.where(df[col] < lower_bound, lower_bound, df[col])
                    df[col] = np.where(df[col] > upper_bound, upper_bound, df[col])
            
            return df
            
        except Exception as e:
            logger.error(f"Outlier removal failed: {str(e)}")
            return df
    
    def encode_categorical_features(self, df):
        """
        Encode categorical features for ML models
        """
        try:
            df_encoded = df.copy()
            
            for col in self.categorical_columns:
                if col in df_encoded.columns:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                        df_encoded[col] = self.label_encoders[col].fit_transform(df_encoded[col].astype(str))
                    else:
                        # Handle unseen categories
                        unique_values = set(df_encoded[col].astype(str))
                        known_values = set(self.label_encoders[col].classes_)
                        
                        if unique_values.issubset(known_values):
                            df_encoded[col] = self.label_encoders[col].transform(df_encoded[col].astype(str))
                        else:
                            # Add unknown category
                            unknown_mask = ~df_encoded[col].astype(str).isin(known_values)
                            df_encoded.loc[unknown_mask, col] = 'unknown'
                            
                            # Update encoder if needed
                            if 'unknown' not in known_values:
                                all_values = list(known_values) + ['unknown']
                                self.label_encoders[col].classes_ = np.array(all_values)
                            
                            df_encoded[col] = self.label_encoders[col].transform(df_encoded[col].astype(str))
            
            return df_encoded
            
        except Exception as e:
            logger.error(f"Categorical encoding failed: {str(e)}")
            return df
    
    def scale_features(self, df, fit=False):
        """
        Scale numerical features
        """
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            df_scaled = df.copy()
            
            if fit:
                df_scaled[numeric_columns] = self.scaler.fit_transform(df[numeric_columns])
            else:
                df_scaled[numeric_columns] = self.scaler.transform(df[numeric_columns])
            
            return df_scaled
            
        except Exception as e:
            logger.error(f"Feature scaling failed: {str(e)}")
            return df
