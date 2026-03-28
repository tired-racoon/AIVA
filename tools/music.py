# tools\music.py
from typing import Dict, Any, Optional
import os
import tempfile
import time
from threading import Thread, Lock
from .base import BaseTool, BaseMusicProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class YandexMusicProvider(BaseMusicProvider):
    def __init__(self):
        from yandex_music import Client
        self.client = Client(settings.yandex_music_token).init()
        self.temp_dir = tempfile.mkdtemp(prefix="aiva_music_")
        self.downloaded_tracks = {}
        self.cleanup_lock = Lock()
        self.current_playback = None
        self.playback_thread = None
        self.stop_playback_flag = False
        self.playback_process = None
        self.pygame_initialized = False
        self.paused = False
        self.pause_position = 0
        logger.info("Yandex Music provider initialized")
    
    def is_playing(self) -> bool:
        if self.paused:
            return False
        
        import platform
        system = platform.system()
        
        if system == "Windows":
            try:
                if hasattr(self, 'pygame_initialized') and self.pygame_initialized:
                    import pygame
                    return pygame.mixer.music.get_busy()
            except:
                pass
        
        if self.playback_process and self.playback_process.poll() is None:
            return True
        
        return False
    
    def pause_music(self) -> str:
        if self.paused:
            return "Музыка уже на паузе"
        
        import platform
        system = platform.system()
        
        if system == "Windows":
            try:
                if hasattr(self, 'pygame_initialized') and self.pygame_initialized:
                    import pygame
                    if pygame.mixer.music.get_busy():
                        self.pause_position = pygame.mixer.music.get_pos()
                        pygame.mixer.music.pause()
                        self.paused = True
                        logger.info(f"Music paused at position: {self.pause_position}")
                        return "Музыка поставлена на паузу"
            except Exception as e:
                logger.error(f"Failed to pause music: {e}")
        
        return "Пауза не поддерживается на этой системе"
    
    def resume_music(self) -> str:
        if not self.paused:
            return "Музыка не на паузе"
        
        import platform
        system = platform.system()
        
        if system == "Windows":
            try:
                if hasattr(self, 'pygame_initialized') and self.pygame_initialized:
                    import pygame
                    pygame.mixer.music.unpause()
                    self.paused = False
                    logger.info("Music resumed")
                    return "Воспроизведение продолжено"
            except Exception as e:
                logger.error(f"Failed to resume music: {e}")
        
        return "Продолжение не поддерживается на этой системе"
    
    def _download_track(self, track_id: str, timeout: int = 300) -> Optional[str]:
        track_path = os.path.join(self.temp_dir, f"{track_id}.mp3")
        
        if os.path.exists(track_path):
            return track_path
        
        try:
            track = self.client.tracks([track_id])[0]
            track.download(track_path)
            
            with self.cleanup_lock:
                self.downloaded_tracks[track_id] = {
                    'path': track_path,
                    'timestamp': time.time(),
                    'timeout': timeout
                }
            
            self._schedule_cleanup(track_id, timeout)
            
            return track_path
        except Exception as e:
            logger.error(f"Failed to download track {track_id}: {e}")
            return None
    
    def _schedule_cleanup(self, track_id: str, timeout: int):
        def cleanup_task():
            time.sleep(timeout)
            with self.cleanup_lock:
                if track_id in self.downloaded_tracks:
                    track_info = self.downloaded_tracks[track_id]
                    if os.path.exists(track_info['path']):
                        try:
                            os.remove(track_info['path'])
                            logger.info(f"Cleaned up track {track_id}")
                        except Exception as e:
                            logger.error(f"Failed to cleanup track {track_id}: {e}")
                    del self.downloaded_tracks[track_id]
        
        Thread(target=cleanup_task, daemon=True).start()
    
    def _play_audio(self, file_path: str):
        try:
            import platform
            import subprocess
            system = platform.system()
            
            if system == "Windows":
                try:
                    import pygame
                    
                    if not hasattr(self, 'pygame_initialized') or not self.pygame_initialized:
                        pygame.mixer.init()
                        self.pygame_initialized = True
                    else:
                        pygame.mixer.music.stop()
                    
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy() and not self.stop_playback_flag:
                        import time
                        time.sleep(0.1)
                    
                    if self.stop_playback_flag:
                        pygame.mixer.music.stop()
                        
                except ImportError:
                    logger.warning("pygame not available, trying winmm")
                    try:
                        import winsound
                        import threading
                        
                        def play_with_winsound():
                            winsound.PlaySound(file_path, winsound.SND_FILENAME)
                        
                        play_thread = threading.Thread(target=play_with_winsound, daemon=True)
                        play_thread.start()
                        
                        while play_thread.is_alive() and not self.stop_playback_flag:
                            import time
                            time.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"winsound failed: {e}")
                    
            elif system == "Darwin":
                self.playback_process = subprocess.Popen(
                    ['afplay', file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                while self.playback_process.poll() is None and not self.stop_playback_flag:
                    import time
                    time.sleep(0.1)
                if self.stop_playback_flag and self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process = None
            else:
                self.playback_process = subprocess.Popen(
                    ['mpg123', file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                while self.playback_process.poll() is None and not self.stop_playback_flag:
                    import time
                    time.sleep(0.1)
                if self.stop_playback_flag and self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process = None
        
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self.playback_process = None
    
    def _start_playback(self, track_path: str):
        self.stop_music()
        
        self.stop_playback_flag = False
        self.playback_thread = Thread(target=self._play_audio, args=(track_path,), daemon=True)
        self.playback_thread.start()
    
    def stop_music(self) -> str:
        import platform
        
        self.stop_playback_flag = True
        
        system = platform.system()
        if system == "Windows":
            try:
                if hasattr(self, 'pygame_initialized') and self.pygame_initialized:
                    import pygame
                    pygame.mixer.music.stop()
            except:
                pass
        
        if self.playback_process:
            try:
                self.playback_process.terminate()
                self.playback_process.wait(timeout=1.0)
                self.playback_process = None
            except:
                pass
        
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
            self.playback_thread = None
        
        import time
        time.sleep(0.2)
        
        return "Музыка остановлена"
    
    def search(self, query: str) -> str:
        search_result = self.client.search(query)
        
        results = []
        
        if search_result.best:
            best = search_result.best.result
            type_ = search_result.best.type
            
            if type_ in ['track', 'podcast_episode']:
                artists = ', '.join(a.name for a in best.artists) if best.artists else ""
                results.append(f"Лучший результат (трек): {best.title} - {artists} [ID: {best.id}]")
            elif type_ == 'artist':
                results.append(f"Лучший результат (исполнитель): {best.name} [ID: {best.id}]")
            elif type_ in ['album', 'podcast']:
                results.append(f"Лучший результат (альбом): {best.title} [ID: {best.id}]")
        
        if search_result.tracks and search_result.tracks.results:
            results.append("\nТреки:")
            for idx, track in enumerate(search_result.tracks.results[:5], 1):
                artists = ', '.join(a.name for a in track.artists) if track.artists else ""
                results.append(f"  {idx}. {track.title} - {artists} [ID: {track.id}]")
        
        if search_result.artists and search_result.artists.results:
            results.append("\nИсполнители:")
            for idx, artist in enumerate(search_result.artists.results[:5], 1):
                results.append(f"  {idx}. {artist.name} [ID: {artist.id}]")
        
        if search_result.albums and search_result.albums.results:
            results.append("\nАльбомы:")
            for idx, album in enumerate(search_result.albums.results[:5], 1):
                artists = ', '.join(a.name for a in album.artists) if album.artists else ""
                results.append(f"  {idx}. {album.title} - {artists} [ID: {album.id}]")
        
        return "\n".join(results) if results else "Ничего не найдено"
    
    def _find_artist_id(self, query: str) -> Optional[str]:
        try:
            search_result = self.client.search(query)
            
            if search_result.best and search_result.best.type == 'artist':
                return str(search_result.best.result.id)
            
            if search_result.artists and search_result.artists.results:
                return str(search_result.artists.results[0].id)
            
            return None
        except Exception as e:
            logger.error(f"Failed to find artist ID for '{query}': {e}")
            return None

    def _find_track_id(self, query: str) -> Optional[str]:
        try:
            search_result = self.client.search(query)
            
            if search_result.best and search_result.best.type in ['track', 'podcast_episode']:
                return str(search_result.best.result.id)
            
            if search_result.tracks and search_result.tracks.results:
                return str(search_result.tracks.results[0].id)
            
            return None
        except Exception as e:
            logger.error(f"Failed to find track ID for '{query}': {e}")
            return None

    def _find_album_id(self, query: str) -> Optional[str]:
        try:
            search_result = self.client.search(query)
            
            if search_result.best and search_result.best.type in ['album', 'podcast']:
                return str(search_result.best.result.id)
            
            if search_result.albums and search_result.albums.results:
                return str(search_result.albums.results[0].id)
            
            return None
        except Exception as e:
            logger.error(f"Failed to find album ID for '{query}': {e}")
            return None

    def play_track(self, track_id: str) -> str:
        try:
            self.stop_music()
            
            if not track_id.isdigit():
                logger.info(f"Searching for track: {track_id}")
                found_id = self._find_track_id(track_id)
                if not found_id:
                    return f"Не удалось найти трек '{track_id}'"
                track_id = found_id
            
            track = self.client.tracks([track_id])[0]
            artists = ', '.join(a.name for a in track.artists) if track.artists else ""
            
            track_path = self._download_track(track_id)
            if not track_path:
                return f"Не удалось скачать трек {track.title}"
            
            self._start_playback(track_path)
            
            return f"Воспроизведение: {track.title} - {artists}"
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            return f"Ошибка воспроизведения: {str(e)}"

    def play_artist(self, artist_id: str, limit: int = 10) -> str:
        try:
            self.stop_music()
            
            if not artist_id.isdigit():
                logger.info(f"Searching for artist: {artist_id}")
                found_id = self._find_artist_id(artist_id)
                if not found_id:
                    return f"Не удалось найти исполнителя '{artist_id}'"
                artist_id = found_id
            
            artist = self.client.artists([artist_id])[0]
            tracks = artist.get_tracks(page=0, page_size=limit)
            
            if not tracks:
                return f"У исполнителя {artist.name} не найдено треков"
            
            track_id = tracks[0].id
            track_path = self._download_track(track_id)
            if track_path:
                self._start_playback(track_path)
            
            return f"Воспроизведение треков исполнителя {artist.name} (найдено {len(tracks)} треков)"
        except Exception as e:
            logger.error(f"Error playing artist: {e}")
            return f"Ошибка воспроизведения: {str(e)}"

    def play_album(self, album_id: str) -> str:
        try:
            self.stop_music()
            
            if not album_id.isdigit():
                logger.info(f"Searching for album: {album_id}")
                found_id = self._find_album_id(album_id)
                if not found_id:
                    return f"Не удалось найти альбом '{album_id}'"
                album_id = found_id
            
            album = self.client.albums_with_tracks(album_id)
            
            if not album.volumes or not album.volumes[0]:
                return f"В альбоме {album.title} не найдено треков"
            
            first_track = album.volumes[0][0]
            artists = ', '.join(a.name for a in album.artists) if album.artists else ""
            
            track_path = self._download_track(first_track.id)
            if track_path:
                self._start_playback(track_path)
            
            total_tracks = sum(len(vol) for vol in album.volumes)
            return f"Воспроизведение альбома: {album.title} - {artists} ({total_tracks} треков)"
        except Exception as e:
            logger.error(f"Error playing album: {e}")
            return f"Ошибка воспроизведения: {str(e)}"
    
    def play_likes(self, mode: str) -> str:
        self.stop_music()
        
        tracks = self.client.users_likes_tracks()
        count = len(tracks)
        
        if count == 0:
            return "У вас нет любимых треков"
        
        track = tracks[0].fetch_track()
        track_path = self._download_track(track.id)
        if track_path:
            self._start_playback(track_path)
        
        return f"Воспроизведение {count} любимых треков в режиме {mode}"
    
    def get_track_info(self, track_id: str) -> str:
        track = self.client.tracks([track_id])[0]
        artists = ', '.join(a.name for a in track.artists)
        return f"{track.title} - {artists}"
    
    def cleanup(self):
        self.stop_music()
        
        import platform
        if platform.system() == "Windows":
            try:
                if hasattr(self, 'pygame_initialized') and self.pygame_initialized:
                    import pygame
                    pygame.mixer.quit()
                    self.pygame_initialized = False
            except:
                pass
        
        with self.cleanup_lock:
            for track_id, track_info in list(self.downloaded_tracks.items()):
                if os.path.exists(track_info['path']):
                    try:
                        os.remove(track_info['path'])
                    except Exception as e:
                        logger.error(f"Failed to cleanup track {track_id}: {e}")
            self.downloaded_tracks.clear()
        
        try:
            os.rmdir(self.temp_dir)
        except Exception as e:
            logger.error(f"Failed to remove temp directory: {e}")

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
            
            elif action == "play_track":
                track_id = params.get("track_id")
                if not track_id:
                    return "Не указан ID трека"
                return self.provider.play_track(str(track_id))
            
            elif action == "play_artist":
                artist_id = params.get("artist_id")
                if not artist_id:
                    return "Не указан ID исполнителя"
                limit = params.get("limit", 10)
                return self.provider.play_artist(str(artist_id), limit)
        
            elif action == "play_album":
                album_id = params.get("album_id")
                if not album_id:
                    return "Не указан ID альбома"
                return self.provider.play_album(str(album_id))
            
            elif action == "play_likes":
                mode = params.get("mode", "sequential")
                return self.provider.play_likes(mode)
            
            elif action == "stop_music":
                return self.provider.stop_music()
            
            elif action == "pause_music":
                return self.provider.pause_music()
            
            elif action == "resume_music":
                return self.provider.resume_music()
            
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
                "play_track": {"track_id": "str"},
                "play_artist": {"artist_id": "str", "limit": "int (default: 10)"},
                "play_album": {"album_id": "str"},
                "play_likes": {"mode": "str (sequential|random)"},
                "get_track_info": {"track_id": "str"}
            }
        }

    def cleanup(self):
        if self.provider:
            self.provider.cleanup()