from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta

from apps.authentication.models import User
from apps.loan_application.models import LoanApplication, ApplicationDocument
from apps.document_processing.models import OCRResult, DocumentVerification
from .models import (
    AdminNotification, DocumentFlag, ApplicationApproval, SystemAnalytics,
    AdminUserProfile, RoleChangeHistory, UserSession, UserActivity,
    NotificationTemplate, NotificationRule, NotificationBatch,
    AnalyticsReport, DashboardWidget, ExportJob,
    AIModel, AIPrediction, ModelPerformanceMetric, ManualOverride, ModelTrainingJob,
    SystemConfiguration, ConfigurationHistory, SystemBackup
)


def is_admin_or_officer(user):
    """Check if user is admin, manager, or officer"""
    return user.is_authenticated and user.role in ['admin', 'manager', 'officer']


@login_required
@user_passes_test(is_admin_or_officer)
def dashboard_overview(request):
    """
    Admin dashboard overview with key metrics and quick actions
    """
    # Get basic statistics
    total_applications = LoanApplication.objects.count()
    approved_this_month = LoanApplication.objects.filter(
        status='approved',
        decision_date__month=timezone.now().month,
        decision_date__year=timezone.now().year
    ).count()
    pending_review = LoanApplication.objects.filter(
        status__in=['submitted', 'under_review']
    ).count()
    total_users = User.objects.count()

    context = {
        'total_applications': total_applications,
        'approved_this_month': approved_this_month,
        'pending_review': pending_review,
        'total_users': total_users,
    }

    return render(request, 'admin_dashboard/dashboard_overview.html', context)


