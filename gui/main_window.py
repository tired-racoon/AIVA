import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTextEdit, QLineEdit, QLabel, 
                             QTabWidget, QGroupBox, QSpinBox, QComboBox,
                             QCheckBox, QScrollArea, QGridLayout, QDoubleSpinBox,
                             QApplication)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QTextCursor, QFont
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class VoiceThread(QThread):
    message_received = pyqtSignal(str)
    response_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.running = False
        self.voice_input_enabled = True
        self.voice_output_enabled = True
    
    def set_voice_input(self, enabled):
        self.voice_input_enabled = enabled
    
    def set_voice_output(self, enabled):
        self.voice_output_enabled = enabled
    
    def run(self):
        self.running = True
        self.status_changed.emit("Listening for activation...")
        
        try:
            while self.running:
                try:
                    if self.voice_input_enabled and self.assistant.voice_handler.listen_for_activation():
                        self.status_changed.emit("Activated! Listening...")
                        self.assistant.conversation_history = [self.assistant.system_prompt]
                        
                        audio_path = self.assistant.voice_handler.record_command()
                        
                        if not audio_path:
                            self.status_changed.emit("Recording failed. Listening for activation...")
                            continue
                        
                        user_text = self.assistant.voice_handler.transcribe(audio_path)
                        
                        if user_text and len(user_text.strip()) > 2:
                            self.message_received.emit(user_text)
                            self.status_changed.emit("Processing...")
                            
                            response = self.assistant.process_message(user_text)
                            self.response_received.emit(response)
                            
                            if self.voice_output_enabled:
                                self.status_changed.emit("Speaking...")
                                self.assistant.voice_handler.speak(response)
                        
                        self.status_changed.emit("Listening for activation...")
                        
                except Exception as e:
                    logger.error(f"Error in voice loop: {e}", exc_info=True)
                    self.status_changed.emit(f"Error: {str(e)}")
                    import time
                    time.sleep(1)
        
        except Exception as e:
            logger.error(f"Voice thread error: {e}", exc_info=True)
            self.status_changed.emit(f"Critical error: {str(e)}")
    
    def stop(self):
        self.running = False

class SecretLineEdit(QLineEdit):
    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self.full_value = value
        self.is_revealed = False
        self.update_display()
        self.textChanged.connect(self.on_text_changed)
    
    def update_display(self):
        if self.full_value and not self.is_revealed:
            if len(self.full_value) > 8:
                masked = self.full_value[:4] + "*" * (len(self.full_value) - 8) + self.full_value[-4:]
            else:
                masked = "*" * len(self.full_value)
            self.blockSignals(True)
            self.setText(masked)
            self.blockSignals(False)
        else:
            self.blockSignals(True)
            self.setText(self.full_value)
            self.blockSignals(False)
    
    def on_text_changed(self, text):
        if not self.is_revealed and text != self.get_masked_value():
            self.full_value = text
    
    def get_masked_value(self):
        if len(self.full_value) > 8:
            return self.full_value[:4] + "*" * (len(self.full_value) - 8) + self.full_value[-4:]
        else:
            return "*" * len(self.full_value)
    
    def reveal(self):
        self.is_revealed = True
        self.update_display()
    
    def hide_value(self):
        self.is_revealed = False
        self.update_display()
    
    def get_value(self):
        return self.full_value

