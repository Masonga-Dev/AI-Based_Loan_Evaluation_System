from django.db import models
from django.contrib.auth import get_user_model
from apps.loan_application.models import LoanApplication, ApplicationDocument
import uuid

User = get_user_model()


class AdminNotification(models.Model):
    """
    Notifications for admin users about system events
    """
    NOTIFICATION_TYPES = [
        ('missing_document', 'Missing Document'),
        ('document_flagged', 'Document Flagged'),
        ('application_submitted', 'Application Submitted'),
        ('ai_prediction_ready', 'AI Prediction Ready'),
        ('manual_review_required', 'Manual Review Required'),
        ('user_suspicious', 'Suspicious User Activity'),
        ('system_alert', 'System Alert'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    related_application = models.ForeignKey(LoanApplication, on_delete=models.CASCADE, null=True, blank=True)
    related_document = models.ForeignKey(ApplicationDocument, on_delete=models.CASCADE, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications_about')
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    action_required = models.BooleanField(default=False)
    action_taken = models.BooleanField(default=False)
    
    # Metadata
    data = models.JSONField(default=dict, blank=True)  # Additional context data
    link_url = models.URLField(blank=True)  # Direct link to relevant page
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'admin_notification'
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.recipient.get_full_name()}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def mark_action_taken(self):
        """Mark that action has been taken on this notification"""
        self.action_taken = True
        self.save()

    def archive(self):
        """Archive the notification"""
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()

    @property
    def age_in_hours(self):
        """Get notification age in hours"""
        return (timezone.now() - self.created_at).total_seconds() / 3600

    @property
    def is_urgent_and_unread(self):
        """Check if notification is urgent and unread"""
        return self.priority == 'urgent' and not self.is_read

    @property
    def priority_color(self):
        """Get color class for priority level"""
        colors = {
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger'
        }
        return colors.get(self.priority, 'secondary')


class NotificationTemplate(models.Model):
    """
    Templates for generating consistent notifications
    """
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.CharField(max_length=30, choices=AdminNotification.NOTIFICATION_TYPES)
    default_priority = models.CharField(max_length=10, choices=AdminNotification.PRIORITY_LEVELS, default='medium')

    title_template = models.CharField(max_length=200)
    message_template = models.TextField()

    # Auto-assignment rules
    assign_to_role = models.CharField(max_length=20, blank=True, help_text="Auto-assign to users with this role")
    requires_action = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_template'
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'

    def __str__(self):
        return self.name

    def generate_notification(self, context=None, recipient=None):
        """Generate a notification from this template"""
        if context is None:
            context = {}

        # Format title and message with context
        title = self.title_template.format(**context)
        message = self.message_template.format(**context)

        notification_data = {
            'notification_type': self.notification_type,
            'priority': self.default_priority,
            'title': title,
            'message': message,
            'action_required': self.requires_action,
            'data': context
        }

        if recipient:
            notification_data['recipient'] = recipient

        return AdminNotification.objects.create(**notification_data)


class NotificationRule(models.Model):
    """
    Rules for automatic notification generation
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Trigger conditions
    trigger_event = models.CharField(max_length=50, choices=[
        ('application_submitted', 'Application Submitted'),
        ('document_uploaded', 'Document Uploaded'),
        ('ai_prediction_complete', 'AI Prediction Complete'),
        ('user_login_failed', 'Failed Login Attempt'),
        ('document_flagged', 'Document Flagged'),
        ('application_approved', 'Application Approved'),
        ('application_rejected', 'Application Rejected'),
        ('user_role_changed', 'User Role Changed'),
        ('system_error', 'System Error'),
    ])

    # Conditions (JSON field for flexible conditions)
    conditions = models.JSONField(default=dict, help_text="Conditions that must be met to trigger notification")

    # Notification settings
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE)
    delay_minutes = models.IntegerField(default=0, help_text="Delay before sending notification")

    # Targeting
    target_roles = models.JSONField(default=list, help_text="List of roles to notify")
    target_users = models.ManyToManyField(User, blank=True, help_text="Specific users to notify")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_rule'
        verbose_name = 'Notification Rule'
        verbose_name_plural = 'Notification Rules'

    def __str__(self):
        return self.name


class NotificationBatch(models.Model):
    """
    Batch notifications for bulk operations
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Batch settings
    notification_type = models.CharField(max_length=30, choices=AdminNotification.NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=AdminNotification.PRIORITY_LEVELS, default='medium')

    title_template = models.CharField(max_length=200)
    message_template = models.TextField()

    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')

    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_batches')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification_batch'
        verbose_name = 'Notification Batch'
        verbose_name_plural = 'Notification Batches'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"


class AnalyticsReport(models.Model):
    """
    Saved analytics reports with custom parameters
    """
    REPORT_TYPES = [
        ('loan_performance', 'Loan Performance'),
        ('user_activity', 'User Activity'),
        ('document_analysis', 'Document Analysis'),
        ('ai_accuracy', 'AI Model Accuracy'),
        ('approval_trends', 'Approval Trends'),
        ('risk_assessment', 'Risk Assessment'),
        ('geographic_analysis', 'Geographic Analysis'),
        ('time_series', 'Time Series Analysis'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)

    # Report parameters (JSON field for flexible configuration)
    parameters = models.JSONField(default=dict)

    # Data and results
    data = models.JSONField(default=dict)
    generated_at = models.DateTimeField(null=True, blank=True)

    # Scheduling
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reports')
    shared_with = models.ManyToManyField(User, blank=True, related_name='shared_reports')
    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_report'
        verbose_name = 'Analytics Report'
        verbose_name_plural = 'Analytics Reports'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def generate_report(self):
        """Generate report data based on type and parameters"""
        from django.db.models import Count, Avg, Sum
        from django.utils import timezone
        from datetime import timedelta

        data = {}

        if self.report_type == 'loan_performance':
            # Loan performance metrics
            applications = LoanApplication.objects.all()

            if self.parameters.get('date_range'):
                start_date = timezone.now() - timedelta(days=self.parameters['date_range'])
                applications = applications.filter(created_at__gte=start_date)

            data = {
                'total_applications': applications.count(),
                'approved_count': applications.filter(status='approved').count(),
                'rejected_count': applications.filter(status='rejected').count(),
                'pending_count': applications.filter(status='pending').count(),
                'average_amount': applications.aggregate(avg=Avg('loan_amount'))['avg'] or 0,
                'total_amount': applications.aggregate(sum=Sum('loan_amount'))['sum'] or 0,
                'approval_rate': self._calculate_approval_rate(applications),
                'status_breakdown': list(applications.values('status').annotate(count=Count('id'))),
                'monthly_trends': self._get_monthly_trends(applications),
            }

        elif self.report_type == 'user_activity':
            # User activity metrics
            users = User.objects.all()
            activities = UserActivity.objects.all()

            if self.parameters.get('date_range'):
                start_date = timezone.now() - timedelta(days=self.parameters['date_range'])
                activities = activities.filter(created_at__gte=start_date)

            data = {
                'total_users': users.count(),
                'active_users': users.filter(is_active=True).count(),
                'new_users': users.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count(),
                'role_distribution': list(users.values('role').annotate(count=Count('id'))),
                'activity_types': list(activities.values('activity_type').annotate(count=Count('id'))),
                'daily_activity': self._get_daily_activity(activities),
            }

        elif self.report_type == 'ai_accuracy':
            # AI model accuracy metrics
            applications = LoanApplication.objects.exclude(ai_recommendation__isnull=True)

            data = {
                'total_predictions': applications.count(),
                'accuracy_rate': self._calculate_ai_accuracy(applications),
                'prediction_distribution': list(applications.values('ai_recommendation').annotate(count=Count('id'))),
                'score_ranges': self._get_score_distribution(applications),
            }

        self.data = data
        self.generated_at = timezone.now()
        self.save()

        return data

    def _calculate_approval_rate(self, applications):
        """Calculate approval rate percentage"""
        total = applications.count()
        if total == 0:
            return 0
        approved = applications.filter(status='approved').count()
        return round((approved / total) * 100, 2)

    def _calculate_ai_accuracy(self, applications):
        """Calculate AI prediction accuracy"""
        total = applications.filter(status__in=['approved', 'rejected']).count()
        if total == 0:
            return 0

        correct = 0
        for app in applications.filter(status__in=['approved', 'rejected']):
            if (app.status == 'approved' and app.ai_recommendation == 'approve') or \
               (app.status == 'rejected' and app.ai_recommendation == 'reject'):
                correct += 1

        return round((correct / total) * 100, 2)

    def _get_monthly_trends(self, applications):
        """Get monthly application trends"""
        from django.db.models.functions import TruncMonth

        return list(
            applications.annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

    def _get_daily_activity(self, activities):
        """Get daily activity trends"""
        from django.db.models.functions import TruncDate

        return list(
            activities.annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

    def _get_score_distribution(self, applications):
        """Get AI score distribution"""
        ranges = [
            (0, 20, 'Very Low'),
            (20, 40, 'Low'),
            (40, 60, 'Medium'),
            (60, 80, 'High'),
            (80, 100, 'Very High'),
        ]

        distribution = []
        for min_score, max_score, label in ranges:
            count = applications.filter(
                ai_score__gte=min_score,
                ai_score__lt=max_score
            ).count()
            distribution.append({
                'range': label,
                'count': count,
                'min_score': min_score,
                'max_score': max_score
            })

        return distribution


class DashboardWidget(models.Model):
    """
    Customizable dashboard widgets for analytics display
    """
    WIDGET_TYPES = [
        ('chart_line', 'Line Chart'),
        ('chart_bar', 'Bar Chart'),
        ('chart_pie', 'Pie Chart'),
        ('chart_doughnut', 'Doughnut Chart'),
        ('metric_card', 'Metric Card'),
        ('table', 'Data Table'),
        ('gauge', 'Gauge Chart'),
        ('heatmap', 'Heat Map'),
    ]

    name = models.CharField(max_length=200)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)

    # Widget configuration
    config = models.JSONField(default=dict)
    data_source = models.CharField(max_length=100)  # Method name or query identifier

    # Layout
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=6)  # Grid columns (1-12)
    height = models.IntegerField(default=4)  # Grid rows

    # Access control
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_widgets')
    is_public = models.BooleanField(default=True)

    # Status
    is_active = models.BooleanField(default=True)
    refresh_interval = models.IntegerField(default=300)  # Seconds

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_widget'
        verbose_name = 'Dashboard Widget'
        verbose_name_plural = 'Dashboard Widgets'
        ordering = ['position_y', 'position_x']

    def __str__(self):
        return self.name


class ExportJob(models.Model):
    """
    Track data export jobs and their status
    """
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ]

    EXPORT_TYPES = [
        ('applications', 'Loan Applications'),
        ('users', 'Users'),
        ('documents', 'Documents'),
        ('analytics', 'Analytics Report'),
        ('notifications', 'Notifications'),
    ]

    name = models.CharField(max_length=200)
    export_type = models.CharField(max_length=20, choices=EXPORT_TYPES)
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS)

    # Export parameters
    parameters = models.JSONField(default=dict)

    # Status tracking
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')

    # File information
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    download_count = models.IntegerField(default=0)

    # Progress tracking
    total_records = models.IntegerField(default=0)
    processed_records = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'export_job'
        verbose_name = 'Export Job'
        verbose_name_plural = 'Export Jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def progress_percentage(self):
        """Calculate export progress percentage"""
        if self.total_records == 0:
            return 0
        return round((self.processed_records / self.total_records) * 100, 2)


class AIModel(models.Model):
    """
    AI Model configuration and metadata
    """
    MODEL_TYPES = [
        ('loan_approval', 'Loan Approval Model'),
        ('risk_assessment', 'Risk Assessment Model'),
        ('document_verification', 'Document Verification Model'),
        ('fraud_detection', 'Fraud Detection Model'),
        ('credit_scoring', 'Credit Scoring Model'),
    ]

    MODEL_STATUS = [
        ('training', 'Training'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=30, choices=MODEL_TYPES)
    version = models.CharField(max_length=50)

    # Model configuration
    config = models.JSONField(default=dict)
    parameters = models.JSONField(default=dict)

    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)

    # Training information
    training_data_size = models.IntegerField(null=True, blank=True)
    training_started_at = models.DateTimeField(null=True, blank=True)
    training_completed_at = models.DateTimeField(null=True, blank=True)

    # Status and deployment
    status = models.CharField(max_length=20, choices=MODEL_STATUS, default='training')
    is_default = models.BooleanField(default=False)
    deployment_date = models.DateTimeField(null=True, blank=True)

    # File paths
    model_file_path = models.CharField(max_length=500, blank=True)
    weights_file_path = models.CharField(max_length=500, blank=True)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_models')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_model'
        verbose_name = 'AI Model'
        verbose_name_plural = 'AI Models'
        ordering = ['-created_at']
        unique_together = ['model_type', 'version']

    def __str__(self):
        return f"{self.name} v{self.version}"

    def activate(self):
        """Activate this model and deactivate others of the same type"""
        # Deactivate other models of the same type
        AIModel.objects.filter(model_type=self.model_type, is_default=True).update(is_default=False)

        # Activate this model
        self.is_default = True
        self.status = 'active'
        self.deployment_date = timezone.now()
        self.save()

    @property
    def training_duration(self):
        """Calculate training duration in hours"""
        if self.training_started_at and self.training_completed_at:
            duration = self.training_completed_at - self.training_started_at
            return round(duration.total_seconds() / 3600, 2)
        return None

    @property
    def performance_score(self):
        """Calculate overall performance score"""
        if self.accuracy and self.precision and self.recall:
            return round((self.accuracy + self.precision + self.recall) / 3, 2)
        return None


class AIPrediction(models.Model):
    """
    Track AI predictions and their outcomes
    """
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE, related_name='predictions')
    application = models.ForeignKey('loan_application.LoanApplication', on_delete=models.CASCADE, related_name='ai_predictions')

    # Prediction details
    prediction = models.CharField(max_length=20, choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('review', 'Manual Review'),
    ])
    confidence_score = models.FloatField()
    risk_score = models.FloatField(null=True, blank=True)

    # Feature importance (JSON field for model interpretability)
    feature_importance = models.JSONField(default=dict)

    # Prediction metadata
    processing_time = models.FloatField(help_text="Processing time in seconds")
    model_version = models.CharField(max_length=50)

    # Outcome tracking
    actual_outcome = models.CharField(max_length=20, choices=[
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('pending', 'Pending'),
    ], null=True, blank=True)

    is_correct = models.BooleanField(null=True, blank=True)
    feedback_provided = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_prediction'
        verbose_name = 'AI Prediction'
        verbose_name_plural = 'AI Predictions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.model.name} - {self.prediction} ({self.confidence_score}%)"

    def update_outcome(self, actual_outcome):
        """Update the actual outcome and calculate correctness"""
        self.actual_outcome = actual_outcome

        # Determine if prediction was correct
        if self.prediction == 'approve' and actual_outcome == 'approved':
            self.is_correct = True
        elif self.prediction == 'reject' and actual_outcome == 'rejected':
            self.is_correct = True
        else:
            self.is_correct = False

        self.save()