@login_required
@user_passes_test(is_admin_or_officer)
def loan_applications(request):
    """
    Enhanced loan applications management with filtering, sorting, and bulk operations
    """
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    amount_min = request.GET.get('amount_min', '')
    amount_max = request.GET.get('amount_max', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-created_at')

    # Base queryset
    applications = LoanApplication.objects.select_related(
        'applicant', 'assigned_officer'
    ).prefetch_related(
        'documents', 'documents__ocr_result', 'documents__flags'
    )

    # Apply filters
    if status_filter:
        applications = applications.filter(status=status_filter)

    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            applications = applications.filter(created_at__date__gte=date_from_parsed)
        except ValueError:
            pass

    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            applications = applications.filter(created_at__date__lte=date_to_parsed)
        except ValueError:
            pass

    if amount_min:
        try:
            applications = applications.filter(loan_amount__gte=float(amount_min))
        except ValueError:
            pass

    if amount_max:
        try:
            applications = applications.filter(loan_amount__lte=float(amount_max))
        except ValueError:
            pass

    if search_query:
        applications = applications.filter(
            Q(application_number__icontains=search_query) |
            Q(applicant__first_name__icontains=search_query) |
            Q(applicant__last_name__icontains=search_query) |
            Q(applicant__email__icontains=search_query)
        )

    # Apply sorting
    valid_sort_fields = [
        'created_at', '-created_at', 'loan_amount', '-loan_amount',
        'status', '-status', 'ai_score', '-ai_score'
    ]
    if sort_by in valid_sort_fields:
        applications = applications.order_by(sort_by)
    else:
        applications = applications.order_by('-created_at')

    # Pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get statistics
    stats = {
        'total': applications.count(),
        'pending': applications.filter(status='under_review').count(),
        'approved': applications.filter(status='approved').count(),
        'rejected': applications.filter(status='rejected').count(),
        'total_amount': applications.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0,
        'avg_amount': applications.aggregate(Avg('loan_amount'))['loan_amount__avg'] or 0,
    }

    context = {
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'stats': stats,
        'filters': {
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
            'amount_min': amount_min,
            'amount_max': amount_max,
            'search': search_query,
            'sort': sort_by,
        },
        'status_choices': LoanApplication.STATUS_CHOICES,
    }

    return render(request, 'admin_dashboard/loan_applications.html', context)

@login_required
@user_passes_test(is_admin_or_officer)
def uploaded_documents(request):
    """
    Document management with OCR preview and verification status
    """
    # Get filter parameters
    doc_type = request.GET.get('type', '')
    verification_status = request.GET.get('verification', '')
    flagged_only = request.GET.get('flagged', '') == 'true'
    search_query = request.GET.get('search', '')

    # Base queryset
    documents = ApplicationDocument.objects.select_related(
        'application', 'application__applicant'
    ).prefetch_related(
        'ocr_result', 'verification', 'flags'
    )

    # Apply filters
    if doc_type:
        documents = documents.filter(document_type=doc_type)

    if verification_status:
        documents = documents.filter(verification__status=verification_status)

    if flagged_only:
        documents = documents.filter(flags__isnull=False).distinct()

    if search_query:
        documents = documents.filter(
            Q(document_name__icontains=search_query) |
            Q(application__application_number__icontains=search_query) |
            Q(application__applicant__first_name__icontains=search_query) |
            Q(application__applicant__last_name__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(documents.order_by('-uploaded_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'documents': page_obj.object_list,
        'document_types': ApplicationDocument.DOCUMENT_TYPE_CHOICES,
        'verification_statuses': DocumentVerification.VERIFICATION_STATUS_CHOICES,
        'filters': {
            'type': doc_type,
            'verification': verification_status,
            'flagged': flagged_only,
            'search': search_query,
        }
    }

    return render(request, 'admin_dashboard/document_management.html', context)


@login_required
@user_passes_test(is_admin_or_officer)
def ocr_data(request):
    """
    OCR data preview and comparison with manual entries
    """
    document_id = request.GET.get('document_id')
    if not document_id:
        return redirect('admin_dashboard:uploaded_documents')

    document = get_object_or_404(ApplicationDocument, pk=document_id)

    try:
        ocr_result = document.ocr_result
        comparison = getattr(ocr_result, 'comparison', None)
    except OCRResult.DoesNotExist:
        ocr_result = None
        comparison = None

    context = {
        'document': document,
        'ocr_result': ocr_result,
        'comparison': comparison,
        'application': document.application,
    }

    return render(request, 'admin_dashboard/ocr_data.html', context)


@login_required
@user_passes_test(is_admin_or_officer)
def ai_predictions(request):
    """
    AI predictions review and manual override interface
    """
    # Get applications with AI predictions
    applications = LoanApplication.objects.filter(
        ai_score__isnull=False
    ).select_related('applicant', 'assigned_officer').order_by('-created_at')

    # Filter by prediction accuracy if requested
    accuracy_filter = request.GET.get('accuracy', '')
    if accuracy_filter == 'high':
        applications = applications.filter(ai_score__gte=80)
    elif accuracy_filter == 'medium':
        applications = applications.filter(ai_score__gte=50, ai_score__lt=80)
    elif accuracy_filter == 'low':
        applications = applications.filter(ai_score__lt=50)

    # Pagination
    paginator = Paginator(applications, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'applications': page_obj.object_list,
        'accuracy_filter': accuracy_filter,
    }

    return render(request, 'admin_dashboard/ai_predictions.html', context)


@login_required
@user_passes_test(is_admin_or_officer)
def approve_reject(request):
    """
    Application approval/rejection interface
    """
    application_id = request.GET.get('application_id')
    if not application_id:
        return redirect('admin_dashboard:loan_applications')

    application = get_object_or_404(LoanApplication, pk=application_id)

    if request.method == 'POST':
        decision = request.POST.get('decision')
        reason = request.POST.get('reason', '')
        approved_amount = request.POST.get('approved_amount')
        approved_term = request.POST.get('approved_term')
        approved_rate = request.POST.get('approved_rate')
        conditions = request.POST.get('conditions', '')

        if decision in ['approved', 'rejected', 'conditional', 'deferred']:
            # Create or update approval decision
            approval, created = ApplicationApproval.objects.get_or_create(
                application=application,
                defaults={
                    'decision': decision,
                    'decision_reason': reason,
                    'decided_by': request.user,
                    'ai_recommendation': application.ai_recommendation,
                    'ai_score': application.ai_score,
                }
            )

            if not created:
                approval.decision = decision
                approval.decision_reason = reason
                approval.decided_by = request.user
                approval.save()

            # Update approval details for approved applications
            if decision == 'approved' and approved_amount:
                try:
                    approval.approved_amount = float(approved_amount)
                    approval.approved_term = int(approved_term) if approved_term else None
                    approval.approved_rate = float(approved_rate) if approved_rate else None
                    approval.conditions = conditions
                    approval.save()
                except (ValueError, TypeError):
                    pass

            # Update application status
            if decision == 'approved':
                application.status = 'approved'
            elif decision == 'rejected':
                application.status = 'rejected'
                application.rejection_reason = reason
            elif decision == 'conditional':
                application.status = 'conditional_approval'
            elif decision == 'deferred':
                application.status = 'deferred'

            application.decision_date = timezone.now()
            application.save()

            # Create notification for applicant
            AdminNotification.objects.create(
                recipient=application.applicant,
                notification_type='application_submitted',
                priority='high',
                title=f'Application {decision.title()}',
                message=f'Your loan application {application.application_number} has been {decision}.',
                related_application=application,
                link_url=f'/applications/{application.pk}/detail/'
            )

            messages.success(request, f'Application {decision} successfully.')
            return redirect('admin_dashboard:loan_applications')

    context = {
        'application': application,
        'documents': application.documents.all(),
        'ai_prediction': {
            'score': application.ai_score,
            'recommendation': application.ai_recommendation,
            'risk_level': application.risk_level,
        }
    }

    return render(request, 'admin_dashboard/approve_reject.html', context)

@login_required
@user_passes_test(is_admin_or_officer)
def flag_documents(request):
    """
    Flag suspicious documents with reasons
    """
    if request.method == 'POST':
        document_id = request.POST.get('document_id')
        flag_type = request.POST.get('flag_type')
        severity = request.POST.get('severity', 'medium')
        reason = request.POST.get('reason', '')

        if document_id and flag_type and reason:
            document = get_object_or_404(ApplicationDocument, pk=document_id)

            # Create document flag
            flag = DocumentFlag.objects.create(
                document=document,
                flag_type=flag_type,
                severity=severity,
                reason=reason,
                flagged_by=request.user
            )

            # Create admin notification
            AdminNotification.objects.create(
                recipient=document.application.applicant,
                notification_type='document_flagged',
                priority='high' if severity in ['high', 'critical'] else 'medium',
                title='Document Flagged',
                message=f'Your document "{document.document_name}" has been flagged for review.',
                related_document=document,
                related_application=document.application,
                link_url=f'/applications/{document.application.pk}/detail/'
            )

            messages.success(request, 'Document flagged successfully.')
            return JsonResponse({'success': True})

        return JsonResponse({'success': False, 'error': 'Missing required fields'})

    # Get recent flagged documents
    flagged_documents = ApplicationDocument.objects.filter(
        flags__isnull=False
    ).select_related('application', 'application__applicant').prefetch_related('flags').distinct()[:20]

    context = {
        'flagged_documents': flagged_documents,
        'flag_types': DocumentFlag.FLAG_TYPES,
        'severity_levels': DocumentFlag.SEVERITY_LEVELS,
    }

    return render(request, 'admin_dashboard/flag_documents.html', context)


def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)


@login_required
@user_passes_test(is_admin_or_officer)
def user_list(request):
    """
    Enhanced user management interface with advanced filtering and analytics
    """
    # Get filter parameters
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    risk_filter = request.GET.get('risk', '')
    verified_filter = request.GET.get('verified', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-date_joined')

    # Base queryset with related data
    users = User.objects.prefetch_related(
        'role_changes', 'sessions', 'activities'
    )

    # Apply filters
    if role_filter:
        users = users.filter(role=role_filter)

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'locked':
        users = users.filter(admin_profile__account_locked_until__gt=timezone.now())

    if risk_filter:
        users = users.filter(admin_profile__risk_level=risk_filter)

    if verified_filter == 'verified':
        users = users.filter(admin_profile__is_verified=True)
    elif verified_filter == 'unverified':
        users = users.filter(
            Q(admin_profile__is_verified=False) | Q(admin_profile__isnull=True)
        )

    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )

    # Apply sorting
    valid_sort_fields = [
        'date_joined', '-date_joined', 'last_login', '-last_login',
        'first_name', '-first_name', 'email', '-email'
    ]
    if sort_by in valid_sort_fields:
        users = users.order_by(sort_by)
    else:
        users = users.order_by('-date_joined')

    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get enhanced user statistics
    user_stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'inactive': User.objects.filter(is_active=False).count(),
        'applicants': User.objects.filter(role='applicant').count(),
        'officers': User.objects.filter(role='officer').count(),
        'managers': User.objects.filter(role='manager').count(),
        'admins': User.objects.filter(role='admin').count(),
        'verified': AdminUserProfile.objects.filter(is_verified=True).count(),
        'high_risk': AdminUserProfile.objects.filter(risk_level__in=['high', 'critical']).count(),
        'locked': AdminUserProfile.objects.filter(account_locked_until__gt=timezone.now()).count(),
        'new_this_month': User.objects.filter(
            date_joined__month=timezone.now().month,
            date_joined__year=timezone.now().year
        ).count(),
    }

    # Get recent activities
    recent_activities = UserActivity.objects.select_related('user').order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'users': page_obj.object_list,
        'user_stats': user_stats,
        'recent_activities': recent_activities,
        'role_choices': User.ROLE_CHOICES,
        'risk_choices': AdminUserProfile._meta.get_field('risk_level').choices,
        'filters': {
            'role': role_filter,
            'status': status_filter,
            'risk': risk_filter,
            'verified': verified_filter,
            'search': search_query,
            'sort': sort_by,
        }
    }

    return render(request, 'admin_dashboard/user_list.html', context)


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def promote_user(request, user_id):
    """
    Promote user with role change tracking
    """
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        new_role = request.POST.get('new_role')
        reason = request.POST.get('reason', 'Role promotion by admin')

        if new_role in ['officer', 'manager', 'admin'] and request.user.role == 'admin':
            old_role = user.role

            # Update user role
            user.role = new_role
            user.save()

            # Create role change history
            RoleChangeHistory.objects.create(
                user=user,
                old_role=old_role,
                new_role=new_role,
                changed_by=request.user,
                reason=reason
            )

            # Create user activity record
            UserActivity.objects.create(
                user=user,
                activity_type='admin_action',
                description=f'Role changed from {old_role} to {new_role} by {request.user.get_full_name()}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                related_user=request.user
            )

            # Create notification
            AdminNotification.objects.create(
                recipient=user,
                notification_type='system_alert',
                priority='high',
                title='Role Updated',
                message=f'Your role has been updated from {old_role} to {new_role}. Reason: {reason}',
                related_user=user
            )

            messages.success(request, f'User {user.get_full_name()} promoted to {new_role} successfully.')
        else:
            messages.error(request, 'Invalid role or insufficient permissions.')

    return redirect('admin_dashboard:user_list')


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def deactivate_user(request, user_id):
    """
    Deactivate suspicious users
    """
    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)
        reason = request.POST.get('reason', 'Account deactivated by admin')

        if user != request.user:  # Prevent self-deactivation
            user.is_active = False
            user.save()

            # Create notification
            AdminNotification.objects.create(
                recipient=user,
                notification_type='system_alert',
                priority='urgent',
                title='Account Deactivated',
                message=f'Your account has been deactivated. Reason: {reason}',
                related_user=user
            )

            messages.success(request, f'User {user.get_full_name()} deactivated successfully.')
        else:
            messages.error(request, 'You cannot deactivate your own account.')

    return redirect('admin_dashboard:user_list')

