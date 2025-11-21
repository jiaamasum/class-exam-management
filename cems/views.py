from django.shortcuts import render

def home(request):
    return render(request, 'home.html')
def adminfunction(request):
    return render(request, 'admin_dashboard.html')
def student_dashboard(request):
    return render(request, 'student_dashboard.html')
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard.html')