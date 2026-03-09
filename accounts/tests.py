from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import StatusUpdate

User = get_user_model()


class AccountViewTests(TestCase):
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

    def test_signup_page_loads(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_profile_redirects_to_user_profile(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("user-profile", args=["student1"]))

    def test_user_profile_page_loads_for_logged_in_user(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("user-profile", args=["student1"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student One")

    def test_teacher_can_access_user_search(self):
        self.client.login(username="teacher1", password="testpass123")
        response = self.client.get(reverse("user-search"))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_user_search(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("user-search"))
        self.assertEqual(response.status_code, 403)

    def test_edit_profile_updates_email_and_bio(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(
            reverse("edit-profile"),
            {
                "display_name": "Student One Updated",
                "email": "updated@example.com",
                "bio": "Updated bio text",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.display_name, "Student One Updated")
        self.assertEqual(self.student.email, "updated@example.com")
        self.assertEqual(self.student.bio, "Updated bio text")

    def test_owner_can_post_status_update(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(
            reverse("user-profile", args=["student1"]),
            {"text": "My first status update"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            StatusUpdate.objects.filter(user=self.student, text="My first status update").exists()
        )