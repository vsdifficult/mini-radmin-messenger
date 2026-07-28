import os
import uuid

from src.core.local_db import Repository


class MessengerEngine:
    def __init__(self, core_path: str):
        self.repository = Repository(os.path.join(core_path, "db"))
        self.owner_id: uuid.UUID | None = None

    async def initialize(self, display_name: str = "Я") -> uuid.UUID:
        self.owner_id = await self.repository.get_or_create_profile(display_name)
        return self.owner_id

    async def create_chat(self, contact_name: str, contact_ip: str) -> tuple[uuid.UUID, uuid.UUID]:
        return await self.repository.create_contact(contact_name.strip(), contact_ip.strip())

    async def send_message(self, text: str, chat_id: uuid.UUID, contact_id: uuid.UUID,
                           owner_id: uuid.UUID | None = None, **kwargs):
        return await self.repository.send_message(text, contact_id, chat_id, owner_id or self.owner_id, **kwargs)

    async def receive_message(self, text: str, chat_id: uuid.UUID, contact_id: uuid.UUID, sender_id: uuid.UUID,
                              message_id: uuid.UUID | None = None, **kwargs):
        return await self.repository.send_message(text, contact_id, chat_id, sender_id, status="delivered", message_id=message_id, **kwargs)
