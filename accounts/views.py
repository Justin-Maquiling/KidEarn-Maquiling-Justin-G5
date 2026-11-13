from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import ProfileForm, RegistrationForm
from .models import Profile


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user)
        messages.success(request, "Your account has been created.")
        return redirect("dashboard:home")
    return render(request, "accounts/register.html", {"form": form})


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    next_page = reverse_lazy("dashboard:home")


class AccountLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


@login_required
def profile(request):
    profile_record = getattr(request.user, "profile", None)
    if profile_record is None and request.user.is_staff:
        profile_record = Profile.objects.create(
            user=request.user,
            role=Profile.Role.ADMIN,
        )
    if profile_record is None:
        messages.error(request, "Your account profile has not been configured.")
        return redirect("dashboard:home")

    form = ProfileForm(
        request.POST or None,
        instance=profile_record,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})
