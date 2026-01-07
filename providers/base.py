from abc import ABC, abstractmethod
from typing import List, Dict, Iterator, Optional, Any

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[Dict[str, Any]]:
        pass