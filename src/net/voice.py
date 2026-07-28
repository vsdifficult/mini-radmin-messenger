import asyncio
import queue

import numpy as np
import sounddevice as sd


class AsyncVoiceEngine:
    """Full-duplex UDP voice call engine for peers reachable through Radmin VPN/LAN."""

    def __init__(self, port: int = 5005, rate: int = 44100, channels: int = 1, block_size: int = 1024):
        self.port = port
        self.rate = rate
        self.channels = channels
        self.block_size = block_size

        self.running = False
        self.muted = False
        self.mic_volume = 1.0
        self.speaker_volume = 1.0

        self.target_ip = ""
        self.transport = None
        self.loop = None
        self.input_queue = None
        self.playback_queue = None
        self.input_stream = None
        self.output_stream = None
        self._send_task = None

    def set_mic_volume(self, volume_percent: float):
        self.mic_volume = max(0.0, min(volume_percent, 200.0)) / 100.0

    def set_speaker_volume(self, volume_percent: float):
        self.speaker_volume = max(0.0, min(volume_percent, 200.0)) / 100.0

    def set_mute(self, is_muted: bool):
        self.muted = is_muted

    def _input_callback(self, indata, frames, time, status):
        if self.running and not self.muted and self.loop and self.input_queue:
            self.loop.call_soon_threadsafe(self._safe_put_input, indata.copy())

    def _output_callback(self, outdata, frames, time, status):
        outdata.fill(0)
        if not self.running or not self.playback_queue:
            return
        chunks = []
        remaining = frames
        while remaining > 0:
            try:
                chunk = self.playback_queue.get_nowait()
            except queue.Empty:
                break
            chunk = chunk.reshape(-1, self.channels)
            if len(chunk) > remaining:
                chunks.append(chunk[:remaining])
                tail = chunk[remaining:]
                if len(tail):
                    self._safe_put_playback(tail.copy())
                remaining = 0
            else:
                chunks.append(chunk)
                remaining -= len(chunk)
        if chunks:
            audio = np.vstack(chunks)[:frames] * self.speaker_volume
            outdata[:len(audio)] = np.clip(audio, -1.0, 1.0)

    def _safe_put_input(self, data):
        if not self.input_queue:
            return
        try:
            self.input_queue.put_nowait(data)
        except asyncio.QueueFull:
            pass

    def _safe_put_playback(self, data):
        if not self.playback_queue:
            return
        try:
            self.playback_queue.put_nowait(data)
        except queue.Full:
            try:
                self.playback_queue.get_nowait()
                self.playback_queue.put_nowait(data)
            except queue.Empty:
                pass

    class UDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, engine):
            self.engine = engine

        def datagram_received(self, data, addr):
            if not self.engine.running or addr[0] != self.engine.target_ip:
                return
            try:
                audio_data = np.frombuffer(data, dtype=np.float32).reshape(-1, self.engine.channels)
                self.engine._safe_put_playback(audio_data)
            except Exception as exc:
                print(f"[Voice Error]: {exc}")

    async def start(self, target_ip: str, on_level_update=None):
        if self.running:
            return
        self.target_ip = target_ip
        self.loop = asyncio.get_running_loop()
        self.input_queue = asyncio.Queue(maxsize=20)
        self.playback_queue = queue.Queue(maxsize=80)
        self.running = True

        self.transport, _ = await self.loop.create_datagram_endpoint(
            lambda: self.UDPProtocol(self),
            local_addr=("0.0.0.0", self.port),
        )

        self.input_stream = sd.InputStream(
            samplerate=self.rate,
            channels=self.channels,
            callback=self._input_callback,
            blocksize=self.block_size,
            dtype="float32",
        )
        self.output_stream = sd.OutputStream(
            samplerate=self.rate,
            channels=self.channels,
            callback=self._output_callback,
            blocksize=self.block_size,
            dtype="float32",
        )
        self.input_stream.start()
        self.output_stream.start()
        self._send_task = asyncio.create_task(self._send_loop(on_level_update))

    async def _send_loop(self, on_level_update):
        while self.running:
            data = await self.input_queue.get()
            if on_level_update:
                rms = float(np.sqrt(np.mean(data**2))) if data.size else 0.0
                bars = "█" * min(int(rms * 100), 15)
                on_level_update(bars or ".")
            data = np.clip(data * self.mic_volume, -1.0, 1.0)
            if self.transport:
                self.transport.sendto(data.astype(np.float32).tobytes(), (self.target_ip, self.port))
            self.input_queue.task_done()

    async def stop(self):
        self.running = False
        if self._send_task:
            self._send_task.cancel()
            self._send_task = None
        for stream_name in ("input_stream", "output_stream"):
            stream = getattr(self, stream_name, None)
            if stream:
                stream.stop()
                stream.close()
                setattr(self, stream_name, None)
        if self.transport:
            self.transport.close()
            self.transport = None
