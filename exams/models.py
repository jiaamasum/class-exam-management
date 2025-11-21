from django.db import models
from accounts.models import StudentProfile, TeacherProfile
from academics.models import AcademicYear, ClassLevel, Subject


class Exam(models.Model):
    title = models.CharField(max_length=128)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="exams")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="exams")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="exams")
    assigned_teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="exams")
    exam_date = models.DateField(null=True, blank=True)
    max_marks = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("title", "class_level", "subject", "academic_year")
        ordering = ["exam_date", "title"]

    def __str__(self):
        return f"{self.title} - {self.class_level} ({self.subject})"


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
