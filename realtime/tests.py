from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Enrolment
from realtime.models import CourseMessage

User = get_user_model()


class RealtimeViewTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher1",
            password="testpass123",
            role="TEACHER",
            email="teacher@example.com",
        )
        self.student = User.objects.create_user(
            username="student1",
            password="testpass123",
            role="STUDENT",
            email="student@example.com",
        )
        self.other_student = User.objects.create_user(
            username="student2",
            password="testpass123",
            role="STUDENT",
            email="student2@example.com",
        )

        self.course = Course.objects.create(
            teacher=self.teacher,
            title="Realtime Course",
            description="Course with study room",
            is_visible=True,
        )

    def test_teacher_can_access_course_room(self):
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.get(reverse("course-room", args=[self.course.id]))
        self.assertEqual(response.status_code, 200)

    def test_active_student_can_access_course_room(self):
        Enrolment.objects.create(
            course=self.course,
            student=self.student,
            status=Enrolment.Status.ACTIVE,
        )
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("course-room", args=[self.course.id]))
        self.assertEqual(response.status_code, 200)

    def test_non_enrolled_student_is_redirected_from_course_room(self):
        self.client.login(username="student2", password="testpass123")
        response = self.client.get(reverse("course-room", args=[self.course.id]))
        self.assertEqual(response.status_code, 302)

    def test_older_messages_requires_course_access(self):
        self.client.login(username="student2", password="testpass123")
        response = self.client.get(reverse("course-room-older", args=[self.course.id]))
        self.assertEqual(response.status_code, 403)

    def test_older_messages_returns_json_for_authorised_user(self):
        Enrolment.objects.create(
            course=self.course,
            student=self.student,
            status=Enrolment.Status.ACTIVE,
        )
        CourseMessage.objects.create(course=self.course, sender=self.teacher, text="Hello")
        CourseMessage.objects.create(course=self.course, sender=self.student, text="Hi")

        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("course-room-older", args=[self.course.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("messages", data)
        self.assertEqual(len(data["messages"]), 2)