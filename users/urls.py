# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("auth/register/", views.register_user, name="register"),
    path("auth/login/", views.login_user, name="login"),
    path("auth/refresh-token/", views.refresh_token, name="refresh-token"),
    path("auth/logout/", views.logout_user, name="logout"),
    path("me/", views.profile_view, name="profile"),
]