@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def bulk_approve_applications(request):
    """
    Bulk approve multiple applications
    """
    try:
        data = json.loads(request.body)
        application_ids = data.get('application_ids', [])
        decision = data.get('decision', 'approved')
        reason = data.get('reason', 'Bulk approval')

        if not application_ids:
            return JsonResponse({'success': False, 'error': 'No applications selected'})

        applications = LoanApplication.objects.filter(id__in=application_ids)
        results = []

        for application in applications:
            try:
                # Create approval decision
                approval, created = ApplicationApproval.objects.get_or_create(
                    application=application,
                    defaults={
                        'decision': decision,
                        'decision_reason': reason,
                        'decided_by': request.user,
                        'ai_recommendation': application.ai_recommendation,
                        'ai_score': application.ai_score,
                    }
                )

                # Update application status
                if decision == 'approved':
                    application.status = 'approved'
                elif decision == 'rejected':
                    application.status = 'rejected'
                    application.rejection_reason = reason

                application.decision_date = timezone.now()
                application.save()

                # Create notification
                AdminNotification.objects.create(
                    recipient=application.applicant,
                    notification_type='application_submitted',
                    priority='high',
                    title=f'Application {decision.title()}',
                    message=f'Your loan application {application.application_number} has been {decision}.',
                    related_application=application,
                    link_url=f'/applications/{application.pk}/detail/'
                )

                results.append({
                    'application_id': application.id,
                    'application_number': application.application_number,
                    'success': True
                })

            except Exception as e:
                results.append({
                    'application_id': application.id,
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({
            'success': True,
            'results': results,
            'processed': len(results)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def verify_document(request, document_id):
    """
    Mark document as verified or needs correction
    """
    try:
        document = get_object_or_404(ApplicationDocument, pk=document_id)
        data = json.loads(request.body)

        status = data.get('status', 'verified')
        notes = data.get('notes', '')

        # Create or update verification
        verification, created = DocumentVerification.objects.get_or_create(
            document=document,
            defaults={
                'status': status,
                'verified_by': request.user,
                'verification_notes': notes,
                'verified_at': timezone.now()
            }
        )

        if not created:
            verification.status = status
            verification.verified_by = request.user
            verification.verification_notes = notes
            verification.verified_at = timezone.now()
            verification.save()

        return JsonResponse({
            'success': True,
            'status': status,
            'verified_by': request.user.get_full_name(),
            'verified_at': verification.verified_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin_or_officer)
def get_application_details(request, application_id):
    """
    Get detailed application information for AJAX requests
    """
    try:
        application = get_object_or_404(
            LoanApplication.objects.select_related('applicant').prefetch_related('documents'),
            pk=application_id
        )

        data = {
            'application_number': application.application_number,
            'applicant_name': application.applicant.get_full_name(),
            'applicant_email': application.applicant.email,
            'loan_amount': float(application.loan_amount),
            'loan_type': application.loan_type,
            'status': application.status,
            'ai_score': float(application.ai_score) if application.ai_score else None,
            'ai_recommendation': application.ai_recommendation,
            'risk_level': application.risk_level,
            'created_at': application.created_at.isoformat(),
            'documents': [
                {
                    'id': doc.id,
                    'name': doc.document_name,
                    'type': doc.document_type,
                    'uploaded_at': doc.uploaded_at.isoformat(),
                    'is_processed': doc.is_processed,
                    'processing_status': doc.processing_status,
                }
                for doc in application.documents.all()
            ]
        }

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin_or_officer)
def user_profile_detail(request, user_id):
    """
    Detailed user profile view with activity history and security information
    """
    user = get_object_or_404(User, pk=user_id)

    # Get or create user profile
    profile, created = AdminUserProfile.objects.get_or_create(user=user)

    # Get user activities
    activities = UserActivity.objects.filter(user=user).order_by('-created_at')[:20]

    # Get role change history
    role_changes = RoleChangeHistory.objects.filter(user=user).order_by('-created_at')[:10]

    # Get active sessions
    active_sessions = UserSession.objects.filter(user=user, is_active=True).order_by('-last_activity')

    # Get user applications
    applications = LoanApplication.objects.filter(applicant=user).order_by('-created_at')[:5]

    # Calculate statistics
    stats = {
        'total_logins': profile.total_logins,
        'applications_count': LoanApplication.objects.filter(applicant=user).count(),
        'documents_count': ApplicationDocument.objects.filter(application__applicant=user).count(),
        'last_login': user.last_login,
        'account_age': (timezone.now() - user.date_joined).days,
        'active_sessions': active_sessions.count(),
    }

    context = {
        'profile_user': user,
        'profile': profile,
        'activities': activities,
        'role_changes': role_changes,
        'active_sessions': active_sessions,
        'applications': applications,
        'stats': stats,
    }

    return render(request, 'admin_dashboard/user_profile_detail.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def update_user_profile(request, user_id):
    """
    Update user profile information
    """
    try:
        user = get_object_or_404(User, pk=user_id)
        data = json.loads(request.body)

        # Get or create profile
        profile, created = AdminUserProfile.objects.get_or_create(user=user)

        # Update profile fields
        if 'risk_level' in data:
            profile.risk_level = data['risk_level']

        if 'admin_notes' in data:
            profile.admin_notes = data['admin_notes']

        if 'is_verified' in data:
            profile.is_verified = data['is_verified']
            if data['is_verified']:
                profile.verified_by = request.user
                profile.verified_at = timezone.now()

        profile.save()

        # Create activity record
        UserActivity.objects.create(
            user=user,
            activity_type='admin_action',
            description=f'Profile updated by {request.user.get_full_name()}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            related_user=request.user
        )

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def bulk_user_actions(request):
    """
    Perform bulk actions on multiple users
    """
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        action = data.get('action')

        if not user_ids:
            return JsonResponse({'success': False, 'error': 'No users selected'})

        users = User.objects.filter(id__in=user_ids)
        results = []

        for user in users:
            try:
                if action == 'deactivate':
                    user.is_active = False
                    user.save()

                    # Create activity record
                    UserActivity.objects.create(
                        user=user,
                        activity_type='admin_action',
                        description=f'Account deactivated by {request.user.get_full_name()} (bulk action)',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        related_user=request.user
                    )

                elif action == 'activate':
                    user.is_active = True
                    user.save()

                    # Create activity record
                    UserActivity.objects.create(
                        user=user,
                        activity_type='admin_action',
                        description=f'Account activated by {request.user.get_full_name()} (bulk action)',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        related_user=request.user
                    )

                elif action == 'verify':
                    profile, created = AdminUserProfile.objects.get_or_create(user=user)
                    profile.is_verified = True
                    profile.verified_by = request.user
                    profile.verified_at = timezone.now()
                    profile.save()

                results.append({
                    'user_id': user.id,
                    'username': user.username,
                    'success': True
                })

            except Exception as e:
                results.append({
                    'user_id': user.id,
                    'username': user.username,
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({
            'success': True,
            'results': results,
            'processed': len(results)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin_or_officer)
def notifications_center(request):
    """
    Comprehensive notifications management center
    """
    # Get filter parameters
    priority_filter = request.GET.get('priority', '')
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', 'unread')
    search_query = request.GET.get('search', '')

    # Base queryset
    notifications = AdminNotification.objects.filter(recipient=request.user)

    # Apply filters
    if priority_filter:
        notifications = notifications.filter(priority=priority_filter)

    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)

    if status_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status_filter == 'read':
        notifications = notifications.filter(is_read=True)
    elif status_filter == 'archived':
        notifications = notifications.filter(is_archived=True)
    elif status_filter == 'action_required':
        notifications = notifications.filter(action_required=True, action_taken=False)

    if search_query:
        notifications = notifications.filter(
            Q(title__icontains=search_query) |
            Q(message__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(notifications.order_by('-created_at'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get notification statistics
    notification_stats = {
        'total': AdminNotification.objects.filter(recipient=request.user).count(),
        'unread': AdminNotification.objects.filter(recipient=request.user, is_read=False).count(),
        'urgent': AdminNotification.objects.filter(recipient=request.user, priority='urgent', is_read=False).count(),
        'action_required': AdminNotification.objects.filter(
            recipient=request.user, action_required=True, action_taken=False
        ).count(),
        'today': AdminNotification.objects.filter(
            recipient=request.user,
            created_at__date=timezone.now().date()
        ).count(),
    }

    # Get recent activity for all users (admin view)
    if request.user.role in ['admin', 'manager']:
        recent_notifications = AdminNotification.objects.select_related('recipient').order_by('-created_at')[:10]
    else:
        recent_notifications = []

    context = {
        'page_obj': page_obj,
        'notifications': page_obj.object_list,
        'notification_stats': notification_stats,
        'recent_notifications': recent_notifications,
        'notification_types': AdminNotification.NOTIFICATION_TYPES,
        'priority_levels': AdminNotification.PRIORITY_LEVELS,
        'filters': {
            'priority': priority_filter,
            'type': type_filter,
            'status': status_filter,
            'search': search_query,
        }
    }

    return render(request, 'admin_dashboard/notifications_center.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def notification_action(request, notification_id):
    """
    Handle notification actions (mark read, archive, take action)
    """
    try:
        notification = get_object_or_404(AdminNotification, pk=notification_id, recipient=request.user)
        data = json.loads(request.body)
        action = data.get('action')

        if action == 'mark_read':
            notification.mark_as_read()

        elif action == 'mark_unread':
            notification.is_read = False
            notification.read_at = None
            notification.save()

        elif action == 'archive':
            notification.archive()

        elif action == 'take_action':
            notification.mark_action_taken()

        elif action == 'delete':
            notification.delete()
            return JsonResponse({'success': True, 'message': 'Notification deleted'})

        return JsonResponse({
            'success': True,
            'notification': {
                'id': str(notification.id),
                'is_read': notification.is_read,
                'is_archived': notification.is_archived,
                'action_taken': notification.action_taken,
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def bulk_notification_actions(request):
    """
    Perform bulk actions on multiple notifications
    """
    try:
        data = json.loads(request.body)
        notification_ids = data.get('notification_ids', [])
        action = data.get('action')

        if not notification_ids:
            return JsonResponse({'success': False, 'error': 'No notifications selected'})

        notifications = AdminNotification.objects.filter(
            id__in=notification_ids,
            recipient=request.user
        )

        results = []
        for notification in notifications:
            try:
                if action == 'mark_read':
                    notification.mark_as_read()
                elif action == 'mark_unread':
                    notification.is_read = False
                    notification.read_at = None
                    notification.save()
                elif action == 'archive':
                    notification.archive()
                elif action == 'delete':
                    notification.delete()

                results.append({
                    'notification_id': str(notification.id),
                    'success': True
                })

            except Exception as e:
                results.append({
                    'notification_id': str(notification.id),
                    'success': False,
                    'error': str(e)
                })

        return JsonResponse({
            'success': True,
            'results': results,
            'processed': len(results)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def notification_templates(request):
    """
    Manage notification templates
    """
    templates = NotificationTemplate.objects.all().order_by('name')

    context = {
        'templates': templates,
        'notification_types': AdminNotification.NOTIFICATION_TYPES,
        'priority_levels': AdminNotification.PRIORITY_LEVELS,
    }

    return render(request, 'admin_dashboard/notification_templates.html', context)


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def create_notification_template(request):
    """
    Create a new notification template
    """
    try:
        data = json.loads(request.body)

        template = NotificationTemplate.objects.create(
            name=data['name'],
            notification_type=data['notification_type'],
            default_priority=data['default_priority'],
            title_template=data['title_template'],
            message_template=data['message_template'],
            assign_to_role=data.get('assign_to_role', ''),
            requires_action=data.get('requires_action', False)
        )

        return JsonResponse({
            'success': True,
            'template': {
                'id': template.id,
                'name': template.name,
                'notification_type': template.notification_type,
                'default_priority': template.default_priority,
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def send_bulk_notification(request):
    """
    Send notifications to multiple users
    """
    try:
        data = json.loads(request.body)

        # Create notification batch
        batch = NotificationBatch.objects.create(
            name=data['batch_name'],
            description=data.get('description', ''),
            notification_type=data['notification_type'],
            priority=data['priority'],
            title_template=data['title'],
            message_template=data['message'],
            created_by=request.user
        )

        # Get target users
        target_users = []
        if data.get('target_roles'):
            target_users.extend(
                User.objects.filter(role__in=data['target_roles'])
            )

        if data.get('target_user_ids'):
            target_users.extend(
                User.objects.filter(id__in=data['target_user_ids'])
            )

        # Remove duplicates
        target_users = list(set(target_users))
        batch.total_recipients = len(target_users)
        batch.status = 'processing'
        batch.started_at = timezone.now()
        batch.save()

        # Create notifications
        sent_count = 0
        failed_count = 0

        for user in target_users:
            try:
                AdminNotification.objects.create(
                    recipient=user,
                    notification_type=batch.notification_type,
                    priority=batch.priority,
                    title=batch.title_template,
                    message=batch.message_template,
                    data={'batch_id': batch.id}
                )
                sent_count += 1
            except Exception:
                failed_count += 1

        # Update batch status
        batch.sent_count = sent_count
        batch.failed_count = failed_count
        batch.status = 'completed'
        batch.completed_at = timezone.now()
        batch.save()

        return JsonResponse({
            'success': True,
            'batch_id': batch.id,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'total_recipients': len(target_users)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin_or_officer)
def analytics_dashboard(request):
    """
    Main analytics dashboard with interactive charts and metrics
    """
    from django.db.models import Count, Avg, Sum
    from django.db.models.functions import TruncDate, TruncMonth
    from datetime import timedelta

    # Get date range filter
    date_range = request.GET.get('range', '30')  # Default 30 days
    try:
        days = int(date_range)
    except ValueError:
        days = 30

    start_date = timezone.now() - timedelta(days=days)

    # Loan Applications Analytics
    applications = LoanApplication.objects.filter(created_at__gte=start_date)

    loan_analytics = {
        'total_applications': applications.count(),
        'approved_count': applications.filter(status='approved').count(),
        'rejected_count': applications.filter(status='rejected').count(),
        'pending_count': applications.filter(status='pending').count(),
        'average_amount': applications.aggregate(avg=Avg('loan_amount'))['avg'] or 0,
        'total_amount': applications.aggregate(sum=Sum('loan_amount'))['sum'] or 0,
    }

    # Calculate rates
    total_apps = loan_analytics['total_applications']
    loan_analytics['approval_rate'] = round((loan_analytics['approved_count'] / total_apps * 100), 2) if total_apps > 0 else 0
    loan_analytics['rejection_rate'] = round((loan_analytics['rejected_count'] / total_apps * 100), 2) if total_apps > 0 else 0

    # Daily trends
    daily_trends = list(
        applications.annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Status distribution
    status_distribution = list(
        applications.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )

    # Loan type distribution
    loan_type_distribution = list(
        applications.values('loan_type')
        .annotate(count=Count('id'))
        .order_by('loan_type')
    )

    # User Analytics
    users = User.objects.filter(date_joined__gte=start_date)
    user_analytics = {
        'new_users': users.count(),
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'role_distribution': list(User.objects.values('role').annotate(count=Count('id'))),
    }

    # Document Analytics
    documents = ApplicationDocument.objects.filter(uploaded_at__gte=start_date)
    document_analytics = {
        'total_documents': documents.count(),
        'processed_documents': documents.filter(is_processed=True).count(),
        'flagged_documents': DocumentFlag.objects.filter(created_at__gte=start_date).count(),
        'document_types': list(documents.values('document_type').annotate(count=Count('id'))),
    }

    # AI Performance Analytics
    ai_applications = applications.exclude(ai_recommendation__isnull=True)
    ai_analytics = {
        'total_predictions': ai_applications.count(),
        'average_score': ai_applications.aggregate(avg=Avg('ai_score'))['avg'] or 0,
        'recommendation_distribution': list(
            ai_applications.values('ai_recommendation').annotate(count=Count('id'))
        ),
    }

    # Calculate AI accuracy
    decided_apps = ai_applications.filter(status__in=['approved', 'rejected'])
    correct_predictions = 0
    for app in decided_apps:
        if (app.status == 'approved' and app.ai_recommendation == 'approve') or \
           (app.status == 'rejected' and app.ai_recommendation == 'reject'):
            correct_predictions += 1

    ai_analytics['accuracy_rate'] = round(
        (correct_predictions / decided_apps.count() * 100), 2
    ) if decided_apps.count() > 0 else 0

    # Recent activities
    recent_activities = UserActivity.objects.select_related('user').order_by('-created_at')[:10]

    # System performance metrics
    system_metrics = {
        'avg_processing_time': 2.3,  # Mock data - would be calculated from actual processing times
        'system_uptime': 99.8,
        'error_rate': 0.2,
        'response_time': 150,  # milliseconds
    }

    context = {
        'loan_analytics': loan_analytics,
        'user_analytics': user_analytics,
        'document_analytics': document_analytics,
        'ai_analytics': ai_analytics,
        'system_metrics': system_metrics,
        'daily_trends': daily_trends,
        'status_distribution': status_distribution,
        'loan_type_distribution': loan_type_distribution,
        'recent_activities': recent_activities,
        'date_range': date_range,
        'start_date': start_date,
    }

    return render(request, 'admin_dashboard/analytics_dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_officer)
def analytics_reports(request):
    """
    Analytics reports management page
    """
    reports = AnalyticsReport.objects.filter(
        Q(created_by=request.user) | Q(is_public=True) | Q(shared_with=request.user)
    ).distinct().order_by('-created_at')

    context = {
        'reports': reports,
        'report_types': AnalyticsReport.REPORT_TYPES,
    }

    return render(request, 'admin_dashboard/analytics_reports.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["POST"])
def create_analytics_report(request):
    """
    Create a new analytics report
    """
    try:
        data = json.loads(request.body)

        report = AnalyticsReport.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            report_type=data['report_type'],
            parameters=data.get('parameters', {}),
            created_by=request.user,
            is_public=data.get('is_public', False)
        )

        # Generate initial report data
        report_data = report.generate_report()

        return JsonResponse({
            'success': True,
            'report': {
                'id': report.id,
                'name': report.name,
                'report_type': report.report_type,
                'generated_at': report.generated_at.isoformat() if report.generated_at else None,
                'data': report_data
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_admin_or_officer)
def view_analytics_report(request, report_id):
    """
    View a specific analytics report
    """
    report = get_object_or_404(
        AnalyticsReport.objects.filter(
            Q(created_by=request.user) | Q(is_public=True) | Q(shared_with=request.user)
        ),
        id=report_id
    )

    # Regenerate if data is stale (older than 1 hour)
    if not report.generated_at or \
       (timezone.now() - report.generated_at).total_seconds() > 3600:
        report.generate_report()

    context = {
        'report': report,
        'data': report.data,
    }

    return render(request, 'admin_dashboard/analytics_report_detail.html', context)


@csrf_exempt
@login_required
@user_passes_test(is_admin_or_officer)
@require_http_methods(["GET"])
def analytics_api_data(request):
    """
    API endpoint for real-time analytics data
    """
    try:
        data_type = request.GET.get('type', 'overview')
        date_range = int(request.GET.get('range', 30))

        start_date = timezone.now() - timedelta(days=date_range)

        if data_type == 'overview':
            # Overview metrics
            applications = LoanApplication.objects.filter(created_at__gte=start_date)

            data = {
                'total_applications': applications.count(),
                'approved_count': applications.filter(status='approved').count(),
                'rejected_count': applications.filter(status='rejected').count(),
                'pending_count': applications.filter(status='pending').count(),
                'average_amount': float(applications.aggregate(avg=Avg('loan_amount'))['avg'] or 0),
            }

        elif data_type == 'trends':
            # Daily trends data
            applications = LoanApplication.objects.filter(created_at__gte=start_date)

            daily_data = list(
                applications.annotate(date=TruncDate('created_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )

            data = {
                'labels': [item['date'].strftime('%Y-%m-%d') for item in daily_data],
                'values': [item['count'] for item in daily_data]
            }

        elif data_type == 'status_distribution':
            # Status distribution pie chart data
            applications = LoanApplication.objects.filter(created_at__gte=start_date)

            status_data = list(
                applications.values('status')
                .annotate(count=Count('id'))
                .order_by('status')
            )

            data = {
                'labels': [item['status'].title() for item in status_data],
                'values': [item['count'] for item in status_data]
            }

        elif data_type == 'ai_performance':
            # AI performance metrics
            applications = LoanApplication.objects.filter(
                created_at__gte=start_date,
                ai_recommendation__isnull=False
            )

            total_predictions = applications.count()
            decided_apps = applications.filter(status__in=['approved', 'rejected'])

            correct_predictions = 0
            for app in decided_apps:
                if (app.status == 'approved' and app.ai_recommendation == 'approve') or \
                   (app.status == 'rejected' and app.ai_recommendation == 'reject'):
                    correct_predictions += 1

            accuracy = round(
                (correct_predictions / decided_apps.count() * 100), 2
            ) if decided_apps.count() > 0 else 0

            data = {
                'total_predictions': total_predictions,
                'accuracy_rate': accuracy,
                'average_score': float(applications.aggregate(avg=Avg('ai_score'))['avg'] or 0),
            }

        else:
            data = {'error': 'Invalid data type'}

        return JsonResponse({'success': True, 'data': data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def ai_model_management(request):
    """
    AI Model management dashboard with performance monitoring
    """
    # Get all AI models
    models = AIModel.objects.all().order_by('-created_at')

    # Get active models by type
    active_models = {}
    for model_type, _ in AIModel.MODEL_TYPES:
        active_model = AIModel.objects.filter(
            model_type=model_type,
            is_default=True,
            status='active'
        ).first()
        active_models[model_type] = active_model

    # Get recent predictions
    recent_predictions = AIPrediction.objects.select_related('model', 'application').order_by('-created_at')[:10]

    # Get training jobs
    training_jobs = ModelTrainingJob.objects.order_by('-created_at')[:5]

    # Calculate overall AI performance
    total_predictions = AIPrediction.objects.count()
    correct_predictions = AIPrediction.objects.filter(is_correct=True).count()
    overall_accuracy = round((correct_predictions / total_predictions * 100), 2) if total_predictions > 0 else 0

    # Get manual overrides
    recent_overrides = ManualOverride.objects.select_related('prediction', 'overridden_by').order_by('-created_at')[:5]

    # Model statistics
    model_stats = {
        'total_models': models.count(),
        'active_models': models.filter(status='active').count(),
        'training_models': models.filter(status='training').count(),
        'total_predictions': total_predictions,
        'overall_accuracy': overall_accuracy,
        'manual_overrides': ManualOverride.objects.count(),
        'avg_processing_time': AIPrediction.objects.aggregate(
            avg=Avg('processing_time')
        )['avg'] or 0,
    }

    context = {
        'models': models,
        'active_models': active_models,
        'recent_predictions': recent_predictions,
        'training_jobs': training_jobs,
        'recent_overrides': recent_overrides,
        'model_stats': model_stats,
        'model_types': AIModel.MODEL_TYPES,
    }

    return render(request, 'admin_dashboard/ai_model_management.html', context)


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def ai_model_detail(request, model_id):
    """
    Detailed view of a specific AI model with performance analytics
    """
    model = get_object_or_404(AIModel, id=model_id)

    # Get model predictions
    predictions = AIPrediction.objects.filter(model=model).order_by('-created_at')

    # Calculate performance metrics
    total_predictions = predictions.count()
    correct_predictions = predictions.filter(is_correct=True).count()
    accuracy = round((correct_predictions / total_predictions * 100), 2) if total_predictions > 0 else 0

    # Get prediction distribution
    prediction_distribution = list(
        predictions.values('prediction')
        .annotate(count=Count('id'))
        .order_by('prediction')
    )

    # Get confidence score distribution
    confidence_ranges = [
        (0, 60, 'Low'),
        (60, 80, 'Medium'),
        (80, 100, 'High'),
    ]

    confidence_distribution = []
    for min_conf, max_conf, label in confidence_ranges:
        count = predictions.filter(
            confidence_score__gte=min_conf,
            confidence_score__lt=max_conf
        ).count()
        confidence_distribution.append({
            'range': label,
            'count': count,
            'percentage': round((count / total_predictions * 100), 2) if total_predictions > 0 else 0
        })

    # Get performance over time
    performance_metrics = ModelPerformanceMetric.objects.filter(
        model=model
    ).order_by('-date')[:30]

    # Get manual overrides for this model
    overrides = ManualOverride.objects.filter(
        prediction__model=model
    ).select_related('prediction', 'overridden_by').order_by('-created_at')[:10]

    # Get training jobs for this model
    training_jobs = ModelTrainingJob.objects.filter(
        output_model=model
    ).order_by('-created_at')[:5]

    context = {
        'model': model,
        'predictions': predictions[:20],  # Latest 20 predictions
        'total_predictions': total_predictions,
        'accuracy': accuracy,
        'prediction_distribution': prediction_distribution,
        'confidence_distribution': confidence_distribution,
        'performance_metrics': performance_metrics,
        'overrides': overrides,
        'training_jobs': training_jobs,
    }

    return render(request, 'admin_dashboard/ai_model_detail.html', context)


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def activate_ai_model(request, model_id):
    """
    Activate an AI model and deactivate others of the same type
    """
    try:
        model = get_object_or_404(AIModel, id=model_id)
        model.activate()

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Activated AI model: {model.name} v{model.version}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return JsonResponse({
            'success': True,
            'message': f'Model {model.name} activated successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def create_manual_override(request):
    """
    Create a manual override for an AI prediction
    """
    try:
        data = json.loads(request.body)

        prediction = get_object_or_404(AIPrediction, id=data['prediction_id'])

        # Check if override already exists
        if hasattr(prediction, 'manual_override'):
            return JsonResponse({'success': False, 'error': 'Override already exists for this prediction'})

        override = ManualOverride.objects.create(
            prediction=prediction,
            original_prediction=prediction.prediction,
            override_decision=data['override_decision'],
            reason=data['reason'],
            detailed_reason=data['detailed_reason'],
            confidence_in_override=data['confidence_in_override'],
            overridden_by=request.user
        )

        # Update the application status if needed
        application = prediction.application
        if data['override_decision'] == 'approve':
            application.status = 'approved'
        elif data['override_decision'] == 'reject':
            application.status = 'rejected'
        application.save()

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Manual override: {prediction.prediction} → {data["override_decision"]} for application {application.application_number}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            related_user=application.applicant
        )

        return JsonResponse({
            'success': True,
            'override_id': override.id,
            'message': 'Manual override created successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
@require_http_methods(["POST"])
def start_model_training(request):
    """
    Start a new model training job
    """
    try:
        data = json.loads(request.body)

        training_job = ModelTrainingJob.objects.create(
            name=data['name'],
            model_type=data['model_type'],
            training_config=data.get('training_config', {}),
            dataset_info=data.get('dataset_info', {}),
            total_epochs=data.get('total_epochs', 100),
            created_by=request.user
        )

        # In a real implementation, this would trigger the actual training process
        # For now, we'll just set it to queued
        training_job.status = 'queued'
        training_job.save()

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Started model training job: {training_job.name}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return JsonResponse({
            'success': True,
            'job_id': training_job.id,
            'message': 'Training job started successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.role in ['admin', 'manager'])
def ai_performance_analytics(request):
    """
    Comprehensive AI performance analytics dashboard
    """
    from django.db.models.functions import TruncDate

    # Get date range
    date_range = request.GET.get('range', '30')
    try:
        days = int(date_range)
    except ValueError:
        days = 30

    start_date = timezone.now() - timedelta(days=days)

    # Get predictions in date range
    predictions = AIPrediction.objects.filter(created_at__gte=start_date)

    # Overall performance metrics
    total_predictions = predictions.count()
    correct_predictions = predictions.filter(is_correct=True).count()
    overall_accuracy = round((correct_predictions / total_predictions * 100), 2) if total_predictions > 0 else 0

    # Performance by model type
    model_performance = {}
    for model_type, model_name in AIModel.MODEL_TYPES:
        model_predictions = predictions.filter(model__model_type=model_type)
        total = model_predictions.count()
        correct = model_predictions.filter(is_correct=True).count()
        accuracy = round((correct / total * 100), 2) if total > 0 else 0

        model_performance[model_type] = {
            'name': model_name,
            'total_predictions': total,
            'accuracy': accuracy,
            'avg_confidence': model_predictions.aggregate(avg=Avg('confidence_score'))['avg'] or 0,
            'avg_processing_time': model_predictions.aggregate(avg=Avg('processing_time'))['avg'] or 0,
        }

    # Daily accuracy trends
    daily_accuracy = []
    daily_predictions = predictions.annotate(date=TruncDate('created_at')).values('date').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True))
    ).order_by('date')

    for day_data in daily_predictions:
        accuracy = round((day_data['correct'] / day_data['total'] * 100), 2) if day_data['total'] > 0 else 0
        daily_accuracy.append({
            'date': day_data['date'].strftime('%Y-%m-%d'),
            'accuracy': accuracy,
            'total_predictions': day_data['total']
        })

    # Manual override analysis
    overrides = ManualOverride.objects.filter(created_at__gte=start_date)
    override_stats = {
        'total_overrides': overrides.count(),
        'override_rate': round((overrides.count() / total_predictions * 100), 2) if total_predictions > 0 else 0,
        'reason_distribution': list(overrides.values('reason').annotate(count=Count('id'))),
    }

    # Confidence score analysis
    confidence_ranges = [
        (0, 60, 'Low (0-60%)'),
        (60, 80, 'Medium (60-80%)'),
        (80, 100, 'High (80-100%)'),
    ]

    confidence_analysis = []
    for min_conf, max_conf, label in confidence_ranges:
        range_predictions = predictions.filter(
            confidence_score__gte=min_conf,
            confidence_score__lt=max_conf
        )
        total = range_predictions.count()
        correct = range_predictions.filter(is_correct=True).count()
        accuracy = round((correct / total * 100), 2) if total > 0 else 0

        confidence_analysis.append({
            'range': label,
            'count': total,
            'accuracy': accuracy,
            'percentage': round((total / total_predictions * 100), 2) if total_predictions > 0 else 0
        })

    context = {
        'total_predictions': total_predictions,
        'overall_accuracy': overall_accuracy,
        'model_performance': model_performance,
        'daily_accuracy': daily_accuracy,
        'override_stats': override_stats,
        'confidence_analysis': confidence_analysis,
        'date_range': date_range,
        'start_date': start_date,
    }

    return render(request, 'admin_dashboard/ai_performance_analytics.html', context)


@login_required
@user_passes_test(lambda u: u.role in ['admin'])
def system_settings(request):
    """
    System settings and configuration management
    """
    # Get all configurations grouped by category
    configurations = {}
    for category, category_name in SystemConfiguration.CATEGORIES:
        configurations[category] = {
            'name': category_name,
            'settings': SystemConfiguration.objects.filter(category=category).order_by('name')
        }

    # Get recent configuration changes
    recent_changes = ConfigurationHistory.objects.select_related(
        'configuration', 'changed_by'
    ).order_by('-changed_at')[:10]

    # Get system backups
    recent_backups = SystemBackup.objects.select_related('created_by').order_by('-created_at')[:5]

    # System statistics
    system_stats = {
        'total_settings': SystemConfiguration.objects.count(),
        'editable_settings': SystemConfiguration.objects.filter(is_editable=True).count(),
        'recent_changes': ConfigurationHistory.objects.filter(
            changed_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'total_backups': SystemBackup.objects.count(),
        'successful_backups': SystemBackup.objects.filter(status='completed').count(),
    }

    context = {
        'configurations': configurations,
        'recent_changes': recent_changes,
        'recent_backups': recent_backups,
        'system_stats': system_stats,
        'setting_types': SystemConfiguration.SETTING_TYPES,
        'categories': SystemConfiguration.CATEGORIES,
    }

    return render(request, 'admin_dashboard/system_settings.html', context)


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin'])
@require_http_methods(["POST"])
def update_system_setting(request):
    """
    Update a system configuration setting
    """
    try:
        data = json.loads(request.body)
        setting_id = data.get('setting_id')
        new_value = data.get('value')
        change_reason = data.get('reason', '')

        setting = get_object_or_404(SystemConfiguration, id=setting_id)

        if not setting.is_editable:
            return JsonResponse({'success': False, 'error': 'This setting is not editable'})

        # Store old value for history
        old_value = setting.value

        # Update the setting
        setting.set_typed_value(new_value)
        setting.updated_by = request.user
        setting.save()

        # Create history record
        ConfigurationHistory.objects.create(
            configuration=setting,
            old_value=old_value,
            new_value=setting.value,
            change_reason=change_reason,
            changed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Updated system setting: {setting.key} = {new_value}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return JsonResponse({
            'success': True,
            'message': f'Setting {setting.name} updated successfully',
            'requires_restart': setting.requires_restart
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin'])
@require_http_methods(["POST"])
def create_system_setting(request):
    """
    Create a new system configuration setting
    """
    try:
        data = json.loads(request.body)

        setting = SystemConfiguration.objects.create(
            key=data['key'],
            name=data['name'],
            description=data.get('description', ''),
            value=data['value'],
            setting_type=data['setting_type'],
            category=data['category'],
            is_required=data.get('is_required', False),
            is_public=data.get('is_public', False),
            is_editable=data.get('is_editable', True),
            requires_restart=data.get('requires_restart', False),
            default_value=data.get('default_value', ''),
            validation_regex=data.get('validation_regex', ''),
            min_value=data.get('min_value'),
            max_value=data.get('max_value'),
            updated_by=request.user
        )

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Created system setting: {setting.key}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return JsonResponse({
            'success': True,
            'setting_id': setting.id,
            'message': f'Setting {setting.name} created successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role in ['admin'])
@require_http_methods(["POST"])
def create_system_backup(request):
    """
    Create a new system backup
    """
    try:
        data = json.loads(request.body)

        backup = SystemBackup.objects.create(
            name=data['name'],
            backup_type=data['backup_type'],
            created_by=request.user
        )

        # In a real implementation, this would trigger the actual backup process
        # For now, we'll just set it to pending
        backup.status = 'pending'
        backup.save()

        # Create activity log
        UserActivity.objects.create(
            user=request.user,
            activity_type='admin_action',
            description=f'Started system backup: {backup.name}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )

        return JsonResponse({
            'success': True,
            'backup_id': backup.id,
            'message': f'Backup {backup.name} started successfully'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.role in ['admin'])
def system_logs(request):
    """
    System logs and monitoring
    """
    # Get recent user activities
    recent_activities = UserActivity.objects.select_related('user').order_by('-created_at')[:50]

    # Get configuration changes
    config_changes = ConfigurationHistory.objects.select_related(
        'configuration', 'changed_by'
    ).order_by('-changed_at')[:20]

    # Get system statistics
    log_stats = {
        'total_activities': UserActivity.objects.count(),
        'suspicious_activities': UserActivity.objects.filter(is_suspicious=True).count(),
        'admin_actions': UserActivity.objects.filter(activity_type='admin_action').count(),
        'recent_logins': UserActivity.objects.filter(
            activity_type='login',
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count(),
        'config_changes': ConfigurationHistory.objects.filter(
            changed_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }

    context = {
        'recent_activities': recent_activities,
        'config_changes': config_changes,
        'log_stats': log_stats,
    }

    return render(request, 'admin_dashboard/system_logs.html', context)


def debug_url_test(request):
    return render(request, 'admin_dashboard/debug_url_test.html')
