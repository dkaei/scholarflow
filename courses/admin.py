from django.contrib import admin
from .models import Course, Enrolment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "teacher")
    search_fields = ("title", "teacher__username", "teacher__email")


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
    list_display = ("student_name", "course_name", "status")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
        "student__email",
        "course__title",
    )
    list_filter = ("course", "status")
    autocomplete_fields = ("student", "course")

    @admin.display(ordering="student__username", description="Student")
    def student_name(self, obj):
        full = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full or obj.student.username

    @admin.display(ordering="course__title", description="Course")
    def course_name(self, obj):
        return obj.course.title
