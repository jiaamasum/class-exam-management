import string
import json

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import AcademicYear, ClassLevel, Subject, TeacherAssignment, StudentEnrollment, normalize_section
from .services import promote_enrollments


def all_model_fields(model_class):
    return [field.name for field in model_class._meta.fields]


class ClassLevelAdminForm(forms.ModelForm):
    name = forms.ChoiceField(
        choices=[(f"Class {n}", f"Class {n}") for n in range(1, 11)],
        label="Class",
        help_text="Select from fixed classes (Class 1-10).",
    )
    section = forms.ChoiceField(
        choices=[("", "No section")] + [(letter, letter) for letter in string.ascii_uppercase],
        required=False,
        label="Section",
        help_text="Single letter A-Z. Leave blank if sections are not used.",
    )

    class Meta:
        model = ClassLevel
        fields = "__all__"


class SubjectAdminForm(forms.ModelForm):
    reuse_subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        label="Use existing subject",
        help_text="Pick an existing subject for this class (across sections) to attach to this section.",
    )

    class Meta:
        model = Subject
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Attach metadata for client-side filtering
        classes = list(ClassLevel.objects.select_related("academic_year").only("id", "name", "academic_year_id"))
        class_meta = {
            str(cls.pk): {"name": cls.name, "year_id": cls.academic_year_id}
            for cls in classes
        }
        self.fields["class_level"].widget.attrs["data-class-meta"] = json.dumps(class_meta)

        family_subjects_by_class = {}
        # Build family buckets by (name, year)
        family_ids = {}
        for cls in classes:
            key = (cls.name.lower(), cls.academic_year_id)
            family_ids.setdefault(key, []).append(cls.id)

        subjects = Subject.objects.select_related("class_level", "class_level__academic_year")
        subjects_by_family = {}
        for subj in subjects:
            cls = subj.class_level
            key = (cls.name.lower(), cls.academic_year_id)
            subjects_by_family.setdefault(key, []).append(
                {"id": subj.id, "name": subj.name, "code": subj.code or ""}
            )

        for key, class_ids in family_ids.items():
            subject_list = subjects_by_family.get(key, [])
            for cid in class_ids:
                family_subjects_by_class[str(cid)] = subject_list

        self.fields["reuse_subject"].widget.attrs["data-family-subjects"] = json.dumps(family_subjects_by_class)

        class_level_id = self.initial.get("class_level") or self.data.get("class_level")
        cls = None
        if class_level_id:
            try:
                cls = ClassLevel.objects.get(pk=class_level_id)
            except ClassLevel.DoesNotExist:
                cls = None
        elif getattr(self.instance, "pk", None):
            cls = self.instance.class_level

        if cls:
            family_ids = ClassLevel.objects.filter(
                name__iexact=cls.name, academic_year_id=cls.academic_year_id
            ).values_list("id", flat=True)
            self.fields["reuse_subject"].queryset = Subject.objects.filter(class_level_id__in=family_ids)
            self.fields["reuse_subject"].help_text = "Existing subjects for this class/year across sections."
        else:
            self.fields["reuse_subject"].queryset = Subject.objects.none()

    def clean(self):
        cleaned = super().clean()
        cls = cleaned.get("class_level")
        reuse = cleaned.get("reuse_subject")
        name = (cleaned.get("name") or "").strip()
        code = (cleaned.get("code") or "").strip()

        if not cls:
            return cleaned

        family_ids = ClassLevel.objects.filter(
            name__iexact=cls.name, academic_year_id=cls.academic_year_id
        ).values_list("id", flat=True)

        if reuse:
            cleaned["name"] = reuse.name
            cleaned["code"] = reuse.code
            if reuse.class_level_id not in family_ids:
                self.add_error("reuse_subject", "Pick a subject from the same class and academic year.")
            exists_here = Subject.objects.filter(
                class_level=cls,
                name__iexact=reuse.name,
            ).exclude(pk=self.instance.pk).exists()
            if exists_here:
                self.add_error("reuse_subject", f"'{reuse.name}' is already attached to this section.")
        else:
            if name and Subject.objects.filter(name__iexact=name, class_level_id__in=family_ids).exclude(
                pk=self.instance.pk
            ).exists():
                self.add_error("name", "This subject name already exists for this class across sections.")
            if code and Subject.objects.filter(code__iexact=code, class_level_id__in=family_ids).exclude(
                pk=self.instance.pk
            ).exists():
                self.add_error("code", "This subject code already exists for this class across sections.")

        return cleaned


