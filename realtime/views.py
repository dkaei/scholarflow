from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course
from courses.services import can_access_course
from .models import CourseMessage


@login_required
def course_room(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not can_access_course(request.user, course):
        messages.warning(
            request,
            "This study room is available only to the teacher and students whose enrolment has been approved."
        )
        return redirect("course-detail", course_id=course.id)

    messages_qs = (
        CourseMessage.objects.filter(course=course)
        .select_related("sender")
        .order_by("-created_at")[:30]
    )
    messages_list = list(messages_qs)
    oldest_id = messages_list[-1].id if messages_list else None
    history = list(reversed(messages_list))

    return render(
        request,
        "realtime/course_room.html",
        {
            "course": course,
            "history": history,
            "oldest_id": oldest_id,
        },
    )


@login_required
def older_messages(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not can_access_course(request.user, course):
        return JsonResponse(
            {"detail": "This study room is available only to approved participants."},
            status=403,
        )

    before_id = request.GET.get("before")
    limit = min(int(request.GET.get("limit", 30)), 50)

    queryset = (
        CourseMessage.objects.filter(course=course)
        .select_related("sender")
        .order_by("-id")
    )
    if before_id:
        queryset = queryset.filter(id__lt=before_id)

    messages_list = list(queryset[:limit])
    next_before = messages_list[-1].id if messages_list else None

    return JsonResponse(
        {
            "messages": [
                {
                    "id": message.id,
                    "user": message.sender.display_name or message.sender.username,
                    "sender_id": message.sender_id,
                    "role": getattr(message.sender, "role", ""),
                    "text": message.text,
                    "created_at": message.created_at.isoformat(),
                }
                for message in reversed(messages_list)
            ],
            "next_before": next_before,
        }
    )