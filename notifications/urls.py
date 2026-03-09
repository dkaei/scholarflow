from django.urls import path
from . import views

urlpatterns = [
    path("", views.notification_list, name="notification-list"),
    path("<int:pk>/open/", views.notification_open, name="notification-open"),
    path("<int:pk>/delete/", views.notification_delete, name="notification-delete"),
]