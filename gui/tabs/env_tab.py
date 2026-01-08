from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGroupBox, QSpinBox, QComboBox, QLineEdit,
                             QScrollArea, QGridLayout, QDoubleSpinBox, QMessageBox)
from config.settings import settings
from gui.widgets.secret_line_edit import SecretLineEdit
from utils import setup_logger

logger = setup_logger(__name__)

class EnvTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
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
        
        logger.info("Environment values loaded from .env file")

    def save_env_values(self):
        from config.settings import Settings
        from core.llm_provider import clear_provider_cache
        
        current_settings = Settings.get_current()
        
        current_settings.local_model_name = self.env_local_model.text()
        current_settings.local_device_map = self.env_local_device.text()
        current_settings.yandex_api_key = self.env_yandex_key.get_value()
        current_settings.yandex_folder_id = self.env_yandex_folder.text()
        current_settings.yandex_model = self.env_yandex_model.text()
        current_settings.openrouter_api_key = self.env_openrouter_key.get_value()
        current_settings.openrouter_model = self.env_openrouter_model.text()
        current_settings.openrouter_proxy_url = self.env_openrouter_proxy.get_value()
        current_settings.music_provider = self.env_music_provider.currentText()
        current_settings.yandex_music_token = self.env_yandex_music_token.get_value()
        current_settings.search_provider = self.env_search_provider.currentText()
        current_settings.tts_model_name = self.env_tts_model.text()
        current_settings.min_frequency = self.env_min_freq.value()
        current_settings.max_frequency = self.env_max_freq.value()
        current_settings.buffer_duration = self.env_buffer_duration.value()
        current_settings.log_level = self.env_log_level.currentText()
        current_settings.log_file = self.env_log_file.text()
        
        current_settings.save()
        clear_provider_cache()
        
        logger.info("Environment settings saved and cache cleared")
        