class TeacherAssignmentAdminForm(forms.ModelForm):
    class Meta:
        model = TeacherAssignment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        class_id = self.initial.get("class_level") or self.data.get("class_level")

        # Show full subject list; validation will enforce class match.
        self.fields["subject"].queryset = Subject.objects.select_related("class_level", "class_level__academic_year")

        # If a class is already picked, scope queryset server-side too
        if class_id:
            try:
                class_id_int = int(class_id)
            except (TypeError, ValueError):
                class_id_int = None
            if class_id_int:
                self.fields["subject"].queryset = Subject.objects.filter(class_level_id=class_id_int)
                if "academic_year" in self.fields:
                    cls = ClassLevel.objects.filter(pk=class_id_int).select_related("academic_year").first()
                    if cls:
                        self.fields["academic_year"].initial = cls.academic_year
        else:
            self.fields["subject"].help_text = "Select a class level to load its subjects."

    def clean(self):
        cleaned = super().clean()
        cls = cleaned.get("class_level")
        subj = cleaned.get("subject")

        if not cls:
            self.add_error("class_level", "Select a class level first.")
            if not subj:
                self.add_error("subject", "Select a subject after choosing a class level.")
            return cleaned

        if not subj:
            self.add_error("subject", "Select a subject that belongs to the chosen class level.")
            return cleaned

        same_year = subj.class_level.academic_year_id == cls.academic_year_id
        same_class_name = subj.class_level.name.lower() == cls.name.lower()
        if not (same_year and same_class_name):
            self.add_error("subject", "Pick a subject from the same class (any section) and academic year.")

        if "academic_year" in cleaned:
            cleaned["academic_year"] = cls.academic_year
        return cleaned


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = all_model_fields(AcademicYear)
    list_filter = ("is_current",)
    search_fields = ("name", "id")


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    form = ClassLevelAdminForm
    list_display = all_model_fields(ClassLevel)
    list_filter = ("academic_year",)
    search_fields = ("name", "section", "id")
    actions = ("promote_entire_class",)

    def save_model(self, request, obj, form, change):
        """
        Allow comma-separated sections to create multiple ClassLevel entries at once
        e.g. section field of "A, B, C" will create three sections for the same class name/year.
        """
        raw_sections = obj.section or ""
        if not change and "," in raw_sections:
            sections = [section.strip() for section in raw_sections.split(",") if section.strip()]
            created_sections = []
            for section in sections:
                try:
                    normalized = normalize_section(section)
                except ValidationError as exc:
                    self.message_user(request, f"Skipping '{section}': {'; '.join(exc.messages)}", level=messages.ERROR)
                    continue

                _, created = ClassLevel.objects.get_or_create(
                    name=obj.name,
                    section=normalized,
                    academic_year=obj.academic_year,
                )
                if created:
                    created_sections.append(normalized)

            if created_sections:
                self.message_user(
                    request,
                    f"Created sections for {obj.name}: {', '.join(created_sections)}",
                )
            return

        super().save_model(request, obj, form, change)

    def promote_entire_class(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select a single class to promote.", level=messages.ERROR)
            return

        target_year = AcademicYear.objects.filter(is_current=True).order_by("-start_date").first()
        if not target_year:
            self.message_user(request, "Mark an academic year as current before promoting.", level=messages.ERROR)
            return

        class_level = queryset.first()
        enrollments = StudentEnrollment.objects.filter(class_level=class_level, status="current")
        try:
            result = promote_enrollments(enrollments, target_year=target_year)
        except ValidationError as exc:
            self.message_user(request, "; ".join(exc.messages), level=messages.ERROR)
            return

        target_label = result.get("target_class") or "target class"
        self.message_user(
            request,
            f"Promoted {result['created']} students from {class_level} to {target_label}. "
            f"Skipped {result['skipped']} already placed.",
            level=messages.INFO,
        )
    promote_entire_class.short_description = "Promote all current students in selected class to next class"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    form = SubjectAdminForm
    list_display = all_model_fields(Subject)
    list_filter = ("class_level",)
    search_fields = ("name", "code", "id")

    class Media:
        js = ("admin/js/subject_reuse_filter.js",)


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    form = TeacherAssignmentAdminForm
    list_display = ("teacher_display",) + tuple(all_model_fields(TeacherAssignment))
    list_filter = ("academic_year", "class_level", "subject")
    search_fields = (
        "teacher__employee_code",
        "teacher__user__username",
        "teacher__user__first_name",
        "teacher__user__last_name",
        "subject__name",
        "class_level__name",
    )

    class Media:
        js = ("admin/js/subject_reuse_filter.js",)

    def teacher_display(self, obj):
        code = obj.teacher.employee_code or "N/A"
        name = obj.teacher.user.get_full_name() or obj.teacher.user.username
        return f"{code} - {name}"
    teacher_display.short_description = "Teacher"


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student_display",) + tuple(all_model_fields(StudentEnrollment))
    list_filter = ("academic_year", "status")
    search_fields = ("student__student_id", "student__user__username", "class_level__name", "roll_number", "id")
    actions = ("promote_selected_students",)

    def student_display(self, obj):
        student = obj.student
        name = student.user.get_full_name() or student.user.username
        code = student.student_id or "N/A"
        return f"{code} - {name}"
    student_display.short_description = "Student"

    def promote_selected_students(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "Select at least one enrollment to promote.", level=messages.WARNING)
            return

        enrollment = queryset.first()
        if queryset.exclude(class_level_id=enrollment.class_level_id).exists():
            self.message_user(request, "Promotions must be run for one class at a time.", level=messages.ERROR)
            return

        target_year = AcademicYear.objects.filter(is_current=True).order_by("-start_date").first()
        if not target_year:
            self.message_user(request, "Mark an academic year as current before promoting students.", level=messages.ERROR)
            return

        try:
            result = promote_enrollments(queryset, target_year=target_year)
        except ValidationError as exc:
            self.message_user(request, "; ".join(exc.messages), level=messages.ERROR)
            return

        target_label = result.get("target_class") or "target class"
        self.message_user(
            request,
            f"Promoted {result['created']} students to {target_label}; skipped {result['skipped']} already enrolled.",
            level=messages.INFO,
        )
    promote_selected_students.short_description = "Promote selected students to their next class"
