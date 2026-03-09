from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, permissions

from .models import Course, Lesson
from .serializers import CourseListSerializer, CourseDetailSerializer, LessonSerializer


class PublicCoursePermission(permissions.BasePermission):
    """
    Allow authenticated users to read.
    Students only see visible courses.
    Teachers can see their own courses in detail if needed.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


@extend_schema(
    tags=["Courses API"],
    summary="List courses",
    description="Returns visible courses for students. Teachers can also search courses by title.",
    parameters=[
        OpenApiParameter(
            name="q",
            description="Optional course title search",
            required=False,
            type=str,
        ),
    ],
)
class CourseListAPIView(generics.ListAPIView):
    serializer_class = CourseListSerializer
    permission_classes = [PublicCoursePermission]

    def get_queryset(self):
        user = self.request.user
        q = (self.request.GET.get("q") or "").strip()

        if getattr(user, "role", None) == "TEACHER":
            queryset = Course.objects.select_related("teacher").order_by("-created_at")
        else:
            queryset = (
                Course.objects.select_related("teacher")
                .filter(is_visible=True)
                .order_by("-created_at")
            )

        if q:
            queryset = queryset.filter(title__icontains=q)

        return queryset


@extend_schema(
    tags=["Courses API"],
    summary="Retrieve a course",
    description="Returns a course with its lessons and materials.",
)
class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CourseDetailSerializer
    permission_classes = [PublicCoursePermission]
    lookup_url_kwarg = "course_id"

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "role", None) == "TEACHER":
            return (
                Course.objects.select_related("teacher")
                .prefetch_related("lessons__materials")
                .order_by("-created_at")
            )

        return (
            Course.objects.select_related("teacher")
            .filter(is_visible=True)
            .prefetch_related("lessons__materials")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Courses API"],
    summary="List lessons for a course",
    description="Returns ordered lessons and their materials for a given course.",
)
class CourseLessonListAPIView(generics.ListAPIView):
    serializer_class = LessonSerializer
    permission_classes = [PublicCoursePermission]

    def get_queryset(self):
        user = self.request.user
        course_id = self.kwargs["course_id"]

        if getattr(user, "role", None) == "TEACHER":
            course_qs = Course.objects.filter(id=course_id)
        else:
            course_qs = Course.objects.filter(id=course_id, is_visible=True)

        course = course_qs.first()
        if not course:
            return Lesson.objects.none()

        return course.lessons.prefetch_related("materials").order_by("order", "id")