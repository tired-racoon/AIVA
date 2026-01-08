from pydantic import BaseModel
from typing import Literal
from .config_manager import config_manager

class Settings(BaseModel):
    llm_provider: Literal["local", "yandex", "openrouter"] = "local"
    music_provider: Literal["yandex"] = "yandex"
    search_provider: Literal["duckduckgo"] = "duckduckgo"
    
    streaming_enabled: bool = True
    
    local_model_name: str = "Qwen/Qwen3-0.6B"
    local_device_map: str = "auto"
    
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_model: str = "gpt-oss-20b"
    
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    openrouter_proxy_url: str = ""
    
    yandex_music_token: str = ""
    
    tts_speaker_id: int = 2
    tts_model_name: str = "vosk-model-tts-ru-0.9-multi"
    
    activation_phrase: str = "айва"
    silence_threshold: int = 500
    silence_duration: float = 1.5
    min_frequency: int = 300
    max_frequency: int = 3400
    buffer_duration: float = 2.0
    
    log_level: str = "INFO"
    log_file: str = "assistant.log"
    
    max_tokens: int = 512
    temperature: float = 0.7
    
    @classmethod
    def get_current(cls):
        config_data = {}
        for key in cls.model_fields.keys():
            value = config_manager.get(key)
            if value is not None:
                config_data[key] = value
        return cls(**config_data)
    
    def save(self):
        config_manager.update(self.model_dump())

def get_settings():
    return Settings.get_current()

settings = Settings.get_current()