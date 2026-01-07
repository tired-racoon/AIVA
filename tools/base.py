from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    @abstractmethod
    def execute(self, action: str, params: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        pass

class BaseMusicProvider(ABC):
    @abstractmethod
    def search(self, query: str) -> str:
        pass
    
    @abstractmethod
    def play_likes(self, mode: str) -> str:
        pass
    
    @abstractmethod
    def get_track_info(self, track_id: str) -> str:
        pass

class BaseSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int) -> str:
        pass