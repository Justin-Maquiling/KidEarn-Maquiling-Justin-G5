from django.contrib import admin

from .models import Chore, FamilyLink


@admin.register(FamilyLink)
class FamilyLinkAdmin(admin.ModelAdmin):
    list_display = ("parent", "child", "created_at")
    search_fields = ("parent__username", "child__username")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "family_link", "due_date", "reward_amount", "status")
    list_filter = ("status", "due_date")
    search_fields = ("title", "created_by__username", "family_link__child__username")
