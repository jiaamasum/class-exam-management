from django.contrib import admin
from .models import TeacherProfile, StudentProfile

# Register your models here.

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_code', 'joining_date', 'created_at', 'updated_at')

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'roll_number', 'created_at', 'updated_at')

admin.site.register(StudentProfile, StudentProfileAdmin)
