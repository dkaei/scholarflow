from .models import Enrolment

def can_access_course(user, course) -> bool:
    if not user.is_authenticated:
        return False

    if course.teacher_id == user.id:
        return True

    return Enrolment.objects.filter(
        course=course,
        student=user,
        status=Enrolment.Status.ACTIVE,
    ).exists()
