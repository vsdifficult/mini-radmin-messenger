import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from src.models.chat import Chat, Message
from src.models.contact import Contact


class LocalDataBaseManager:
    def __init__(self, db_path: str):
        if db_path.endswith(os.sep) or not os.path.splitext(db_path)[1]:
            os.makedirs(db_path, exist_ok=True)
            db_path = os.path.join(db_path, "messenger.sqlite3")
        else:
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None

    async def connect(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        await self._init_tables()
        return self.connection

    async def _init_tables(self):
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ip TEXT NOT NULL UNIQUE,
                is_online INTEGER DEFAULT 0,
                last_seen TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL UNIQUE,
                contact_name TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                text TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                reply_to TEXT,
                attachment_path TEXT,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        ''')
        for statement in (
            "ALTER TABLE contacts ADD COLUMN is_online INTEGER DEFAULT 0",
            "ALTER TABLE contacts ADD COLUMN last_seen TEXT",
            "ALTER TABLE messages ADD COLUMN status TEXT DEFAULT 'sent'",
            "ALTER TABLE messages ADD COLUMN reply_to TEXT",
            "ALTER TABLE messages ADD COLUMN attachment_path TEXT",
        ):
            try:
                cursor.execute(statement)
            except sqlite3.OperationalError:
                pass
        self.connection.commit()

    async def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    async def execute_query(self, query, params=None):
        if not self.connection:
            await self.connect()
        cursor = self.connection.cursor()
        cursor.execute(query, params or ())
        self.connection.commit()
        return cursor.fetchall()


class Repository:
    def __init__(self, db_path: str):
        self.db = LocalDataBaseManager(db_path)

    async def get_or_create_profile(self, display_name: str = "Я") -> uuid.UUID:
        rows = await self.db.execute_query("SELECT id FROM profile LIMIT 1")
        if rows:
            return uuid.UUID(rows[0]["id"])
        profile_id = uuid.uuid4()
        await self.db.execute_query(
            "INSERT INTO profile (id, display_name) VALUES (?, ?)",
            (str(profile_id), display_name),
        )
        return profile_id

    async def create_contact(self, name: str, ip: str) -> tuple[uuid.UUID, uuid.UUID]:
        rows = await self.db.execute_query("SELECT id FROM contacts WHERE ip = ?", (ip,))
        if rows:
            contact_id = uuid.UUID(rows[0]["id"])
            await self.db.execute_query("UPDATE contacts SET name = ? WHERE id = ?", (name, str(contact_id)))
            chat_rows = await self.db.execute_query("SELECT id FROM chats WHERE contact_id = ?", (str(contact_id),))
            return contact_id, uuid.UUID(chat_rows[0]["id"])

        contact_id = uuid.uuid4()
        chat_id = uuid.uuid4()
        await self.db.execute_query("INSERT INTO contacts (id, name, ip) VALUES (?, ?, ?)", (str(contact_id), name, ip))
        await self.db.execute_query(
            "INSERT INTO chats (id, contact_id, contact_name) VALUES (?, ?, ?)",
            (str(chat_id), str(contact_id), name),
        )
        return contact_id, chat_id

    async def send_message(self, text: str, contact_id: uuid.UUID, chat_id: uuid.UUID, owner_id: uuid.UUID,
                           status: str = "sent", reply_to=None, attachment_path=None, message_id=None):
        msg_id = message_id or uuid.uuid4()
        await self.db.execute_query(
            """INSERT OR IGNORE INTO messages
               (id, chat_id, text, owner_id, status, reply_to, attachment_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(msg_id), str(chat_id), text, str(owner_id), status, str(reply_to) if reply_to else None, attachment_path),
        )
        return msg_id

    async def update_message_status(self, message_id: uuid.UUID, status: str):
        await self.db.execute_query("UPDATE messages SET status = ? WHERE id = ?", (status, str(message_id)))

    async def get_chat(self, chat_id: uuid.UUID) -> List[Message]:
        rows = await self.db.execute_query(
            "SELECT id, chat_id, text, owner_id, timestamp, status, reply_to, attachment_path FROM messages WHERE chat_id = ? ORDER BY timestamp, id",
            (str(chat_id),),
        )
        return [Message(id=uuid.UUID(r["id"]), chatId=uuid.UUID(r["chat_id"]), text=r["text"], owner=uuid.UUID(r["owner_id"]),
                        timestamp=datetime.fromisoformat(r["timestamp"]), status=r["status"] or "sent",
                        reply_to=uuid.UUID(r["reply_to"]) if r["reply_to"] else None, attachment_path=r["attachment_path"]) for r in rows]

    async def get_contact(self, contact_id: uuid.UUID) -> Optional[Contact]:
        rows = await self.db.execute_query("SELECT id, name, ip FROM contacts WHERE id = ?", (str(contact_id),))
        return Contact(id=uuid.UUID(rows[0]["id"]), name=rows[0]["name"], ip=rows[0]["ip"], chats=[]) if rows else None

    async def get_all_contacts(self) -> List[Contact]:
        rows = await self.db.execute_query("SELECT id, name, ip FROM contacts ORDER BY name")
        return [Contact(id=uuid.UUID(r["id"]), name=r["name"], ip=r["ip"], chats=[]) for r in rows]

    async def get_chats(self) -> List[Chat]:
        rows = await self.db.execute_query('''
            SELECT ch.id, c.id AS contact_id, c.name, c.ip,
                   (SELECT text FROM messages m WHERE m.chat_id = ch.id ORDER BY timestamp DESC LIMIT 1) AS last_message,
                   (SELECT timestamp FROM messages m WHERE m.chat_id = ch.id ORDER BY timestamp DESC LIMIT 1) AS last_timestamp
            FROM chats ch JOIN contacts c ON c.id = ch.contact_id
            ORDER BY COALESCE(last_timestamp, '') DESC, c.name
        ''')
        return [Chat(id=uuid.UUID(r["id"]), contact_id=uuid.UUID(r["contact_id"]), contact_name=r["name"], contact_ip=r["ip"],
                     last_message=r["last_message"] or "", last_timestamp=datetime.fromisoformat(r["last_timestamp"]) if r["last_timestamp"] else None) for r in rows]

    async def search_messages(self, text: str) -> List[Message]:
        rows = await self.db.execute_query(
            "SELECT id, chat_id, text, owner_id, timestamp, status, reply_to, attachment_path FROM messages WHERE text LIKE ? ORDER BY timestamp DESC",
            (f"%{text}%",),
        )
        return [Message(id=uuid.UUID(r["id"]), chatId=uuid.UUID(r["chat_id"]), text=r["text"], owner=uuid.UUID(r["owner_id"]),
                        timestamp=datetime.fromisoformat(r["timestamp"]), status=r["status"] or "sent",
                        reply_to=uuid.UUID(r["reply_to"]) if r["reply_to"] else None, attachment_path=r["attachment_path"]) for r in rows]
