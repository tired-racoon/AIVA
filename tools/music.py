from typing import Dict, Any
from .base import BaseTool, BaseMusicProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class YandexMusicProvider(BaseMusicProvider):
    def __init__(self):
        from yandex_music import Client
        self.client = Client(settings.yandex_music_token).init()
        logger.info("Yandex Music provider initialized")
    
    def search(self, query: str) -> str:
        search_result = self.client.search(query)
        
        results = []
        if search_result.best:
            best = search_result.best.result
            type_ = search_result.best.type
            
            if type_ in ['track', 'podcast_episode']:
                artists = ', '.join(a.name for a in best.artists) if best.artists else ""
                results.append(f"Лучший результат: {best.title} - {artists}")
            elif type_ == 'artist':
                results.append(f"Исполнитель: {best.name}")
            elif type_ in ['album', 'podcast']:
                results.append(f"Альбом: {best.title}")
        
        if search_result.tracks:
            results.append(f"Найдено треков: {search_result.tracks.total}")
        if search_result.artists:
            results.append(f"Найдено исполнителей: {search_result.artists.total}")
        
        return "\n".join(results) if results else "Ничего не найдено"
    
    def play_likes(self, mode: str) -> str:
        tracks = self.client.users_likes_tracks()
        count = len(tracks)
        return f"Воспроизведение {count} любимых треков в режиме {mode}"
    
    def get_track_info(self, track_id: str) -> str:
        track = self.client.tracks([track_id])[0]
        artists = ', '.join(a.name for a in track.artists)
        return f"{track.title} - {artists}"

class MusicTool(BaseTool):
    def __init__(self):
        try:
            if settings.music_provider == "yandex":
                self.provider = YandexMusicProvider()
            else:
                raise ValueError(f"Unknown music provider: {settings.music_provider}")
            logger.info(f"Music tool initialized with provider: {settings.music_provider}")
        except Exception as e:
            logger.error(f"Failed to initialize music provider: {e}")
            self.provider = None
    
    def execute(self, action: str, params: Dict[str, Any]) -> str:
        if not self.provider:
            return "Music provider not available"
        
        try:
            if action == "search":
                query = params.get("query", "")
                return self.provider.search(query)
            
            elif action == "play_likes":
                mode = params.get("mode", "sequential")
                return self.provider.play_likes(mode)
            
            elif action == "get_track_info":
                track_id = params.get("track_id")
                return self.provider.get_track_info(track_id)
            
            else:
                return f"Unknown action: {action}"
        
        except Exception as e:
            logger.error(f"Error in music tool: {e}")
            return f"Ошибка: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "music",
            "description": "Control music service",
            "actions": {
                "search": {"query": "str"},
                "play_likes": {"mode": "str (sequential|random)"},
                "get_track_info": {"track_id": "str"}
            }
        }