import json
from typing import List, Dict, Iterator, Optional, Any
from openai import OpenAI
from .base import BaseLLMProvider
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class YandexProvider(BaseLLMProvider):
    def __init__(self):
        logger.info("Initializing Yandex provider")
        self.client = OpenAI(
            api_key=settings.yandex_api_key,
            base_url="https://llm.api.cloud.yandex.net/v1",
            project=settings.yandex_folder_id
        )
        self.model = f"gpt://{settings.yandex_folder_id}/{settings.yandex_model}"
    
    def generate(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        from config.settings import get_settings
        settings = get_settings()
        
        logger.info(f"Using model: yandex - {settings.yandex_model}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": settings.max_tokens,
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
        
        logger.info(f"Using model: yandex - {settings.yandex_model}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "stream": True
        }
        
        if tools:
            kwargs["tools"] = tools
        
        try:
            stream = self.client.chat.completions.create(**kwargs)
            
            accumulated_content = ""
            tool_calls_accumulator = {}
            
            try:
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
                            index = tc.index if hasattr(tc, 'index') else 0
                            
                            if index not in tool_calls_accumulator:
                                tool_calls_accumulator[index] = {
                                    "function_name": "",
                                    "arguments": ""
                                }
                            
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_accumulator[index]["function_name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_accumulator[index]["arguments"] += tc.function.arguments
            except Exception as stream_error:
                logger.error(f"Stream iteration error: {stream_error}", exc_info=True)
                yield {
                    "type": "error",
                    "content": f"Ошибка при получении данных: {str(stream_error)}",
                    "tool_calls": None
                }
                return
            
            tool_calls_data = []
            if tool_calls_accumulator:
                for idx in sorted(tool_calls_accumulator.keys()):
                    tc = tool_calls_accumulator[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                        tool_calls_data.append({
                            "function": tc["function_name"],
                            "arguments": args
                        })
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse tool call arguments: {tc['arguments']}, error: {je}")
                        yield {
                            "type": "error",
                            "content": f"Ошибка парсинга аргументов инструмента: {str(je)}",
                            "tool_calls": None
                        }
                        return
            
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