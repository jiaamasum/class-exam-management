from django.contrib import admin
from .models import Exam, ExamResult


def all_model_fields(model_class):
    return [field.name for field in model_class._meta.fields]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = all_model_fields(Exam)
    list_filter = ("academic_year", "class_level", "subject")
    search_fields = ("title", "subject__name", "class_level__name", "id")


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = all_model_fields(ExamResult)
    list_filter = ("published", "attendance")
    search_fields = ("exam__title", "student__student_id", "student__user__username", "id")
