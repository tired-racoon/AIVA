import json
from typing import List, Dict, Iterator, Optional, Any
from openai import OpenAI
import httpx
from .base import BaseLLMProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self):
        logger.info("Initializing OpenRouter provider")
        
        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1"
        )
    
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        from config.settings import get_settings
        settings = get_settings()
        
        logger.info(f"Using model: {settings.openrouter_model}")

        kwargs = {
            "model": settings.openrouter_model,
            "messages": messages,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature
        }
        
        if tools:
            kwargs["tools"] = tools
        
        response = self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        
        if message.tool_calls:
            return {
                "content": message.content,
                "tool_calls": [
                    {
                        "function": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    }
                    for tc in message.tool_calls
                ]
            }
        
        return {
            "content": message.content,
            "tool_calls": None
        }

    def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Iterator[Dict[str, Any]]:
        from config.settings import get_settings
        settings = get_settings()
        
        logger.info(f"Using model: {settings.openrouter_model}")

        kwargs = {
            "model": settings.openrouter_model,
            "messages": messages,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "stream": True
        }
        
        if tools:
            kwargs["tools"] = tools
        
        try:
            stream = self.client.chat.completions.create(**kwargs)
            
            accumulated_content = ""
            tool_calls_data = []
            
            for chunk in stream:
                if not chunk.choices or len(chunk.choices) == 0:
                    continue
                
                delta = chunk.choices[0].delta
                
                if hasattr(delta, 'content') and delta.content:
                    accumulated_content += delta.content
                    yield {
                        "type": "content",
                        "content": delta.content,
                        "tool_calls": None
                    }
                
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tc in delta.tool_calls:
                        if tc.function:
                            tool_calls_data.append({
                                "function": tc.function.name,
                                "arguments": json.loads(tc.function.arguments)
                            })
            
            if accumulated_content and not tool_calls_data:
                yield {
                    "type": "final",
                    "content": accumulated_content,
                    "tool_calls": None
                }
            
            if tool_calls_data:
                yield {
                    "type": "tool_calls",
                    "content": accumulated_content,
                    "tool_calls": tool_calls_data
                }
                
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield {
                "type": "error",
                "content": f"Ошибка стриминга: {str(e)}",
                "tool_calls": None
            }