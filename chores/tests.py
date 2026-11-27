from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile

from .models import Chore, FamilyLink, WalletEntry


class ChoreManagementTests(TestCase):
    def create_user(self, username, role):
        user = User.objects.create_user(username=username, password="SafePass2026!")
        Profile.objects.create(user=user, role=role)
        return user

    def create_link(self, parent, child):
        return FamilyLink.objects.create(parent=parent, child=child)

    def create_chore(self, parent, link, title="Wash dishes"):
        return Chore.objects.create(
            created_by=parent,
            family_link=link,
            title=title,
            description="Clean and dry the dishes.",
            due_date=timezone.localdate() + timedelta(days=1),
            reward_amount=Decimal("25.00"),
        )

    def setUp(self):
        self.parent = self.create_user("parent_one", Profile.Role.PARENT)
        self.kid = self.create_user("kid_one", Profile.Role.KID)
        self.link = self.create_link(self.parent, self.kid)
        self.client.force_login(self.parent)

    def test_parent_links_existing_kid_account_once(self):
        other_kid = self.create_user("kid_two", Profile.Role.KID)
        response = self.client.post(
            reverse("chores:link_child"),
            {"child_username": other_kid.username},
        )

        self.assertRedirects(response, reverse("dashboard:parent"))
        self.assertTrue(FamilyLink.objects.filter(parent=self.parent, child=other_kid).exists())

        duplicate = self.client.post(
            reverse("chores:link_child"),
            {"child_username": other_kid.username},
        )
        self.assertContains(duplicate, "already linked to a parent.")

    def test_parent_can_create_update_and_delete_own_chore(self):
        create_response = self.client.post(
            reverse("chores:create"),
            {
                "family_link": self.link.pk,
                "title": "Tidy bedroom",
                "description": "Put toys away.",
                "due_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
                "reward_amount": "30.00",
            },
        )

        chore = Chore.objects.get(title="Tidy bedroom")
        self.assertEqual(chore.created_by, self.parent)
        self.assertRedirects(create_response, reverse("dashboard:parent"))

        update_response = self.client.post(
            reverse("chores:update", args=(chore.pk,)),
            {
                "family_link": self.link.pk,
                "title": "Tidy the bedroom",
                "description": "Put toys and books away.",
                "due_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
                "reward_amount": "35.00",
            },
        )
        chore.refresh_from_db()
        self.assertRedirects(update_response, reverse("dashboard:parent"))
        self.assertEqual(chore.title, "Tidy the bedroom")
        self.assertEqual(chore.reward_amount, Decimal("35.00"))

        delete_url = reverse("chores:delete", args=(chore.pk,))
        confirmation = self.client.get(delete_url)
        self.assertContains(confirmation, "Are you sure you want to delete")
        self.assertTrue(Chore.objects.filter(pk=chore.pk).exists())
        delete_response = self.client.post(delete_url)
        self.assertRedirects(delete_response, reverse("dashboard:parent"))
        self.assertFalse(Chore.objects.filter(pk=chore.pk).exists())

    def test_parent_cannot_assign_to_unlinked_kid_or_edit_another_parents_chore(self):
        other_parent = self.create_user("parent_two", Profile.Role.PARENT)
        other_kid = self.create_user("kid_two", Profile.Role.KID)
        other_link = self.create_link(other_parent, other_kid)
        other_chore = self.create_chore(other_parent, other_link, "Other family's chore")

        invalid_create = self.client.post(
            reverse("chores:create"),
            {
                "family_link": other_link.pk,
                "title": "Unauthorized chore",
                "description": "Should not be accepted.",
                "due_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "reward_amount": "10.00",
            },
        )
        self.assertEqual(invalid_create.status_code, 200)
        self.assertFalse(Chore.objects.filter(title="Unauthorized chore").exists())
        self.assertEqual(
            self.client.get(reverse("chores:update", args=(other_chore.pk,))).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("chores:delete", args=(other_chore.pk,))).status_code,
            404,
        )

    def test_invalid_due_date_and_reward_are_rejected(self):
        response = self.client.post(
            reverse("chores:create"),
            {
                "family_link": self.link.pk,
                "title": "Invalid chore",
                "description": "Invalid values.",
                "due_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "reward_amount": "0.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The due date cannot be in the past.")
        self.assertContains(response, "Ensure this value is greater than or equal to 0.01.")
        self.assertFalse(Chore.objects.filter(title="Invalid chore").exists())

    def test_kid_dashboard_only_shows_chores_assigned_to_that_kid(self):
        other_parent = self.create_user("parent_two", Profile.Role.PARENT)
        other_kid = self.create_user("kid_two", Profile.Role.KID)
        other_link = self.create_link(other_parent, other_kid)
        self.create_chore(self.parent, self.link, "My assigned chore")
        self.create_chore(other_parent, other_link, "Someone else's chore")
        self.client.force_login(self.kid)

        response = self.client.get(reverse("dashboard:kid"))

        self.assertContains(response, "My assigned chore")
        self.assertNotContains(response, "Someone else&#x27;s chore")

    def test_kid_cannot_access_parent_chore_management(self):
        self.client.force_login(self.kid)

        self.assertEqual(self.client.get(reverse("chores:create")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("chores:link_child")).status_code,
            403,
        )


class ChoreReviewTests(TestCase):
    def create_user(self, username, role):
        user = User.objects.create_user(username=username, password="SafePass2026!")
        Profile.objects.create(user=user, role=role)
        return user

    def setUp(self):
        self.parent = self.create_user("review_parent", Profile.Role.PARENT)
        self.kid = self.create_user("review_kid", Profile.Role.KID)
        self.link = FamilyLink.objects.create(parent=self.parent, child=self.kid)
        self.chore = Chore.objects.create(
            created_by=self.parent,
            family_link=self.link,
            title="Water plants",
            description="Water the garden plants.",
            due_date=timezone.localdate() + timedelta(days=1),
            reward_amount=Decimal("25.00"),
        )

    def test_child_submission_parent_rework_and_approval_award_one_reward(self):
        self.client.force_login(self.kid)
        submit_response = self.client.post(
            reverse("chores:submit", args=(self.chore.pk,))
        )
        self.assertRedirects(submit_response, reverse("dashboard:kid"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.status, Chore.Status.SUBMITTED)
        self.assertIsNotNone(self.chore.submitted_at)

        self.client.force_login(self.parent)
        forbidden_edit = self.client.get(reverse("chores:update", args=(self.chore.pk,)))
        forbidden_delete = self.client.post(reverse("chores:delete", args=(self.chore.pk,)))
        self.assertEqual(forbidden_edit.status_code, 403)
        self.assertEqual(forbidden_delete.status_code, 403)

        invalid_rejection = self.client.post(
            reverse("chores:review", args=(self.chore.pk,)),
            {"action": "reject", "review_note": "  "},
        )
        self.assertContains(invalid_rejection, "Explain what needs to be corrected.")
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.status, Chore.Status.SUBMITTED)
        self.assertFalse(WalletEntry.objects.filter(chore=self.chore).exists())

        rejected = self.client.post(
            reverse("chores:review", args=(self.chore.pk,)),
            {"action": "reject", "review_note": "Please water all the plants."},
        )
        self.assertRedirects(rejected, reverse("dashboard:parent"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.status, Chore.Status.REJECTED)
        self.assertEqual(self.chore.review_note, "Please water all the plants.")
        self.assertIsNotNone(self.chore.reviewed_at)
        self.assertFalse(WalletEntry.objects.filter(chore=self.chore).exists())

        self.client.force_login(self.kid)
        self.assertContains(
            self.client.get(reverse("dashboard:kid")),
            "Please water all the plants.",
        )
        resubmitted = self.client.post(
            reverse("chores:submit", args=(self.chore.pk,))
        )
        self.assertRedirects(resubmitted, reverse("dashboard:kid"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.status, Chore.Status.SUBMITTED)
        self.assertIsNone(self.chore.reviewed_at)

        self.client.force_login(self.parent)
        approved = self.client.post(
            reverse("chores:review", args=(self.chore.pk,)),
            {"action": "approve", "review_note": ""},
        )
        self.assertRedirects(approved, reverse("dashboard:parent"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.status, Chore.Status.APPROVED)
        self.assertEqual(WalletEntry.objects.filter(chore=self.chore).count(), 1)
        self.assertEqual(self.chore.wallet_entry.user, self.kid)
        self.assertEqual(self.chore.wallet_entry.amount, Decimal("25.00"))

        repeated_review = self.client.post(
            reverse("chores:review", args=(self.chore.pk,)),
            {"action": "approve", "review_note": ""},
        )
        self.assertEqual(repeated_review.status_code, 403)
        self.assertEqual(WalletEntry.objects.filter(chore=self.chore).count(), 1)

        self.client.force_login(self.kid)
        other_parent = self.create_user("wallet_parent", Profile.Role.PARENT)
        other_kid = self.create_user("wallet_kid", Profile.Role.KID)
        other_link = FamilyLink.objects.create(parent=other_parent, child=other_kid)
        other_chore = Chore.objects.create(
            created_by=other_parent,
            family_link=other_link,
            title="Private reward",
            description="Another kid's approved chore.",
            due_date=timezone.localdate() + timedelta(days=1),
            reward_amount=Decimal("10.00"),
            status=Chore.Status.APPROVED,
        )
        WalletEntry.objects.create(
            user=other_kid,
            chore=other_chore,
            amount=other_chore.reward_amount,
        )
        wallet = self.client.get(reverse("dashboard:kid"))
        self.assertContains(wallet, "Approved rewards: 25.00")
        self.assertContains(wallet, "Water plants")
        self.assertNotContains(wallet, "Private reward")

    def test_only_assigned_kid_and_creating_parent_can_submit_or_review(self):
        other_parent = self.create_user("other_review_parent", Profile.Role.PARENT)
        other_kid = self.create_user("other_review_kid", Profile.Role.KID)
        other_link = FamilyLink.objects.create(parent=other_parent, child=other_kid)
        other_chore = Chore.objects.create(
            created_by=other_parent,
            family_link=other_link,
            title="Other chore",
            description="Not this family's chore.",
            due_date=timezone.localdate() + timedelta(days=1),
            reward_amount=Decimal("10.00"),
            status=Chore.Status.SUBMITTED,
        )

        self.client.force_login(self.kid)
        self.assertEqual(
            self.client.post(reverse("chores:submit", args=(other_chore.pk,))).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("chores:review", args=(self.chore.pk,)),
                {"action": "approve"},
            ).status_code,
            403,
        )

        self.client.force_login(self.parent)
        self.assertEqual(
            self.client.get(reverse("chores:review", args=(other_chore.pk,))).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("chores:submit", args=(self.chore.pk,))).status_code,
            403,
        )
