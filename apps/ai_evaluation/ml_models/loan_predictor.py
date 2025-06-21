"""
Loan Prediction Model
This module contains the main loan prediction model using scikit-learn.
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import os
from django.conf import settings


class LoanPredictor:
    """
    Main loan prediction model class
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = [
            'age', 'income', 'loan_amount', 'credit_score', 
            'employment_years', 'debt_to_income_ratio',
            'loan_term', 'property_value'
        ]
        self.categorical_columns = [
            'employment_type', 'education_level', 'marital_status',
            'property_type', 'loan_purpose'
        ]
        
    def preprocess_data(self, data):
        """
        Preprocess the input data for prediction
        """
        # Handle categorical variables
        for col in self.categorical_columns:
            if col in data.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    data[col] = self.label_encoders[col].fit_transform(data[col])
                else:
                    data[col] = self.label_encoders[col].transform(data[col])
        
        # Scale numerical features
        numerical_data = data[self.feature_columns]
        scaled_data = self.scaler.fit_transform(numerical_data)
        
        return scaled_data
    
    def train_model(self, training_data):
        """
        Train the loan prediction model
        """
        # Prepare features and target
        X = training_data.drop('loan_approved', axis=1)
        y = training_data['loan_approved']
        
        # Preprocess data
        X_processed = self.preprocess_data(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_processed, y, test_size=0.2, random_state=42
        )
        
        # Train model
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Model Accuracy: {accuracy:.4f}")
        print(classification_report(y_test, y_pred))
        
        return accuracy
    
    def predict(self, application_data):
        """
        Predict loan approval for a single application
        """
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        # Preprocess the input data
        processed_data = self.preprocess_data(application_data)
        
        # Make prediction
        prediction = self.model.predict(processed_data)
        probability = self.model.predict_proba(processed_data)
        
        return {
            'prediction': int(prediction[0]),
            'probability': float(probability[0][1]),  # Probability of approval
            'risk_level': self._calculate_risk_level(probability[0][1])
        }
    
    def _calculate_risk_level(self, probability):
        """
        Calculate risk level based on approval probability
        """
        if probability >= 0.8:
            return 'Low Risk'
        elif probability >= 0.6:
            return 'Medium Risk'
        elif probability >= 0.4:
            return 'High Risk'
        else:
            return 'Very High Risk'
    
    def save_model(self, filepath=None):
        """
        Save the trained model to disk
        """
        if filepath is None:
            filepath = os.path.join(settings.BASE_DIR, 'ml_models', 'saved_models', 'loan_predictor.joblib')
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'categorical_columns': self.categorical_columns
        }
        
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath=None):
        """
        Load a trained model from disk
        """
        if filepath is None:
            filepath = os.path.join(settings.BASE_DIR, 'ml_models', 'saved_models', 'loan_predictor.joblib')
        
        if os.path.exists(filepath):
            model_data = joblib.load(filepath)
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.label_encoders = model_data['label_encoders']
            self.feature_columns = model_data['feature_columns']
            self.categorical_columns = model_data['categorical_columns']
            print(f"Model loaded from {filepath}")
        else:
            print(f"Model file not found at {filepath}")
