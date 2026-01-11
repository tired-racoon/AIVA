from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from gui.widgets.chat_display import ChatDisplay
from utils import setup_logger
import json
import re

logger = setup_logger(__name__)

class StreamingThread(QThread):
    chunk_received = pyqtSignal(str)
    response_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, assistant, message):
        super().__init__()
        self.assistant = assistant
        self.message = message
    
    def _looks_like_tool_call(self, text: str) -> bool:
        if not text.strip():
            return False
        
        json_pattern = r'\s*\{\s*["\']function["\']'
        if re.match(json_pattern, text.strip()):
            return True
        
        if text.strip().startswith('{') and 'function' in text:
            return True
        
        return False
    
    def run(self):
        try:
            from config.settings import get_settings
            
            self.assistant.conversation_history.append({
                "role": "user",
                "content": self.message
            })
            
            tools = self.assistant.tool_executor.get_tools_definition()
            max_iterations = 5
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                logger.info(f"Processing iteration {iteration}")
                
                settings = get_settings()
                provider = self.assistant._get_provider()
                
                try:
                    if settings.streaming_enabled:
                        response_content = ""
                        tool_calls = None
                        first_chunk_received = False
                        has_tool_calls = False
                        
                        try:
                            for chunk in provider.generate_stream(
                                self.assistant.conversation_history, 
                                tools=tools
                            ):
                                chunk_type = chunk.get("type", "")
                                
                                if chunk_type == "content" and chunk.get("content"):
                                    content_piece = chunk["content"]
                                    response_content += content_piece
                                    
                                    if not has_tool_calls:
                                        if not first_chunk_received:
                                            first_chunk_received = True
                                        
                                        self.chunk_received.emit(content_piece)
                                
                                elif chunk_type == "final" and chunk.get("content"):
                                    response_content = chunk["content"]
                                    if not first_chunk_received and not has_tool_calls:
                                        self.chunk_received.emit(response_content)
                                        first_chunk_received = True
                                
                                elif chunk_type == "tool_calls" and chunk.get("tool_calls"):
                                    has_tool_calls = True
                                    tool_calls = chunk["tool_calls"]
                                    if chunk.get("content"):
                                        response_content = chunk["content"]
                                
                                elif chunk_type == "error":
                                    logger.error(f"Stream error: {chunk.get('content')}")
                                    self.error_occurred.emit(chunk.get("content", "Ошибка стриминга"))
                                    return
                        except Exception as stream_iter_error:
                            logger.error(f"Stream iteration failed: {stream_iter_error}", exc_info=True)
                            self.error_occurred.emit(f"Ошибка при получении ответа: {str(stream_iter_error)}")
                            return
                        
                        response = {
                            "content": response_content if response_content else None,
                            "tool_calls": tool_calls
                        }
                    else:
                        response = provider.generate(
                            self.assistant.conversation_history,
                            tools=tools
                        )
                        if response.get("content"):
                            self.chunk_received.emit(response["content"])
                    
                    if response.get("tool_calls"):
                        logger.info(f"Tool calls detected: {response['tool_calls']}")
                        
                        tool_results = self.assistant._handle_tool_calls(response["tool_calls"])
                        
                        if response.get("content"):
                            self.assistant.conversation_history.append({
                                "role": "assistant",
                                "content": response["content"]
                            })
                        
                        self.assistant.conversation_history.append({
                            "role": "user",
                            "content": f"Результаты выполнения инструментов:\n{tool_results}\n\nТеперь дай понятный ответ пользователю на основе этих результатов."
                        })
                        
                        logger.info(f"Tool results: {tool_results}")
                        continue
                    
                    if response.get("content"):
                        self.assistant.conversation_history.append({
                            "role": "assistant",
                            "content": response["content"]
                        })
                        self.response_complete.emit()
                        return
                
                except Exception as iter_error:
                    logger.error(f"Iteration {iteration} error: {iter_error}", exc_info=True)
                    self.error_occurred.emit(f"Ошибка в итерации {iteration}: {str(iter_error)}")
                    return
            
            self.error_occurred.emit("Не удалось получить ответ после всех итераций")
            
        except Exception as e:
            logger.error(f"Streaming thread error: {e}", exc_info=True)
            self.error_occurred.emit(f"Критическая ошибка: {str(e)}")

