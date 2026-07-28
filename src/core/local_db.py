import sqlite3, uuid 

from src.models.chat import Chat, Message 
from src.models.contact import Contact 

from typing import List, Optional

class LocalDataBaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    async def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        await self._init_tables()
        return self.connection

    async def _init_tables(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                text TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id)
            )
        ''')
        self.connection.commit()

    async def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    async def execute_query(self, query, params=None):
        if not self.connection:
            await self.connect()
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        self.connection.commit()
        return cursor.fetchall()
    
class Repository:
    def __init__(self, db_path: str):
        self.db = LocalDataBaseManager(db_path)

    async def create_contact(self, name: str, ip: str) -> uuid.UUID:
        contact_id = uuid.uuid4()
        query = "INSERT INTO contacts (id, name, ip) VALUES (?, ?, ?)"
        await self.db.execute_query(query, (str(contact_id), name, ip))
        
        chat_id = uuid.uuid4()
        query = "INSERT INTO chats (id, contact_id, contact_name) VALUES (?, ?, ?)"
        await self.db.execute_query(query, (str(chat_id), str(contact_id), name))
        return contact_id

    async def send_message(self, text: str, contact_id: uuid.UUID, chat_id: uuid.UUID, owner_id: uuid.UUID):
        msg_id = uuid.uuid4()
        query = "INSERT INTO messages (id, chat_id, text, owner_id) VALUES (?, ?, ?, ?)"
        await self.db.execute_query(query, (str(msg_id), str(chat_id), text, str(owner_id)))
        return msg_id

    async def get_chat(self, chat_id: uuid.UUID) -> List[Message]:
        query = "SELECT id, chat_id, text, owner_id, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp"
        rows = await self.db.execute_query(query, (str(chat_id),))
        return [Message(
            id=uuid.UUID(row[0]),
            chatId=uuid.UUID(row[1]),
            text=row[2],
            owner=uuid.UUID(row[3]),
            timestamp=row[4]
        ) for row in rows]

    async def get_contact(self, contact_id: uuid.UUID) -> Optional[Contact]:
        query = "SELECT id, name, ip FROM contacts WHERE id = ?"
        rows = await self.db.execute_query(query, (str(contact_id),))
        if rows:
            row = rows[0]
            return Contact(id=uuid.UUID(row[0]), name=row[1], ip=row[2], chats=[])
        return None

    async def get_all_contacts(self) -> List[Contact]:
        query = "SELECT id, name, ip FROM contacts"
        rows = await self.db.execute_query(query)
        return [Contact(id=uuid.UUID(row[0]), name=row[1], ip=row[2], chats=[]) for row in rows]

        