class ModelPerformanceMetric(models.Model):
    """
    Track model performance metrics over time
    """
    model = models.ForeignKey(AIModel, on_delete=models.CASCADE, related_name='performance_metrics')

    # Time period
    date = models.DateField()
    period_type = models.CharField(max_length=10, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ])

    # Performance metrics
    total_predictions = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    precision = models.FloatField(default=0.0)
    recall = models.FloatField(default=0.0)
    f1_score = models.FloatField(default=0.0)

    # Response time metrics
    avg_processing_time = models.FloatField(default=0.0)
    min_processing_time = models.FloatField(default=0.0)
    max_processing_time = models.FloatField(default=0.0)

    # Confidence metrics
    avg_confidence = models.FloatField(default=0.0)
    high_confidence_count = models.IntegerField(default=0)  # >80%
    low_confidence_count = models.IntegerField(default=0)   # <60%

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_model_performance_metric'
        verbose_name = 'Model Performance Metric'
        verbose_name_plural = 'Model Performance Metrics'
        ordering = ['-date']
        unique_together = ['model', 'date', 'period_type']

    def __str__(self):
        return f"{self.model.name} - {self.date} ({self.period_type})"


class ManualOverride(models.Model):
    """
    Track manual overrides of AI predictions
    """
    OVERRIDE_REASONS = [
        ('insufficient_data', 'Insufficient Data'),
        ('policy_exception', 'Policy Exception'),
        ('human_judgment', 'Human Judgment'),
        ('external_factors', 'External Factors'),
        ('model_error', 'Model Error'),
        ('compliance_requirement', 'Compliance Requirement'),
        ('customer_relationship', 'Customer Relationship'),
        ('other', 'Other'),
    ]

    prediction = models.OneToOneField(AIPrediction, on_delete=models.CASCADE, related_name='manual_override')

    # Override details
    original_prediction = models.CharField(max_length=20)
    override_decision = models.CharField(max_length=20, choices=[
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('review', 'Further Review'),
    ])

    # Reasoning
    reason = models.CharField(max_length=30, choices=OVERRIDE_REASONS)
    detailed_reason = models.TextField()
    confidence_in_override = models.IntegerField(help_text="Confidence level 1-10")

    # Metadata
    overridden_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='manual_overrides')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manual_override'
        verbose_name = 'Manual Override'
        verbose_name_plural = 'Manual Overrides'
        ordering = ['-created_at']

    def __str__(self):
        return f"Override: {self.original_prediction} → {self.override_decision}"


