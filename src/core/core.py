from src.core.local_db import * 

class MessengerEngine: 

    def __init__(self, core_path: str): 
        self.repository = Repository(core_path + "/db/") 

    async def create_chat(self, contact_name: str, contact_ip: str) -> uuid.UUID:
        contact_id = await self.repository.create_contact(contact_name, contact_ip)
        return contact_id

    async def send_message(self, text: str, chat_id: uuid.UUID, contact_id: uuid.UUID, owner_id: uuid.UUID):
        await self.repository.send_message(text, contact_id, chat_id, owner_id)

    