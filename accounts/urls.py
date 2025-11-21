from django.urls import path
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from .forms import EmailExistsPasswordResetForm

app_name = 'accounts'

urlpatterns = [
    # Login and Logout
    path('login/', views.CEMSLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Registration - for students only
    path('register/student/', views.student_register, name='student_register'),

    # Role based redirect after login
    path('role-redirect/', views.role_redirect, name='role_redirect'),

    # Password reset flow
    path('password-reset/', views.CEMSPasswordResetView.as_view(
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),



]