class ModelTrainingJob(models.Model):
    """
    Track model training jobs and their progress
    """
    JOB_STATUS = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    name = models.CharField(max_length=200)
    model_type = models.CharField(max_length=30, choices=AIModel.MODEL_TYPES)

    # Training configuration
    training_config = models.JSONField(default=dict)
    dataset_info = models.JSONField(default=dict)

    # Progress tracking
    status = models.CharField(max_length=20, choices=JOB_STATUS, default='queued')
    progress_percentage = models.FloatField(default=0.0)
    current_epoch = models.IntegerField(default=0)
    total_epochs = models.IntegerField(default=100)

    # Results
    final_accuracy = models.FloatField(null=True, blank=True)
    final_loss = models.FloatField(null=True, blank=True)
    training_logs = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)

    # Output
    output_model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_jobs')

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'model_training_job'
        verbose_name = 'Model Training Job'
        verbose_name_plural = 'Model Training Jobs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def duration(self):
        """Calculate job duration"""
        if self.started_at:
            end_time = self.completed_at or timezone.now()
            duration = end_time - self.started_at
            return duration.total_seconds() / 3600  # Hours
        return None

    @property
    def estimated_time_remaining(self):
        """Estimate remaining time based on progress"""
        if self.started_at and self.progress_percentage > 0:
            elapsed = timezone.now() - self.started_at
            total_estimated = elapsed / (self.progress_percentage / 100)
            remaining = total_estimated - elapsed
            return remaining.total_seconds() / 3600  # Hours
        return None


