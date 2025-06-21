from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class MLModel(models.Model):
    """
    Machine Learning models used for loan evaluation
    """
    MODEL_TYPE_CHOICES = [
        ('classification', 'Classification'),
        ('regression', 'Regression'),
        ('ensemble', 'Ensemble'),
        ('neural_network', 'Neural Network'),
    ]

    STATUS_CHOICES = [
        ('training', 'Training'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
    ]

    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES)
    description = models.TextField()

    # Model file information
    model_file_path = models.CharField(max_length=500)
    model_size = models.IntegerField(help_text="Model file size in bytes")

    # Model performance metrics
    accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    precision = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    recall = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    f1_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # Model configuration
    hyperparameters = models.JSONField(default=dict)
    feature_columns = models.JSONField(default=list)
    target_column = models.CharField(max_length=100, blank=True)

    # Model status and lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='training')
    is_default = models.BooleanField(default=False)

    # Training information
    training_data_size = models.IntegerField(null=True, blank=True)
    training_duration = models.DurationField(null=True, blank=True)
    trained_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ml_model'
        verbose_name = 'ML Model'
        verbose_name_plural = 'ML Models'
        unique_together = ['name', 'version']

    def __str__(self):
        return f"{self.name} v{self.version}"


class PredictionResult(models.Model):
    """
    Store AI/ML prediction results for loan applications
    """
    PREDICTION_TYPE_CHOICES = [
        ('approval', 'Loan Approval'),
        ('risk_assessment', 'Risk Assessment'),
        ('credit_score', 'Credit Score Prediction'),
        ('default_probability', 'Default Probability'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        'loan_application.LoanApplication',
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='predictions')

    # Prediction details
    prediction_type = models.CharField(max_length=30, choices=PREDICTION_TYPE_CHOICES)
    prediction_value = models.JSONField()  # Store various prediction outputs
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4)

    # Input features used for prediction
    input_features = models.JSONField()

    # Prediction metadata
    processing_time = models.DurationField()
    model_version = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prediction_result'
        verbose_name = 'Prediction Result'
        verbose_name_plural = 'Prediction Results'
        ordering = ['-created_at']

    def __str__(self):
        return f"Prediction for {self.application.application_number}"


class FeatureImportance(models.Model):
    """
    Store feature importance for model interpretability
    """
    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='feature_importances')
    feature_name = models.CharField(max_length=100)
    importance_score = models.DecimalField(max_digits=8, decimal_places=6)
    rank = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feature_importance'
        verbose_name = 'Feature Importance'
        verbose_name_plural = 'Feature Importances'
        unique_together = ['model', 'feature_name']
        ordering = ['rank']

    def __str__(self):
        return f"{self.feature_name} - {self.importance_score}"


class ModelPerformanceMetric(models.Model):
    """
    Track model performance over time
    """
    METRIC_TYPE_CHOICES = [
        ('accuracy', 'Accuracy'),
        ('precision', 'Precision'),
        ('recall', 'Recall'),
        ('f1_score', 'F1 Score'),
        ('auc_roc', 'AUC-ROC'),
        ('confusion_matrix', 'Confusion Matrix'),
    ]

    model = models.ForeignKey(MLModel, on_delete=models.CASCADE, related_name='performance_metrics')
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPE_CHOICES)
    metric_value = models.JSONField()  # Can store single values or complex metrics like confusion matrix

    # Evaluation dataset information
    dataset_size = models.IntegerField()
    dataset_description = models.CharField(max_length=200, blank=True)

    evaluated_at = models.DateTimeField(auto_now_add=True)
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'model_performance_metric'
        verbose_name = 'Model Performance Metric'
        verbose_name_plural = 'Model Performance Metrics'
        ordering = ['-evaluated_at']

    def __str__(self):
        return f"{self.model.name} - {self.metric_type}"
