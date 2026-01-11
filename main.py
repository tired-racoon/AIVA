import json
import sys
import os
from typing import List, Dict, Any
from core import get_provider, ToolExecutor
from core.voice_handler import VoiceHandler
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

def check_and_install_dependencies():
    try:
        from install_dependencies import install_os_dependencies
        install_os_dependencies()
    except Exception as e:
        logger.warning(f"Failed to install OS-specific dependencies: {e}")

class Assistant:
    def __init__(self):
        check_and_install_dependencies()
        
        self.provider = get_provider()
        self.tool_executor = ToolExecutor()
        self.voice_handler = VoiceHandler()
        self.conversation_history: List[Dict[str, Any]] = []
        
        self.base_system_prompt = """Ты - голосовой помощник Айва. Говори на русском языке.
    Отвечай коротко и по существу. Используй доступные инструменты для выполнения задач пользователя.

    КОГДА ИСПОЛЬЗОВАТЬ ИНСТРУМЕНТЫ:

    web_search - используй когда:
    - Пользователь явно просит найти информацию ("найди", "поищи", "что такое", "кто такой")
    - Тебе нужна актуальная информация (новости, погода, курсы валют)
    - Ты не уверен в ответе или у тебя нет информации по теме
    - Пользователь спрашивает о событиях после января 2025 года
    Примеры: "найди информацию о Python", "какая погода в Москве", "что случилось сегодня"

    music - используй когда:
    - Пользователь просит включить/воспроизвести музыку, трек, песню, исполнителя, альбом
    - Пользователь называет название трека или имя исполнителя
    - Пользователь просит найти музыку
    - Пользователь просит включить любимые треки
    - Пользователь просит выключить/остановить музыку
    Примеры: "включи Call Me Karizma", "поставь Linkin Park", "включи любимое", "выключи музыку"

    os_control - используй когда:
    - Пользователь просит изменить громкость звука
    - Пользователь просит включить/выключить звук (мут)
    - Пользователь просит изменить яркость экрана
    Примеры: "сделай громче", "установи громкость на 50%", "выключи звук", "увеличь яркость"

    ОБЩИЕ ПРАВИЛА:
    - При необходимости используй информацию о текущем времени и местоположении пользователя из USER_INFO
    - Не используй web search для поиска текущего времени
    - Если не знаешь ответ - используй web_search
    - Если пользователь упоминает музыку или исполнителя - используй music
    - Отвечай обычным текстом только на простые вопросы, где инструменты не нужны"""
        
        system_message = {
            "role": "system",
            "content": self.base_system_prompt
        }
        self.conversation_history.append(system_message)
        
        logger.info("Assistant initialized")

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

    def _get_time_info(self) -> str:
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        except:
            pass
        now = datetime.now()
        date_str = now.strftime("%d.%m.%Y")
        time_str = now.strftime("%H:%M")
        weekday = now.strftime("%A")
        return f"Текущая дата и время: {date_str}, {time_str} ({weekday})"

    def _update_system_prompt(self):
        location_info = self._get_location_info()
        time_info = self._get_time_info()
        
        full_prompt = f"{location_info}\n{time_info}\n\n{self.base_system_prompt}"
        
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
    
    def _handle_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> str:
        results = []
        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = tool_call["arguments"]
            
            logger.info(f"Executing tool: {function_name} with args: {arguments}")
            result = self.tool_executor.execute_tool_call(function_name, arguments)
            results.append(f"[{function_name}]: {result}")
        
        return "\n".join(results)
    
    def process_message(self, user_message: str) -> str:
        location_info = self._get_location_info()
        time_info = self._get_time_info()
        
        user_info = f"<USER_INFO>\n{location_info}\n{time_info}\n</USER_INFO>\n\n"
        
        self.conversation_history.append({
            "role": "user",
            "content": user_info + user_message
        })
        
        tools = self.tool_executor.get_tools_definition()
        max_iterations = 3
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Processing iteration {iteration}")
            
            if settings.streaming_enabled:
                response_content = ""
                tool_calls = None
                
                for chunk in self.provider.generate_stream(
                    self.conversation_history, 
                    tools=tools
                ):
                    if chunk.get("type") == "content" and chunk.get("content"):
                        response_content += chunk["content"]
                    
                    if chunk.get("tool_calls"):
                        tool_calls = chunk["tool_calls"]
                
                response = {
                    "content": response_content if response_content else None,
                    "tool_calls": tool_calls
                }
            else:
                response = self.provider.generate(
                    self.conversation_history,
                    tools=tools
                )
            
            if response.get("tool_calls"):
                tool_results = self._handle_tool_calls(response["tool_calls"])
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": response["tool_calls"]
                })
                
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Результаты выполнения инструментов:\n{tool_results}"
                })
                
                logger.info(f"Tool results: {tool_results}")
                continue
            
            if response.get("content"):
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response["content"]
                })
                return response["content"]
            
            break
        
        return "Не удалось получить ответ"

    def run_voice_mode(self):
        logger.info("Voice assistant started")
        print(f"Voice assistant ready. Say '{settings.activation_phrase}' to activate.")
        print("Press Ctrl+C to stop.")
        
        try:
            while True:
                if self.voice_handler.listen_for_activation():
                    self.conversation_history = []
                    self._update_system_prompt()
                    
                    self.voice_handler.speak("Слушаю")
                    
                    audio_path = self.voice_handler.record_command()
                    user_text = self.voice_handler.transcribe(audio_path)
                    
                    if user_text and len(user_text.strip()) > 2:
                        logger.info(f"User: {user_text}")
                        
                        response = self.process_message(user_text)
                        logger.info(f"Assistant: {response}")
                        
                        self.voice_handler.speak(response)
        
        except KeyboardInterrupt:
            logger.info("Voice assistant stopped by user")
        finally:
            self.cleanup()
    
    def run_text_mode(self):
        logger.info("Text assistant started")
        print("Assistant ready. Type 'exit' to quit.")
        print("Examples:")
        print("  - Найди информацию о Python")
        print("  - Включи музыку")
        print("  - Установи громкость на 50%")
        print()
        
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ["exit", "quit"]:
                    logger.info("Assistant stopped by user")
                    break
                
                response = self.process_message(user_input)
                print(f"Assistant: {response}")
                
            except KeyboardInterrupt:
                logger.info("Assistant stopped by interrupt")
                break
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                print(f"Error: {e}")
    
    def cleanup(self):
        self.voice_handler.cleanup()

if __name__ == "__main__":
    mode = os.getenv("ASSISTANT_MODE", "voice")
    
    assistant = Assistant()
    
    if mode == "text":
        assistant.run_text_mode()
    else:
        assistant.run_voice_mode()