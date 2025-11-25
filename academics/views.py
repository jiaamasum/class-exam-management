from datetime import date
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, Max, Min
from django.shortcuts import render, redirect

from accounts.models import StudentProfile
from academics.models import TeacherAssignment, StudentEnrollment
from exams.models import Exam


def _get_teacher(request):
    return getattr(request.user, "teacher_profile", None)


def _teacher_assignments(teacher):
    assignments = (
        TeacherAssignment.objects.filter(teacher=teacher)
        .select_related("class_level", "subject", "academic_year")
        .order_by("class_level__name", "subject__name")
    )
    class_map = {}
    subjects_by_class = defaultdict(list)
    for assignment in assignments:
        class_map[assignment.class_level_id] = assignment.class_level
        subjects_by_class[assignment.class_level_id].append(assignment.subject)
    return assignments, class_map, subjects_by_class


def _redirect_dashboard():
    return redirect("academics:teacher_dashboard")


@login_required
def teacher_dashboard(request):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    assignments, class_map, subjects_by_class = _teacher_assignments(teacher)
    assigned_classes = list(class_map.values())
    class_rows = []
    for cls in assigned_classes:
        student_total = StudentEnrollment.objects.filter(
            class_level=cls, academic_year=cls.academic_year
        ).count()
        class_rows.append(
            {"class_level": cls, "subjects": subjects_by_class.get(cls.id, []), "student_count": student_total}
        )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "enroll_student":
            class_id = request.POST.get("class_id")
            identifier = (request.POST.get("student_identifier") or "").strip()
            try:
                class_id_int = int(class_id)
            except (TypeError, ValueError):
                class_id_int = None

            if not class_id_int or class_id_int not in class_map:
                messages.error(request, "You can only admit students into your assigned classes.")
                return _redirect_dashboard()

            if not identifier:
                messages.error(request, "Provide a student ID or username/name to admit.")
                return _redirect_dashboard()

            student = (
                StudentProfile.objects.select_related("user")
                .filter(
                    Q(student_id__iexact=identifier)
                    | Q(user__username__iexact=identifier)
                    | Q(user__first_name__icontains=identifier)
                    | Q(user__last_name__icontains=identifier)
                )
                .first()
            )
            if not student:
                messages.error(request, "No student found for that ID or name.")
                return _redirect_dashboard()

            class_level = class_map[class_id_int]
            enrollment, created = StudentEnrollment.objects.get_or_create(
                student=student,
                class_level=class_level,
                academic_year=class_level.academic_year,
                defaults={"status": "current", "enrolled_on": date.today()},
            )
            if created:
                messages.success(
                    request,
                    f"{student.user.get_full_name() or student.user.username} admitted to {class_level} "
                    f"as roll {enrollment.roll_number}.",
                )
            else:
                messages.info(request, "Student is already enrolled in that class.")
            return _redirect_dashboard()

    teacher_exams = (
        Exam.objects.filter(assigned_teacher=teacher)
        .select_related("class_level", "subject", "academic_year")
        .annotate(
            result_count=Count("results"),
            highest=Max("results__marks_obtained"),
            lowest=Min("results__marks_obtained"),
            average=Avg("results__marks_obtained"),
        )
        .order_by("-exam_date", "title")
    )

    context = {
        "teacher": teacher,
        "assigned_classes": assigned_classes,
        "class_rows": class_rows,
        "subjects_by_class": subjects_by_class,
        "assignments": assignments,
        "teacher_exams": teacher_exams,
        "class_count": len(assigned_classes),
        "subject_count": len(assignments),
        "student_count": StudentEnrollment.objects.filter(class_level__in=assigned_classes).count(),
    }
    return render(request, "teacher_dashboard.html", context)


@login_required
def teacher_class_students(request, class_id):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    _, class_map, _ = _teacher_assignments(teacher)
    class_level = class_map.get(int(class_id))
    if not class_level:
        messages.error(request, "You can only view your assigned classes.")
        return _redirect_dashboard()

    enrollments = (
        StudentEnrollment.objects.filter(class_level=class_level, academic_year=class_level.academic_year)
        .select_related("student__user")
        .order_by("roll_number", "student__user__username")
    )
    return render(
        request,
        "teacher_class_students.html",
        {"class_level": class_level, "enrollments": enrollments, "teacher": teacher},
    )


@login_required
def teacher_class_subjects(request, class_id):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    _, class_map, subjects_by_class = _teacher_assignments(teacher)
    class_level = class_map.get(int(class_id))
    if not class_level:
        messages.error(request, "You can only view your assigned classes.")
        return _redirect_dashboard()

    return render(
        request,
        "teacher_class_subjects.html",
        {
            "class_level": class_level,
            "subjects": subjects_by_class.get(class_level.id, []),
            "teacher": teacher,
        },
    )
