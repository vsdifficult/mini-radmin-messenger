import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    id: uuid.UUID
    chatId: uuid.UUID
    text: str
    owner: uuid.UUID
    timestamp: datetime
    status: str = "sent"
    reply_to: Optional[uuid.UUID] = None
    attachment_path: Optional[str] = None


@dataclass
class Chat:
    id: uuid.UUID
    contact_id: uuid.UUID
    contact_name: str
    contact_ip: str
    unread_count: int = 0
    last_message: str = ""
    last_timestamp: Optional[datetime] = None
