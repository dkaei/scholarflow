from django.conf import settings
from django.db import models


class Course(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teaching_courses",
        limit_choices_to={"role": "TEACHER"},
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_visible = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class Enrolment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        REJECTED = "REJECTED", "Rejected"
        BLOCKED = "BLOCKED", "Blocked"
        REMOVED = "REMOVED", "Removed"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrolments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrolments",
        limit_choices_to={"role": "STUDENT"},
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    remark = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="uniq_course_student")
        ]
        indexes = [
            models.Index(fields=["course", "status"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student.username} → {self.course.title} ({self.status})"


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.course.title} · {self.title}"


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ("video", "Video"),
        ("pdf", "PDF"),
        ("image", "Image"),
        ("file", "File"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="materials",
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    material_type = models.CharField(max_length=10, choices=MATERIAL_TYPES, default="file")
    order = models.PositiveIntegerField(default=1)
    file = models.FileField(upload_to="materials/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lesson__order", "order", "id"]

    def __str__(self) -> str:
        return f"{self.course.title}: {self.title}"


class CourseFeedback(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="feedbacks")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "student"], name="uniq_feedback_per_course_student")
        ]

    def __str__(self) -> str:
        return f"{self.course.title}: {self.student.username} ({self.rating})"