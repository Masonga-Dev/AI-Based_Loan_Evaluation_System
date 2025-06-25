from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Count, Q
from datetime import datetime, timedelta
from apps.loan_application.models import LoanApplication
from apps.ai_evaluation.models import PredictionResult
from django.urls import reverse
from .models import Notification
from django.views.decorators.csrf import csrf_exempt
from .forms import ApplicantProfileForm
from django.contrib import messages


def home(request):
    """
    Home page view - shows professional landing page for all users
    """
    return render(request, 'home.html')


def landing(request):
    """
    Landing page view
    """
    return render(request, 'landing.html')


@login_required
def dashboard_redirect(request):
    """
    Redirect to dashboard after login
    """
    return HttpResponseRedirect('/')


@login_required
def dashboard_home(request):
    """
    Main dashboard view
    """
    user = request.user
    context = {}

    # Enforce correct dashboard URL
    path = request.path
    if user.role == 'applicant' and not path.endswith('/applicant-dashboard/'):
        return HttpResponseRedirect(reverse('dashboard:applicant_dashboard'))
    elif user.role in ['officer', 'manager', 'admin'] and not path.endswith('/admin-dashboard/'):
        return HttpResponseRedirect(reverse('dashboard:admin_dashboard'))

    if user.role == 'applicant':
        # Applicant dashboard
        applications = LoanApplication.objects.filter(applicant=user)
        context.update({
            'loan_applications': applications.order_by('-created_at'),
            'total_applications': applications.count(),
            'pending_applications': applications.filter(status__in=['draft', 'submitted', 'under_review']).count(),
            'approved_applications': applications.filter(status='approved').count(),
            'recent_applications': applications.order_by('-created_at')[:5],
        })
        template = 'dashboard/applicant_dashboard.html'

    elif user.role in ['officer', 'manager', 'admin']:
        # Staff dashboard
        all_applications = LoanApplication.objects.all()
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        context.update({
            'total_applications': all_applications.count(),
            'pending_review': all_applications.filter(status='under_review').count(),
            'approved_today': all_applications.filter(status='approved', decision_date__date=today).count(),
            'new_this_week': all_applications.filter(created_at__date__gte=week_ago).count(),
            'recent_applications': all_applications.order_by('-created_at')[:10],
            'assigned_to_me': all_applications.filter(assigned_officer=user).count() if user.role in ['officer', 'manager'] else 0,
        })
        template = 'dashboard/staff_dashboard.html'

    else:
        template = 'dashboard/default_dashboard.html'

    return render(request, template, context)


@login_required
def dashboard_stats(request):
    """
    Dashboard statistics API endpoint
    """
    if request.user.role not in ['officer', 'manager', 'admin']:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Get statistics for the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)

    applications = LoanApplication.objects.filter(created_at__gte=thirty_days_ago)

    stats = {
        'total_applications': applications.count(),
        'approved': applications.filter(status='approved').count(),
        'rejected': applications.filter(status='rejected').count(),
        'pending': applications.filter(status__in=['submitted', 'under_review']).count(),
        'average_processing_time': 0,  # Calculate this based on your needs
    }

    # Application trends by day
    daily_stats = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=i)).date()
        daily_count = applications.filter(created_at__date=date).count()
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': daily_count
        })

    stats['daily_trends'] = list(reversed(daily_stats))

    return JsonResponse(stats)


@login_required
def recent_activity(request):
    """
    Recent activity feed
    """
    if request.user.role == 'applicant':
        # Show user's own activity
        applications = LoanApplication.objects.filter(
            applicant=request.user
        ).order_by('-updated_at')[:10]
    else:
        # Show all recent activity for staff
        applications = LoanApplication.objects.all().order_by('-updated_at')[:20]

    activities = []
    for app in applications:
        activities.append({
            'id': app.id,
            'application_number': app.application_number,
            'applicant_name': app.applicant.get_full_name(),
            'status': app.status,
            'updated_at': app.updated_at,
            'loan_amount': app.loan_amount,
        })

    return JsonResponse({'activities': activities})


@login_required
def user_notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    unread_count = notifications.filter(is_read=False).count()
    data = {
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'created_at': n.created_at.strftime('%b %d, %Y %H:%M'),
                'is_read': n.is_read,
                'link': n.link
            } for n in notifications
        ],
        'unread_count': unread_count
    }
    return JsonResponse(data)

@csrf_exempt
@login_required
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@login_required
def notifications_page(request):
    return render(request, 'dashboard/notifications.html')

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = ApplicantProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return render(request, 'dashboard/edit_profile.html', {'form': form})
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ApplicantProfileForm(instance=user)
    return render(request, 'dashboard/edit_profile.html', {'form': form})
