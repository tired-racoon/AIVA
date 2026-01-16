import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from gui import MainWindow
from gui.splash_screen import SplashScreen
from core import Assistant
from utils import setup_logger

logger = setup_logger(__name__)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    def init_step_1():
        splash.update_progress(20, "Loading configuration...")
        QTimer.singleShot(100, init_step_2)
    
    def init_step_2():
        splash.update_progress(40, "Initializing LLM provider...")
        QTimer.singleShot(100, init_step_3)
    
    def init_step_3():
        global assistant
        assistant = Assistant()
        splash.update_progress(80, "Setting up interface...")
        QTimer.singleShot(100, init_step_4)
    
    def init_step_4():
        global window
        window = MainWindow(assistant)
        splash.update_progress(100, "Ready!")
        QTimer.singleShot(500, show_main_window)
    
    def show_main_window():
        window.show()
        splash.finish(window)
    
    QTimer.singleShot(100, init_step_1)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()