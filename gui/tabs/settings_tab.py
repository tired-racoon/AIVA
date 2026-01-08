from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QGroupBox, QSpinBox, QComboBox, QCheckBox,
                             QLineEdit, QDoubleSpinBox, QMessageBox)
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
    
    def save_settings(self):
        from config.settings import Settings
        from core.llm_provider import clear_provider_cache
        
        current_settings = Settings.get_current()
        old_provider = current_settings.llm_provider
        
        current_settings.llm_provider = self.provider_combo.currentText()
        current_settings.temperature = self.temp_spin.value()
        current_settings.max_tokens = self.tokens_spin.value()
        current_settings.streaming_enabled = self.streaming_check.isChecked()
        current_settings.activation_phrase = self.activation_input.text()
        current_settings.silence_threshold = self.silence_spin.value()
        current_settings.silence_duration = self.silence_duration_spin.value()
        current_settings.tts_speaker_id = self.speaker_spin.value()
        
        current_settings.save()
        
        if old_provider != current_settings.llm_provider:
            clear_provider_cache()
            logger.info(f"Provider changed from {old_provider} to {current_settings.llm_provider}, cache cleared")
        
        logger.info("Settings updated:")
        logger.info(f"  LLM Provider: {current_settings.llm_provider}")
        logger.info(f"  Temperature: {current_settings.temperature}")
        logger.info(f"  Max Tokens: {current_settings.max_tokens}")
        logger.info(f"  Streaming: {current_settings.streaming_enabled}")
        logger.info(f"  Activation Phrase: {current_settings.activation_phrase}")
        logger.info(f"  Silence Threshold: {current_settings.silence_threshold}")
        logger.info(f"  Silence Duration: {current_settings.silence_duration}")
        logger.info(f"  TTS Speaker ID: {current_settings.tts_speaker_id}")
        