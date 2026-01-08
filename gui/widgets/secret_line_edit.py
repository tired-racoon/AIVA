from PyQt5.QtWidgets import QLineEdit

class SecretLineEdit(QLineEdit):
    def __init__(self, value="", parent=None):
        super().__init__(parent)
        self.full_value = value
        self.is_revealed = False
        self.update_display()
        self.textChanged.connect(self.on_text_changed)
    
    def update_display(self):
        if self.full_value and not self.is_revealed:
            if len(self.full_value) > 8:
                masked = self.full_value[:4] + "*" * (len(self.full_value) - 8) + self.full_value[-4:]
            else:
                masked = "*" * len(self.full_value)
            self.blockSignals(True)
            self.setText(masked)
            self.blockSignals(False)
        else:
            self.blockSignals(True)
            self.setText(self.full_value)
            self.blockSignals(False)
    
    def on_text_changed(self, text):
        if not self.is_revealed and text != self.get_masked_value():
            self.full_value = text
    
    def get_masked_value(self):
        if len(self.full_value) > 8:
            return self.full_value[:4] + "*" * (len(self.full_value) - 8) + self.full_value[-4:]
        else:
            return "*" * len(self.full_value)
    
    def reveal(self):
        self.is_revealed = True
        self.update_display()
    
    def hide_value(self):
        self.is_revealed = False
        self.update_display()
    
    def get_value(self):
        return self.full_value