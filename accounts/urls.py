from django.urls import path
from .views import AccountLoginView, AccountLogoutView, profile, register

app_name = "accounts"

urlpatterns = [
    path("register/", register, name="register"),
    path("login/", AccountLoginView.as_view(), name="login"),
    path("logout/", AccountLogoutView.as_view(), name="logout"),
    path("profile/", profile, name="profile"),
]
