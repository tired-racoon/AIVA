from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

class ChatBubble(QWidget):
    def __init__(self, text, is_user=False, is_loading=False, is_streaming=False, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_user = is_user
        self.is_loading = is_loading
        self.is_streaming = is_streaming
        self.loading_state = 0
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self.is_loading:
            self.loading_label = QLabel("●○○")
            self.loading_label.setStyleSheet("""
                color: #999;
                font-size: 16pt;
                padding: 8px 12px;
            """)
            layout.addWidget(self.loading_label)
        else:
            self.message_label = QLabel(self.text)
            self.message_label.setWordWrap(True)
            self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.message_label.setMaximumWidth(400)
            
            if self.is_user:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: #005c4b;
                        color: #ffffff;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)
            else:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: #1f1f1f;
                        color: #e4e4e4;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)
            
            layout.addWidget(self.message_label)
    
    def update_loading_state(self, state):
        if self.is_loading and hasattr(self, 'loading_label'):
            dots_variants = ["●○○", "●●○", "●●●", "○●●", "○○●", "○○○"]
            self.loading_label.setText(dots_variants[state % len(dots_variants)])
    
    def append_text(self, text):
        if hasattr(self, 'message_label'):
            self.text += text
            self.message_label.setText(self.text)
    
    def set_error(self, error_text):
        if hasattr(self, 'message_label'):
            self.message_label.setStyleSheet("""
                QLabel {
                    background-color: #ffcdd2;
                    color: #d32f2f;
                    padding: 12px 16px;
                    border-radius: 18px;
                    font-size: 11pt;
                }
            """)
            self.message_label.setText(error_text)

    def apply_dark_theme(self):
        if hasattr(self, 'message_label'):
            if self.is_user:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: #005c4b;
                        color: #ffffff;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)
            else:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: #1f1f1f;
                        color: #e4e4e4;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)

    def apply_light_theme(self):
        if hasattr(self, 'message_label'):
            if self.is_user:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: #DCF8C6;
                        color: #000000;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)
            else:
                self.message_label.setStyleSheet("""
                    QLabel {
                        background-color: white;
                        color: #000000;
                        padding: 12px 16px;
                        border-radius: 18px;
                        font-size: 11pt;
                    }
                """)