class MainWindow(QMainWindow):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.voice_thread = None
        self.response_thread = None
        self.loading_timer = None
        self.loading_dots = 0
        self.dark_mode = False
        self.init_ui()
    
    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #3d3d3d;
                    background-color: #2d2d2d;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #3d3d3d;
                }
                QTabBar::tab:selected {
                    background-color: #3d3d3d;
                }
            """)
            
            self.chat_display.setStyleSheet("""
                QTextEdit {
                    background-color: #0d1117;
                    border: none;
                    padding: 10px;
                    color: #ffffff;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f0f0f0;
                    color: #000000;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #e0e0e0;
                    color: #000000;
                    padding: 8px 16px;
                    border: 1px solid #cccccc;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                }
            """)
            
            self.chat_display.setStyleSheet("""
                QTextEdit {
                    background-color: #e5ddd5;
                    border: none;
                    padding: 10px;
                    color: #000000;
                }
            """)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def init_ui(self):
        self.setWindowTitle("Voice Assistant")
        
        screen = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.showMaximized()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_layout.addStretch(1)
        
        center_widget = QWidget()
        center_widget.setMaximumWidth(1200)
        center_widget.setMinimumWidth(800)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        center_layout.addWidget(self.tabs)
        
        self.chat_tab = self.create_chat_tab()
        self.voice_tab = self.create_voice_tab()
        self.settings_tab = self.create_settings_tab()
        self.env_tab = self.create_env_tab()
        
        self.tabs.addTab(self.chat_tab, "Chat")
        self.tabs.addTab(self.voice_tab, "Voice Assistant")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.env_tab, "Environment")
        
        main_layout.addWidget(center_widget)
        main_layout.addStretch(1)
        
        self.apply_theme()
    
    def create_chat_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 10, 10, 5)
        
        top_bar.addStretch()
        
        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        self.theme_button.clicked.connect(self.on_theme_toggle)
        top_bar.addWidget(self.theme_button)
        
        layout.addLayout(top_bar)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        font = QFont("Segoe UI", 10)
        self.chat_display.setFont(font)
        layout.addWidget(self.chat_display)
        
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 5, 10, 10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 20px;
                background-color: white;
                font-size: 11pt;
                color: #000000;
            }
            QLineEdit:focus {
                border: 2px solid #25D366;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_chat_message)
        input_layout.addWidget(self.chat_input)
        
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: #25D366;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #20BA5A;
            }
            QPushButton:pressed {
                background-color: #1DA851;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.send_button.clicked.connect(self.send_chat_message)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(10, 0, 10, 10)
        
        self.clear_chat_button = QPushButton("Clear Chat")
        self.clear_chat_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.clear_chat_button.clicked.connect(self.clear_chat)
        buttons_layout.addWidget(self.clear_chat_button)
        
        self.reset_conversation_button = QPushButton("Reset Conversation")
        self.reset_conversation_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #ff9800;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        self.reset_conversation_button.clicked.connect(self.reset_conversation)
        buttons_layout.addWidget(self.reset_conversation_button)
        
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        return widget

    def on_theme_toggle(self):
        self.toggle_theme()
        if self.dark_mode:
            self.theme_button.setText("☀️ Light Mode")
        else:
            self.theme_button.setText("🌙 Dark Mode")
    
    def create_voice_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.voice_status_label = QLabel("Inactive")
        self.voice_status_label.setAlignment(Qt.AlignCenter)
        status_font = QFont("Arial", 14, QFont.Bold)
        self.voice_status_label.setFont(status_font)
        status_layout.addWidget(self.voice_status_label)
        
        layout.addWidget(status_group)
        
        voice_options_group = QGroupBox("Voice Options")
        voice_options_layout = QVBoxLayout(voice_options_group)
        
        self.voice_input_check = QCheckBox("Enable Voice Input (Microphone)")
        self.voice_input_check.setChecked(True)
        self.voice_input_check.stateChanged.connect(self.on_voice_input_changed)
        voice_options_layout.addWidget(self.voice_input_check)
        
        self.voice_output_check = QCheckBox("Enable Voice Output (Speaker)")
        self.voice_output_check.setChecked(True)
        self.voice_output_check.stateChanged.connect(self.on_voice_output_changed)
        voice_options_layout.addWidget(self.voice_output_check)
        
        layout.addWidget(voice_options_group)
        
        self.voice_display = QTextEdit()
        self.voice_display.setReadOnly(True)
        font = QFont("Consolas", 10)
        self.voice_display.setFont(font)
        layout.addWidget(self.voice_display)
        
        control_layout = QHBoxLayout()
        
        self.start_voice_button = QPushButton("Start Voice Assistant")
        self.start_voice_button.clicked.connect(self.start_voice_assistant)
        control_layout.addWidget(self.start_voice_button)
        
        self.stop_voice_button = QPushButton("Stop Voice Assistant")
        self.stop_voice_button.clicked.connect(self.stop_voice_assistant)
        self.stop_voice_button.setEnabled(False)
        control_layout.addWidget(self.stop_voice_button)
        
        layout.addLayout(control_layout)
        
        info_label = QLabel(f"Activation phrase: '{settings.activation_phrase}'")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        return widget
    
    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        llm_group = QGroupBox("LLM Settings")
        llm_layout = QVBoxLayout(llm_group)
        
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["local", "yandex", "openrouter"])
        self.provider_combo.setCurrentText(settings.llm_provider)
        provider_layout.addWidget(self.provider_combo)
        llm_layout.addLayout(provider_layout)
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(settings.temperature)
        temp_layout.addWidget(self.temp_spin)
        llm_layout.addLayout(temp_layout)
        
        tokens_layout = QHBoxLayout()
        tokens_layout.addWidget(QLabel("Max Tokens:"))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(64, 4096)
        self.tokens_spin.setValue(settings.max_tokens)
        tokens_layout.addWidget(self.tokens_spin)
        llm_layout.addLayout(tokens_layout)
        
        self.streaming_check = QCheckBox("Enable Streaming")
        self.streaming_check.setChecked(settings.streaming_enabled)
        llm_layout.addWidget(self.streaming_check)
        
        layout.addWidget(llm_group)
        
        voice_group = QGroupBox("Voice Settings")
        voice_layout = QVBoxLayout(voice_group)
        
        activation_layout = QHBoxLayout()
        activation_layout.addWidget(QLabel("Activation Phrase:"))
        self.activation_input = QLineEdit(settings.activation_phrase)
        activation_layout.addWidget(self.activation_input)
        voice_layout.addLayout(activation_layout)
        
        silence_layout = QHBoxLayout()
        silence_layout.addWidget(QLabel("Silence Threshold:"))
        self.silence_spin = QSpinBox()
        self.silence_spin.setRange(100, 2000)
        self.silence_spin.setValue(settings.silence_threshold)
        silence_layout.addWidget(self.silence_spin)
        voice_layout.addLayout(silence_layout)
        
        silence_duration_layout = QHBoxLayout()
        silence_duration_layout.addWidget(QLabel("Silence Duration (s):"))
        self.silence_duration_spin = QDoubleSpinBox()
        self.silence_duration_spin.setRange(0.5, 5.0)
        self.silence_duration_spin.setSingleStep(0.1)
        self.silence_duration_spin.setValue(settings.silence_duration)
        silence_duration_layout.addWidget(self.silence_duration_spin)
        voice_layout.addLayout(silence_duration_layout)
        
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("TTS Speaker ID:"))
        self.speaker_spin = QSpinBox()
        self.speaker_spin.setRange(0, 10)
        self.speaker_spin.setValue(settings.tts_speaker_id)
        speaker_layout.addWidget(self.speaker_spin)
        voice_layout.addLayout(speaker_layout)
        
        layout.addWidget(voice_group)
        
        layout.addStretch()
        
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        return widget
    
    def create_env_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        llm_group = QGroupBox("LLM Provider Settings")
        llm_layout = QGridLayout(llm_group)
        
        row = 0
        
        llm_layout.addWidget(QLabel("Local Model Name:"), row, 0)
        self.env_local_model = QLineEdit(settings.local_model_name)
        llm_layout.addWidget(self.env_local_model, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("Local Device Map:"), row, 0)
        self.env_local_device = QLineEdit(settings.local_device_map)
        llm_layout.addWidget(self.env_local_device, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("Yandex API Key:"), row, 0)
        self.env_yandex_key = SecretLineEdit(settings.yandex_api_key)
        key_layout = QHBoxLayout()
        key_layout.addWidget(self.env_yandex_key)
        self.yandex_key_reveal = QPushButton("👁")
        self.yandex_key_reveal.setMaximumWidth(40)
        self.yandex_key_reveal.pressed.connect(lambda: self.env_yandex_key.reveal())
        self.yandex_key_reveal.released.connect(lambda: self.env_yandex_key.hide_value())
        key_layout.addWidget(self.yandex_key_reveal)
        llm_layout.addLayout(key_layout, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("Yandex Folder ID:"), row, 0)
        self.env_yandex_folder = QLineEdit(settings.yandex_folder_id)
        llm_layout.addWidget(self.env_yandex_folder, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("Yandex Model:"), row, 0)
        self.env_yandex_model = QLineEdit(settings.yandex_model)
        llm_layout.addWidget(self.env_yandex_model, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("OpenRouter API Key:"), row, 0)
        self.env_openrouter_key = SecretLineEdit(settings.openrouter_api_key)
        or_key_layout = QHBoxLayout()
        or_key_layout.addWidget(self.env_openrouter_key)
        self.openrouter_key_reveal = QPushButton("👁")
        self.openrouter_key_reveal.setMaximumWidth(40)
        self.openrouter_key_reveal.pressed.connect(lambda: self.env_openrouter_key.reveal())
        self.openrouter_key_reveal.released.connect(lambda: self.env_openrouter_key.hide_value())
        or_key_layout.addWidget(self.openrouter_key_reveal)
        llm_layout.addLayout(or_key_layout, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("OpenRouter Model:"), row, 0)
        self.env_openrouter_model = QLineEdit(settings.openrouter_model)
        llm_layout.addWidget(self.env_openrouter_model, row, 1)
        row += 1
        
        llm_layout.addWidget(QLabel("OpenRouter Proxy URL:"), row, 0)
        self.env_openrouter_proxy = SecretLineEdit(settings.openrouter_proxy_url)
        proxy_layout = QHBoxLayout()
        proxy_layout.addWidget(self.env_openrouter_proxy)
        self.openrouter_proxy_reveal = QPushButton("👁")
        self.openrouter_proxy_reveal.setMaximumWidth(40)
        self.openrouter_proxy_reveal.pressed.connect(lambda: self.env_openrouter_proxy.reveal())
        self.openrouter_proxy_reveal.released.connect(lambda: self.env_openrouter_proxy.hide_value())
        proxy_layout.addWidget(self.openrouter_proxy_reveal)
        llm_layout.addLayout(proxy_layout, row, 1)
        row += 1
        
        layout.addWidget(llm_group)
        
        services_group = QGroupBox("Services Settings")
        services_layout = QGridLayout(services_group)
        
        row = 0
        
        services_layout.addWidget(QLabel("Music Provider:"), row, 0)
        self.env_music_provider = QComboBox()
        self.env_music_provider.addItems(["yandex"])
        self.env_music_provider.setCurrentText(settings.music_provider)
        services_layout.addWidget(self.env_music_provider, row, 1)
        row += 1
        
        services_layout.addWidget(QLabel("Yandex Music Token:"), row, 0)
        self.env_yandex_music_token = SecretLineEdit(settings.yandex_music_token)
        music_layout = QHBoxLayout()
        music_layout.addWidget(self.env_yandex_music_token)
        self.yandex_music_reveal = QPushButton("👁")
        self.yandex_music_reveal.setMaximumWidth(40)
        self.yandex_music_reveal.pressed.connect(lambda: self.env_yandex_music_token.reveal())
        self.yandex_music_reveal.released.connect(lambda: self.env_yandex_music_token.hide_value())
        music_layout.addWidget(self.yandex_music_reveal)
        services_layout.addLayout(music_layout, row, 1)
        row += 1
        
        services_layout.addWidget(QLabel("Search Provider:"), row, 0)
        self.env_search_provider = QComboBox()
        self.env_search_provider.addItems(["duckduckgo"])
        self.env_search_provider.setCurrentText(settings.search_provider)
        services_layout.addWidget(self.env_search_provider, row, 1)
        row += 1
        
        layout.addWidget(services_group)
        
        voice_env_group = QGroupBox("Voice Settings")
        voice_env_layout = QGridLayout(voice_env_group)
        
        row = 0
        
        voice_env_layout.addWidget(QLabel("TTS Model Name:"), row, 0)
        self.env_tts_model = QLineEdit(settings.tts_model_name)
        voice_env_layout.addWidget(self.env_tts_model, row, 1)
        row += 1
        
        voice_env_layout.addWidget(QLabel("Min Frequency (Hz):"), row, 0)
        self.env_min_freq = QSpinBox()
        self.env_min_freq.setRange(0, 10000)
        self.env_min_freq.setValue(settings.min_frequency)
        voice_env_layout.addWidget(self.env_min_freq, row, 1)
        row += 1
        
        voice_env_layout.addWidget(QLabel("Max Frequency (Hz):"), row, 0)
        self.env_max_freq = QSpinBox()
        self.env_max_freq.setRange(0, 10000)
        self.env_max_freq.setValue(settings.max_frequency)
        voice_env_layout.addWidget(self.env_max_freq, row, 1)
        row += 1
        
        voice_env_layout.addWidget(QLabel("Buffer Duration (s):"), row, 0)
        self.env_buffer_duration = QDoubleSpinBox()
        self.env_buffer_duration.setRange(0.5, 10.0)
        self.env_buffer_duration.setSingleStep(0.1)
        self.env_buffer_duration.setValue(settings.buffer_duration)
        voice_env_layout.addWidget(self.env_buffer_duration, row, 1)
        row += 1
        
        layout.addWidget(voice_env_group)
        
        logging_group = QGroupBox("Logging Settings")
        logging_layout = QGridLayout(logging_group)
        
        logging_layout.addWidget(QLabel("Log Level:"), 0, 0)
        self.env_log_level = QComboBox()
        self.env_log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.env_log_level.setCurrentText(settings.log_level)
        logging_layout.addWidget(self.env_log_level, 0, 1)
        
        logging_layout.addWidget(QLabel("Log File:"), 1, 0)
        self.env_log_file = QLineEdit(settings.log_file)
        logging_layout.addWidget(self.env_log_file, 1, 1)
        
        layout.addWidget(logging_group)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        
        load_button = QPushButton("Load from .env")
        load_button.clicked.connect(self.load_env_values)
        button_layout.addWidget(load_button)
        
        save_env_button = QPushButton("Save to .env")
        save_env_button.clicked.connect(self.save_env_values)
        button_layout.addWidget(save_env_button)
        
        main_layout.addLayout(button_layout)
        
        return widget
    
    def send_chat_message(self):
        message = self.chat_input.text().strip()
        if not message:
            return
        
        self.chat_input.clear()
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self.append_to_chat(message, is_user=True)
        
        self.append_to_chat("", is_loading=True)
        self.start_loading_animation()
        
        from PyQt5.QtCore import QThread, pyqtSignal
        
        class ResponseThread(QThread):
            response_ready = pyqtSignal(str, bool)
            
            def __init__(self, assistant, message):
                super().__init__()
                self.assistant = assistant
                self.message = message
            
            def run(self):
                try:
                    response = self.assistant.process_message(self.message)
                    if response and response.strip():
                        self.response_ready.emit(response, False)
                    else:
                        self.response_ready.emit("(пустой ответ)", True)
                except Exception as e:
                    logger.error(f"Chat error: {e}", exc_info=True)
                    self.response_ready.emit(f"Ошибка: {str(e)}", True)
        
        def on_response_ready(response, is_error):
            self.stop_loading_animation()
            self.remove_loading_message()
            self.append_to_chat(response, is_user=False)
            
            self.chat_input.setEnabled(True)
            self.send_button.setEnabled(True)
            self.chat_input.setFocus()
        
        self.response_thread = ResponseThread(self.assistant, message)
        self.response_thread.response_ready.connect(on_response_ready)
        self.response_thread.start()
    
    def append_to_chat(self, text, is_user=False, is_loading=False):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        if is_loading:
            html = '''
            <div id="loading-msg" style="margin: 15px 20px; text-align: left; clear: both;">
                <div style="display: inline-block; max-width: 60%; background-color: white; 
                            color: #303030; padding: 12px 16px; border-radius: 18px;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <span id="loading-dots" style="color: #666; font-size: 14pt;">●●●</span>
                </div>
            </div>
            '''
        elif is_user:
            escaped_text = text.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            html = f'''
            <div style="margin: 15px 20px; text-align: right; clear: both;">
                <div style="display: inline-block; max-width: 60%; background-color: #DCF8C6; 
                            color: #000000; padding: 12px 16px; border-radius: 18px 18px 4px 18px;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.1); text-align: left;">
                    {escaped_text}
                </div>
            </div>
            '''
        else:
            escaped_text = text.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            html = f'''
            <div style="margin: 15px 20px; text-align: left; clear: both;">
                <div style="display: inline-block; max-width: 60%; background-color: white; 
                            color: #000000; padding: 12px 16px; border-radius: 18px 18px 18px 4px;
                            box-shadow: 0 1px 2px rgba(0,0,0,0.1); text-align: left;">
                    {escaped_text}
                </div>
            </div>
            '''
        
        cursor.insertHtml(html)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def remove_loading_message(self):
        html = self.chat_display.toHtml()
        
        import re
        html = re.sub(r'<div id="loading-msg".*?</div>\s*</div>', '', html, flags=re.DOTALL)
        
        self.chat_display.setHtml(html)
        self.chat_display.ensureCursorVisible()
    
    def clear_chat(self):
        self.chat_display.clear()
    
    def reset_conversation(self):
        self.assistant.conversation_history = [self.assistant.system_prompt]
        self.append_to_chat("Conversation reset", "#666666")
    
    def on_voice_input_changed(self, state):
        if self.voice_thread:
            self.voice_thread.set_voice_input(state == Qt.Checked)
    
    def on_voice_output_changed(self, state):
        if self.voice_thread:
            self.voice_thread.set_voice_output(state == Qt.Checked)
    
    def start_voice_assistant(self):
        if self.voice_thread is None or not self.voice_thread.isRunning():
            self.voice_thread = VoiceThread(self.assistant)
            self.voice_thread.set_voice_input(self.voice_input_check.isChecked())
            self.voice_thread.set_voice_output(self.voice_output_check.isChecked())
            self.voice_thread.message_received.connect(self.on_voice_message)
            self.voice_thread.response_received.connect(self.on_voice_response)
            self.voice_thread.status_changed.connect(self.on_voice_status)
            self.voice_thread.start()
            
            self.start_voice_button.setEnabled(False)
            self.stop_voice_button.setEnabled(True)
            self.voice_status_label.setText("Active")
            self.voice_status_label.setStyleSheet("color: green;")
    
    def stop_voice_assistant(self):
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait()
            
            self.start_voice_button.setEnabled(True)
            self.stop_voice_button.setEnabled(False)
            self.voice_status_label.setText("Inactive")
            self.voice_status_label.setStyleSheet("color: red;")
    
    def on_voice_message(self, message):
        cursor = self.voice_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(f'<p style="color: #0066cc;"><b>User:</b> {message}</p>')
        self.voice_display.setTextCursor(cursor)
        self.voice_display.ensureCursorVisible()
    
    def on_voice_response(self, response):
        cursor = self.voice_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(f'<p style="color: #009900;"><b>Assistant:</b> {response}</p>')
        self.voice_display.setTextCursor(cursor)
        self.voice_display.ensureCursorVisible()
    
    def on_voice_status(self, status):
        self.voice_status_label.setText(status)
    
    def save_settings(self):
        settings.llm_provider = self.provider_combo.currentText()
        settings.temperature = self.temp_spin.value()
        settings.max_tokens = self.tokens_spin.value()
        settings.streaming_enabled = self.streaming_check.isChecked()
        settings.activation_phrase = self.activation_input.text()
        settings.silence_threshold = self.silence_spin.value()
        settings.silence_duration = self.silence_duration_spin.value()
        settings.tts_speaker_id = self.speaker_spin.value()
        
        settings.save()
        
        self.append_to_chat("Settings saved successfully!", "#00cc00")

    def load_env_values(self):
        from config.settings import Settings
        new_settings = Settings()
        
        self.env_local_model.setText(new_settings.local_model_name)
        self.env_local_device.setText(new_settings.local_device_map)
        self.env_yandex_key.full_value = new_settings.yandex_api_key
        self.env_yandex_key.update_display()
        self.env_yandex_folder.setText(new_settings.yandex_folder_id)
        self.env_yandex_model.setText(new_settings.yandex_model)
        self.env_openrouter_key.full_value = new_settings.openrouter_api_key
        self.env_openrouter_key.update_display()
        self.env_openrouter_model.setText(new_settings.openrouter_model)
        self.env_openrouter_proxy.full_value = new_settings.openrouter_proxy_url
        self.env_openrouter_proxy.update_display()
        self.env_music_provider.setCurrentText(new_settings.music_provider)
        self.env_yandex_music_token.full_value = new_settings.yandex_music_token
        self.env_yandex_music_token.update_display()
        self.env_search_provider.setCurrentText(new_settings.search_provider)
        self.env_tts_model.setText(new_settings.tts_model_name)
        self.env_min_freq.setValue(new_settings.min_frequency)
        self.env_max_freq.setValue(new_settings.max_frequency)
        self.env_buffer_duration.setValue(new_settings.buffer_duration)
        self.env_log_level.setCurrentText(new_settings.log_level)
        self.env_log_file.setText(new_settings.log_file)
        
        self.provider_combo.setCurrentText(new_settings.llm_provider)
        self.temp_spin.setValue(new_settings.temperature)
        self.tokens_spin.setValue(new_settings.max_tokens)
        self.streaming_check.setChecked(new_settings.streaming_enabled)
        self.activation_input.setText(new_settings.activation_phrase)
        self.silence_spin.setValue(new_settings.silence_threshold)
        self.silence_duration_spin.setValue(new_settings.silence_duration)
        self.speaker_spin.setValue(new_settings.tts_speaker_id)
    
    def save_env_values(self):
        settings.local_model_name = self.env_local_model.text()
        settings.local_device_map = self.env_local_device.text()
        settings.yandex_api_key = self.env_yandex_key.get_value()
        settings.yandex_folder_id = self.env_yandex_folder.text()
        settings.yandex_model = self.env_yandex_model.text()
        settings.openrouter_api_key = self.env_openrouter_key.get_value()
        settings.openrouter_model = self.env_openrouter_model.text()
        settings.openrouter_proxy_url = self.env_openrouter_proxy.get_value()
        settings.music_provider = self.env_music_provider.currentText()
        settings.yandex_music_token = self.env_yandex_music_token.get_value()
        settings.search_provider = self.env_search_provider.currentText()
        settings.tts_model_name = self.env_tts_model.text()
        settings.min_frequency = self.env_min_freq.value()
        settings.max_frequency = self.env_max_freq.value()
        settings.buffer_duration = self.env_buffer_duration.value()
        settings.log_level = self.env_log_level.currentText()
        settings.log_file = self.env_log_file.text()
        
        settings.save()
        
        self.append_to_chat("Environment saved successfully!", "#00cc00")
    
    def _build_env_content(self):
        return f"""LLM_PROVIDER={self.provider_combo.currentText()}
MUSIC_PROVIDER={self.env_music_provider.currentText()}
SEARCH_PROVIDER={self.env_search_provider.currentText()}
STREAMING_ENABLED={str(self.streaming_check.isChecked()).lower()}

LOCAL_MODEL_NAME={self.env_local_model.text()}
LOCAL_DEVICE_MAP={self.env_local_device.text()}

YANDEX_API_KEY={self.env_yandex_key.get_value()}
YANDEX_FOLDER_ID={self.env_yandex_folder.text()}
YANDEX_MODEL={self.env_yandex_model.text()}
OPENROUTER_API_KEY={self.env_openrouter_key.get_value()}
OPENROUTER_MODEL={self.env_openrouter_model.text()}
OPENROUTER_PROXY_URL={self.env_openrouter_proxy.get_value()}
YANDEX_MUSIC_TOKEN={self.env_yandex_music_token.get_value()}
TTS_SPEAKER_ID={self.speaker_spin.value()}
TTS_MODEL_NAME={self.env_tts_model.text()}
ACTIVATION_PHRASE={self.activation_input.text()}
SILENCE_THRESHOLD={self.silence_spin.value()}
SILENCE_DURATION={self.silence_duration_spin.value()}
MIN_FREQUENCY={self.env_min_freq.value()}
MAX_FREQUENCY={self.env_max_freq.value()}
BUFFER_DURATION={self.env_buffer_duration.value()}
LOG_LEVEL={self.env_log_level.currentText()}
LOG_FILE={self.env_log_file.text()}
MAX_TOKENS={self.tokens_spin.value()}
TEMPERATURE={self.temp_spin.value()}
"""
    
    def closeEvent(self, event):
        if self.loading_timer:
            self.loading_timer.stop()
        
        if self.response_thread and self.response_thread.isRunning():
            self.response_thread.wait(1000)
        
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait()
        
        self.assistant.cleanup()
        event.accept()

    def start_loading_animation(self):
        self.loading_dots = 0
        if self.loading_timer:
            self.loading_timer.stop()
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_timer.start(300)

    def update_loading_animation(self):
        dots_variants = ["●○○", "●●○", "●●●", "○●●", "○○●", "○○○"]
        self.loading_dots = (self.loading_dots + 1) % len(dots_variants)
        current_dots = dots_variants[self.loading_dots]
        
        html = self.chat_display.toHtml()
        
        import re
        pattern = r'(<span id="loading-dots"[^>]*>)[^<]*(</span>)'
        replacement = r'\g<1>' + current_dots + r'\g<2>'
        html = re.sub(pattern, replacement, html)
        
        cursor_position = self.chat_display.textCursor().position()
        self.chat_display.setHtml(html)
        
        cursor = self.chat_display.textCursor()
        cursor.setPosition(min(cursor_position, len(self.chat_display.toPlainText())))
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def stop_loading_animation(self):
        if self.loading_timer:
            self.loading_timer.stop()
            self.loading_timer = None