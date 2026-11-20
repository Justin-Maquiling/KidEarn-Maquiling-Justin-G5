from django.urls import path

from . import views

app_name = "chores"

urlpatterns = [
    path("link-child/", views.link_child, name="link_child"),
    path("create/", views.chore_create, name="create"),
    path("<int:pk>/edit/", views.chore_update, name="update"),
    path("<int:pk>/delete/", views.chore_delete, name="delete"),
]
