from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import Profile

from .models import Chore, FamilyLink


class FamilyLinkForm(forms.Form):
    child_username = forms.CharField(max_length=150, label="Child's username")

    def __init__(self, *args, parent, **kwargs):
        self.parent = parent
        self.child_user = None
        super().__init__(*args, **kwargs)

    def clean_child_username(self):
        username = self.cleaned_data["child_username"].strip()
        profile = (
            Profile.objects.select_related("user")
            .filter(role=Profile.Role.KID, user__username__iexact=username)
            .first()
        )
        if profile is None:
            raise ValidationError("Enter the username of an existing kid account.")
        if FamilyLink.objects.filter(child=profile.user).exists():
            raise ValidationError("That kid account is already linked to a parent.")
        self.child_user = profile.user
        return username

    def save(self):
        if not self.is_valid() or self.child_user is None:
            raise ValueError("A valid child account is required.")
        link = FamilyLink(parent=self.parent, child=self.child_user)
        link.full_clean()
        link.save()
        return link


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ("family_link", "title", "description", "due_date", "reward_amount")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, parent, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["family_link"].queryset = FamilyLink.objects.filter(
            parent=parent
        ).select_related("child")

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date < timezone.localdate():
            raise ValidationError("The due date cannot be in the past.")
        return due_date
