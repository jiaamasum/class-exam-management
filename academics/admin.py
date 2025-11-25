from django.contrib import admin
from .models import AcademicYear, ClassLevel, Subject, TeacherAssignment, StudentEnrollment


def all_model_fields(model_class):
    return [field.name for field in model_class._meta.fields]


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = all_model_fields(AcademicYear)
    list_filter = ("is_current",)
    search_fields = ("name", "id")


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = all_model_fields(ClassLevel)
    list_filter = ("academic_year",)
    search_fields = ("name", "section", "id")

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
                _, created = ClassLevel.objects.get_or_create(
                    name=obj.name,
                    section=section,
                    academic_year=obj.academic_year,
                )
                if created:
                    created_sections.append(section)

            if created_sections:
                self.message_user(
                    request,
                    f"Created sections for {obj.name}: {', '.join(created_sections)}",
                )
            return

        super().save_model(request, obj, form, change)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = all_model_fields(Subject)
    list_filter = ("class_level",)
    search_fields = ("name", "code", "id")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
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

    def student_display(self, obj):
        student = obj.student
        name = student.user.get_full_name() or student.user.username
        code = student.student_id or "N/A"
        return f"{code} - {name}"
    student_display.short_description = "Student"
