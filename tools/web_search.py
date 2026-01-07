from typing import Dict, Any
from .base import BaseTool, BaseSearchProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class DuckDuckGoProvider(BaseSearchProvider):
    def __init__(self):
        from ddgs import DDGS
        self.DDGS = DDGS
        logger.info("DuckDuckGo search provider initialized")
    
    def search(self, query: str, max_results: int) -> str:
        with self.DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        formatted_results = []
        for r in results:
            formatted_results.append(f"{r['title']}\n{r['href']}\n{r.get('body', '')}\n")
        
        return "\n".join(formatted_results) if formatted_results else "Ничего не найдено"

class WebSearchTool(BaseTool):
    def __init__(self):
        try:
            if settings.search_provider == "duckduckgo":
                self.provider = DuckDuckGoProvider()
            else:
                raise ValueError(f"Unknown search provider: {settings.search_provider}")
            logger.info(f"Web search tool initialized with provider: {settings.search_provider}")
        except Exception as e:
            logger.error(f"Failed to initialize search provider: {e}")
            self.provider = None
    
    def execute(self, action: str, params: Dict[str, Any]) -> str:
        if not self.provider:
            return "Search provider not available"
        
        try:
            if action == "search":
                query = params.get("query", "")
                max_results = params.get("max_results", 5)
                return self.provider.search(query, max_results)
            
            else:
                return f"Unknown action: {action}"
        
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return f"Ошибка: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "web_search",
            "description": "Search the web",
            "actions": {
                "search": {
                    "query": "str",
                    "max_results": "int (default: 5)"
                }
            }
        }