from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountFlowTests(TestCase):
    def registration_data(self, **overrides):
        data = {
            "username": "parent_one",
            "email": "parent@example.com",
            "role": Profile.Role.PARENT,
            "password1": "SafePass2026!",
            "password2": "SafePass2026!",
        }
        data.update(overrides)
        return data

    def test_registration_creates_hashed_password_and_role_dashboard(self):
        response = self.client.post(
            reverse("accounts:register"),
            self.registration_data(),
        )

        user = User.objects.get(username="parent_one")
        self.assertRedirects(
            response,
            reverse("dashboard:home"),
            fetch_redirect_response=False,
        )
        self.assertTrue(user.check_password("SafePass2026!"))
        self.assertNotEqual(user.password, "SafePass2026!")
        self.assertEqual(user.profile.role, Profile.Role.PARENT)
        self.assertRedirects(
            self.client.get(reverse("dashboard:home")),
            reverse("dashboard:parent"),
        )

    def test_registration_rejects_mismatched_passwords_and_duplicate_email(self):
        mismatch = self.client.post(
            reverse("accounts:register"),
            self.registration_data(password2="DifferentPass2026!"),
        )
        self.assertEqual(mismatch.status_code, 200)
        self.assertFalse(User.objects.filter(username="parent_one").exists())

        invalid_email = self.client.post(
            reverse("accounts:register"),
            self.registration_data(email="not-an-email"),
        )
        self.assertContains(invalid_email, "Enter a valid email address.")

        User.objects.create_user(
            username="existing",
            email="parent@example.com",
            password="SafePass2026!",
        )
        duplicate = self.client.post(
            reverse("accounts:register"),
            self.registration_data(username="another_parent"),
        )
        self.assertContains(duplicate, "An account with this email already exists.")

        duplicate_username = self.client.post(
            reverse("accounts:register"),
            self.registration_data(email="another@example.com", username="existing"),
        )
        self.assertContains(duplicate_username, "A user with that username already exists.")

    def test_login_invalid_credentials_and_logout(self):
        User.objects.create_user(
            username="parent_one",
            email="parent@example.com",
            password="SafePass2026!",
        )
        invalid = self.client.post(
            reverse("accounts:login"),
            {"username": "parent_one", "password": "wrong"},
        )
        self.assertContains(invalid, "Please enter a correct username and password.")

        self.client.post(
            reverse("accounts:login"),
            {"username": "parent_one", "password": "SafePass2026!"},
        )
        logout = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(logout, reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_profile_updates_only_the_logged_in_users_details(self):
        user = User.objects.create_user(
            username="parent_one",
            email="parent@example.com",
            password="SafePass2026!",
        )
        Profile.objects.create(user=user, role=Profile.Role.PARENT)
        self.client.force_login(user)

        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Pat",
                "last_name": "Parent",
                "email": "pat@example.com",
                "contact_number": "555-0101",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Pat")
        self.assertEqual(user.email, "pat@example.com")
        self.assertEqual(user.profile.contact_number, "555-0101")

    def test_logged_out_users_are_redirected_to_login_for_protected_pages(self):
        response = self.client.get(reverse("dashboard:parent"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('dashboard:parent')}",
        )


class RoleDashboardTests(TestCase):
    def create_role_user(self, username, role, **user_options):
        user = User.objects.create_user(
            username=username,
            password="SafePass2026!",
            **user_options,
        )
        Profile.objects.create(user=user, role=role)
        return user

    def test_parent_and_kid_cannot_open_another_role_dashboard(self):
        parent = self.create_role_user("parent", Profile.Role.PARENT)
        self.client.force_login(parent)
        self.assertEqual(self.client.get(reverse("dashboard:parent")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:kid")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:admin")).status_code, 403)

        kid = self.create_role_user("kid", Profile.Role.KID)
        self.client.force_login(kid)
        self.assertEqual(self.client.get(reverse("dashboard:kid")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:parent")).status_code, 403)

    def test_staff_user_gets_admin_dashboard_and_profile(self):
        admin = self.create_role_user(
            "site_admin",
            Profile.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        self.assertEqual(self.client.get(reverse("dashboard:admin")).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse("dashboard:home")),
            reverse("dashboard:admin"),
        )
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)
