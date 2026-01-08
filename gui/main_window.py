from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QApplication
from PyQt5.QtCore import Qt
from gui.tabs.chat_tab import ChatTab
from gui.tabs.voice_tab import VoiceTab
from gui.tabs.settings_tab import SettingsTab
from gui.tabs.env_tab import EnvTab
from utils import setup_logger

logger = setup_logger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.dark_mode = False
        self.init_ui()
    
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
        
        self.chat_tab = ChatTab(self.assistant)
        self.voice_tab = VoiceTab(self.assistant)
        self.settings_tab = SettingsTab()
        self.env_tab = EnvTab()
        
        self.tabs.addTab(self.chat_tab, "Chat")
        self.tabs.addTab(self.voice_tab, "Voice Assistant")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.env_tab, "Environment")
        
        main_layout.addWidget(center_widget)
        main_layout.addStretch(1)
        
        self.dark_mode = self.chat_tab.dark_mode
        self.apply_theme()
    
    def apply_theme(self):
        if self.dark_mode:
            app_style = """
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
                QGroupBox {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #ffffff;
                }
                QGroupBox::title {
                    color: #ffffff;
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #ffffff;
                    background-color: transparent;
                }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px;
                }
                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                    border: 1px solid #0d7377;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 3px;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QPushButton:pressed {
                    background-color: #2d2d2d;
                }
                QTextEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QScrollArea {
                    background-color: #1e1e1e;
                    border: none;
                }
                QScrollBar:vertical {
                    background-color: #2d2d2d;
                    width: 12px;
                }
                QScrollBar::handle:vertical {
                    background-color: #555555;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #666666;
                }
            """
            self.setStyleSheet(app_style)
            self.chat_tab.apply_theme()
        else:
            app_style = """
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
                QGroupBox {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                    color: #000000;
                }
                QGroupBox::title {
                    color: #000000;
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #000000;
                    background-color: transparent;
                }
                QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 5px;
                }
                QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                    border: 1px solid #25D366;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:pressed {
                    background-color: #c0c0c0;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                }
                QCheckBox {
                    color: #000000;
                }
                QScrollArea {
                    background-color: #f0f0f0;
                    border: none;
                }
                QScrollBar:vertical {
                    background-color: #f0f0f0;
                    width: 12px;
                }
                QScrollBar::handle:vertical {
                    background-color: #cccccc;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #bbbbbb;
                }
            """
            self.setStyleSheet(app_style)
            self.chat_tab.apply_theme()
    
    def closeEvent(self, event):
        self.chat_tab.cleanup()
        self.voice_tab.cleanup()
        self.assistant.cleanup()
        event.accept()