class ChatTab(QWidget):
    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self.assistant = assistant
        self.streaming_thread = None
        self.response_thread = None
        self.current_bubble = None
        self.dark_mode = True
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 10, 10, 5)
        top_bar.addStretch()
        
        self.theme_button = QPushButton("☀️ Light Mode")
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
        self.theme_button.clicked.connect(self.toggle_theme)
        top_bar.addWidget(self.theme_button)
        
        layout.addLayout(top_bar)
        
        self.chat_display = ChatDisplay()
        layout.addWidget(self.chat_display)
        
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(10, 5, 10, 10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.update_input_style()
        self.chat_input.returnPressed.connect(self.send_message)
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
        self.send_button.clicked.connect(self.send_message)
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
    
    def update_input_style(self):
        if self.dark_mode:
            self.chat_input.setStyleSheet("""
                QLineEdit {
                    padding: 12px;
                    border: 2px solid #3d3d3d;
                    border-radius: 20px;
                    background-color: #2d2d2d;
                    font-size: 11pt;
                    color: #ffffff;
                }
                QLineEdit:focus {
                    border: 2px solid #25D366;
                }
            """)
        else:
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
    
    def apply_theme(self):
        if self.dark_mode:
            self.chat_display.apply_dark_theme()
        else:
            self.chat_display.apply_light_theme()
        self.update_input_style()
    
    def send_message(self):
        message = self.chat_input.text().strip()
        if not message:
            return
        
        self.chat_input.clear()
        self.chat_input.setEnabled(False)
        self.send_button.setEnabled(False)
        
        self.chat_display.add_message(message, is_user=True)
        
        from config.settings import settings
        
        self.chat_display.add_loading_message()
        
        if settings.streaming_enabled:
            self.current_bubble = None
            
            self.streaming_thread = StreamingThread(self.assistant, message)
            self.streaming_thread.chunk_received.connect(self.on_chunk_received)
            self.streaming_thread.response_complete.connect(self.on_response_complete)
            self.streaming_thread.error_occurred.connect(self.on_error)
            self.streaming_thread.start()
        else:
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
                self.chat_display.remove_loading_message()
                self.chat_display.add_message(response, is_user=False)
                
                self.chat_input.setEnabled(True)
                self.send_button.setEnabled(True)
                self.chat_input.setFocus()
            
            self.response_thread = ResponseThread(self.assistant, message)
            self.response_thread.response_ready.connect(on_response_ready)
            self.response_thread.start()

    def on_chunk_received(self, chunk):
        if self.current_bubble is None:
            self.chat_display.remove_loading_message()
            self.current_bubble = self.chat_display.add_streaming_message()
        
        self.current_bubble.append_text(chunk)
    

    
    def on_response_complete(self):
        self.current_bubble = None
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.chat_input.setFocus()
    
    def on_error(self, error_message):
        if self.current_bubble:
            self.current_bubble.set_error(error_message)
        else:
            self.chat_display.add_message(error_message, is_user=False)
        
        self.current_bubble = None
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.chat_input.setFocus()
    
    def clear_chat(self):
        self.chat_display.clear()
    
    def reset_conversation(self):
        self.assistant.conversation_history = []
        self.assistant._update_system_prompt()
        self.chat_display.add_message("Conversation reset", is_user=False)
    
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.theme_button.setText("☀️ Light Mode")
        else:
            self.theme_button.setText("🌙 Dark Mode")
        
        self.apply_theme()
        
        main_window = self.window()
        if hasattr(main_window, 'dark_mode'):
            main_window.dark_mode = self.dark_mode
            main_window.apply_theme()
    
    def cleanup(self):
        if self.streaming_thread and self.streaming_thread.isRunning():
            self.streaming_thread.wait(1000)
        if self.response_thread and self.response_thread.isRunning():
            self.response_thread.wait(1000)