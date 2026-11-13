from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render


def _role_for(user):
    if user.is_staff:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


@login_required
def home(request):
    role = _role_for(request.user)
    if role in {"admin", "parent", "kid"}:
        return redirect(f"dashboard:{role}")
    return HttpResponseForbidden("Your account does not have a dashboard role.")


@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("This dashboard is for administrators.")
    return render(request, "dashboard/admin.html")


@login_required
def parent_dashboard(request):
    if _role_for(request.user) != "parent":
        return HttpResponseForbidden("This dashboard is for parents.")
    return render(request, "dashboard/parent.html")


@login_required
def kid_dashboard(request):
    if _role_for(request.user) != "kid":
        return HttpResponseForbidden("This dashboard is for kids.")
    return render(request, "dashboard/kid.html")
