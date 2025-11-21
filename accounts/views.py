from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import TeacherProfile, StudentProfile
from .forms import EmailExistsPasswordResetForm


class RedirectIfAuthenticatedMixin:
    """
    Redirect logged-in users away from auth pages (login/signup/reset)
    to their role-based destination.
    """
    redirect_url = 'accounts:role_redirect'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.redirect_url)
        return super().dispatch(request, *args, **kwargs)


class CEMSLoginView(RedirectIfAuthenticatedMixin, auth_views.LoginView):
    redirect_authenticated_user = True
    template_name = 'login.html'


class CEMSPasswordResetView(RedirectIfAuthenticatedMixin, auth_views.PasswordResetView):
    template_name = 'password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    form_class = EmailExistsPasswordResetForm


def student_register(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'signup.html', {
                'error': 'Passwords do not match'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {
                'error': 'Username already exists'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # create student profile
        StudentProfile.objects.create(user=user)

        # auto login
        login(request, user)

        return redirect('accounts:role_redirect')

    return render(request, 'signup.html')


@login_required
def role_redirect(request):
    user = request.user

    if user.is_superuser:
        # super admin: send to Django admin for now
        return redirect('/admin_dashboard/')

    # teacher check
    if hasattr(user, 'teacher_profile'):
        # update this later when you create teacher dashboard
        return redirect('/teacher_dashboard')  

    # student check
    if hasattr(user, 'student_profile'):
        # update this later when you create student dashboard
        return redirect('/student_dashboard')  

    # fallback
    return redirect('accounts:login')


def logout_view(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    logout(request)
    return redirect('accounts:login')


