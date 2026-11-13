from django.db import models
from django.conf import settings


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        PARENT = "parent", "Parent"
        KID = "kid", "Kid"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=10, choices=Role.choices)
    contact_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
