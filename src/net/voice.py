import asyncio
import socket
import sounddevice as sd
import numpy as np

class AsyncVoiceEngine:
    def __init__(self, port: int = 5005):
        self.port = port
        self.rate = 44100
        self.channels = 1
        self.block_size = 1024 
        
        self.running = False
        self.muted = False
        self.mic_volume = 1.0
        self.speaker_volume = 1.5
        
        self.target_ip = ""
        self.transport = None
        self.input_queue = asyncio.Queue()

    def set_mic_volume(self, volume_percent: float):
        self.mic_volume = volume_percent / 100.0

    def set_speaker_volume(self, volume_percent: float):
        self.speaker_volume = volume_percent / 100.0

    def set_mute(self, is_muted: bool):
        self.muted = is_muted

    def _input_callback(self, indata, frames, time, status):
        if self.running and not self.muted:
            asyncio.run_coroutine_threadsafe(
                self.input_queue.put(indata.copy()), 
                asyncio.get_event_loop()
            )

    class UDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, engine):
            self.engine = engine

        def datagram_received(self, data, addr):
            if not self.engine.running or addr[0] != self.engine.target_ip:
                return
            try:
                audio_data = np.frombuffer(data, dtype=np.float32)
                audio_data = audio_data * self.engine.speaker_volume
                audio_data = np.clip(audio_data, -1.0, 1.0)
                sd.play(audio_data, samplerate=self.engine.rate)
            except Exception as e:
                print(f"[Voice Error]: {e}")

    async def start(self, target_ip: str, on_level_update=None):
        if self.running:
            return
        self.target_ip = target_ip
        self.running = True

        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: self.UDPProtocol(self),
            local_addr=('0.0.0.0', self.port)
        )

        self.input_stream = sd.InputStream(
            samplerate=self.rate, 
            channels=self.channels, 
            callback=self._input_callback, 
            blocksize=self.block_size,
            dtype='float32'
        )
        self.input_stream.start()

        asyncio.create_task(self._send_loop(on_level_update))

    async def _send_loop(self, on_level_update):
        while self.running:
            data = await self.input_queue.get()
            
            if on_level_update:
                rms = np.sqrt(np.mean(data**2))
                bars = "█" * min(int(rms * 100), 15)
                on_level_update(bars or ".")

            data = data * self.mic_volume
            data = np.clip(data, -1.0, 1.0)
            
            if self.transport:
                self.transport.sendto(data.tobytes(), (self.target_ip, self.port))
            self.input_queue.task_done()

    async def stop(self):
        self.running = False
        if hasattr(self, 'input_stream'):
            self.input_stream.stop()
            self.input_stream.close()
        if self.transport:
            self.transport.close()
            self.transport = None
