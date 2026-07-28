import threading

import numpy as np
import sounddevice as sd


class Ringtone:
    """Простой зацикленный рингтон на двух тонах (как классический вызов), без сторонних аудио-библиотек."""

    def __init__(self, rate: int = 44100):
        self.rate = rate
        self._stream = None
        self._phase = 0.0
        self._playing = False
        self._lock = threading.Lock()
        self._pattern_pos = 0  # позиция в секундах внутри паттерна гудок/тишина

    def _callback(self, outdata, frames, time, status):
        t = (np.arange(frames) + self._phase) / self.rate
        # Паттерн: 1с тон, 1с тишина (двухтональный гудок ~ телефонный)
        cycle = (t + self._pattern_pos) % 2.0
        tone_mask = (cycle < 1.0).astype(np.float32)
        wave = (
            0.15 * np.sin(2 * np.pi * 440 * t) +
            0.10 * np.sin(2 * np.pi * 480 * t)
        ) * tone_mask
        outdata[:, 0] = wave.astype(np.float32)
        self._phase += frames

    def start(self):
        with self._lock:
            if self._playing:
                return
            self._playing = True
            self._phase = 0.0
            self._stream = sd.OutputStream(
                samplerate=self.rate, channels=1, dtype="float32",
                callback=self._callback, blocksize=1024,
            )
            self._stream.start()

    def stop(self):
        with self._lock:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            self._playing = False