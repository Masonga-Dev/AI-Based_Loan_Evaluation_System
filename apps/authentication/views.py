from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.contrib.auth.forms import PasswordChangeForm
from .models import User, UserProfile
from .forms import UserRegistrationForm, UserProfileForm, CustomAuthenticationForm
import json


def login_view(request):
    """
    Custom login view
    """
    if request.user.is_authenticated:
        if request.user.role == 'admin' or request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        elif request.user.role == 'applicant':
            return redirect('dashboard:admin_dashboard')
        return redirect('/')

    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                if user.role == 'admin' or user.is_staff or user.is_superuser:
                    return redirect('dashboard:admin_dashboard')
                elif user.role == 'applicant':
                    return redirect('dashboard:admin_dashboard')
                next_page = request.GET.get('next', '/')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = CustomAuthenticationForm()

    return render(request, 'authentication/login.html', {'form': form})


def register_view(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  # You might want to set this to False for email verification
            # Always enforce applicant role and no admin privileges
            user.role = 'applicant'
            user.is_staff = False
            user.is_superuser = False
            # Ensure username is set to a unique value (email)
            user.username = user.email
            user.save()

            # Create user profile
            UserProfile.objects.create(user=user)

            # Send welcome email (optional)
            try:
                send_mail(
                    'Welcome to Loan Evaluation System',
                    f'Hello {user.get_full_name()},\n\nWelcome to our AI-Based Loan Evaluation System!',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except:
                pass

            messages.success(request, 'Registration successful! You can now log in.')
            return redirect('authentication:login')
        else:
            # Debug: print form errors to console/logs
            print('Registration form errors:', form.errors.as_json())
    else:
        form = UserRegistrationForm()

    return render(request, 'authentication/register.html', {'form': form})


def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('dashboard:home')


@login_required
def profile_view(request):
    """
    User profile view
    """
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('authentication:profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'authentication/profile.html', context)


@login_required
def settings_view(request):
    """
    User settings view
    """
    if request.method == 'POST':
        password_form = PasswordChangeForm(request.user, request.POST)

        if password_form.is_valid():
            password_form.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('authentication:settings')
    else:
        password_form = PasswordChangeForm(request.user)

    context = {
        'password_form': password_form,
    }
    return render(request, 'authentication/settings.html', context)


def check_email_availability(request):
    """
    AJAX view to check email availability
    """
    if request.method == 'GET':
        email = request.GET.get('email', '')
        is_available = not User.objects.filter(email=email).exists()
        return JsonResponse({'available': is_available})

    return JsonResponse({'available': False})


def check_username_availability(request):
    """
    AJAX view to check username availability
    """
    if request.method == 'GET':
        username = request.GET.get('username', '')
        is_available = not User.objects.filter(username=username).exists()
        return JsonResponse({'available': is_available})

    return JsonResponse({'available': False})
