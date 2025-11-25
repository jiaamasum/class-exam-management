from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [
    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/classes/<int:class_id>/students/", views.teacher_class_students, name="teacher_class_students"),
    path("teacher/classes/<int:class_id>/subjects/", views.teacher_class_subjects, name="teacher_class_subjects"),
]
