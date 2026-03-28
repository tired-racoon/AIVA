import platform
from typing import Dict, Any
from .base import BaseTool
from utils import setup_logger
import pythoncom

logger = setup_logger(__name__)

class BaseOSController:
    def set_volume(self, level: int) -> str:
        raise NotImplementedError
    
    def mute(self) -> str:
        raise NotImplementedError
    
    def unmute(self) -> str:
        raise NotImplementedError
    
    def set_brightness(self, level: int) -> str:
        raise NotImplementedError

class WindowsOSController(BaseOSController):
    def __init__(self):
        try:
            from pycaw.pycaw import AudioUtilities
            import wmi
            self.AudioUtilities = AudioUtilities
            self.wmi = wmi
            logger.info("Windows OS controller initialized")
        except ImportError as e:
            logger.error(f"Failed to import Windows dependencies: {e}")
            raise
    
    def set_volume(self, level: int) -> str:
        pythoncom.CoInitialize()
        volume_level = level / 100.0
        device = self.AudioUtilities.GetSpeakers()
        device.EndpointVolume.SetMasterVolumeLevelScalar(volume_level, None)
        pythoncom.CoUninitialize()
        return f"Громкость установлена на {level}%"
    
    def mute(self) -> str:
        pythoncom.CoInitialize()
        device = self.AudioUtilities.GetSpeakers()
        device.EndpointVolume.SetMute(1, None)
        pythoncom.CoUninitialize()
        return "Звук выключен"
    
    def unmute(self) -> str:
        pythoncom.CoInitialize()
        device = self.AudioUtilities.GetSpeakers()
        device.EndpointVolume.SetMute(0, None)
        pythoncom.CoUninitialize()
        return "Звук включен"
    
    def set_brightness(self, level: int) -> str:
        c = self.wmi.WMI(namespace='wmi')
        methods = c.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(level, 0)
        return f"Яркость установлена на {level}%"

class LinuxOSController(BaseOSController):
    def __init__(self):
        import subprocess
        self.subprocess = subprocess
        logger.info("Linux OS controller initialized")
    
    def _run_command(self, command: list) -> tuple:
        try:
            result = self.subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except self.subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def set_volume(self, level: int) -> str:
        success, output = self._run_command(['amixer', 'set', 'Master', f'{level}%'])
        if success:
            return f"Громкость установлена на {level}%"
        return f"Ошибка установки громкости: {output}"
    
    def mute(self) -> str:
        success, output = self._run_command(['amixer', 'set', 'Master', 'mute'])
        if success:
            return "Звук выключен"
        return f"Ошибка выключения звука: {output}"
    
    def unmute(self) -> str:
        success, output = self._run_command(['amixer', 'set', 'Master', 'unmute'])
        if success:
            return "Звук включен"
        return f"Ошибка включения звука: {output}"
    
    def set_brightness(self, level: int) -> str:
        try:
            brightness_path = '/sys/class/backlight/intel_backlight/brightness'
            max_brightness_path = '/sys/class/backlight/intel_backlight/max_brightness'
            
            with open(max_brightness_path, 'r') as f:
                max_brightness = int(f.read().strip())
            
            new_brightness = int((level / 100.0) * max_brightness)
            
            success, output = self._run_command([
                'sudo', 'tee', brightness_path
            ])
            
            if success:
                return f"Яркость установлена на {level}%"
            return f"Ошибка установки яркости: {output}"
        except Exception as e:
            return f"Ошибка доступа к яркости: {str(e)}"

class MacOSController(BaseOSController):
    def __init__(self):
        import subprocess
        self.subprocess = subprocess
        logger.info("macOS controller initialized")
    
    def _run_command(self, command: list) -> tuple:
        try:
            result = self.subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            return True, result.stdout
        except self.subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def set_volume(self, level: int) -> str:
        success, output = self._run_command([
            'osascript', '-e', f'set volume output volume {level}'
        ])
        if success:
            return f"Громкость установлена на {level}%"
        return f"Ошибка установки громкости: {output}"
    
    def mute(self) -> str:
        success, output = self._run_command([
            'osascript', '-e', 'set volume with output muted'
        ])
        if success:
            return "Звук выключен"
        return f"Ошибка выключения звука: {output}"
    
    def unmute(self) -> str:
        success, output = self._run_command([
            'osascript', '-e', 'set volume without output muted'
        ])
        if success:
            return "Звук включен"
        return f"Ошибка включения звука: {output}"
    
    def set_brightness(self, level: int) -> str:
        brightness_value = level / 100.0
        success, output = self._run_command([
            'osascript', '-e', 
            f'tell application "System Events" to set brightness of display to {brightness_value}'
        ])
        if success:
            return f"Яркость установлена на {level}%"
        return f"Ошибка установки яркости: {output}"

class OSControlTool(BaseTool):
    def __init__(self):
        system = platform.system()
        logger.info(f"Detected OS: {system}")
        
        try:
            if system == "Windows":
                self.controller = WindowsOSController()
            elif system == "Linux":
                self.controller = LinuxOSController()
            elif system == "Darwin":
                self.controller = MacOSController()
            else:
                logger.warning(f"Unsupported OS: {system}")
                self.controller = None
        except Exception as e:
            logger.error(f"Failed to initialize OS controller: {e}")
            self.controller = None
    
    def execute(self, action: str, params: Dict[str, Any]) -> str:
        if not self.controller:
            return "OS control not available on this system"
        
        try:
            if action == "set_volume":
                level = params.get("level", 50)
                return self.controller.set_volume(level)
            
            elif action == "mute":
                return self.controller.mute()
            
            elif action == "unmute":
                return self.controller.unmute()
            
            elif action == "set_brightness":
                level = params.get("level", 50)
                return self.controller.set_brightness(level)
            
            else:
                return f"Unknown action: {action}"
        
        except Exception as e:
            logger.error(f"Error executing OS control: {e}")
            return f"Ошибка: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "os_control",
            "description": "Control system settings like volume and brightness",
            "actions": {
                "set_volume": {"level": "int (0-100)"},
                "mute": {},
                "unmute": {},
                "set_brightness": {"level": "int (0-100)"}
            }
        }