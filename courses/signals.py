from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import Enrolment, CourseMaterial
from notifications.models import Notification


@receiver(post_save, sender=Enrolment)
def notify_teacher_on_enrolment(sender, instance: Enrolment, created, **kwargs):
    if not created:
        return

    course = instance.course
    Notification.objects.create(
        user=course.teacher,
        message=f"{instance.student.username} requested to enrol in {course.title}.",
        link=reverse("teacher-course-manage", kwargs={"course_id": course.id}),
    )


@receiver(post_save, sender=CourseMaterial)
def notify_students_on_material_upload(sender, instance: CourseMaterial, created, **kwargs):
    if not created:
        return

    course = instance.course
    qs = course.enrolments.filter(status=Enrolment.Status.ACTIVE).select_related("student")

    Notification.objects.bulk_create([
        Notification(
            user=e.student,
            message=f"New material uploaded in {course.title}: {instance.title}",
            link=reverse("course-detail", kwargs={"course_id": course.id}),
        )
        for e in qs
    ])