import asyncio
import json
import uuid
from datetime import datetime


class AsyncTextEngine:
    """Newline-delimited JSON transport for Radmin VPN/LAN peer-to-peer chats."""

    def __init__(self, port: int = 5006):
        self.port = port
        self.running = False
        self.target_ip = ""
        self.server = None
        self.writer = None
        self._on_message_received = None

    async def start(self, target_ip: str, on_message_received):
        if self.running:
            return
        self.target_ip = target_ip
        self._on_message_received = on_message_received
        self.running = True
        self.server = await asyncio.start_server(
            lambda r, w: self._handle_incoming_connection(r, w, on_message_received),
            "0.0.0.0", self.port,
        )
        asyncio.create_task(self._connect_to_friend_loop(on_message_received))

    async def _handle_incoming_connection(self, reader, writer, on_msg_cb):
        addr = writer.get_extra_info("peername")
        if self.target_ip and addr and addr[0] != self.target_ip:
            writer.close(); await writer.wait_closed(); return
        if self.writer is None:
            self.writer = writer
        while self.running:
            try:
                data = await reader.readline()
                if not data:
                    break
                payload = json.loads(data.decode("utf-8"))
                on_msg_cb(payload)
            except Exception as exc:
                on_msg_cb({"type": "system", "text": f"Ошибка приема: {exc}"})
                break
        if self.writer is writer:
            self.writer = None
        writer.close(); await writer.wait_closed()

    async def _connect_to_friend_loop(self, on_msg_cb):
        while self.running and not self.writer:
            try:
                _, writer = await asyncio.open_connection(self.target_ip, self.port)
                self.writer = writer
                on_msg_cb({"type": "system", "text": "Текстовое соединение установлено"})
                return
            except OSError:
                await asyncio.sleep(2)

    async def send_payload(self, payload: dict) -> bool:
        if not self.writer:
            return False
        payload.setdefault("id", str(uuid.uuid4()))
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        try:
            self.writer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            await self.writer.drain()
            return True
        except OSError:
            self.writer = None
            if self._on_message_received:
                asyncio.create_task(self._connect_to_friend_loop(self._on_message_received))
            return False

    async def send_message(self, text: str, **extra) -> bool:
        return await self.send_payload({"type": "message", "text": text, **extra})

    async def send_typing(self, is_typing: bool = True) -> bool:
        return await self.send_payload({"type": "typing", "is_typing": is_typing})

    async def stop(self):
        self.running = False
        if self.writer:
            self.writer.close()
            try: await self.writer.wait_closed()
            except Exception: pass
            self.writer = None
        if self.server:
            self.server.close(); await self.server.wait_closed(); self.server = None