class DocumentFlag(models.Model):
    """
    Flags for suspicious or problematic documents
    """
    FLAG_TYPES = [
        ('suspicious', 'Suspicious Document'),
        ('poor_quality', 'Poor Quality'),
        ('incomplete', 'Incomplete Information'),
        ('inconsistent', 'Inconsistent Data'),
        ('fraudulent', 'Potentially Fraudulent'),
        ('expired', 'Expired Document'),
        ('unreadable', 'Unreadable Text'),
        ('wrong_type', 'Wrong Document Type'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    document = models.ForeignKey(ApplicationDocument, on_delete=models.CASCADE, related_name='flags')
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    
    reason = models.TextField()
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flagged_documents')
    
    # Resolution tracking
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'document_flag'
        verbose_name = 'Document Flag'
        verbose_name_plural = 'Document Flags'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.flag_type} - {self.document.document_name}"


class ApplicationApproval(models.Model):
    """
    Track approval/rejection decisions and workflow
    """
    DECISION_TYPES = [
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('conditional', 'Conditional Approval'),
        ('deferred', 'Deferred'),
    ]

    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, related_name='approval_decision')
    decision = models.CharField(max_length=20, choices=DECISION_TYPES)
    
    # Decision details
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    approved_term = models.IntegerField(null=True, blank=True)  # months
    approved_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Decision reasoning
    decision_reason = models.TextField()
    conditions = models.TextField(blank=True)  # For conditional approvals
    
    # Decision makers
    decided_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approval_decisions')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_approvals')
    
    # AI vs Manual decision tracking
    ai_recommendation = models.CharField(max_length=20, blank=True)
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    manual_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'application_approval'
        verbose_name = 'Application Approval'
        verbose_name_plural = 'Application Approvals'

    def __str__(self):
        return f"{self.decision} - {self.application.application_number}"


