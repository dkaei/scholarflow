import json
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from courses.models import Course
from courses.services import can_access_course
from realtime.models import CourseMessage

MAX_MESSAGES = 5
WINDOW_SECONDS = 8


class CourseRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.course_id = int(self.scope["url_route"]["kwargs"]["course_id"])
        self.group_name = f"course_{self.course_id}"
        self.message_times = []

        if not await self._can_access():
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        payload = json.loads(text_data or "{}")
        event_type = payload.get("type")

        if event_type == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "typing_event", "sender_id": self.scope["user"].id},
            )
            return

        if event_type != "chat":
            return

        text = (payload.get("text") or "").strip()
        if not text or not self._rate_limit_ok():
            return

        message = await self._save_message(text)
        await self.channel_layer.group_send(self.group_name, {"type": "chat_event", "data": message})

    async def chat_event(self, event):
        await self.send(text_data=json.dumps({"event": "chat", "data": event["data"]}))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps({"event": "typing", "sender_id": event["sender_id"]}))

    def _rate_limit_ok(self):
        now = time.time()
        self.message_times = [timestamp for timestamp in self.message_times if now - timestamp < WINDOW_SECONDS]
        if len(self.message_times) >= MAX_MESSAGES:
            return False
        self.message_times.append(now)
        return True

    @database_sync_to_async
    def _can_access(self):
        try:
            course = Course.objects.get(id=self.course_id)
        except Course.DoesNotExist:
            return False
        return can_access_course(self.scope["user"], course)

    @database_sync_to_async
    def _save_message(self, text):
        message = CourseMessage.objects.create(
            course_id=self.course_id,
            sender=self.scope["user"],
            text=text,
        )
        return {
            "user": message.sender.display_name or message.sender.username,
            "sender_id": message.sender_id,
            "role": getattr(message.sender, "role", ""),
            "text": message.text,
            "created_at": message.created_at.isoformat(),
        }
