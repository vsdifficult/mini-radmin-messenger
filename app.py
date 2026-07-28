import asyncio
import os
import sys
import threading
import uuid
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QAction, QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSlider, QTextBrowser,
    QToolBar, QVBoxLayout, QWidget
)

from src.core.core import MessengerEngine
from src.net.text import AsyncTextEngine
from src.net.voice import AsyncVoiceEngine


APP_DIR = os.path.join(os.path.expanduser("~"), ".mini-radmin-messenger")


class MessengerWindow(QMainWindow):
    network_event = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        os.makedirs(APP_DIR, exist_ok=True)
        self.engine = MessengerEngine(APP_DIR)
        self.owner_id = asyncio.run(self.engine.initialize())
        self.current_chat = None
        self.current_contact = None
        self.text_engine = None
        self.voice_engine = None
        self.call_ip = None
        self.call_active = False
        self.muted = False
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

        self.setWindowTitle("Mini Radmin Messenger")
        self.resize(980, 680)
        self.network_event.connect(self.on_network_event)
        self.build_ui()
        self.refresh_chats()

    def build_ui(self):
        toolbar = QToolBar("main")
        self.addToolBar(toolbar)
        add = QAction("➕ Контакт", self); add.triggered.connect(self.add_contact); toolbar.addAction(add)
        self.call_action = QAction("📞 Позвонить", self); self.call_action.triggered.connect(self.toggle_voice); toolbar.addAction(self.call_action)
        self.mute_action = QAction("🎙 Микрофон", self); self.mute_action.triggered.connect(self.toggle_mute); toolbar.addAction(self.mute_action)
        attach = QAction("📎 Файл", self); attach.triggered.connect(self.attach_file); toolbar.addAction(attach)

        root = QWidget(); self.setCentralWidget(root)
        main = QHBoxLayout(root)

        left = QVBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Поиск чатов и сообщений")
        self.search.textChanged.connect(self.refresh_chats)
        self.chat_list = QListWidget(); self.chat_list.itemSelectionChanged.connect(self.open_selected_chat)
        left.addWidget(QLabel("Чаты")); left.addWidget(self.search); left.addWidget(self.chat_list, 1)

        right = QVBoxLayout()
        chat_header = QHBoxLayout()
        self.avatar = QLabel("💬")
        self.header = QLabel("Выберите чат или добавьте контакт Radmin VPN")
        self.chat_call_button = QPushButton("📞")
        self.chat_call_button.setToolTip("Позвонить контакту")
        self.chat_call_button.clicked.connect(self.toggle_voice)
        self.chat_call_button.setEnabled(False)
        chat_header.addWidget(self.avatar)
        chat_header.addWidget(self.header, 1)
        chat_header.addWidget(self.chat_call_button)
        self.messages = QTextBrowser(); self.messages.setOpenExternalLinks(True)
        composer = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("Сообщение")
        self.input.returnPressed.connect(self.send_message)
        self.input.textEdited.connect(lambda: self.run_net(lambda: self.text_engine and self.text_engine.send_typing(True)))
        send = QPushButton("Отправить"); send.clicked.connect(self.send_message)
        composer.addWidget(self.input, 1); composer.addWidget(send)
        self.status = QLabel("Оффлайн")
        call_controls = QHBoxLayout()
        self.mic_slider = QSlider(Qt.Horizontal); self.mic_slider.setRange(0, 200); self.mic_slider.setValue(100)
        self.speaker_slider = QSlider(Qt.Horizontal); self.speaker_slider.setRange(0, 200); self.speaker_slider.setValue(100)
        self.mic_slider.valueChanged.connect(lambda value: self.voice_engine and self.voice_engine.set_mic_volume(value))
        self.speaker_slider.valueChanged.connect(lambda value: self.voice_engine and self.voice_engine.set_speaker_volume(value))
        call_controls.addWidget(QLabel("Mic")); call_controls.addWidget(self.mic_slider)
        call_controls.addWidget(QLabel("Speaker")); call_controls.addWidget(self.speaker_slider)
        right.addLayout(chat_header); right.addWidget(self.messages, 1); right.addLayout(composer); right.addLayout(call_controls); right.addWidget(self.status)
        main.addLayout(left, 1); main.addLayout(right, 3)

        self.setStyleSheet('''
            QMainWindow { background: #17212b; color: #dbe7f3; }
            QLabel { color: #dbe7f3; font-size: 14px; }
            QListWidget, QTextBrowser, QLineEdit { background: #0e1621; color: #dbe7f3; border: 1px solid #253341; border-radius: 8px; padding: 8px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #253341; }
            QListWidget::item:selected { background: #2b5278; }
            QPushButton { background: #2b5278; color: white; border: none; padding: 9px 16px; border-radius: 8px; }
            QToolBar { background: #17212b; border: none; }
        ''')

    def run_net(self, factory):
        if self.loop.is_running():
            result = factory()
            if asyncio.iscoroutine(result):
                asyncio.run_coroutine_threadsafe(result, self.loop)

    def refresh_chats(self):
        query = self.search.text().lower() if hasattr(self, "search") else ""
        chats = asyncio.run(self.engine.repository.get_chats())
        self.chat_list.clear()
        for chat in chats:
            if query and query not in chat.contact_name.lower() and query not in chat.last_message.lower():
                continue
            item = QListWidgetItem(f"{chat.contact_name}\n{chat.last_message[:60]}")
            item.setData(Qt.UserRole, chat)
            self.chat_list.addItem(item)

    def add_contact(self):
        name, ok = QInputDialog.getText(self, "Контакт", "Имя:")
        if not ok or not name.strip(): return
        ip, ok = QInputDialog.getText(self, "Radmin VPN IP", "IP адрес друга:")
        if not ok or not ip.strip(): return
        asyncio.run(self.engine.create_chat(name, ip))
        self.refresh_chats()

    def open_selected_chat(self):
        items = self.chat_list.selectedItems()
        if not items: return
        chat = items[0].data(Qt.UserRole)
        self.current_chat, self.current_contact = chat.id, chat.contact_id
        self.avatar.setText(chat.contact_name[:1].upper() if chat.contact_name else "👤")
        self.header.setText(f"<b>{chat.contact_name}</b><br><span style='color:#8aa2b6'>Radmin VPN: {chat.contact_ip}</span>")
        self.chat_call_button.setEnabled(True)
        self.load_messages()
        self.start_text(chat.contact_ip)

    def start_text(self, ip):
        if self.text_engine:
            self.run_net(lambda: self.text_engine.stop())
        self.text_engine = AsyncTextEngine()
        self.run_net(lambda: self.text_engine.start(ip, self.network_event.emit))
        self.status.setText("Подключение к peer через Radmin VPN...")

    def load_messages(self):
        self.messages.clear()
        if not self.current_chat: return
        for msg in asyncio.run(self.engine.repository.get_chat(self.current_chat)):
            mine = msg.owner == self.owner_id
            author = "Вы" if mine else "Друг"
            color = "#2b5278" if mine else "#182533"
            extra = f"<br><a href='file://{msg.attachment_path}'>{os.path.basename(msg.attachment_path)}</a>" if msg.attachment_path else ""
            self.messages.append(f"<div style='background:{color}; margin:6px; padding:8px; border-radius:8px;'><b>{author}</b> <small>{msg.timestamp:%H:%M} · {msg.status}</small><br>{msg.text}{extra}</div>")
        QTimer.singleShot(0, lambda: self.messages.verticalScrollBar().setValue(self.messages.verticalScrollBar().maximum()))

    def send_message(self):
        text = self.input.text().strip()
        if not text or not self.current_chat: return
        message_id = asyncio.run(self.engine.send_message(text, self.current_chat, self.current_contact, status="queued"))
        self.input.clear(); self.load_messages(); self.refresh_chats()
        async def send():
            ok = self.text_engine and await self.text_engine.send_message(text, id=str(message_id), owner_id=str(self.owner_id))
            await self.engine.repository.update_message_status(message_id, "sent" if ok else "queued")
            self.network_event.emit({"type": "refresh"})
        self.run_net(lambda: send())

    def attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if path and self.current_chat:
            text = f"Файл: {os.path.basename(path)}"
            asyncio.run(self.engine.send_message(text, self.current_chat, self.current_contact, status="local", attachment_path=path))
            self.load_messages(); self.refresh_chats()

    def on_network_event(self, payload):
        if payload.get("type") == "message" and self.current_chat and self.current_contact:
            sender = uuid.uuid5(uuid.NAMESPACE_DNS, payload.get("owner_id", "peer"))
            try: sender = uuid.UUID(payload.get("owner_id"))
            except Exception: pass
            asyncio.run(self.engine.receive_message(payload.get("text", ""), self.current_chat, self.current_contact, sender, message_id=uuid.UUID(payload["id"])))
            self.load_messages(); self.refresh_chats(); self.status.setText("Онлайн")
        elif payload.get("type") == "typing":
            self.status.setText("Печатает..." if payload.get("is_typing") else "Онлайн")
        elif payload.get("type") == "call_invite":
            self.handle_call_invite()
        elif payload.get("type") == "call_accept":
            self.start_voice_call("Звонок принят")
        elif payload.get("type") == "call_end":
            self.stop_voice_call("Звонок завершен собеседником", notify_peer=False)
        elif payload.get("type") == "system":
            self.status.setText(payload.get("text", ""))
        elif payload.get("type") == "refresh":
            self.load_messages(); self.refresh_chats()

    def selected_chat(self):
        items = self.chat_list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def toggle_voice(self):
        chat = self.selected_chat()
        if not chat:
            QMessageBox.information(self, "Звонок", "Сначала выберите чат")
            return
        self.call_ip = chat.contact_ip
        if self.call_active:
            self.stop_voice_call("Звонок завершен")
            return
        self.status.setText("Исходящий звонок...")
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({"type": "call_invite", "owner_id": str(self.owner_id)}))

    def handle_call_invite(self):
        answer = QMessageBox.question(self, "Входящий звонок", "Принять голосовой звонок?", QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            chat = self.selected_chat()
            self.call_ip = chat.contact_ip if chat else self.call_ip
            self.run_net(lambda: self.text_engine and self.text_engine.send_payload({"type": "call_accept", "owner_id": str(self.owner_id)}))
            self.start_voice_call("Звонок начался")
        else:
            self.run_net(lambda: self.text_engine and self.text_engine.send_payload({"type": "call_end", "owner_id": str(self.owner_id)}))

    def start_voice_call(self, message):
        chat = self.selected_chat()
        target_ip = self.call_ip or (chat.contact_ip if chat else None)
        if not target_ip:
            self.status.setText("Нет IP для звонка")
            return
        if not self.voice_engine:
            self.voice_engine = AsyncVoiceEngine()
        self.voice_engine.set_mic_volume(self.mic_slider.value())
        self.voice_engine.set_speaker_volume(self.speaker_slider.value())
        self.voice_engine.set_mute(self.muted)
        self.run_net(lambda: self.voice_engine.start(target_ip, lambda bars: self.network_event.emit({"type": "system", "text": f"{message} · уровень {bars}"})))
        self.call_active = True
        self.call_action.setText("☎ Завершить")
        self.chat_call_button.setText("☎")
        self.chat_call_button.setToolTip("Завершить звонок")
        self.status.setText(message)

    def stop_voice_call(self, message, notify_peer=True):
        if self.voice_engine and self.voice_engine.running:
            self.run_net(lambda: self.voice_engine.stop())
        if notify_peer:
            self.run_net(lambda: self.text_engine and self.text_engine.send_payload({"type": "call_end", "owner_id": str(self.owner_id)}))
        self.call_active = False
        self.call_action.setText("📞 Позвонить")
        self.chat_call_button.setText("📞")
        self.chat_call_button.setToolTip("Позвонить контакту")
        self.status.setText(message)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.voice_engine:
            self.voice_engine.set_mute(self.muted)
        self.mute_action.setText("🔇 Микрофон выкл" if self.muted else "🎙 Микрофон")

    def closeEvent(self, event):
        if self.text_engine: self.run_net(lambda: self.text_engine.stop())
        if self.voice_engine: self.run_net(lambda: self.voice_engine.stop())
        self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MessengerWindow(); win.show()
    sys.exit(app.exec_())
