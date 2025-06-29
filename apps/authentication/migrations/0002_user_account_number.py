# Generated by Django 4.2.7 on 2025-06-22 19:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='account_number',
            field=models.CharField(blank=True, help_text='Enter your Equity Bank account number.', max_length=20, null=True, unique=True, verbose_name='Equity Account Number'),
        ),
    ]
