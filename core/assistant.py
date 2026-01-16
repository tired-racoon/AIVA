from typing import List, Dict, Any
from core import get_provider, ToolExecutor
from core.voice_handler import VoiceHandler
from config.settings import settings
from utils import setup_logger
from prompts import BASE_SYSTEM_PROMPT, VOICE_SYSTEM_PROMPT

logger = setup_logger(__name__)

class Assistant:
    def __init__(self):
        self.tool_executor = ToolExecutor()
        self.voice_handler = VoiceHandler()
        self.conversation_history: List[Dict[str, Any]] = []
        self.voice_mode = False
        
        self.base_system_prompt = BASE_SYSTEM_PROMPT
        
        location_info = self._get_location_info()
        user_info = f"\n\n<USER_INFO>\n{location_info}\n</USER_INFO>"
        
        system_message = {
            "role": "system",
            "content": self.base_system_prompt + user_info
        }
        self.conversation_history.append(system_message)
        
        logger.info("Assistant initialized")

    def set_voice_mode(self, enabled: bool):
        self.voice_mode = enabled
        self._update_system_prompt()
        logger.info(f"Voice mode set to: {enabled}")

    def _get_location_info(self) -> str:
        try:
            import requests
            response = requests.get('https://ipapi.co/json/', timeout=3)
            if response.status_code == 200:
                data = response.json()
                city = data.get('city', 'неизвестно')
                country = data.get('country_name', 'неизвестно')
                return f"Текущее местоположение пользователя: {city}, {country}"
        except:
            pass
        return "Местоположение пользователя: неизвестно"
    
    def _update_system_prompt(self):
        location_info = self._get_location_info()
        
        if self.voice_mode:
            base_prompt = VOICE_SYSTEM_PROMPT
        else:
            base_prompt = BASE_SYSTEM_PROMPT
        
        full_prompt = f"{location_info}\n\n{base_prompt}"
        
        system_message = {
            "role": "system",
            "content": full_prompt
        }
        
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            self.conversation_history[0] = system_message
        else:
            if self.conversation_history:
                self.conversation_history[0:0] = [system_message]
            else:
                self.conversation_history.append(system_message)
    
    def _get_provider(self):
        from core import get_provider
        return get_provider()
    
    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> str:
        results = []
        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = tool_call["arguments"]
            
            logger.info(f"Executing tool: {function_name} with args: {arguments}")
            result = self.tool_executor.execute_tool_call(function_name, arguments)
            results.append(f"[{function_name}]: {result}")
        
        return "\n".join(results)
    
    def process_message(self, user_message: str, skip_llm_after_tools: bool = False) -> str:
        from config.settings import get_settings
        settings = get_settings()
        
        logger.info(f"Processing message: {user_message}")
        
        location_info = self._get_location_info()
        
        user_info = f"<USER_INFO>\n{location_info}\n</USER_INFO>\n\n"
        
        self.conversation_history.append({
            "role": "user",
            "content": user_info + user_message
        })
        
        tools = self.tool_executor.get_tools_definition()
        max_iterations = 5
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Processing iteration {iteration}")
            
            provider = self._get_provider()
            
            try:
                if settings.streaming_enabled:
                    response_content = ""
                    tool_calls = None
                    has_content = False
                    
                    try:
                        for chunk in provider.generate_stream(
                            self.conversation_history, 
                            tools=tools
                        ):
                            chunk_type = chunk.get("type", "")
                            
                            if chunk_type == "content" and chunk.get("content"):
                                content_piece = chunk["content"]
                                response_content += content_piece
                                has_content = True
                            
                            elif chunk_type == "final" and chunk.get("content"):
                                response_content = chunk["content"]
                                has_content = True
                            
                            elif chunk_type == "tool_calls" and chunk.get("tool_calls"):
                                tool_calls = chunk["tool_calls"]
                                if chunk.get("content"):
                                    response_content = chunk["content"]
                            
                            elif chunk_type == "error":
                                logger.error(f"Stream error: {chunk.get('content')}")
                                return chunk.get("content", "Ошибка стриминга")
                    except Exception as stream_iter_error:
                        logger.error(f"Stream iteration failed: {stream_iter_error}", exc_info=True)
                        return f"Ошибка при получении ответа: {str(stream_iter_error)}"
                    
                    if not has_content and not tool_calls:
                        logger.warning("Stream completed with no content, falling back to non-streaming")
                        response = provider.generate(
                            self.conversation_history,
                            tools=tools
                        )
                    else:
                        response = {
                            "content": response_content if response_content else None,
                            "tool_calls": tool_calls
                        }
                else:
                    response = provider.generate(
                        self.conversation_history,
                        tools=tools
                    )
                
                logger.info(f"Response: content={bool(response.get('content'))}, tool_calls={bool(response.get('tool_calls'))}")
                
                if response.get("tool_calls"):
                    logger.info(f"Tool calls detected: {response['tool_calls']}")
                    
                    tool_results = self._handle_tool_calls(response["tool_calls"])
                    
                    if response.get("content"):
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response["content"]
                        })
                    
                    if skip_llm_after_tools:
                        logger.info("Skipping LLM call after tool execution (skip_llm_after_tools=True)")
                        return tool_results
                    
                    self.conversation_history.append({
                        "role": "user",
                        "content": f"Результаты выполнения инструментов:\n{tool_results}\n\nТеперь дай понятный ответ пользователю на основе этих результатов."
                    })
                    
                    logger.info(f"Tool results: {tool_results}")
                    continue
                
                if response.get("content"):
                    content = response["content"].strip()
                    
                    if content.startswith('{') and content.endswith('}'):
                        logger.warning("Response looks like JSON, not natural text")
                        try:
                            import json
                            parsed = json.loads(content)
                            if "function" in parsed:
                                logger.info("Detected tool call in content, executing...")
                                tool_results = self._handle_tool_calls([parsed])
                                
                                self.conversation_history.append({
                                    "role": "assistant",
                                    "content": content
                                })
                                
                                if skip_llm_after_tools:
                                    logger.info("Skipping LLM call after tool execution (skip_llm_after_tools=True)")
                                    return tool_results
                                
                                self.conversation_history.append({
                                    "role": "user",
                                    "content": f"Результаты: {tool_results}\n\nДай понятный ответ."
                                })
                                continue
                        except:
                            pass
                    
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": content
                    })
                    logger.info(f"Returning response: {content[:100]}...")
                    return content
                
                logger.warning("No content in response")
                
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)
                return f"Ошибка: {str(e)}"
        
        logger.error("Failed to get response after all iterations")
        return "Не удалось получить ответ. Попробуйте еще раз."
    
    def cleanup(self):
        self.voice_handler.cleanup()