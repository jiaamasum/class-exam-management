from datetime import date

from django.core.exceptions import ValidationError


def validate_not_past_exam(value):
    if value and value < date.today():
        raise ValidationError("Exam date cannot be in the past.")
