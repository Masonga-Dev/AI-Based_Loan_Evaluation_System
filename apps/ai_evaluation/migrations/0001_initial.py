# Generated by Django 4.2.7 on 2025-06-19 10:52

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FeatureImportance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_name', models.CharField(max_length=100)),
                ('importance_score', models.DecimalField(decimal_places=6, max_digits=8)),
                ('rank', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Feature Importance',
                'verbose_name_plural': 'Feature Importances',
                'db_table': 'feature_importance',
                'ordering': ['rank'],
            },
        ),
        migrations.CreateModel(
            name='MLModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('version', models.CharField(max_length=20)),
                ('model_type', models.CharField(choices=[('classification', 'Classification'), ('regression', 'Regression'), ('ensemble', 'Ensemble'), ('neural_network', 'Neural Network')], max_length=20)),
                ('description', models.TextField()),
                ('model_file_path', models.CharField(max_length=500)),
                ('model_size', models.IntegerField(help_text='Model file size in bytes')),
                ('accuracy', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('precision', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('recall', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('f1_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('hyperparameters', models.JSONField(default=dict)),
                ('feature_columns', models.JSONField(default=list)),
                ('target_column', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('training', 'Training'), ('active', 'Active'), ('inactive', 'Inactive'), ('deprecated', 'Deprecated')], default='training', max_length=20)),
                ('is_default', models.BooleanField(default=False)),
                ('training_data_size', models.IntegerField(blank=True, null=True)),
                ('training_duration', models.DurationField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'ML Model',
                'verbose_name_plural': 'ML Models',
                'db_table': 'ml_model',
            },
        ),
        migrations.CreateModel(
            name='ModelPerformanceMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_type', models.CharField(choices=[('accuracy', 'Accuracy'), ('precision', 'Precision'), ('recall', 'Recall'), ('f1_score', 'F1 Score'), ('auc_roc', 'AUC-ROC'), ('confusion_matrix', 'Confusion Matrix')], max_length=20)),
                ('metric_value', models.JSONField()),
                ('dataset_size', models.IntegerField()),
                ('dataset_description', models.CharField(blank=True, max_length=200)),
                ('evaluated_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Model Performance Metric',
                'verbose_name_plural': 'Model Performance Metrics',
                'db_table': 'model_performance_metric',
                'ordering': ['-evaluated_at'],
            },
        ),
        migrations.CreateModel(
            name='PredictionResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('prediction_type', models.CharField(choices=[('approval', 'Loan Approval'), ('risk_assessment', 'Risk Assessment'), ('credit_score', 'Credit Score Prediction'), ('default_probability', 'Default Probability')], max_length=30)),
                ('prediction_value', models.JSONField()),
                ('confidence_score', models.DecimalField(decimal_places=4, max_digits=5)),
                ('input_features', models.JSONField()),
                ('processing_time', models.DurationField()),
                ('model_version', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Prediction Result',
                'verbose_name_plural': 'Prediction Results',
                'db_table': 'prediction_result',
                'ordering': ['-created_at'],
            },
        ),
    ]