class SystemAnalytics(models.Model):
    """
    Store daily analytics data for dashboard reporting
    """
    date = models.DateField(unique=True)

    # Application metrics
    applications_submitted = models.IntegerField(default=0)
    applications_approved = models.IntegerField(default=0)
    applications_rejected = models.IntegerField(default=0)
    applications_pending = models.IntegerField(default=0)

    # Financial metrics
    total_loan_amount_requested = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_loan_amount_approved = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # AI metrics
    ai_predictions_made = models.IntegerField(default=0)
    ai_accuracy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    manual_overrides = models.IntegerField(default=0)

    # Document metrics
    documents_uploaded = models.IntegerField(default=0)
    documents_flagged = models.IntegerField(default=0)
    ocr_processed = models.IntegerField(default=0)
    ocr_success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # User metrics
    new_users_registered = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_analytics'
        verbose_name = 'System Analytics'
        verbose_name_plural = 'System Analytics'
        ordering = ['-date']

    def __str__(self):
        return f"Analytics for {self.date}"


class SystemConfiguration(models.Model):
    """
    System-wide configuration settings
    """
    SETTING_TYPES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('file', 'File Path'),
    ]

    CATEGORIES = [
        ('general', 'General Settings'),
        ('ai_models', 'AI Model Settings'),
        ('notifications', 'Notification Settings'),
        ('security', 'Security Settings'),
        ('email', 'Email Settings'),
        ('file_upload', 'File Upload Settings'),
        ('api', 'API Settings'),
        ('backup', 'Backup Settings'),
        ('logging', 'Logging Settings'),
        ('performance', 'Performance Settings'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    setting_type = models.CharField(max_length=20, choices=SETTING_TYPES, default='string')
    category = models.CharField(max_length=30, choices=CATEGORIES, default='general')

    # Metadata
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    default_value = models.TextField(blank=True)

    # Validation
    is_required = models.BooleanField(default=False)
    validation_regex = models.CharField(max_length=500, blank=True)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)

    # Access control
    is_public = models.BooleanField(default=False)  # Can be viewed by non-admin users
    is_editable = models.BooleanField(default=True)  # Can be modified
    requires_restart = models.BooleanField(default=False)  # Requires system restart

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'system_configuration'
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.key})"

    def get_typed_value(self):
        """Get value converted to appropriate type"""
        if self.setting_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.setting_type == 'integer':
            try:
                return int(self.value)
            except ValueError:
                return 0
        elif self.setting_type == 'float':
            try:
                return float(self.value)
            except ValueError:
                return 0.0
        elif self.setting_type == 'json':
            try:
                import json
                return json.loads(self.value)
            except (ValueError, TypeError):
                return {}
        else:
            return self.value

    def set_typed_value(self, value):
        """Set value with type conversion"""
        if self.setting_type == 'boolean':
            self.value = str(bool(value)).lower()
        elif self.setting_type in ['integer', 'float']:
            self.value = str(value)
        elif self.setting_type == 'json':
            import json
            self.value = json.dumps(value)
        else:
            self.value = str(value)


