from datetime import date
from typing import Iterable, Optional

from django.core.exceptions import ValidationError
from django.db import transaction

from academics.models import (
    AcademicYear,
    ClassLevel,
    StudentEnrollment,
    ALLOWED_CLASS_NUMBERS,
    normalize_class_name,
)


def extract_class_number(name: str) -> Optional[int]:
    _, number = normalize_class_name(name)
    return number


def next_class_name(class_level: ClassLevel) -> Optional[str]:
    number = extract_class_number(class_level.name)
    if number is None or number >= max(ALLOWED_CLASS_NUMBERS):
        return None
    return f"Class {number + 1}"


def resolve_target_class(source_class: ClassLevel, target_year: AcademicYear) -> Optional[ClassLevel]:
    next_name = next_class_name(source_class)
    if not next_name:
        return None

    return (
        ClassLevel.objects.filter(
            name__iexact=next_name,
            section=source_class.section,
            academic_year=target_year,
        )
        .select_related("academic_year")
        .first()
    )


def _validate_target_year(target_year: AcademicYear):
    if not target_year:
        raise ValidationError("Target academic year is required for promotion.")

    today = date.today()
    if not target_year.is_current:
        raise ValidationError("Target academic year must be marked current before promoting students.")
    if target_year.start_date and target_year.start_date > today:
        raise ValidationError("Cannot promote students into a future academic year.")
    if target_year.end_date and target_year.end_date < today:
        raise ValidationError("Cannot promote students into a past academic year.")


@transaction.atomic
def promote_enrollments(
    enrollments: Iterable[StudentEnrollment],
    target_year: AcademicYear,
):
    """
    Promote a set of enrollments to the next class within the given target academic year.

    Returns a dict with counts and the resolved target class.
    """
    _validate_target_year(target_year)

    enrollment_list = list(enrollments)
    if not enrollment_list:
        return {"created": 0, "skipped": 0, "target_class": None}

    enrollment_list = list(
        StudentEnrollment.objects.filter(pk__in=[e.pk for e in enrollment_list]).select_related(
            "class_level", "academic_year", "student", "class_level__academic_year"
        )
    )
    source_class = enrollment_list[0].class_level
    if any(enr.class_level_id != source_class.id for enr in enrollment_list):
        raise ValidationError("Promotions must target a single class at a time.")

    if source_class.academic_year_id == target_year.id:
        raise ValidationError("Set the next academic year as current before promoting this class.")

    target_class = resolve_target_class(source_class, target_year)
    if not target_class:
        next_name = next_class_name(source_class) or "next class"
        raise ValidationError(
            f"Create '{next_name}' for {target_year} (matching section) before running a promotion."
        )

    created = 0
    skipped = 0
    for enrollment in enrollment_list:
        _, created_flag = StudentEnrollment.objects.get_or_create(
            student=enrollment.student,
            class_level=target_class,
            academic_year=target_year,
            defaults={"status": "current", "enrolled_on": date.today()},
        )
        if created_flag:
            created += 1
            if enrollment.status != "promoted":
                enrollment.status = "promoted"
                enrollment.save(update_fields=["status", "updated_at"])
        else:
            skipped += 1

    return {
        "created": created,
        "skipped": skipped,
        "target_class": target_class,
    }
