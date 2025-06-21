from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta

from .models import MLModel, PredictionResult, FeatureImportance, ModelPerformanceMetric
from .ml_models.loan_predictor import LoanPredictor
from .prediction_service import PredictionService
from .data_preprocessing import DataPreprocessor
from apps.loan_application.models import LoanApplication


class ModelListView(LoginRequiredMixin, ListView):
    """
    List view for ML models
    """
    model = MLModel
    template_name = 'ai_evaluation/model_list.html'
    context_object_name = 'models'
    paginate_by = 20

    def get_queryset(self):
        return MLModel.objects.all().order_by('-created_at')

    def dispatch(self, request, *args, **kwargs):
        # Only allow officers, managers, and admins
        if request.user.role not in ['officer', 'manager', 'admin']:
            messages.error(request, "You don't have permission to access AI models.")
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class ModelDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for a specific ML model
    """
    model = MLModel
    template_name = 'ai_evaluation/model_detail.html'
    context_object_name = 'ml_model'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ml_model = self.get_object()

        # Get feature importances
        context['feature_importances'] = ml_model.feature_importances.all()[:10]

        # Get recent predictions
        context['recent_predictions'] = ml_model.predictions.all()[:10]

        # Get performance metrics
        context['performance_metrics'] = ml_model.performance_metrics.all()[:5]

        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['officer', 'manager', 'admin']:
            messages.error(request, "You don't have permission to view AI models.")
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


@login_required
def evaluate_application(request, application_id):
    """
    Evaluate a loan application using AI/ML models
    """
    if request.user.role not in ['officer', 'manager', 'admin']:
        messages.error(request, "You don't have permission to run AI evaluations.")
        return redirect('loan_application:detail', pk=application_id)

    application = get_object_or_404(LoanApplication, pk=application_id)

    try:
        # Initialize prediction service
        prediction_service = PredictionService()

        # Run evaluation
        results = prediction_service.evaluate_application(application)

        # Update application with AI results
        application.ai_score = results.get('approval_probability', 0) * 100
        application.ai_recommendation = results.get('recommendation', 'manual_review')
        application.risk_level = results.get('risk_level', 'medium')
        application.save()

        messages.success(request, 'AI evaluation completed successfully!')

        # Return JSON response for AJAX requests
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'results': results
            })

    except Exception as e:
        messages.error(request, f'AI evaluation failed: {str(e)}')

        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    return redirect('loan_application:detail', pk=application_id)


@csrf_exempt
def batch_evaluate_applications(request):
    """
    Batch evaluate multiple applications
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if request.user.role not in ['officer', 'manager', 'admin']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        application_ids = data.get('application_ids', [])

        if not application_ids:
            return JsonResponse({'error': 'No applications specified'}, status=400)

        prediction_service = PredictionService()
        results = []

        for app_id in application_ids:
            try:
                application = LoanApplication.objects.get(pk=app_id)
                result = prediction_service.evaluate_application(application)

                # Update application
                application.ai_score = result.get('approval_probability', 0) * 100
                application.ai_recommendation = result.get('recommendation', 'manual_review')
                application.risk_level = result.get('risk_level', 'medium')
                application.save()

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

        return JsonResponse({
            'success': True,
            'results': results
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def train_model(request):
    """
    Train a new ML model
    """
    if request.user.role not in ['manager', 'admin']:
        messages.error(request, "You don't have permission to train models.")
        return redirect('ai_evaluation:model_list')

    if request.method == 'POST':
        try:
            # Initialize model trainer
            predictor = LoanPredictor()

            # Get training data
            preprocessor = DataPreprocessor()
            training_data = preprocessor.prepare_training_data()

            if training_data.empty:
                messages.error(request, 'No training data available.')
                return redirect('ai_evaluation:model_list')

            # Train model
            accuracy = predictor.train_model(training_data)

            # Save model
            model_path = f'loan_predictor_v{datetime.now().strftime("%Y%m%d_%H%M%S")}.joblib'
            predictor.save_model(model_path)

            # Create model record
            ml_model = MLModel.objects.create(
                name='Loan Predictor',
                version=datetime.now().strftime("%Y%m%d_%H%M%S"),
                model_type='ensemble',
                description='Random Forest model for loan approval prediction',
                model_file_path=model_path,
                accuracy=accuracy,
                training_data_size=len(training_data),
                trained_by=request.user,
                status='active'
            )

            # Set as default if it's the first model or has better accuracy
            if not MLModel.objects.filter(is_default=True).exists() or accuracy > 0.8:
                MLModel.objects.filter(is_default=True).update(is_default=False)
                ml_model.is_default = True
                ml_model.save()

            messages.success(request, f'Model trained successfully with {accuracy:.2%} accuracy!')

        except Exception as e:
            messages.error(request, f'Model training failed: {str(e)}')

    return redirect('ai_evaluation:model_list')


@login_required
def model_performance(request, model_id):
    """
    View model performance metrics
    """
    if request.user.role not in ['officer', 'manager', 'admin']:
        messages.error(request, "You don't have permission to view model performance.")
        return redirect('dashboard:home')

    ml_model = get_object_or_404(MLModel, pk=model_id)

    # Get performance metrics
    metrics = ml_model.performance_metrics.all().order_by('-evaluated_at')

    # Get recent predictions for analysis
    recent_predictions = ml_model.predictions.all()[:100]

    # Calculate prediction statistics
    prediction_stats = {
        'total_predictions': recent_predictions.count(),
        'avg_confidence': 0,
        'approval_rate': 0,
        'rejection_rate': 0
    }

    if recent_predictions:
        confidences = [p.confidence_score for p in recent_predictions if p.confidence_score]
        if confidences:
            prediction_stats['avg_confidence'] = sum(confidences) / len(confidences)

        # Calculate approval/rejection rates
        approvals = sum(1 for p in recent_predictions
                       if p.prediction_value.get('recommendation') == 'approve')
        prediction_stats['approval_rate'] = (approvals / len(recent_predictions)) * 100
        prediction_stats['rejection_rate'] = 100 - prediction_stats['approval_rate']

    context = {
        'ml_model': ml_model,
        'metrics': metrics,
        'prediction_stats': prediction_stats,
        'recent_predictions': recent_predictions[:10]
    }

    return render(request, 'ai_evaluation/model_performance.html', context)


@login_required
def prediction_history(request):
    """
    View prediction history
    """
    if request.user.role not in ['officer', 'manager', 'admin']:
        messages.error(request, "You don't have permission to view prediction history.")
        return redirect('dashboard:home')

    predictions = PredictionResult.objects.all().order_by('-created_at')

    # Filter by date range if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        predictions = predictions.filter(created_at__date__gte=date_from)
    if date_to:
        predictions = predictions.filter(created_at__date__lte=date_to)

    # Filter by model if provided
    model_id = request.GET.get('model')
    if model_id:
        predictions = predictions.filter(model_id=model_id)

    # Pagination
    paginator = Paginator(predictions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get available models for filter
    models = MLModel.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'models': models,
        'date_from': date_from,
        'date_to': date_to,
        'selected_model': model_id
    }

    return render(request, 'ai_evaluation/prediction_history.html', context)


@login_required
def model_management(request):
    """
    Placeholder view for AI Model Management
    """
    return render(request, 'ai_evaluation/model_management.html')
