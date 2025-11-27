import re
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q
from accounts.models import TeacherProfile, StudentProfile

ALLOWED_CLASS_NUMBERS = list(range(1, 11))
CLASS_NAME_PATTERN = re.compile(r"^class\s*(\d{1,2})$", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^[A-Z]$")


def normalize_class_name(raw_name):
    """
    Normalize class names to the pattern 'Class X' where X is 1-10.
    Returns a tuple of (normalized_name, number or None).
    """
    name = (raw_name or "").strip()
    match = CLASS_NAME_PATTERN.match(name)
    if not match:
        return name, None
    number = int(match.group(1))
    return f"Class {number}", number


def normalize_section(raw_section):
    """
    Normalize section to a single uppercase letter A-Z.
    Returns the normalized value or None if input is falsy.
    Raises ValidationError for invalid values.
    """
    if not raw_section:
        return ""
    section = raw_section.strip().upper()
    if not SECTION_PATTERN.match(section):
        raise ValidationError({"section": "Section must be a single letter A-Z."})
    return section


def _years_in_range(start_date, end_date):
    if start_date and end_date:
        start_year = start_date.year
        end_year = end_date.year
    elif start_date:
        start_year = end_year = start_date.year
    elif end_date:
        start_year = end_year = end_date.year
    else:
        return set()
    return set(range(start_year, end_year + 1))


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

    def clean(self):
        super().clean()
        errors = {}
        if self.start_date and self.end_date and self.start_date > self.end_date:
            errors["end_date"] = "End date must be after start date."

        candidate_years = _years_in_range(self.start_date, self.end_date)
        if candidate_years:
            overlapping = []
            qs = AcademicYear.objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            for other in qs:
                other_years = _years_in_range(other.start_date, other.end_date)
                if candidate_years & other_years:
                    overlapping.extend(sorted(candidate_years & other_years))
            if overlapping:
                unique_years = ", ".join(str(y) for y in sorted(set(overlapping)))
                errors["start_date"] = f"Only one academic year can exist per calendar year. Conflict in: {unique_years}."
                errors["end_date"] = errors["start_date"]

        if errors:
            raise ValidationError(errors)


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

    def clean(self):
        super().clean()
        normalized_name, number = normalize_class_name(self.name)
        if number not in ALLOWED_CLASS_NUMBERS:
            raise ValidationError({"name": "Class name must be between Class 1 and Class 10."})
        self.name = normalized_name
        self.section = normalize_section(self.section)

        if self.academic_year and self.academic_year.start_date and self.academic_year.start_date > date.today():
            raise ValidationError({"academic_year": "Cannot create classes for a future academic year."})

        if (
            self.academic_year_id
            and ClassLevel.objects.filter(
                name__iexact=self.name,
                section__iexact=self.section,
                academic_year_id=self.academic_year_id,
            )
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError({"section": "This class and section already exists for the academic year."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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

    def clean(self):
        super().clean()
        errors = {}
        if self.class_level and self.class_level.academic_year:
            year = self.class_level.academic_year
            today = date.today()
            if not year.is_current:
                errors["class_level"] = "Subjects can only be created for the current academic year."
            elif year.start_date and year.start_date > today:
                errors["class_level"] = "Cannot create subjects for a future academic year."
            elif year.end_date and year.end_date < today:
                errors["class_level"] = "Cannot create subjects for a past academic year."

            # Allow reuse of the same subject name/code across other sections of the same class,
            # but keep uniqueness within the specific section/class_level.
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name="assignments")
    class_level = models.ForeignKey(ClassLevel, on_delete=models.CASCADE, related_name="teacher_assignments")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="teacher_assignments")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="teacher_assignments")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        unique_together = ("teacher", "class_level", "subject", "academic_year")
        constraints = [
            models.UniqueConstraint(
                fields=["class_level", "subject", "academic_year"],
                name="unique_class_subject_year_assignment",
            )
        ]
        ordering = ["academic_year", "class_level", "subject"]

    def __str__(self):
        def safe_rel(obj, attr, fallback):
            rel_id = getattr(obj, f"{attr}_id", None)
            if not rel_id:
                return fallback
            try:
                return getattr(obj, attr)
            except Exception:
                return fallback

        teacher_display = safe_rel(self, "teacher", "No teacher")
        class_display = safe_rel(self, "class_level", "No class")
        subject_display = safe_rel(self, "subject", "No subject")
        return f"{teacher_display} -> {class_display} / {subject_display}"

    def clean(self):
        super().clean()
        errors = {}
        if self.subject and self.class_level and self.subject.class_level_id != self.class_level_id:
            errors["subject"] = "Subject must belong to the selected class."

        if self.academic_year and self.class_level and self.class_level.academic_year_id != self.academic_year_id:
            errors["academic_year"] = "Assignment academic year must match the class academic year."

        if self.academic_year:
            today = date.today()
            if not self.academic_year.is_current:
                errors["academic_year"] = "Cannot assign teachers to non-current academic years."
            elif self.academic_year.start_date and self.academic_year.start_date > today:
                errors["academic_year"] = "Cannot assign teachers to a future academic year."
            elif self.academic_year.end_date and self.academic_year.end_date < today:
                errors["academic_year"] = "Cannot assign teachers to a past academic year."

        if self.class_level and self.subject and self.academic_year:
            conflict_exists = (
                TeacherAssignment.objects.filter(
                    class_level=self.class_level,
                    subject=self.subject,
                    academic_year=self.academic_year,
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if conflict_exists:
                errors["subject"] = "This class/subject/year is already assigned to another teacher."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


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
        self.full_clean()
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

    def clean(self):
        super().clean()
        errors = {}
        is_new = self.pk is None
        original = None
        if not is_new:
            original = (
                StudentEnrollment.objects.filter(pk=self.pk)
                .values("academic_year_id", "class_level_id")
                .first()
            )

        enforce_year_rules = is_new or not original or (
            original["academic_year_id"] != self.academic_year_id
            or original["class_level_id"] != self.class_level_id
        )

        if self.class_level and self.academic_year and self.class_level.academic_year_id != self.academic_year_id:
            errors["academic_year"] = "Enrollment academic year must match the class academic year."

        if self.academic_year and enforce_year_rules:
            today = date.today()
            if not self.academic_year.is_current:
                errors["academic_year"] = "Students can only be admitted into the current academic year."
            elif self.academic_year.start_date and self.academic_year.start_date > today:
                errors["academic_year"] = "Cannot admit students into a future academic year."
            elif self.academic_year.end_date and self.academic_year.end_date < today:
                errors["academic_year"] = "Cannot admit students into a past academic year."

        if self.student_id and self.class_level_id and self.academic_year_id:
            exists = (
                StudentEnrollment.objects.filter(
                    student_id=self.student_id,
                    class_level_id=self.class_level_id,
                    academic_year_id=self.academic_year_id,
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if exists:
                errors["student"] = "This student is already enrolled in this class for the academic year."

        if errors:
            raise ValidationError(errors)
