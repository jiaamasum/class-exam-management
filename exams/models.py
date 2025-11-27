from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import StudentProfile, TeacherProfile
from academics.models import AcademicYear, ClassLevel, Subject
from exams.validators import validate_not_past_exam


class Exam(models.Model):
    title = models.CharField(max_length=128)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="exams")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="exams")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="exams")
    assigned_teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="exams")
    exam_date = models.DateField(null=True, blank=True, validators=[validate_not_past_exam])
    max_marks = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("title", "class_level", "subject", "academic_year")
        ordering = ["exam_date", "title"]

    def __str__(self):
        return f"{self.title} - {self.class_level} ({self.subject})"

    def clean(self):
        super().clean()
        errors = {}

        if self.subject and self.class_level and self.subject.class_level_id != self.class_level_id:
            errors["subject"] = "Subject must belong to the selected class."

        if self.class_level and self.academic_year and self.class_level.academic_year_id != self.academic_year_id:
            errors["academic_year"] = "Exam academic year must match the class academic year."

        if self.assigned_teacher and self.class_level and self.subject and self.academic_year:
            from academics.models import TeacherAssignment  # local import to avoid circularity

            assigned = TeacherAssignment.objects.filter(
                teacher=self.assigned_teacher,
                class_level=self.class_level,
                subject=self.subject,
                academic_year=self.academic_year,
            ).exists()
            if not assigned:
                errors["assigned_teacher"] = "Assigned teacher is not mapped to this class/subject/year."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ExamResult(models.Model):
    ATTENDANCE_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
    ]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="results")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="exam_results")
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    attendance = models.CharField(max_length=8, choices=ATTENDANCE_CHOICES, default="present")
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("exam", "student")
        ordering = ["exam", "student"]

    def __str__(self):
        return f"{self.exam} - {self.student}"
