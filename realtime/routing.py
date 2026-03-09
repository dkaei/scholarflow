from django.urls import re_path
from .consumers import CourseRoomConsumer

websocket_urlpatterns = [
    re_path(r"^ws/courses/(?P<course_id>\d+)/room/$", CourseRoomConsumer.as_asgi()),
]
