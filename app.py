import asyncio
import os
import sys
import threading
import uuid
import json
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSettings
from PyQt5.QtWidgets import (
    QAction, QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QLineEdit, QMainWindow, QMessageBox, QPushButton, QSlider, QTextBrowser,
    QToolBar, QVBoxLayout, QWidget, QDialog, QDialogButtonBox, QComboBox, QCheckBox,
    QSpinBox, QTabWidget, QGroupBox, QColorDialog
)
from PyQt5.QtGui import QColor, QPalette

from src.core.core import MessengerEngine
from src.net.text import AsyncTextEngine
from src.net.voice import AsyncVoiceEngine
from src.net.ringtone import Ringtone
from src.ui.call_window import CallWindow


APP_DIR = os.path.join(os.path.expanduser("~"), ".mini-radmin-messenger")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Настройки")
        self.resize(500, 400)
        self.setModal(True)
        
        # Загружаем текущие настройки
        self.settings = self.parent.settings.copy() if parent else {}
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Вкладки
        tabs = QTabWidget()
        
        # Вкладка "Общие"
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        # Группа "Тема"
        theme_group = QGroupBox("Оформление")
        theme_layout = QVBoxLayout()
        
        # Выбор темы
        theme_layout.addWidget(QLabel("Тема:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Тёмная", "Светлая", "Синяя", "Зелёная"])
        theme_layout.addWidget(self.theme_combo)
        
        # Цвет акцента
        theme_layout.addWidget(QLabel("Цвет акцента:"))
        self.accent_color_btn = QPushButton("Выбрать цвет")
        self.accent_color_btn.clicked.connect(self.choose_accent_color)
        theme_layout.addWidget(self.accent_color_btn)
        self.accent_color_label = QLabel()
        theme_layout.addWidget(self.accent_color_label)
        
        theme_group.setLayout(theme_layout)
        general_layout.addWidget(theme_group)
        
        # Группа "Поведение"
        behavior_group = QGroupBox("Поведение")
        behavior_layout = QVBoxLayout()
        
        self.auto_start_chat = QCheckBox("Автоматически открывать последний чат")
        behavior_layout.addWidget(self.auto_start_chat)
        
        self.show_timestamps = QCheckBox("Показывать временные метки")
        behavior_layout.addWidget(self.show_timestamps)
        
        behavior_group.setLayout(behavior_layout)
        general_layout.addWidget(behavior_group)
        
        general_layout.addStretch()
        general_tab.setLayout(general_layout)
        tabs.addTab(general_tab, "Общие")
        
        # Вкладка "Уведомления"
        notify_tab = QWidget()
        notify_layout = QVBoxLayout()
        
        notify_group = QGroupBox("Уведомления")
        notify_group_layout = QVBoxLayout()
        
        self.sound_enabled = QCheckBox("Включить звуки")
        notify_group_layout.addWidget(self.sound_enabled)
        
        self.notify_messages = QCheckBox("Уведомления о новых сообщениях")
        notify_group_layout.addWidget(self.notify_messages)
        
        self.notify_calls = QCheckBox("Уведомления о звонках")
        notify_group_layout.addWidget(self.notify_calls)
        
        notify_group.setLayout(notify_group_layout)
        notify_layout.addWidget(notify_group)
        notify_layout.addStretch()
        notify_tab.setLayout(notify_layout)
        tabs.addTab(notify_tab, "Уведомления")
        
        # Вкладка "Чаты"
        chats_tab = QWidget()
        chats_layout = QVBoxLayout()
        
        chat_group = QGroupBox("Настройки чатов")
        chat_group_layout = QVBoxLayout()
        
        chat_group_layout.addWidget(QLabel("Шрифт сообщений:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setSuffix(" pt")
        chat_group_layout.addWidget(self.font_size_spin)
        
        chat_group_layout.addWidget(QLabel("Максимум сообщений в чате:"))
        self.max_messages_spin = QSpinBox()
        self.max_messages_spin.setRange(50, 1000)
        self.max_messages_spin.setSuffix(" шт")
        self.max_messages_spin.setSingleStep(50)
        chat_group_layout.addWidget(self.max_messages_spin)
        
        chat_group.setLayout(chat_group_layout)
        chats_layout.addWidget(chat_group)
        chats_layout.addStretch()
        chats_tab.setLayout(chats_layout)
        tabs.addTab(chats_tab, "Чаты")
        
        layout.addWidget(tabs)
        
        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def choose_accent_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings["accent_color"] = color.name()
            self.update_accent_color_preview(color)
    
    def update_accent_color_preview(self, color):
        self.accent_color_label.setText(f"Выбран: {color.name()}")
        self.accent_color_label.setStyleSheet(f"background-color: {color.name()}; color: white; padding: 5px; border-radius: 3px;")
    
    def load_settings(self):
        # Загружаем настройки в UI
        theme_map = {"dark": "Тёмная", "light": "Светлая", "blue": "Синяя", "green": "Зелёная"}
        current_theme = self.settings.get("theme", "dark")
        self.theme_combo.setCurrentText(theme_map.get(current_theme, "Тёмная"))
        
        accent_color = self.settings.get("accent_color", "#2b5278")
        self.settings["accent_color"] = accent_color
        self.update_accent_color_preview(QColor(accent_color))
        
        self.auto_start_chat.setChecked(self.settings.get("auto_start_chat", False))
        self.show_timestamps.setChecked(self.settings.get("show_timestamps", True))
        self.sound_enabled.setChecked(self.settings.get("sound_enabled", True))
        self.notify_messages.setChecked(self.settings.get("notify_messages", True))
        self.notify_calls.setChecked(self.settings.get("notify_calls", True))
        self.font_size_spin.setValue(self.settings.get("font_size", 14))
        self.max_messages_spin.setValue(self.settings.get("max_messages", 200))
    
    def get_settings(self):
        # Сохраняем настройки из UI
        theme_map = {"Тёмная": "dark", "Светлая": "light", "Синяя": "blue", "Зелёная": "green"}
        self.settings.update({
            "theme": theme_map.get(self.theme_combo.currentText(), "dark"),
            "accent_color": self.settings.get("accent_color", "#2b5278"),
            "auto_start_chat": self.auto_start_chat.isChecked(),
            "show_timestamps": self.show_timestamps.isChecked(),
            "sound_enabled": self.sound_enabled.isChecked(),
            "notify_messages": self.notify_messages.isChecked(),
            "notify_calls": self.notify_calls.isChecked(),
            "font_size": self.font_size_spin.value(),
            "max_messages": self.max_messages_spin.value()
        })
        return self.settings


class MessengerWindow(QMainWindow):
    network_event = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        os.makedirs(APP_DIR, exist_ok=True)
        
        # Загружаем настройки
        self.settings = self.load_settings()
        
        self.engine = MessengerEngine(APP_DIR)
        self.owner_id = asyncio.run(self.engine.initialize())
        self.current_chat = None
        self.current_contact = None
        self.text_engine = None
        self.voice_engine = None

        # --- состояние звонка ---
        self.call_ip = None
        self.call_contact_name = None
        self.call_state = None  # None | "outgoing" | "incoming" | "active"
        self.call_window = None
        self.ringtone = Ringtone()
        self.muted = False

        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()

        self.setWindowTitle("Mini Radmin Messenger")
        self.resize(980, 680)
        self.network_event.connect(self.on_network_event)
        self.build_ui()
        self.apply_theme()
        self.refresh_chats()
        # Изначально скрываем элементы чата
        self.toggle_chat_ui(False)

    def load_settings(self):
        """Загружает настройки из файла"""
        default_settings = {
            "theme": "dark",
            "accent_color": "#2b5278",
            "auto_start_chat": False,
            "show_timestamps": True,
            "sound_enabled": True,
            "notify_messages": True,
            "notify_calls": True,
            "font_size": 14,
            "max_messages": 200
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_settings.update(loaded)
            except:
                pass
        return default_settings

    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except:
            pass

    def build_ui(self):
        # Создаем toolbar
        toolbar = QToolBar("main")
        self.addToolBar(toolbar)
        
        # Кнопка "Создать контакт"
        add_contact_action = QAction("➕ Создать контакт", self)
        add_contact_action.triggered.connect(self.add_contact)
        toolbar.addAction(add_contact_action)
        
        # Кнопка "Начать чат" (будет активна только когда есть выбранный контакт)
        self.start_chat_action = QAction("💬 Начать чат", self)
        self.start_chat_action.triggered.connect(self.start_new_chat)
        self.start_chat_action.setEnabled(False)
        toolbar.addAction(self.start_chat_action)
        
        # Разделитель
        toolbar.addSeparator()
        
        # Кнопка настроек
        settings_action = QAction("⚙️ Настройки", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        self.toolbar = toolbar
        
        root = QWidget()
        self.setCentralWidget(root)
        main = QHBoxLayout(root)

        left = QVBoxLayout()
        
        # Заголовок "Чаты"
        chats_label = QLabel("Чаты")
        chats_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        left.addWidget(chats_label)
        
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск чатов и контактов")
        self.search.textChanged.connect(self.refresh_chats)
        left.addWidget(self.search)
        
        self.chat_list = QListWidget()
        self.chat_list.itemSelectionChanged.connect(self.on_chat_selected)
        self.chat_list.itemDoubleClicked.connect(self.open_selected_chat)
        left.addWidget(self.chat_list, 1)

        right = QVBoxLayout()
        chat_header = QHBoxLayout()
        self.avatar = QLabel("💬")
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setFixedSize(50, 50)
        self.avatar.setStyleSheet("font-size: 28px; background: transparent;")
        
        self.header = QLabel("Выберите чат или создайте новый контакт")
        self.header.setStyleSheet("font-size: 14px;")
        
        self.chat_call_button = QPushButton("📞")
        self.chat_call_button.setToolTip("Позвонить контакту")
        self.chat_call_button.clicked.connect(self.start_outgoing_call)
        self.chat_call_button.setEnabled(False)
        self.chat_call_button.setFixedSize(40, 40)
        
        chat_header.addWidget(self.avatar)
        chat_header.addWidget(self.header, 1)
        chat_header.addWidget(self.chat_call_button)
        
        self.messages = QTextBrowser()
        self.messages.setOpenExternalLinks(True)
        
        composer = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Введите сообщение...")
        self.input.returnPressed.connect(self.send_message)
        self.input.textEdited.connect(lambda: self.run_net(lambda: self.text_engine and self.text_engine.send_typing(True)))
        
        # Создаем кнопку отправки
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedWidth(100)
        composer.addWidget(self.input, 1)
        composer.addWidget(self.send_button)
        
        self.status = QLabel("Оффлайн")
        self.status.setStyleSheet("padding: 5px; font-size: 12px;")
        
        right.addLayout(chat_header)
        right.addWidget(self.messages, 1)
        right.addLayout(composer)
        right.addWidget(self.status)
        main.addLayout(left, 1)
        main.addLayout(right, 3)

    def on_chat_selected(self):
        """Обработчик выбора чата в списке"""
        items = self.chat_list.selectedItems()
        if items:
            self.start_chat_action.setEnabled(True)
        else:
            self.start_chat_action.setEnabled(False)

    def start_new_chat(self):
        """Начать чат с выбранным контактом"""
        self.open_selected_chat()

    def apply_theme(self):
        """Применяет выбранную тему"""
        theme = self.settings.get("theme", "dark")
        accent = self.settings.get("accent_color", "#2b5278")
        font_size = self.settings.get("font_size", 14)
        
        themes = {
            "dark": {
                "bg": "#17212b",
                "bg_secondary": "#0e1621",
                "text": "#dbe7f3",
                "border": "#253341",
                "selected": accent,
                "message_mine": accent,
                "message_other": "#182533",
                "hover": "#2b5278"
            },
            "light": {
                "bg": "#ffffff",
                "bg_secondary": "#f0f2f5",
                "text": "#1a1a1a",
                "border": "#d0d7de",
                "selected": "#e1f0ff",
                "message_mine": "#d4e8ff",
                "message_other": "#e9ecef",
                "hover": "#e1f0ff"
            },
            "blue": {
                "bg": "#0a1628",
                "bg_secondary": "#0d1f3c",
                "text": "#e8f0fe",
                "border": "#1a3a6a",
                "selected": "#1a4a8a",
                "message_mine": "#1a4a8a",
                "message_other": "#0d2b5a",
                "hover": "#1a4a8a"
            },
            "green": {
                "bg": "#0a1f0a",
                "bg_secondary": "#0d2b0d",
                "text": "#d4edda",
                "border": "#1a4a1a",
                "selected": "#1a6a1a",
                "message_mine": "#1a6a1a",
                "message_other": "#0d3a0d",
                "hover": "#1a6a1a"
            }
        }
        
        t = themes.get(theme, themes["dark"])
        
        # Применяем стиль
        self.setStyleSheet(f'''
            QMainWindow {{ background: {t["bg"]}; color: {t["text"]}; }}
            QLabel {{ color: {t["text"]}; font-size: {font_size}px; }}
            QListWidget, QTextBrowser, QLineEdit {{ 
                background: {t["bg_secondary"]}; 
                color: {t["text"]}; 
                border: 1px solid {t["border"]}; 
                border-radius: 8px; 
                padding: 8px; 
                font-size: {font_size}px;
            }}
            QListWidget::item {{ 
                padding: 12px; 
                border-bottom: 1px solid {t["border"]}; 
            }}
            QListWidget::item:selected {{ 
                background: {t["selected"]}; 
            }}
            QListWidget::item:hover {{
                background: {t["hover"]};
            }}
            QPushButton {{ 
                background: {t["selected"]}; 
                color: white; 
                border: none; 
                padding: 9px 16px; 
                border-radius: 8px; 
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                opacity: 0.5;
            }}
            QToolBar {{ 
                background: {t["bg"]}; 
                border: none; 
                spacing: 5px;
                padding: 5px;
            }}
            QToolBar QAction {{
                color: {t["text"]};
                padding: 5px 10px;
            }}
            QToolBar QAction:hover {{
                background: {t["hover"]};
                border-radius: 5px;
            }}
            QToolBar QAction:disabled {{
                opacity: 0.5;
            }}
            QScrollBar:vertical {{
                background: {t["bg_secondary"]};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {t["selected"]};
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: {t["bg_secondary"]};
            }}
        ''')
        
        # Обновляем цвет сообщений в зависимости от темы
        self.message_colors = {
            "mine": t["message_mine"],
            "other": t["message_other"]
        }
        
        # Перезагружаем сообщения с новой темой
        if self.current_chat:
            self.load_messages()

    def open_settings(self):
        """Открывает окно настроек"""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_settings = dialog.get_settings()
            self.settings.update(new_settings)
            self.save_settings()
            self.apply_theme()
            QMessageBox.information(self, "Настройки", "Настройки сохранены!")

    def toggle_chat_ui(self, visible):
        """Показывает или скрывает элементы интерфейса чата"""
        # Скрываем/показываем элементы чата
        self.avatar.setVisible(visible)
        self.header.setVisible(visible)
        self.chat_call_button.setVisible(visible)
        self.messages.setVisible(visible)
        self.input.setVisible(visible)
        self.send_button.setVisible(visible)
        self.status.setVisible(visible)

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
            # Показываем имя контакта и последнее сообщение
            last_msg = chat.last_message[:50] if chat.last_message else "Нет сообщений"
            item = QListWidgetItem(f"{chat.contact_name}\n{last_msg}")
            item.setData(Qt.UserRole, chat)
            self.chat_list.addItem(item)

    def add_contact(self):
        name, ok = QInputDialog.getText(self, "Новый контакт", "Введите имя контакта:")
        if not ok or not name.strip(): 
            return
        ip, ok = QInputDialog.getText(self, "Radmin VPN IP", "Введите IP адрес контакта:")
        if not ok or not ip.strip(): 
            return
        asyncio.run(self.engine.create_chat(name, ip))
        self.refresh_chats()
        QMessageBox.information(self, "Успешно", f"Контакт '{name}' добавлен!")

    def open_selected_chat(self):
        items = self.chat_list.selectedItems()
        if not items: 
            return
        chat = items[0].data(Qt.UserRole)
        self.current_chat, self.current_contact = chat.id, chat.contact_id
        self.avatar.setText(chat.contact_name[:1].upper() if chat.contact_name else "👤")
        self.header.setText(f"<b>{chat.contact_name}</b><br><span style='color:#8aa2b6; font-size: 12px;'>Radmin VPN: {chat.contact_ip}</span>")
        self.chat_call_button.setEnabled(True)
        self.load_messages()
        self.start_text(chat.contact_ip)
        # Показываем элементы чата
        self.toggle_chat_ui(True)

    def start_text(self, ip):
        if self.text_engine:
            self.run_net(lambda: self.text_engine.stop())
        self.text_engine = AsyncTextEngine()
        self.run_net(lambda: self.text_engine.start(ip, self.network_event.emit))
        self.status.setText("Подключение к peer через Radmin VPN...")

    def load_messages(self):
        self.messages.clear()
        if not self.current_chat: 
            return
        show_timestamps = self.settings.get("show_timestamps", True)
        max_messages = self.settings.get("max_messages", 200)
        
        messages = asyncio.run(self.engine.repository.get_chat(self.current_chat))
        messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        for msg in messages:
            mine = msg.owner == self.owner_id
            author = "Вы" if mine else "Друг"
            color = self.message_colors["mine"] if mine else self.message_colors["other"]
            
            timestamp = f" <small>{msg.timestamp:%H:%M}</small>" if show_timestamps else ""
            status = f" · {msg.status}" if show_timestamps and msg.status != "sent" else ""
            
            extra = f"<br><a href='file://{msg.attachment_path}' style='color: #4a9eff;'>{os.path.basename(msg.attachment_path)}</a>" if msg.attachment_path else ""
            
            self.messages.append(f"""
                <div style='background:{color}; margin:6px; padding:10px; border-radius:8px;'>
                    <b>{author}</b>{timestamp}{status}<br>
                    {msg.text}{extra}
                </div>
            """)
        QTimer.singleShot(0, lambda: self.messages.verticalScrollBar().setValue(self.messages.verticalScrollBar().maximum()))

    def send_message(self):
        text = self.input.text().strip()
        if not text or not self.current_chat: 
            return
        message_id = asyncio.run(self.engine.send_message(text, self.current_chat, self.current_contact, status="queued"))
        self.input.clear()
        self.load_messages()
        self.refresh_chats()
        async def send():
            ok = self.text_engine and await self.text_engine.send_message(text, id=str(message_id), owner_id=str(self.owner_id))
            await self.engine.repository.update_message_status(message_id, "sent" if ok else "queued")
            self.network_event.emit({"type": "refresh"})
        self.run_net(lambda: send())

    def attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл")
        if path and self.current_chat:
            text = f"📎 {os.path.basename(path)}"
            asyncio.run(self.engine.send_message(text, self.current_chat, self.current_contact, status="local", attachment_path=path))
            self.load_messages()
            self.refresh_chats()

    def on_network_event(self, payload):
        ptype = payload.get("type")
        if ptype == "message" and self.current_chat and self.current_contact:
            sender = uuid.uuid5(uuid.NAMESPACE_DNS, payload.get("owner_id", "peer"))
            try:
                sender = uuid.UUID(payload.get("owner_id"))
            except Exception:
                pass
            asyncio.run(self.engine.receive_message(
                payload.get("text", ""), 
                self.current_chat, 
                self.current_contact, 
                sender, 
                message_id=uuid.UUID(payload["id"])
            ))
            self.load_messages()
            self.refresh_chats()
            self.status.setText("Онлайн")
            
            # Уведомление
            if self.settings.get("notify_messages", True) and self.settings.get("sound_enabled", True):
                QApplication.beep()
            
        elif ptype == "typing":
            self.status.setText("Печатает..." if payload.get("is_typing") else "Онлайн")
        elif ptype == "call_invite":
            self.handle_incoming_call()
        elif ptype == "call_accept":
            self.handle_call_accepted()
        elif ptype == "call_decline":
            self.handle_call_declined()
        elif ptype == "call_end":
            self.handle_call_ended_by_peer()
        elif ptype == "system":
            self.status.setText(payload.get("text", ""))
        elif ptype == "refresh":
            self.load_messages()
            self.refresh_chats()

    def selected_chat(self):
        items = self.chat_list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.current_chat is not None:
            self.close_current_chat()
            return
        super().keyPressEvent(event)

    def close_current_chat(self):
        if self.text_engine:
            self.run_net(lambda: self.text_engine.stop())
            self.text_engine = None
        self.current_chat = None
        self.current_contact = None
        self.chat_list.clearSelection()
        self.messages.clear()
        self.avatar.setText("💬")
        self.header.setText("Выберите чат или создайте новый контакт")
        self.chat_call_button.setEnabled(False)
        self.status.setText("Оффлайн")
        # Скрываем элементы чата
        self.toggle_chat_ui(False)

    # ---------------- Звонки: FSM как в Telegram ----------------
    def _close_call_window(self):
        if self.call_window:
            self.call_window.close()
            self.call_window = None

    def start_outgoing_call(self):
        if self.call_state is not None:
            return
        chat = self.selected_chat()
        if not chat:
            QMessageBox.information(self, "Звонок", "Сначала выберите чат")
            return
        self.call_ip = chat.contact_ip
        self.call_contact_name = chat.contact_name
        self.call_state = "outgoing"

        self.call_window = CallWindow(chat.contact_name, CallWindow.OUTGOING, parent=self)
        self.call_window.hangup_requested.connect(self.cancel_outgoing_call)
        self.call_window.finished.connect(self._on_call_window_closed)
        self.call_window.show()

        self.ringtone.start()
        self.status.setText("Исходящий звонок...")
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
            "type": "call_invite", 
            "owner_id": str(self.owner_id), 
            "name": "Друг"
        }))

    def cancel_outgoing_call(self):
        self.ringtone.stop()
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
            "type": "call_end", 
            "owner_id": str(self.owner_id)
        }))
        self._reset_call_state("Вызов отменён")

    def handle_incoming_call(self):
        if self.call_state is not None:
            self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
                "type": "call_decline", 
                "owner_id": str(self.owner_id)
            }))
            return
        chat = self.selected_chat()
        name = chat.contact_name if chat else (self.call_contact_name or "Друг")
        self.call_ip = chat.contact_ip if chat else self.call_ip
        self.call_contact_name = name
        self.call_state = "incoming"

        self.call_window = CallWindow(name, CallWindow.INCOMING, parent=self)
        self.call_window.accept_requested.connect(self.accept_incoming_call)
        self.call_window.decline_requested.connect(self.decline_incoming_call)
        self.call_window.finished.connect(self._on_call_window_closed)
        self.call_window.show()
        self.call_window.raise_()
        self.call_window.activateWindow()

        self.ringtone.start()
        self.status.setText("Входящий звонок...")
        
        if self.settings.get("notify_calls", True) and self.settings.get("sound_enabled", True):
            QApplication.beep()

    def accept_incoming_call(self):
        self.ringtone.stop()
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
            "type": "call_accept", 
            "owner_id": str(self.owner_id)
        }))
        self._enter_active_call("Звонок начался")

    def decline_incoming_call(self):
        self.ringtone.stop()
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
            "type": "call_decline", 
            "owner_id": str(self.owner_id)
        }))
        self._reset_call_state("Звонок отклонён")

    def handle_call_accepted(self):
        if self.call_state != "outgoing":
            return
        self.ringtone.stop()
        if self.call_window:
            self.call_window.set_active()
        self._enter_active_call("Звонок принят")

    def handle_call_declined(self):
        self.ringtone.stop()
        if self.call_window:
            self.call_window.set_ended("Звонок отклонён")
        self._reset_call_state("Звонок отклонён", close_window=False)

    def handle_call_ended_by_peer(self):
        self.ringtone.stop()
        if self.voice_engine and self.voice_engine.running:
            self.run_net(lambda: self.voice_engine.stop())
        if self.call_window:
            self.call_window.set_ended("Звонок завершён собеседником")
        self._reset_call_state("Звонок завершён собеседником", close_window=False)

    def _enter_active_call(self, message):
        self.call_state = "active"
        if not self.voice_engine:
            self.voice_engine = AsyncVoiceEngine()
        mic_val = self.call_window.mic_slider.value() if self.call_window else 100
        spk_val = self.call_window.speaker_slider.value() if self.call_window else 100
        self.voice_engine.set_mic_volume(mic_val)
        self.voice_engine.set_speaker_volume(spk_val)
        self.voice_engine.set_mute(self.muted)

        if self.call_window and self.call_window.mode != CallWindow.ACTIVE:
            self.call_window.set_active()
        if self.call_window:
            self.call_window.mute_toggled.connect(self._on_call_mute_toggled)
            self.call_window.mic_volume_changed.connect(lambda v: self.voice_engine and self.voice_engine.set_mic_volume(v))
            self.call_window.speaker_volume_changed.connect(lambda v: self.voice_engine and self.voice_engine.set_speaker_volume(v))
            self.call_window.hangup_requested.connect(self.end_active_call)

        self.run_net(lambda: self.voice_engine.start(
            self.call_ip,
            lambda bars: self.network_event.emit({"type": "system", "text": message}) or (self.call_window and self.call_window.set_level(bars))
        ))
        self.chat_call_button.setText("☎")
        self.chat_call_button.setToolTip("Завершить звонок")
        self.status.setText(message)

    def end_active_call(self):
        self.run_net(lambda: self.text_engine and self.text_engine.send_payload({
            "type": "call_end", 
            "owner_id": str(self.owner_id)
        }))
        if self.voice_engine and self.voice_engine.running:
            self.run_net(lambda: self.voice_engine.stop())
        if self.call_window:
            self.call_window.set_ended("Звонок завершён")
        self._reset_call_state("Звонок завершён", close_window=False)

    def _on_call_mute_toggled(self, muted: bool):
        self.muted = muted
        if self.voice_engine:
            self.voice_engine.set_mute(muted)

    def _on_call_window_closed(self, *_):
        if self.call_state == "outgoing":
            self.cancel_outgoing_call()
        elif self.call_state == "incoming":
            self.decline_incoming_call()
        elif self.call_state == "active":
            self.end_active_call()
        self.call_window = None

    def _reset_call_state(self, status_message, close_window=True):
        self.call_state = None
        self.call_ip = None
        self.muted = False
        self.chat_call_button.setText("📞")
        self.chat_call_button.setToolTip("Позвонить контакту")
        self.status.setText(status_message)
        if close_window:
            QTimer.singleShot(0, self._close_call_window)
        else:
            self.call_window = None    
            
    def closeEvent(self, event):
        self.save_settings()
        self.ringtone.stop()
        if self.text_engine:
            self.run_net(lambda: self.text_engine.stop())
        if self.voice_engine:
            self.run_net(lambda: self.voice_engine.stop())
        self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MessengerWindow()
    win.show()
    sys.exit(app.exec_())