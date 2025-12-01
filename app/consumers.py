import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import DiscussionRoom, DiscussionMessage
from channels.db import database_sync_to_async

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group = f"discussion_{self.room_id}"

        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]
        user = self.scope["user"]

        await self.save_message(user, message)

        await self.channel_layer.group_send(
            self.room_group,
            {
                "type": "chat_message",
                "message": message,
                "user": str(user),
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, user, message):
        room = DiscussionRoom.objects.get(id=self.room_id)
        return DiscussionMessage.objects.create(room=room, sender=user, message=message)
