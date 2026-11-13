from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/admin/", views.admin_dashboard, name="admin"),
    path("dashboard/parent/", views.parent_dashboard, name="parent"),
    path("dashboard/kid/", views.kid_dashboard, name="kid"),
]
