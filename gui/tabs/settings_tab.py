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
        
        layout.addWidget(voice_group)
        
        tts_group = QGroupBox("TTS Settings")
        tts_layout = QVBoxLayout(tts_group)
        
        tts_provider_layout = QHBoxLayout()
        tts_provider_layout.addWidget(QLabel("TTS Provider:"))
        self.tts_provider_combo = QComboBox()
        self.tts_provider_combo.addItems(["vosk", "xtts"])
        self.tts_provider_combo.setCurrentText(settings.tts_provider)
        self.tts_provider_combo.currentTextChanged.connect(self.on_tts_provider_changed)
        tts_provider_layout.addWidget(self.tts_provider_combo)
        tts_layout.addLayout(tts_provider_layout)
        
        self.vosk_settings = QWidget()
        vosk_layout = QVBoxLayout(self.vosk_settings)
        vosk_layout.setContentsMargins(0, 0, 0, 0)
        
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("Vosk Speaker ID:"))
        self.speaker_spin = QSpinBox()
        self.speaker_spin.setRange(0, 10)
        self.speaker_spin.setValue(settings.tts_speaker_id)
        speaker_layout.addWidget(self.speaker_spin)
        vosk_layout.addLayout(speaker_layout)
        
        tts_layout.addWidget(self.vosk_settings)
        
        self.xtts_settings = QWidget()
        xtts_layout = QVBoxLayout(self.xtts_settings)
        xtts_layout.setContentsMargins(0, 0, 0, 0)
        
        xtts_speaker_layout = QHBoxLayout()
        xtts_speaker_layout.addWidget(QLabel("XTTS Speaker:"))
        self.xtts_speaker_combo = QComboBox()
        xtts_speakers = ['Claribel Dervla', 'Daisy Studious', 'Gracie Wise', 'Tammie Ema', 
                        'Alison Dietlinde', 'Ana Florence', 'Annmarie Nele', 'Asya Anara', 
                        'Brenda Stern', 'Gitta Nikolina', 'Henriette Usha', 'Sofia Hellen', 
                        'Tammy Grit', 'Tanja Adelina', 'Vjollca Johnnie', 'Andrew Chipper', 
                        'Badr Odhiambo', 'Dionisio Schuyler', 'Royston Min', 'Viktor Eka', 
                        'Abrahan Mack', 'Adde Michal', 'Baldur Sanjin', 'Craig Gutsy', 
                        'Damien Black', 'Gilberto Mathias', 'Ilkin Urbano', 'Kazuhiko Atallah', 
                        'Ludvig Milivoj', 'Suad Qasim', 'Torcull Diarmuid', 'Viktor Menelaos', 
                        'Zacharie Aimilios', 'Nova Hogarth', 'Maja Ruoho', 'Uta Obando', 
                        'Lidiya Szekeres', 'Chandra MacFarland', 'Szofi Granger', 
                        'Camilla Holmström', 'Lilya Stainthorpe', 'Zofija Kendrick', 
                        'Narelle Moon', 'Barbora MacLean', 'Alexandra Hisakawa', 'Alma María', 
                        'Rosemary Okafor', 'Ige Behringer', 'Filip Traverse', 'Damjan Chapman', 
                        'Wulf Carlevaro', 'Aaron Dreschner', 'Kumar Dahl', 'Eugenio Mataracı', 
                        'Ferran Simen', 'Xavier Hayasaka', 'Luis Moray', 'Marcos Rudaski']
        self.xtts_speaker_combo.addItems(xtts_speakers)
        self.xtts_speaker_combo.setCurrentText(settings.tts_xtts_speaker)
        xtts_speaker_layout.addWidget(self.xtts_speaker_combo)
        xtts_layout.addLayout(xtts_speaker_layout)
        xtts_language_layout = QHBoxLayout()
        xtts_language_layout.addWidget(QLabel("XTTS Language:"))
        self.xtts_language_combo = QComboBox()
        self.xtts_language_combo.addItems(["ru", "en", "es", "fr", "de", "it", "pt", "pl", "tr", "zh", "ja", "ko"])
        self.xtts_language_combo.setCurrentText(settings.tts_xtts_language)
        xtts_language_layout.addWidget(self.xtts_language_combo)
        xtts_layout.addLayout(xtts_language_layout)

        tts_layout.addWidget(self.xtts_settings)

        layout.addWidget(tts_group)

        self.on_tts_provider_changed(settings.tts_provider)

        layout.addStretch()

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
    
    def on_tts_provider_changed(self, provider):
        if provider == "vosk":
            self.vosk_settings.setVisible(True)
            self.xtts_settings.setVisible(False)
        elif provider == "xtts":
            self.vosk_settings.setVisible(False)
            self.xtts_settings.setVisible(True)

    def save_settings(self):
        from config.settings import Settings
        from core.llm_provider import clear_provider_cache
        
        current_settings = Settings.get_current()
        old_provider = current_settings.llm_provider
        old_tts_provider = current_settings.tts_provider
        
        current_settings.llm_provider = self.provider_combo.currentText()
        current_settings.temperature = self.temp_spin.value()
        current_settings.max_tokens = self.tokens_spin.value()
        current_settings.streaming_enabled = self.streaming_check.isChecked()
        current_settings.activation_phrase = self.activation_input.text()
        current_settings.silence_threshold = self.silence_spin.value()
        current_settings.silence_duration = self.silence_duration_spin.value()
        
        current_settings.tts_provider = self.tts_provider_combo.currentText()
        current_settings.tts_speaker_id = self.speaker_spin.value()
        current_settings.tts_xtts_speaker = self.xtts_speaker_combo.currentText()
        current_settings.tts_xtts_language = self.xtts_language_combo.currentText()
        
        current_settings.save()
        
        if old_provider != current_settings.llm_provider:
            clear_provider_cache()
            logger.info(f"Provider changed from {old_provider} to {current_settings.llm_provider}, cache cleared")
        
        if old_tts_provider != current_settings.tts_provider:
            logger.info(f"TTS provider changed from {old_tts_provider} to {current_settings.tts_provider}, reinitializing TTS")
            main_window = self.window()
            if hasattr(main_window, 'assistant') and hasattr(main_window.assistant, 'voice_handler'):
                main_window.assistant.voice_handler._init_tts()
        
        logger.info("Settings updated:")
        logger.info(f"  LLM Provider: {current_settings.llm_provider}")
        logger.info(f"  Temperature: {current_settings.temperature}")
        logger.info(f"  Max Tokens: {current_settings.max_tokens}")
        logger.info(f"  Streaming: {current_settings.streaming_enabled}")
        logger.info(f"  Activation Phrase: {current_settings.activation_phrase}")
        logger.info(f"  Silence Threshold: {current_settings.silence_threshold}")
        logger.info(f"  Silence Duration: {current_settings.silence_duration}")
        logger.info(f"  TTS Provider: {current_settings.tts_provider}")
        logger.info(f"  TTS Speaker ID: {current_settings.tts_speaker_id}")
        logger.info(f"  XTTS Speaker: {current_settings.tts_xtts_speaker}")
        logger.info(f"  XTTS Language: {current_settings.tts_xtts_language}")
        