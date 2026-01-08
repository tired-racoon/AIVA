import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from gui import MainWindow
from gui.splash_screen import SplashScreen
from core import get_provider, ToolExecutor
from core.voice_handler import VoiceHandler
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

class Assistant:
    def __init__(self):
        self.tool_executor = ToolExecutor()
        self.voice_handler = VoiceHandler()
        self.conversation_history = []
        self.system_prompt = {
            "role": "system",
            "content": """Ты - голосовой помощник Айва. Говори на русском языке.
Отвечай коротко и по существу. Используй доступные инструменты для выполнения задач пользователя.
Если пользователь просит найти информацию - используй web_search.
Если пользователь просит включить музыку или найти трек - используй music.
Если пользователь просит изменить громкость или яркость - используй os_control."""
        }
        self.conversation_history.append(self.system_prompt)
        logger.info("Assistant initialized")
    
    def _get_provider(self):
        from core import get_provider
        return get_provider()
    
    def _handle_tool_calls(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            function_name = tool_call["function"]
            arguments = tool_call["arguments"]
            
            logger.info(f"Executing tool: {function_name} with args: {arguments}")
            result = self.tool_executor.execute_tool_call(function_name, arguments)
            results.append(f"[{function_name}]: {result}")
        
        return "\n".join(results)
    
    def process_message(self, user_message):
        from config.settings import get_settings
        settings = get_settings()
        
        logger.info(f"Processing message: {user_message}")
        
        self.conversation_history.append({
            "role": "user",
            "content": user_message
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
                    
                    for chunk in provider.generate_stream(
                        self.conversation_history, 
                        tools=tools
                    ):
                        chunk_type = chunk.get("type", "")
                        
                        if chunk_type == "content" and chunk.get("content"):
                            response_content += chunk["content"]
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

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    def init_step_1():
        splash.update_progress(20, "Loading configuration...")
        QTimer.singleShot(100, init_step_2)
    
    def init_step_2():
        splash.update_progress(40, "Initializing LLM provider...")
        QTimer.singleShot(100, init_step_3)
    
    def init_step_3():
        global assistant
        assistant = Assistant()
        splash.update_progress(80, "Setting up interface...")
        QTimer.singleShot(100, init_step_4)
    
    def init_step_4():
        global window
        window = MainWindow(assistant)
        splash.update_progress(100, "Ready!")
        QTimer.singleShot(500, show_main_window)
    
    def show_main_window():
        window.show()
        splash.finish(window)
    
    QTimer.singleShot(100, init_step_1)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()