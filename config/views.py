from django.shortcuts import render
from courses.models import Course, Enrolment


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home.html")

    if request.user.role == "TEACHER":
        courses = Course.objects.filter(teacher=request.user).order_by("-created_at")
        return render(request, "dashboard_teacher.html", {"courses": courses})

    enrolments = (
        Enrolment.objects.filter(student=request.user, status=Enrolment.Status.ACTIVE)
        .select_related("course", "course__teacher")
        .order_by("-created_at")
    )
    return render(request, "dashboard_student.html", {"enrolments": enrolments})