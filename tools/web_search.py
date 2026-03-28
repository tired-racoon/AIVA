from typing import Dict, Any, List
import re
from .base import BaseTool, BaseSearchProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class DuckDuckGoProvider(BaseSearchProvider):
    def __init__(self):
        from ddgs import DDGS
        self.DDGS = DDGS
        self.excluded_domains = ['tiktok.com', 'youtube.com', 'instagram.com', 'youtu.be']
        logger.info("DuckDuckGo search provider initialized")
    
    def _extract_domain(self, url: str) -> str:
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else ""
    
    def _is_excluded(self, url: str) -> bool:
        domain = self._extract_domain(url)
        return any(excluded in domain for excluded in self.excluded_domains)
    
    def _fetch_content(self, url: str, max_chars: int = 500) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            
            return text[:max_chars] if len(text) > max_chars else text
            
        except Exception as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return ""
    
    def search(self, query: str, max_results: int) -> str:
        max_results = max(5, min(15, max_results))
        
        initial_fetch = max_results * 2
        
        with self.DDGS() as ddgs:
            all_results = list(ddgs.text(query, max_results=initial_fetch))
        
        filtered_results = [r for r in all_results if not self._is_excluded(r['href'])]
        
        excluded_count = len(all_results) - len(filtered_results)
        if excluded_count > len(all_results) * 0.5 and len(filtered_results) < max_results:
            logger.info(f"Too many excluded results ({excluded_count}), fetching more")
            with self.DDGS() as ddgs:
                all_results = list(ddgs.text(query, max_results=initial_fetch * 2))
            filtered_results = [r for r in all_results if not self._is_excluded(r['href'])]
        
        results_to_process = filtered_results[:max_results]
        
        formatted_results = []
        for idx, r in enumerate(results_to_process, 1):
            title = r['title']
            url = r['href']
            snippet = r.get('body', '')
            
            content = self._fetch_content(url)
            
            result_text = f"[{idx}] {title}\n{url}\n"
            if snippet:
                result_text += f"Краткое описание: {snippet}\n"
            if content:
                result_text += f"Содержимое страницы: {content}\n"
            
            formatted_results.append(result_text)
        
        return "\n---\n".join(formatted_results) if formatted_results else "Ничего не найдено"

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
                max_results = params.get("max_results", 10)
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
                    "max_results": "int (default: 10, min: 5, max: 15)"
                }
            }
        }