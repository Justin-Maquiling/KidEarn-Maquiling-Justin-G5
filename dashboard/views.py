from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from chores.forms import FamilyLinkForm
from chores.models import Chore, FamilyLink, WalletEntry


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
    chores = (
        Chore.objects.filter(created_by=request.user)
        .select_related("family_link__child")
    )
    family_links = FamilyLink.objects.filter(parent=request.user).select_related("child")
    return render(
        request,
        "dashboard/parent.html",
        {
            "chores": chores,
            "family_links": family_links,
        },
    )


@login_required
def kid_dashboard(request):
    if _role_for(request.user) != "kid":
        return HttpResponseForbidden("This dashboard is for kids.")
    chores = (
        Chore.objects.filter(family_link__child=request.user)
        .select_related("created_by")
    )
    wallet_entries = WalletEntry.objects.filter(user=request.user).select_related("chore")
    wallet_balance = wallet_entries.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    return render(
        request,
        "dashboard/kid.html",
        {
            "chores": chores,
            "wallet_entries": wallet_entries,
            "wallet_balance": wallet_balance,
        },
    )
