from django.db import models
from django.db.models import Max, Q
from accounts.models import TeacherProfile, StudentProfile


class AcademicYear(models.Model):
    name = models.CharField(max_length=32, unique=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]

    def __str__(self):
        return self.name


class ClassLevel(models.Model):
    name = models.CharField(max_length=64)
    section = models.CharField(max_length=16, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="classes")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("name", "section", "academic_year")
        ordering = ["academic_year", "name", "section"]

    def __str__(self):
        suffix = f" - {self.section}" if self.section else ""
        return f"{self.name}{suffix} ({self.academic_year})"


class Subject(models.Model):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=16, blank=True)
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="subjects")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("name", "class_level")
        ordering = ["class_level", "name"]

    def __str__(self):
        return f"{self.name} - {self.class_level}"


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="assignments")
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="teacher_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="teacher_assignments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="teacher_assignments")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("teacher", "class_level", "subject", "academic_year")
        ordering = ["academic_year", "class_level", "subject"]

    def __str__(self):
        return f"{self.teacher} -> {self.class_level} / {self.subject}"


class StudentEnrollment(models.Model):
    STATUS_CHOICES = [
        ("current", "Current"),
        ("promoted", "Promoted"),
        ("archived", "Archived"),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="enrollments")
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="enrollments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="current")
    roll_number = models.PositiveIntegerField(null=True, blank=True)
    enrolled_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("student", "class_level", "academic_year")
        ordering = ["academic_year", "class_level", "student"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_level", "academic_year", "roll_number"],
                condition=Q(roll_number__isnull=False),
                name="unique_roll_per_class_year",
            )
        ]

    def __str__(self):
        return f"{self.student} -> {self.class_level} ({self.academic_year})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if (
            is_new
            and self.roll_number is None
            and self.class_level_id
            and self.academic_year_id
        ):
            max_roll = (
                StudentEnrollment.objects.filter(
                    class_level=self.class_level, academic_year=self.academic_year
                ).aggregate(Max("roll_number"))
            ).get("roll_number__max") or 0
            self.roll_number = max_roll + 1

        super().save(*args, **kwargs)

        if is_new and self.roll_number and self.student_id:
            StudentProfile.objects.filter(pk=self.student_id).update(roll_number=self.roll_number)
