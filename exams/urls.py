from django.urls import path
from . import views

app_name = "exams"

urlpatterns = [
    path("teacher/exams/create/", views.teacher_exam_create, name="teacher_exam_create"),
    path("teacher/exams/<int:exam_id>/manage/", views.teacher_exam_manage, name="teacher_exam_manage"),
    path("teacher/exams/<int:exam_id>/results/", views.teacher_exam_results, name="teacher_exam_results"),
]
