import uuid
from dataclasses import dataclass, field


@dataclass
class Contact:
    id: uuid.UUID
    name: str
    ip: str
    chats: list[uuid.UUID] = field(default_factory=list)