class UserActivity(models.Model):
    """
    Track user activities for security and analytics
    """
    ACTIVITY_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('application_submit', 'Application Submitted'),
        ('document_upload', 'Document Uploaded'),
        ('profile_update', 'Profile Updated'),
        ('password_change', 'Password Changed'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('admin_action', 'Admin Action'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPES)
    description = models.TextField()

    # Context data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    # Related objects
    related_application = models.ForeignKey(LoanApplication, on_delete=models.SET_NULL, null=True, blank=True)
    related_document = models.ForeignKey(ApplicationDocument, on_delete=models.SET_NULL, null=True, blank=True)

    # Flags
    is_suspicious = models.BooleanField(default=False)
    requires_review = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_activity'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.activity_type}"


class AdminUserProfile(models.Model):
    """
    Extended user profile information for admin management
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')

    # Security information
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)

    # Activity tracking
    total_logins = models.IntegerField(default=0)
    total_applications_submitted = models.IntegerField(default=0)
    total_documents_uploaded = models.IntegerField(default=0)

    # Admin notes
    admin_notes = models.TextField(blank=True)
    risk_level = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
            ('critical', 'Critical Risk'),
        ],
        default='low'
    )

    # Verification status
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_users')
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_user_profile'
        verbose_name = 'Admin User Profile'
        verbose_name_plural = 'Admin User Profiles'

    def __str__(self):
        return f"Profile for {self.user.get_full_name()}"


class RoleChangeHistory(models.Model):
    """
    Track role changes for audit purposes
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_changes')
    old_role = models.CharField(max_length=20)
    new_role = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_changes_made')
    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'role_change_history'
        verbose_name = 'Role Change History'
        verbose_name_plural = 'Role Change Histories'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()}: {self.old_role} → {self.new_role}"


