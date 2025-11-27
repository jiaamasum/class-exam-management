from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Max, Min, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.models import StudentProfile
from academics.models import ClassLevel, StudentEnrollment, TeacherAssignment
from exams.models import Exam, ExamResult


def _get_teacher(request):
    return getattr(request.user, "teacher_profile", None)


def _teacher_assignments(teacher):
    return TeacherAssignment.objects.filter(teacher=teacher)


def _redirect_dashboard():
    return redirect(reverse("academics:teacher_dashboard"))


@login_required
def teacher_exam_create(request):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    assignments = _teacher_assignments(teacher).select_related("class_level", "subject", "academic_year")

    if request.method == "POST":
        combo = request.POST.get("class_subject")
        title = (request.POST.get("title") or "").strip()
        exam_date_str = (request.POST.get("exam_date") or "").strip()
        max_marks = request.POST.get("max_marks") or "100"

        if not combo or ":" not in combo:
            messages.error(request, "Pick a class and subject you are assigned to.")
            return redirect("exams:teacher_exam_create")

        try:
            class_part, subject_part = combo.split(":", 1)
            class_id_int = int(class_part)
            subject_id_int = int(subject_part)
        except (TypeError, ValueError):
            messages.error(request, "Invalid class/subject selection.")
            return redirect("exams:teacher_exam_create")

        assignment_exists = assignments.filter(
            class_level_id=class_id_int, subject_id=subject_id_int
        ).exists()
        if not assignment_exists:
            messages.error(request, "You can only create exams for your assigned class-subject pairs.")
            return redirect("exams:teacher_exam_create")

        if not title:
            messages.error(request, "Title is required for an exam.")
            return redirect("exams:teacher_exam_create")

        exam_date_value = None
        if exam_date_str:
            try:
                exam_date_value = date.fromisoformat(exam_date_str)
            except ValueError:
                messages.error(request, "Use a valid exam date (YYYY-MM-DD).")
                return redirect("exams:teacher_exam_create")
            if exam_date_value < date.today():
                messages.error(request, "Exam date cannot be in the past.")
                return redirect("exams:teacher_exam_create")

        try:
            max_marks_value = int(max_marks)
        except (TypeError, ValueError):
            max_marks_value = 100

        class_level = ClassLevel.objects.get(pk=class_id_int)
        exam = Exam.objects.create(
            title=title,
            class_level=class_level,
            subject_id=subject_id_int,
            academic_year=class_level.academic_year,
            assigned_teacher=teacher,
            exam_date=exam_date_value,
            max_marks=max_marks_value,
        )
        messages.success(request, f"Exam '{exam.title}' created for {exam.class_level} ({exam.subject}).")
        return _redirect_dashboard()

    assignment_pairs = [
        {
            "value": f"{a.class_level_id}:{a.subject_id}",
            "label": f"{a.class_level} • {a.subject.name}",
            "class_id": a.class_level_id,
        }
        for a in assignments
    ]
    return render(
        request,
        "teacher_exam_create.html",
        {"assignment_pairs": assignment_pairs, "teacher": teacher},
    )


@login_required
def teacher_exam_manage(request, exam_id):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    exam = get_object_or_404(
        Exam.objects.select_related("class_level", "subject", "academic_year"),
        pk=exam_id,
        assigned_teacher=teacher,
    )

    if request.method == "POST":
        student_identifier = (request.POST.get("student_identifier") or "").strip()
        marks_input = (request.POST.get("marks_obtained") or "").strip()
        attendance = request.POST.get("attendance") or "present"

        student = (
            StudentProfile.objects.select_related("user")
            .filter(
                Q(student_id__iexact=student_identifier)
                | Q(user__username__iexact=student_identifier)
                | Q(user__first_name__icontains=student_identifier)
                | Q(user__last_name__icontains=student_identifier)
            )
            .first()
        )
        if not student:
            messages.error(request, "Student not found for that ID or name.")
            return redirect("exams:teacher_exam_manage", exam_id=exam_id)

        is_enrolled = StudentEnrollment.objects.filter(
            student=student,
            class_level=exam.class_level,
            academic_year=exam.academic_year,
        ).exists()
        if not is_enrolled:
            messages.error(request, "Student is not enrolled in this class for the exam's year.")
            return redirect("exams:teacher_exam_manage", exam_id=exam_id)

        marks_value = None
        if marks_input:
            try:
                marks_value = Decimal(marks_input)
            except (InvalidOperation, ValueError):
                messages.error(request, "Enter a numeric mark or leave blank.")
                return redirect("exams:teacher_exam_manage", exam_id=exam_id)

        ExamResult.objects.update_or_create(
            exam=exam,
            student=student,
            defaults={"marks_obtained": marks_value, "attendance": attendance},
        )
        messages.success(
            request,
            f"Saved marks for {student.user.get_full_name() or student.user.username} on {exam.title}.",
        )
        return redirect("exams:teacher_exam_manage", exam_id=exam_id)

    enrollments = (
        StudentEnrollment.objects.filter(class_level=exam.class_level, academic_year=exam.academic_year)
        .select_related("student__user")
        .order_by("roll_number", "student__user__username")
    )
    results_map = {
        res.student_id: res
        for res in ExamResult.objects.filter(exam=exam).select_related("student__user")
    }
    rows = []
    for enrollment in enrollments:
        res = results_map.get(enrollment.student_id)
        rows.append(
            {
                "student": enrollment.student,
                "roll_number": enrollment.roll_number,
                "marks": res.marks_obtained if res else None,
                "attendance": res.attendance if res else "present",
            }
        )

    return render(
        request,
        "teacher_exam_manage.html",
        {"exam": exam, "rows": rows, "teacher": teacher},
    )


@login_required
def teacher_exam_results(request, exam_id):
    teacher = _get_teacher(request)
    if not teacher:
        return redirect("accounts:role_redirect")

    exam = get_object_or_404(
        Exam.objects.select_related("class_level", "subject", "academic_year"),
        pk=exam_id,
        assigned_teacher=teacher,
    )

    results = (
        ExamResult.objects.filter(exam=exam)
        .select_related("student__user")
        .order_by("marks_obtained", "student__user__username")
    )
    stats = results.aggregate(
        highest=Max("marks_obtained"),
        lowest=Min("marks_obtained"),
        average=Avg("marks_obtained"),
        total=Count("id"),
    )

    return render(
        request,
        "teacher_exam_results.html",
        {"exam": exam, "results": results, "stats": stats, "teacher": teacher},
    )
