from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import Profile


class FamilyLink(models.Model):
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kid_links",
    )
    child = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_link",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("child__username",)

    def clean(self):
        super().clean()
        if self.parent_id and self.child_id:
            if self.parent_id == self.child_id:
                raise ValidationError("A parent cannot link their account as a child.")
            roles = dict(
                Profile.objects.filter(user_id__in=(self.parent_id, self.child_id))
                .values_list("user_id", "role")
            )
            if roles.get(self.parent_id) != Profile.Role.PARENT:
                raise ValidationError({"parent": "The linked account must have the parent role."})
            if roles.get(self.child_id) != Profile.Role.KID:
                raise ValidationError({"child": "The linked account must have the kid role."})

    def __str__(self):
        return f"{self.parent.username} → {self.child.username}"


class Chore(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Needs revision"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_chores",
    )
    family_link = models.ForeignKey(
        FamilyLink,
        on_delete=models.PROTECT,
        related_name="chores",
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    due_date = models.DateField()
    reward_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=(MinValueValidator(Decimal("0.01")),),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date", "created_at")

    def clean(self):
        super().clean()
        if self.created_by_id and self.family_link_id:
            if self.family_link.parent_id != self.created_by_id:
                raise ValidationError(
                    {"family_link": "You can only assign chores to a child linked to your account."}
                )
        if self.due_date and self.due_date < timezone.localdate():
            raise ValidationError({"due_date": "The due date cannot be in the past."})

    def __str__(self):
        return f"{self.title} ({self.family_link.child.username})"
