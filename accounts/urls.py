from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit-profile"),
    path("users/<str:username>/", views.user_profile, name="user-profile"),
    path("search/", views.user_search, name="user-search"),
]