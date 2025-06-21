"""
Prediction Service for AI-based Loan Evaluation
This module handles the prediction logic and model management
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
import logging
import os

from .models import MLModel, PredictionResult
from .ml_models.loan_predictor import LoanPredictor
from .data_preprocessing import DataPreprocessor

logger = logging.getLogger(__name__)
User = get_user_model()


class PredictionService:
    """
    Main service class for handling loan predictions
    """
    
    def __init__(self):
        self.predictor = LoanPredictor()
        self.preprocessor = DataPreprocessor()
        self.default_model = self.get_default_model()
        
        # Load the default model if available
        if self.default_model:
            try:
                model_path = os.path.join(settings.BASE_DIR, self.default_model.model_file_path)
                self.predictor.load_model(model_path)
            except Exception as e:
                logger.warning(f"Could not load default model: {str(e)}")
    
    def get_default_model(self):
        """
        Get the default active ML model
        """
        try:
            return MLModel.objects.filter(is_default=True, status='active').first()
        except Exception as e:
            logger.error(f"Error getting default model: {str(e)}")
            return None
    
    def evaluate_application(self, application):
        """
        Evaluate a loan application and return prediction results
        """
        try:
            # Prepare application data for prediction
            application_data = self.preprocessor.prepare_application_data(application)
            
            if application_data is None:
                raise ValueError("Could not prepare application data for prediction")
            
            # Make prediction
            if self.predictor.model is not None:
                prediction_result = self.predictor.predict(application_data)
            else:
                # Fallback to rule-based evaluation if no ML model is available
                prediction_result = self.rule_based_evaluation(application)
            
            # Store prediction result
            self.store_prediction_result(application, prediction_result)
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Application evaluation failed: {str(e)}")
            raise e
    
    def rule_based_evaluation(self, application):
        """
        Fallback rule-based evaluation when ML model is not available
        """
        try:
            score = 0
            max_score = 100
            
            # Credit score evaluation (30% weight)
            if application.applicant.credit_score:
                credit_score = application.applicant.credit_score
                if credit_score >= 750:
                    score += 30
                elif credit_score >= 700:
                    score += 25
                elif credit_score >= 650:
                    score += 20
                elif credit_score >= 600:
                    score += 15
                else:
                    score += 5
            else:
                score += 15  # Neutral score if no credit score
            
            # Income evaluation (25% weight)
            if application.applicant.annual_income:
                income = float(application.applicant.annual_income)
                loan_amount = float(application.loan_amount)
                
                # Debt-to-income ratio
                if income > 0:
                    loan_to_income_ratio = (loan_amount / income) * 100
                    if loan_to_income_ratio <= 200:  # 2x annual income
                        score += 25
                    elif loan_to_income_ratio <= 300:
                        score += 20
                    elif loan_to_income_ratio <= 400:
                        score += 15
                    else:
                        score += 5
                else:
                    score += 10
            else:
                score += 10
            
            # Employment evaluation (20% weight)
            if application.applicant.employment_status == 'employed':
                score += 20
                if application.applicant.employment_years and application.applicant.employment_years >= 2:
                    score += 5  # Bonus for stable employment
            elif application.applicant.employment_status == 'self_employed':
                score += 15
            else:
                score += 5
            
            # Loan amount evaluation (15% weight)
            loan_amount = float(application.loan_amount)
            if loan_amount <= 50000:
                score += 15
            elif loan_amount <= 100000:
                score += 12
            elif loan_amount <= 250000:
                score += 10
            else:
                score += 5
            
            # Loan term evaluation (10% weight)
            if application.loan_term_months <= 36:
                score += 10
            elif application.loan_term_months <= 60:
                score += 8
            else:
                score += 5
            
            # Calculate probability and recommendation
            probability = min(score / max_score, 1.0)
            
            if probability >= 0.7:
                recommendation = 'approve'
                risk_level = 'Low Risk'
            elif probability >= 0.5:
                recommendation = 'manual_review'
                risk_level = 'Medium Risk'
            elif probability >= 0.3:
                recommendation = 'manual_review'
                risk_level = 'High Risk'
            else:
                recommendation = 'reject'
                risk_level = 'Very High Risk'
            
            return {
                'prediction': 1 if recommendation == 'approve' else 0,
                'approval_probability': probability,
                'recommendation': recommendation,
                'risk_level': risk_level,
                'confidence_score': 0.8,  # Rule-based has consistent confidence
                'evaluation_method': 'rule_based'
            }
            
        except Exception as e:
            logger.error(f"Rule-based evaluation failed: {str(e)}")
            # Return neutral result
            return {
                'prediction': 0,
                'approval_probability': 0.5,
                'recommendation': 'manual_review',
                'risk_level': 'Medium Risk',
                'confidence_score': 0.5,
                'evaluation_method': 'fallback'
            }
    
    def store_prediction_result(self, application, prediction_result):
        """
        Store prediction result in the database
        """
        try:
            # Prepare input features
            input_features = self.preprocessor.prepare_application_data(application)
            if input_features is not None:
                input_features_dict = input_features.to_dict('records')[0]
            else:
                input_features_dict = {}
            
            # Create prediction result record
            prediction = PredictionResult.objects.create(
                application=application,
                model=self.default_model,
                prediction_type='approval',
                prediction_value=prediction_result,
                confidence_score=prediction_result.get('confidence_score', 0),
                input_features=input_features_dict,
                processing_time=timedelta(seconds=1),  # Placeholder
                model_version=self.default_model.version if self.default_model else 'rule_based'
            )
            
            logger.info(f"Prediction result stored for application {application.id}")
            return prediction
            
        except Exception as e:
            logger.error(f"Failed to store prediction result: {str(e)}")
            return None
    
    def batch_evaluate_applications(self, application_ids):
        """
        Evaluate multiple applications in batch
        """
        results = []
        
        for app_id in application_ids:
            try:
                from apps.loan_application.models import LoanApplication
                application = LoanApplication.objects.get(pk=app_id)
                result = self.evaluate_application(application)
                
                results.append({
                    'application_id': app_id,
                    'success': True,
                    'result': result
                })
                
            except Exception as e:
                results.append({
                    'application_id': app_id,
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def get_model_performance_summary(self, model_id=None):
        """
        Get performance summary for a model
        """
        try:
            if model_id:
                model = MLModel.objects.get(pk=model_id)
            else:
                model = self.default_model
            
            if not model:
                return None
            
            # Get recent predictions
            recent_predictions = model.predictions.filter(
                created_at__gte=datetime.now() - timedelta(days=30)
            )
            
            total_predictions = recent_predictions.count()
            if total_predictions == 0:
                return {
                    'model': model,
                    'total_predictions': 0,
                    'avg_confidence': 0,
                    'approval_rate': 0,
                    'accuracy': model.accuracy or 0
                }
            
            # Calculate statistics
            confidences = [p.confidence_score for p in recent_predictions if p.confidence_score]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            approvals = recent_predictions.filter(
                prediction_value__recommendation='approve'
            ).count()
            approval_rate = (approvals / total_predictions) * 100
            
            return {
                'model': model,
                'total_predictions': total_predictions,
                'avg_confidence': avg_confidence,
                'approval_rate': approval_rate,
                'accuracy': model.accuracy or 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get model performance summary: {str(e)}")
            return None
    
    def validate_prediction_input(self, application):
        """
        Validate that application has sufficient data for prediction
        """
        required_fields = [
            'loan_amount',
            'loan_term_months',
            'applicant__annual_income'
        ]
        
        missing_fields = []
        
        if not application.loan_amount:
            missing_fields.append('loan_amount')
        
        if not application.loan_term_months:
            missing_fields.append('loan_term_months')
        
        if not application.applicant.annual_income:
            missing_fields.append('annual_income')
        
        return len(missing_fields) == 0, missing_fields
