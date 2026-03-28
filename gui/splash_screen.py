from PyQt5.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont

class SplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("AIVA Voice Assistant")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Arial", 20, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        widget.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #3b3b3b;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        widget.setFixedSize(400, 200)
        
        pixmap = QPixmap(400, 200)
        pixmap.fill(Qt.transparent)
        self.setPixmap(pixmap)
        self.setMask(pixmap.mask())
        
        layout_widget = QWidget()
        layout_widget.setLayout(layout)
        layout_widget.setFixedSize(400, 200)
        
        self.setCentralWidget(layout_widget)
    
    def setCentralWidget(self, widget):
        widget.setParent(self)
        widget.move(0, 0)
    
    def update_progress(self, value, message=""):
        self.progress.setValue(value)
        if message:
            self.status_label.setText(message)