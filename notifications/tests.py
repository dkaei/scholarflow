from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            password="testpass123",
            role="STUDENT",
            email="student@example.com",
        )
        self.other = User.objects.create_user(
            username="student2",
            password="testpass123",
            role="STUDENT",
            email="student2@example.com",
        )
        self.notification = Notification.objects.create(
            user=self.user,
            message="Test notification",
            link="/",
        )

    def test_notification_list_requires_login(self):
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, 302)

    def test_user_can_view_own_notifications(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("notification-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test notification")

    def test_open_notification_marks_it_as_read(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.get(reverse("notification-open", args=[self.notification.id]))
        self.assertEqual(response.status_code, 302)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_user_cannot_open_another_users_notification(self):
        self.client.login(username="student2", password="testpass123")
        response = self.client.get(reverse("notification-open", args=[self.notification.id]))
        self.assertEqual(response.status_code, 404)

    def test_user_can_delete_own_notification(self):
        self.client.login(username="student1", password="testpass123")
        response = self.client.post(reverse("notification-delete", args=[self.notification.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=self.notification.id).exists())