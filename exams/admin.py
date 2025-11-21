from django.contrib import admin
from .models import Exam, ExamResult


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "class_level", "subject", "academic_year", "exam_date", "max_marks", "created_at")
    list_filter = ("academic_year", "class_level", "subject")
    search_fields = ("title", "subject__name", "class_level__name")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ("exam", "student", "marks_obtained", "attendance", "published", "updated_at")
    list_filter = ("published", "attendance")
    search_fields = ("exam__title", "student__user__username")
