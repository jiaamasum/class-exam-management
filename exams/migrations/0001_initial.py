from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('academics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Exam',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128)),
                ('exam_date', models.DateField(blank=True, null=True)),
                ('max_marks', models.PositiveIntegerField(default=100)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, blank=True)),
                ('academic_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exams', to='academics.academicyear')),
                ('assigned_teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exams', to='accounts.teacherprofile')),
                ('class_level', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exams', to='academics.classlevel')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exams', to='academics.subject')),
            ],
            options={
                'ordering': ['exam_date', 'title'],
                'unique_together': {('title', 'class_level', 'subject', 'academic_year')},
            },
        ),
        migrations.CreateModel(
            name='ExamResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marks_obtained', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('attendance', models.CharField(choices=[('present', 'Present'), ('absent', 'Absent')], default='present', max_length=8)),
                ('published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, blank=True)),
                ('exam', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='exams.exam')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exam_results', to='accounts.studentprofile')),
            ],
            options={
                'ordering': ['exam', 'student'],
                'unique_together': {('exam', 'student')},
            },
        ),
    ]
