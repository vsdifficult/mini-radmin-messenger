import asyncio

class AsyncTextEngine:
    def __init__(self, port: int = 5006):
        self.port = port
        self.running = False
        self.target_ip = ""
        
        self.server = None
        self.writer = None  

    async def start(self, target_ip: str, on_message_received):
        if self.running:
            return
        self.target_ip = target_ip
        self.running = True

        self.server = await asyncio.start_server(
            lambda r, w: self._handle_incoming_connection(r, w, on_message_received),
            '0.0.0.0', self.port
        )

        asyncio.create_task(self._connect_to_friend_loop(on_message_received))

    async def _handle_incoming_connection(self, reader, writer, on_msg_cb):
        addr = writer.get_extra_info('peername')
        if addr[0] != self.target_ip:
            writer.close()
            await writer.wait_closed()
            return

        while self.running:
            try:
                data = await reader.read(2048)
                if not data:
                    break
                msg = data.decode('utf-8')
                on_msg_cb("Друг", msg)
            except:
                break
        writer.close()
        await writer.wait_closed()

    async def _connect_to_friend_loop(self, on_msg_cb):
        while self.running and not self.writer:
            try:
                reader, writer = await asyncio.open_connection(self.target_ip, self.port)
                self.writer = writer
                on_msg_cb("Система", "Текстовое соединение с другом установлено!")
                return
            except:
                await asyncio.sleep(2)

    async def send_message(self, text: str) -> bool:
        if not self.writer:
            return False
        try:
            self.writer.write(text.encode('utf-8'))
            await self.writer.drain() 
            return True
        except:
            self.writer = None
            return False

    async def stop(self):
        self.running = False
        if self.writer:
            self.writer.close()
            try: await self.writer.wait_closed()
            except: pass
            self.writer = None
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
