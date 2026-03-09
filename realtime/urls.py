from django.urls import path
from .views import course_room, older_messages

urlpatterns = [
    path("courses/<int:course_id>/room/", course_room, name="course-room"),
    path("courses/<int:course_id>/room/older/", older_messages, name="course-room-older"),
]