class UserSession(models.Model):
    """
    Track user sessions for security monitoring
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    # Location data (if available)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    # Session tracking
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Security flags
    is_suspicious = models.BooleanField(default=False)
    suspicious_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'user_session'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-login_time']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.login_time}"


class ConfigurationHistory(models.Model):
    """
    Track configuration changes for audit purposes
    """
    configuration = models.ForeignKey(SystemConfiguration, on_delete=models.CASCADE, related_name='history')

    # Change details
    old_value = models.TextField()
    new_value = models.TextField()
    change_reason = models.TextField(blank=True)

    # Metadata
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'configuration_history'
        verbose_name = 'Configuration History'
        verbose_name_plural = 'Configuration Histories'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.configuration.key} changed by {self.changed_by.get_full_name()}"


class SystemBackup(models.Model):
    """
    System backup management
    """
    BACKUP_TYPES = [
        ('full', 'Full Backup'),
        ('database', 'Database Only'),
        ('files', 'Files Only'),
        ('configuration', 'Configuration Only'),
    ]

    BACKUP_STATUS = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=200)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES)

    # Backup details
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    compression_type = models.CharField(max_length=20, default='gzip')

    # Status
    status = models.CharField(max_length=20, choices=BACKUP_STATUS, default='pending')
    progress_percentage = models.FloatField(default=0.0)
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    # Retention
    expires_at = models.DateTimeField(null=True, blank=True)
    is_automatic = models.BooleanField(default=False)

    class Meta:
        db_table = 'system_backup'
        verbose_name = 'System Backup'
        verbose_name_plural = 'System Backups'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.backup_type})"

    @property
    def duration(self):
        """Calculate backup duration"""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return duration.total_seconds()
        return None

    @property
    def formatted_file_size(self):
        """Get formatted file size"""
        if not self.file_size:
            return "Unknown"

        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
