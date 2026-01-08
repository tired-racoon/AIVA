from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QGroupBox, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont, QTextCursor
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

class VoiceTab(QWidget):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.voice_thread = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
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
    
    def cleanup(self):
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait()