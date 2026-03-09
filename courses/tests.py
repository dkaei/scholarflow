import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import Course, Enrolment, Lesson, CourseMaterial, CourseFeedback

User = get_user_model()


TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class CourseTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher1",
            password="testpass123",
            role="TEACHER",
            email="teacher@example.com",
            display_name="Teacher One",
        )
        self.student = User.objects.create_user(
            username="student1",
            password="testpass123",
            role="STUDENT",
            email="student@example.com",
            display_name="Student One",
        )

        self.public_course = Course.objects.create(
            teacher=self.teacher,
            title="Visible Course",
            description="Visible course",
            is_visible=True,
        )
        self.hidden_course = Course.objects.create(
            teacher=self.teacher,
            title="Hidden Course",
            description="Hidden course",
            is_visible=False,
        )
        self.lesson = Lesson.objects.create(
            course=self.public_course,
            title="Lesson 1",
            order=1,
        )

    def test_course_model_creation(self):
        self.assertEqual(self.public_course.title, "Visible Course")
        self.assertEqual(self.public_course.teacher, self.teacher)
        self.assertTrue(self.public_course.is_visible)

    def test_teacher_course_create_view_creates_hidden_course_and_default_lesson(self):
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.post(
            reverse("teacher-course-create"),
            {
                "title": "New Course",
                "description": "New description",
            },
        )
        self.assertEqual(response.status_code, 302)

        course = Course.objects.get(title="New Course")
        self.assertFalse(course.is_visible)
        self.assertTrue(Lesson.objects.filter(course=course, title="Lesson 1", order=1).exists())

    def test_student_course_list_shows_only_visible_courses(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("course-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visible Course")
        self.assertNotContains(response, "Hidden Course")

    def test_course_search_filters_by_title(self):
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.get(reverse("course-list"), {"q": "Visible"})
        self.assertContains(response, "Visible Course")
        self.assertNotContains(response, "Hidden Course")

    def test_student_can_request_enrolment(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(reverse("course-enrol", args=[self.public_course.id]))
        self.assertEqual(response.status_code, 302)
        enrolment = Enrolment.objects.get(course=self.public_course, student=self.student)
        self.assertEqual(enrolment.status, Enrolment.Status.PENDING)

    def test_teacher_can_approve_pending_enrolment(self):
        enrolment = Enrolment.objects.create(
            course=self.public_course,
            student=self.student,
            status=Enrolment.Status.PENDING,
        )
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.post(
            reverse("teacher-enrolment-update", args=[self.public_course.id, enrolment.id]),
            {"action": "approve"},
        )
        self.assertEqual(response.status_code, 302)
        enrolment.refresh_from_db()
        self.assertEqual(enrolment.status, Enrolment.Status.ACTIVE)

    def test_student_cannot_access_teacher_course_manage(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("teacher-course-manage", args=[self.public_course.id]))
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_toggle_course_visibility(self):
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.post(
            reverse("teacher-course-toggle-visibility", args=[self.hidden_course.id])
        )
        self.assertEqual(response.status_code, 302)
        self.hidden_course.refresh_from_db()
        self.assertTrue(self.hidden_course.is_visible)

    def test_teacher_can_upload_material_to_lesson(self):
        self.client.login(username="teacher1", password="testpass123")
        test_file = SimpleUploadedFile(
            "slides.pdf",
            b"%PDF-1.4 test content",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("teacher-material-upload", args=[self.public_course.id]),
            {
                "lesson": self.lesson.id,
                "title": "Week 1 Slides",
                "order": 1,
                "file": test_file,
            },
        )
        self.assertEqual(response.status_code, 302)

        material = CourseMaterial.objects.get(title="Week 1 Slides")
        self.assertEqual(material.course, self.public_course)
        self.assertEqual(material.lesson, self.lesson)
        self.assertEqual(material.material_type, "pdf")

    def test_active_student_can_leave_feedback(self):
        Enrolment.objects.create(
            course=self.public_course,
            student=self.student,
            status=Enrolment.Status.ACTIVE,
        )
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(
            reverse("course-feedback", args=[self.public_course.id]),
            {
                "rating": 5,
                "comment": "Excellent course",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            CourseFeedback.objects.filter(
                course=self.public_course,
                student=self.student,
                rating=5,
            ).exists()
        )

    def test_non_enrolled_student_cannot_leave_feedback(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(
            reverse("course-feedback", args=[self.public_course.id]),
            {
                "rating": 4,
                "comment": "Should not work",
            },
        )
        self.assertEqual(response.status_code, 403)