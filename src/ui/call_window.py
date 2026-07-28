import math

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout


class CallWindow(QDialog):
    """Отдельное окно звонка — как в Telegram: аватар, статус, таймер, кнопки мут/громкость/сброс."""

    hangup_requested = pyqtSignal()
    accept_requested = pyqtSignal()
    decline_requested = pyqtSignal()
    mute_toggled = pyqtSignal(bool)
    mic_volume_changed = pyqtSignal(int)
    speaker_volume_changed = pyqtSignal(int)

    INCOMING, OUTGOING, ACTIVE = "incoming", "outgoing", "active"

    def __init__(self, contact_name: str, mode: str, parent=None):
        super().__init__(parent)
        self.contact_name = contact_name
        self.mode = mode
        self.muted = False
        self.seconds = 0

        self.setWindowTitle(f"Звонок — {contact_name}")
        self.setModal(False)
        self.setFixedSize(360, 460)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self.ring_timer = QTimer(self)
        self.ring_timer.timeout.connect(self._pulse_ring)
        self._ring_phase = 0

        self.build_ui()
        if mode == self.INCOMING:
            self.set_incoming()
        elif mode == self.OUTGOING:
            self.set_outgoing()

    def build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 32, 24, 24)
        root.setSpacing(14)

        self.avatar = QLabel(self.contact_name[:1].upper() if self.contact_name else "👤")
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setFixedSize(120, 120)
        self.avatar.setObjectName("avatar")
        avatar_wrap = QHBoxLayout(); avatar_wrap.addStretch(); avatar_wrap.addWidget(self.avatar); avatar_wrap.addStretch()

        self.name_label = QLabel(self.contact_name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setObjectName("name")

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")

        self.level_label = QLabel("")
        self.level_label.setAlignment(Qt.AlignCenter)
        self.level_label.setObjectName("level")

        root.addLayout(avatar_wrap)
        root.addWidget(self.name_label)
        root.addWidget(self.status_label)
        root.addWidget(self.level_label)
        root.addStretch()

        vol_box = QVBoxLayout()
        mic_row = QHBoxLayout()
        mic_row.addWidget(QLabel("🎙"))
        self.mic_slider = QSlider(Qt.Horizontal); self.mic_slider.setRange(0, 200); self.mic_slider.setValue(100)
        self.mic_slider.valueChanged.connect(self.mic_volume_changed.emit)
        mic_row.addWidget(self.mic_slider)
        spk_row = QHBoxLayout()
        spk_row.addWidget(QLabel("🔊"))
        self.speaker_slider = QSlider(Qt.Horizontal); self.speaker_slider.setRange(0, 200); self.speaker_slider.setValue(100)
        self.speaker_slider.valueChanged.connect(self.speaker_volume_changed.emit)
        spk_row.addWidget(self.speaker_slider)
        vol_box.addLayout(mic_row); vol_box.addLayout(spk_row)
        root.addLayout(vol_box)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(20)
        root.addLayout(self.button_row)

        self.mute_btn = QPushButton("🎙")
        self.mute_btn.setObjectName("roundBtn")
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self._on_mute_clicked)

        self.decline_btn = QPushButton("✕")
        self.decline_btn.setObjectName("declineBtn")
        self.decline_btn.clicked.connect(self._on_decline_clicked)

        self.accept_btn = QPushButton("✓")
        self.accept_btn.setObjectName("acceptBtn")
        self.accept_btn.clicked.connect(self._on_accept_clicked)

        self.hangup_btn = QPushButton("☎")
        self.hangup_btn.setObjectName("declineBtn")
        self.hangup_btn.clicked.connect(self._on_hangup_clicked)

        self.setStyleSheet('''
            QDialog { background: #17212b; }
            QLabel { color: #dbe7f3; }
            QLabel#avatar { background: #2b5278; border-radius: 60px; font-size: 46px; color: white; }
            QLabel#name { font-size: 20px; font-weight: 600; }
            QLabel#status { font-size: 13px; color: #8aa2b6; }
            QLabel#level { font-size: 13px; color: #5eb85e; min-height: 18px; }
            QPushButton#roundBtn { background: #253341; color: white; border: none; border-radius: 30px; min-width: 60px; min-height: 60px; font-size: 20px; }
            QPushButton#roundBtn:checked { background: #dbe7f3; color: #17212b; }
            QPushButton#acceptBtn { background: #4caf50; color: white; border: none; border-radius: 30px; min-width: 60px; min-height: 60px; font-size: 22px; }
            QPushButton#declineBtn { background: #e64646; color: white; border: none; border-radius: 30px; min-width: 60px; min-height: 60px; font-size: 20px; }
            QSlider::groove:horizontal { background: #253341; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #2b5278; width: 14px; margin: -6px 0; border-radius: 7px; }
        ''')

    def _clear_buttons(self):
        while self.button_row.count():
            item = self.button_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def set_incoming(self):
        self.mode = self.INCOMING
        self.status_label.setText("Входящий звонок...")
        self.mic_slider.setEnabled(False); self.speaker_slider.setEnabled(False)
        self._clear_buttons()
        self.button_row.addStretch()
        self.button_row.addWidget(self.decline_btn)
        self.button_row.addWidget(self.accept_btn)
        self.button_row.addStretch()
        self.ring_timer.start(500)

    def set_outgoing(self):
        self.mode = self.OUTGOING
        self.status_label.setText("Вызов...")
        self.mic_slider.setEnabled(False); self.speaker_slider.setEnabled(False)
        self._clear_buttons()
        self.button_row.addStretch()
        self.button_row.addWidget(self.hangup_btn)
        self.button_row.addStretch()
        self.ring_timer.start(500)

    def set_active(self):
        self.mode = self.ACTIVE
        self.ring_timer.stop()
        self.avatar.setStyleSheet("")
        self.mic_slider.setEnabled(True); self.speaker_slider.setEnabled(True)
        self.status_label.setText("00:00")
        self.seconds = 0
        self.timer.start(1000)
        self._clear_buttons()
        self.button_row.addStretch()
        self.button_row.addWidget(self.mute_btn)
        self.button_row.addWidget(self.hangup_btn)
        self.button_row.addStretch()

    def set_ended(self, message: str):
        self.ring_timer.stop()
        self.timer.stop()
        self.status_label.setText(message)
        self.level_label.setText("")
        QTimer.singleShot(1200, self.close)

    def set_level(self, bars: str):
        self.level_label.setText(bars)

    def _tick(self):
        self.seconds += 1
        m, s = divmod(self.seconds, 60)
        self.status_label.setText(f"{m:02d}:{s:02d}")

    def _pulse_ring(self):
        self._ring_phase += 1
        alpha = int(128 + 100 * math.sin(self._ring_phase))
        self.avatar.setStyleSheet(f"background: rgba(43,82,120,{max(80, min(255, alpha))}); border-radius: 60px; font-size: 46px; color: white;")

    def _on_mute_clicked(self):
        self.muted = self.mute_btn.isChecked()
        self.mute_btn.setText("🔇" if self.muted else "🎙")
        self.mute_toggled.emit(self.muted)

    def _on_accept_clicked(self):
        self.accept_requested.emit()

    def _on_decline_clicked(self):
        self.decline_requested.emit()

    def _on_hangup_clicked(self):
        self.hangup_requested.emit()

    def closeEvent(self, event):
        self.ring_timer.stop()
        self.timer.stop()
        event.accept()
