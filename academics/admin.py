from django.contrib import admin
from .models import AcademicYear, ClassLevel, Subject, TeacherAssignment, StudentEnrollment


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "is_current", "start_date", "end_date", "created_at")
    list_filter = ("is_current",)
    search_fields = ("name",)


@admin.register(ClassLevel)
class ClassLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "academic_year", "created_at")
    list_filter = ("academic_year",)
    search_fields = ("name", "section")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "class_level", "created_at")
    list_filter = ("class_level",)
    search_fields = ("name", "code")


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "class_level", "subject", "academic_year", "created_at")
    list_filter = ("academic_year", "class_level", "subject")
    search_fields = ("teacher__user__username", "subject__name", "class_level__name")


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "class_level", "academic_year", "status", "enrolled_on", "created_at")
    list_filter = ("academic_year", "status")
    search_fields = ("student__user__username", "class_level__name")
