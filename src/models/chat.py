import uuid
from pydantic import BaseModel

class Message(BaseModel):
    id: uuid.UUID
    chatId: uuid.UUID
    text: str
    owner: uuid.UUID

class Chat(BaseModel):
    id: uuid.UUID
    contact_name: str
    messages: list[uuid.UUID] = []
