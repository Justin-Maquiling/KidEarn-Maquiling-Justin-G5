from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Profile

from .forms import ChoreForm, FamilyLinkForm
from .models import Chore


def _is_parent(user):
    profile = getattr(user, "profile", None)
    return profile is not None and profile.role == Profile.Role.PARENT


@login_required
def link_child(request):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can link kid accounts.")

    form = FamilyLinkForm(request.POST or None, parent=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Kid account linked successfully.")
        return redirect("dashboard:parent")
    return render(request, "chores/link_child.html", {"form": form})


@login_required
def chore_create(request):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can create chores.")

    form = ChoreForm(request.POST or None, parent=request.user)
    if request.method == "POST" and form.is_valid():
        chore = form.save(commit=False)
        chore.created_by = request.user
        chore.full_clean()
        chore.save()
        messages.success(request, "Chore assigned successfully.")
        return redirect("dashboard:parent")
    return render(
        request,
        "chores/chore_form.html",
        {"form": form, "page_title": "Assign a chore", "submit_label": "Assign chore"},
    )


@login_required
def chore_update(request, pk):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can edit chores.")
    chore = get_object_or_404(Chore, pk=pk, created_by=request.user)
    if chore.status not in (Chore.Status.OPEN, Chore.Status.REJECTED):
        return HttpResponseForbidden("This chore can no longer be edited.")

    form = ChoreForm(request.POST or None, instance=chore, parent=request.user)
    if request.method == "POST" and form.is_valid():
        chore = form.save(commit=False)
        if chore.status == Chore.Status.REJECTED:
            chore.status = Chore.Status.OPEN
        chore.full_clean()
        chore.save()
        messages.success(request, "Chore updated successfully.")
        return redirect("dashboard:parent")
    return render(
        request,
        "chores/chore_form.html",
        {"form": form, "page_title": "Edit chore", "submit_label": "Save changes"},
    )


@login_required
@require_POST
def chore_delete(request, pk):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can delete chores.")
    chore = get_object_or_404(Chore, pk=pk, created_by=request.user)
    if chore.status not in (Chore.Status.OPEN, Chore.Status.REJECTED):
        return HttpResponseForbidden("Submitted or approved chores cannot be deleted.")
    chore.delete()
    messages.success(request, "Chore deleted successfully.")
    return redirect("dashboard:parent")
