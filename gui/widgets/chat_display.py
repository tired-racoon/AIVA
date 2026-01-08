from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from .chat_bubble import ChatBubble

class ChatDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = []
        self.loading_bubble = None
        self.loading_timer = None
        self.loading_state = 0
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0d1117;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)
    
    def add_message(self, text, is_user=False):
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        bubble = ChatBubble(text, is_user=is_user)
        
        if is_user:
            container_layout.addStretch()
            container_layout.addWidget(bubble)
        else:
            container_layout.addWidget(bubble)
            container_layout.addStretch()
        
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, container)
        self.messages.append(container)
        
        self.scroll_to_bottom()
    
    def add_streaming_message(self):
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        bubble = ChatBubble("", is_user=False, is_streaming=True)
        container_layout.addWidget(bubble)
        container_layout.addStretch()
        
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, container)
        self.messages.append(container)
        
        self.scroll_to_bottom()
        return bubble
    
    def add_loading_message(self):
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.loading_bubble = ChatBubble("", is_user=False, is_loading=True)
        container_layout.addWidget(self.loading_bubble)
        container_layout.addStretch()
        
        self.scroll_layout.insertWidget(self.scroll_layout.count() - 1, container)
        self.loading_container = container
        
        self.start_loading_animation()
        self.scroll_to_bottom()
    
    def remove_loading_message(self):
        self.stop_loading_animation()
        if hasattr(self, 'loading_container') and self.loading_container:
            self.scroll_layout.removeWidget(self.loading_container)
            self.loading_container.deleteLater()
            self.loading_container = None
            self.loading_bubble = None
    
    def start_loading_animation(self):
        self.loading_state = 0
        if self.loading_timer:
            self.loading_timer.stop()
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_timer.start(300)
    
    def update_loading_animation(self):
        if self.loading_bubble:
            self.loading_state = (self.loading_state + 1) % 6
            self.loading_bubble.update_loading_state(self.loading_state)
    
    def stop_loading_animation(self):
        if self.loading_timer:
            self.loading_timer.stop()
            self.loading_timer = None
    
    def clear(self):
        for msg in self.messages:
            self.scroll_layout.removeWidget(msg)
            msg.deleteLater()
        self.messages.clear()
        if self.loading_bubble:
            self.remove_loading_message()
    
    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
    
    def apply_dark_theme(self):
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #0d1117;
            }
            QScrollBar:vertical {
                background-color: #0d1117;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #3d3d3d;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4d4d4d;
            }
        """)
        
        for msg_container in self.messages:
            for child in msg_container.findChildren(ChatBubble):
                child.apply_dark_theme()

    def apply_light_theme(self):
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #e5ddd5;
            }
            QScrollBar:vertical {
                background-color: #e5ddd5;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #cccccc;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #bbbbbb;
            }
        """)
        
        for msg_container in self.messages:
            for child in msg_container.findChildren(ChatBubble):
                child.apply_light_theme()