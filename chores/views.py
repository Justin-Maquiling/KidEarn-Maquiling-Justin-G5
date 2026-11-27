from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import Profile

from .forms import ChoreForm, ChoreReviewForm, FamilyLinkForm
from .models import Chore, WalletEntry


def _is_parent(user):
    profile = getattr(user, "profile", None)
    return profile is not None and profile.role == Profile.Role.PARENT


def _is_kid(user):
    profile = getattr(user, "profile", None)
    return profile is not None and profile.role == Profile.Role.KID


@login_required
def link_child(request):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can link kid accounts.")

    form = FamilyLinkForm(
        request.POST if request.method == "POST" else None,
        parent=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error("child_username", "That kid account is already linked to a parent.")
            return render(request, "chores/link_child.html", {"form": form})
        messages.success(request, "Kid account linked successfully.")
        return redirect("dashboard:parent")
    return render(request, "chores/link_child.html", {"form": form})


@login_required
def chore_create(request):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can create chores.")

    form = ChoreForm(
        request.POST if request.method == "POST" else None,
        parent=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                chore = form.save(commit=False)
                chore.created_by = request.user
                chore.full_clean()
                chore.save()
        except ValidationError as error:
            form.add_error(None, error)
            return render(
                request,
                "chores/chore_form.html",
                {"form": form, "page_title": "Assign a chore", "submit_label": "Assign chore"},
            )
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

    form = ChoreForm(
        request.POST if request.method == "POST" else None,
        instance=chore,
        parent=request.user,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                chore = form.save(commit=False)
                if chore.status == Chore.Status.REJECTED:
                    chore.status = Chore.Status.OPEN
                chore.full_clean()
                chore.save()
        except ValidationError as error:
            form.add_error(None, error)
            return render(
                request,
                "chores/chore_form.html",
                {"form": form, "page_title": "Edit chore", "submit_label": "Save changes"},
            )
        messages.success(request, "Chore updated successfully.")
        return redirect("dashboard:parent")
    return render(
        request,
        "chores/chore_form.html",
        {"form": form, "page_title": "Edit chore", "submit_label": "Save changes"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def chore_delete(request, pk):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can delete chores.")
    chore = get_object_or_404(Chore, pk=pk, created_by=request.user)
    if chore.status not in (Chore.Status.OPEN, Chore.Status.REJECTED):
        return HttpResponseForbidden("Submitted or approved chores cannot be deleted.")
    if request.method == "GET":
        return render(request, "chores/chore_confirm_delete.html", {"chore": chore})
    chore.delete()
    messages.success(request, "Chore deleted successfully.")
    return redirect("dashboard:parent")


@login_required
@require_POST
def chore_submit(request, pk):
    if not _is_kid(request.user):
        return HttpResponseForbidden("Only kids can submit chore completion.")

    with transaction.atomic():
        chore = get_object_or_404(
            Chore.objects.select_for_update(),
            pk=pk,
            family_link__child=request.user,
        )
        if chore.status not in (Chore.Status.OPEN, Chore.Status.REJECTED):
            return HttpResponseForbidden("This chore is not ready for submission.")
        chore.status = Chore.Status.SUBMITTED
        chore.submitted_at = timezone.now()
        chore.reviewed_at = None
        chore.save(update_fields=("status", "submitted_at", "reviewed_at", "updated_at"))

    messages.success(request, "Your completed chore was sent to your parent.")
    return redirect("dashboard:kid")


@login_required
def chore_review(request, pk):
    if not _is_parent(request.user):
        return HttpResponseForbidden("Only parents can review chore submissions.")
    chore = get_object_or_404(
        Chore.objects.select_related("family_link__child"),
        pk=pk,
        created_by=request.user,
    )
    if chore.status != Chore.Status.SUBMITTED:
        return HttpResponseForbidden("This chore has no submission to review.")

    form = ChoreReviewForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            chore = get_object_or_404(
                Chore.objects.select_for_update().select_related("family_link__child"),
                pk=pk,
                created_by=request.user,
            )
            if chore.status != Chore.Status.SUBMITTED:
                messages.error(request, "This chore has already been reviewed.")
                return redirect("dashboard:parent")

            if form.cleaned_data["action"] == ChoreReviewForm.Decision.APPROVE:
                if WalletEntry.objects.filter(chore=chore).exists():
                    messages.error(request, "A reward has already been recorded for this chore.")
                    return redirect("dashboard:parent")
                entry = WalletEntry(
                    user=chore.family_link.child,
                    chore=chore,
                    amount=chore.reward_amount,
                )
                entry.full_clean()
                entry.save()
                chore.status = Chore.Status.APPROVED
            else:
                chore.status = Chore.Status.REJECTED

            chore.review_note = form.cleaned_data["review_note"].strip()
            chore.reviewed_at = timezone.now()
            chore.save(
                update_fields=("status", "review_note", "reviewed_at", "updated_at")
            )

        if chore.status == Chore.Status.APPROVED:
            messages.success(request, "Chore approved and reward added to the kid's wallet.")
        else:
            messages.success(request, "Feedback sent to the kid. They can update and resubmit.")
        return redirect("dashboard:parent")

    return render(
        request,
        "chores/chore_review.html",
        {"chore": chore, "form": form},
    )
