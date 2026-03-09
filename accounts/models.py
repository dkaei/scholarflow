from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"

    role = models.CharField(max_length=10, choices=Role.choices)
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.username

class StatusUpdate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="status_updates",
    )
    text = models.TextField(max_length=500)
    image = models.ImageField(upload_to="status_updates/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.text[:40]}"