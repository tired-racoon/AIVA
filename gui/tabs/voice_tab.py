from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QGroupBox, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from config.settings import settings
from utils import setup_logger
import threading
import time

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
        self.processing = False
        self._stop_requested = False
    
    def set_voice_input(self, enabled):
        self.voice_input_enabled = enabled
    
    def set_voice_output(self, enabled):
        self.voice_output_enabled = enabled
    
    def stop(self):
        logger.info("Voice thread stop requested")
        self._stop_requested = True
        self.running = False
        
        self.assistant.voice_handler.stop_listening_flag = True
        self.assistant.voice_handler.stop_playback_flag = True
        
        if hasattr(self.assistant.voice_handler, 'playback_process') and self.assistant.voice_handler.playback_process:
            try:
                self.assistant.voice_handler.playback_process.terminate()
                self.assistant.voice_handler.playback_process.wait(timeout=0.5)
            except:
                pass
            self.assistant.voice_handler.playback_process = None
        
        import platform
        if platform.system() == "Windows":
            try:
                if hasattr(self.assistant.voice_handler, 'pygame_initialized') and self.assistant.voice_handler.pygame_initialized:
                    import pygame
                    pygame.mixer.music.stop()
            except:
                pass
        
        logger.info("Voice thread stopped")
    
    def run(self):
        self.running = True
        self._stop_requested = False
        self.assistant.voice_handler.stop_listening_flag = False
        self.assistant.voice_handler.stop_playback_flag = False
        
        self.assistant.set_voice_mode(True)
        
        self.status_changed.emit("Listening for activation...")
        
        try:
            while self.running and not self._stop_requested:
                try:
                    if self.voice_input_enabled and self.assistant.voice_handler.listen_for_activation():
                        if not self.running or self._stop_requested:
                            break
                        
                        self.processing = True
                        self.status_changed.emit("Processing...")
                        
                        music_was_playing = self.assistant.tool_executor.tools["music"].provider.is_playing()
                        if music_was_playing:
                            self.assistant.tool_executor.tools["music"].provider.pause_music()
                        
                        self.assistant.conversation_history = []
                        self.assistant._update_system_prompt()
                        
                        user_text = self.assistant.voice_handler.last_transcribed_text
                        
                        if not self.running or self._stop_requested:
                            self.processing = False
                            break
                        
                        response = self.assistant.process_message(user_text)
                        
                        if not self.running or self._stop_requested:
                            self.processing = False
                            break
                        
                        if self.voice_output_enabled and response and response.strip():
                            self.status_changed.emit("Speaking...")
                            self.assistant.voice_handler.speak(response)
                        
                        if not self.running or self._stop_requested:
                            self.processing = False
                            break
                        
                        self.status_changed.emit("Waiting for continuation...")
                        wait_start = time.time()
                        conversation_continues = False
                        
                        while time.time() - wait_start < 3.0 and not self._stop_requested:
                            if self.assistant.voice_handler.check_for_speech(timeout=0.5):
                                logger.info("User continues conversation")
                                conversation_continues = True
                                
                                if self.assistant.voice_handler.listen_for_activation():
                                    user_text = self.assistant.voice_handler.last_transcribed_text
                                    logger.info(f"User continues: {user_text}")
                                    self.status_changed.emit("Processing...")
                                    response = self.assistant.process_message(user_text)
                                    
                                    if not self.running or self._stop_requested:
                                        break
                                    
                                    if self.voice_output_enabled and response and response.strip():
                                        self.status_changed.emit("Speaking...")
                                        self.assistant.voice_handler.speak(response)
                                    
                                    wait_start = time.time()
                            time.sleep(0.1)
                        
                        if not conversation_continues or self._stop_requested:
                            logger.info("Conversation ended, resetting history")
                            self.assistant.conversation_history = []
                            self.assistant._update_system_prompt()
                        
                        self.processing = False
                        
                        if music_was_playing:
                            self.assistant.tool_executor.tools["music"].provider.resume_music()
                        
                        if not self.running or self._stop_requested:
                            break
                        
                        self.status_changed.emit("Listening for activation...")
                        
                except Exception as e:
                    self.processing = False
                    logger.error(f"Error in voice loop: {e}", exc_info=True)
                    self.status_changed.emit(f"Error: {str(e)}")
                    time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Voice thread stopped by interrupt")
        except Exception as e:
            logger.error(f"Voice thread error: {e}", exc_info=True)
            self.status_changed.emit(f"Critical error: {str(e)}")
        finally:
            self.processing = False
            self.assistant.set_voice_mode(False)
            self.assistant.voice_handler.stop_listening_flag = False
            self.assistant.voice_handler.stop_playback_flag = False

class VoiceTab(QWidget):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.voice_thread = None
        self.is_active = False
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
        
        layout.addStretch()
        
        control_layout = QVBoxLayout()
        control_layout.setAlignment(Qt.AlignCenter)
        
        self.toggle_voice_button = QPushButton()
        self.toggle_voice_button.setFixedSize(150, 150)
        self.toggle_voice_button.clicked.connect(self.toggle_voice_assistant)
        self.update_button_style(False)
        control_layout.addWidget(self.toggle_voice_button, alignment=Qt.AlignCenter)
        
        layout.addLayout(control_layout)
        
        info_label = QLabel(f"Activation phrase: '{settings.activation_phrase}'")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
    
    def update_button_style(self, active):
        if active:
            self.toggle_voice_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    border: none;
                    border-radius: 75px;
                    font-size: 48pt;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
                QPushButton:pressed {
                    background-color: #cc0000;
                }
            """)
            self.toggle_voice_button.setText("⏹")
        else:
            self.toggle_voice_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    border: none;
                    border-radius: 75px;
                    font-size: 48pt;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #5cbf60;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            self.toggle_voice_button.setText("▶")
    
    def on_voice_input_changed(self, state):
        if self.voice_thread:
            self.voice_thread.set_voice_input(state == Qt.Checked)
    
    def on_voice_output_changed(self, state):
        if self.voice_thread:
            self.voice_thread.set_voice_output(state == Qt.Checked)
    
    def toggle_voice_assistant(self):
        if not self.is_active:
            self.start_voice_assistant()
        else:
            self.stop_voice_assistant()
    
    def start_voice_assistant(self):
        if self.voice_thread is None or not self.voice_thread.isRunning():
            self.voice_thread = VoiceThread(self.assistant)
            self.voice_thread.set_voice_input(self.voice_input_check.isChecked())
            self.voice_thread.set_voice_output(self.voice_output_check.isChecked())
            self.voice_thread.status_changed.connect(self.on_voice_status)
            self.voice_thread.start()
            
            self.is_active = True
            self.update_button_style(True)
            self.voice_status_label.setText("Active")
            self.voice_status_label.setStyleSheet("color: green;")
    
    def stop_voice_assistant(self):
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait(2000)
            
            self.is_active = False
            self.update_button_style(False)
            self.voice_status_label.setText("Inactive")
            self.voice_status_label.setStyleSheet("color: red;")

    def on_voice_status(self, status):
        self.voice_status_label.setText(status)

    def cleanup(self):
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
            self.voice_thread.wait(2000)