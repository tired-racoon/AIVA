import sys
import os
from core import Assistant
from config.settings import settings
from utils import setup_logger

logger = setup_logger(__name__)

def check_and_install_dependencies():
    try:
        from install_dependencies import install_os_dependencies
        install_os_dependencies()
    except Exception as e:
        logger.warning(f"Failed to install OS-specific dependencies: {e}")

def run_voice_mode(assistant):
    logger.info("Voice assistant started")
    print(f"Voice assistant ready. Say '{settings.activation_phrase}' to activate.")
    print("Press Ctrl+C to stop.")
    
    assistant.set_voice_mode(True)
    
    try:
        while True:
            if assistant.voice_handler.listen_for_activation():
                music_was_playing = assistant.tool_executor.tools["music"].provider.is_playing()
                if music_was_playing:
                    assistant.tool_executor.tools["music"].provider.pause_music()
                
                assistant.conversation_history = []
                assistant._update_system_prompt()
                
                assistant.voice_handler.speak("Слушаю")
                
                audio_path = assistant.voice_handler.record_command()
                
                if not audio_path:
                    logger.info("No audio recorded")
                    if music_was_playing:
                        assistant.tool_executor.tools["music"].provider.resume_music()
                    continue
                
                user_text = assistant.voice_handler.transcribe(audio_path)
                
                if user_text and len(user_text.strip()) > 2:
                    logger.info(f"User: {user_text}")
                    
                    is_music_command = any(word in user_text.lower() for word in 
                                        ['включи', 'поставь', 'воспроизведи', 'играй', 'музыка', 'трек', 'песня', 'исполнител', 'альбом', 'лайк'])
                    
                    response = assistant.process_message(user_text, skip_llm_after_tools=is_music_command)
                    logger.info(f"Assistant: {response}")
                    
                    if not is_music_command or "ошибка" in response.lower() or "не удалось" in response.lower():
                        assistant.voice_handler.speak(response)
                
                if music_was_playing:
                    assistant.tool_executor.tools["music"].provider.resume_music()
    
    except KeyboardInterrupt:
        logger.info("Voice assistant stopped by user")
    finally:
        assistant.cleanup()

def run_text_mode(assistant):
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
            
            response = assistant.process_message(user_input)
            print(f"Assistant: {response}")
            
        except KeyboardInterrupt:
            logger.info("Assistant stopped by interrupt")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"Error: {e}")

if __name__ == "__main__":
    check_and_install_dependencies()
    
    mode = os.getenv("ASSISTANT_MODE", "voice")
    assistant = Assistant()
    
    if mode == "text":
        run_text_mode(assistant)
    else:
        run_voice_mode(assistant)