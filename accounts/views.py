from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from academics.models import StudentEnrollment, AcademicYear
from exams.models import Exam, ExamResult
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
        return redirect('accounts:admin_dashboard')

    # teacher check
    if hasattr(user, 'teacher_profile'):
        return redirect('academics:teacher_dashboard')

    # student check
    if hasattr(user, 'student_profile'):
        return redirect('accounts:student_dashboard')

    # fallback
    return redirect('accounts:login')


def logout_view(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    logout(request)
    return redirect('accounts:login')


def catch_home(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect('accounts:role_redirect')


def home(request):
    current_years = AcademicYear.objects.filter(is_current=True).count()
    upcoming_exams = Exam.objects.filter(exam_date__gte=timezone.now().date()).count()
    published_results = ExamResult.objects.filter(published=True).count()

    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')

    context = {
        "live_stats": {
            "active_years": current_years,
            "upcoming_exams": upcoming_exams,
            "published_results": published_results,
        }
    }
    return render(request, "home.html", context)


@login_required
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")


def handle_404(request, exception=None):
    """
    Redirect all unknown routes to the home view (which will route based on auth state).
    """
    return redirect('accounts:home')


@login_required
def student_dashboard(request):
    student = getattr(request.user, "student_profile", None)
    if not student:
        return redirect("accounts:role_redirect")

    enrollments = (
        StudentEnrollment.objects.filter(student=student)
        .select_related("class_level", "academic_year")
        .order_by("-academic_year__start_date", "-created_at")
    )
    current_enrollment = enrollments.filter(status="current").first() or enrollments.first()
    current_class = current_enrollment.class_level if current_enrollment else None
    current_year = current_enrollment.academic_year if current_enrollment else None
    subjects = current_class.subjects.all() if current_class else []

    upcoming_exams = (
        Exam.objects.filter(class_level=current_class, academic_year=current_year)
        .select_related("subject")
        .order_by("exam_date")
        if current_class and current_year
        else Exam.objects.none()
    )

    current_results = (
        ExamResult.objects.filter(
            student=student, exam__class_level=current_class, exam__academic_year=current_year
        )
        .select_related("exam__subject")
        .order_by("-exam__exam_date", "exam__title")
        if current_class and current_year
        else ExamResult.objects.none()
    )

    all_results = (
        ExamResult.objects.filter(student=student)
        .select_related("exam__subject", "exam__academic_year", "exam__class_level")
        .order_by("-exam__academic_year__start_date", "exam__title")
    )

    published_count = current_results.filter(published=True).count()
    absence_count = current_results.filter(attendance="absent").count()
    upcoming_count = upcoming_exams.count()

    history_enrollments = (
        enrollments.exclude(pk=current_enrollment.pk) if current_enrollment else enrollments
    )

    context = {
        "student": student,
        "current_enrollment": current_enrollment,
        "current_class": current_class,
        "current_year": current_year,
        "subjects": subjects,
        "upcoming_exams": upcoming_exams,
        "results": current_results,
        "all_results": all_results,
        "history_enrollments": history_enrollments,
        "metrics": {
            "upcoming": upcoming_count,
            "published": published_count,
            "absences": absence_count,
        },
    }
    return render(request, "student_dashboard.html", context)


def fallback_to_home(request, *args, **kwargs):
    return redirect('accounts:home')


