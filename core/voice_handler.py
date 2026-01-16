import os
import sys
import re

if sys.platform == "win32":
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    os.environ["SDL_AUDIODRIVER"] = "directsound"

import numpy as np
import pyaudio
import wave
import tempfile
from collections import deque
from scipy import signal
from scipy.io import wavfile
import gigaam
from vosk_tts import Model, Synth
from config.settings import settings
from utils import setup_logger
import time
import threading

logger = setup_logger(__name__)

class VoiceHandler:
    def __init__(self):
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        self.audio = pyaudio.PyAudio()
        
        try:
            self.default_input_device = self.audio.get_default_input_device_info()
            logger.info(f"Using input device: {self.default_input_device['name']}")
        except Exception as e:
            logger.error(f"Error getting default input device: {e}")
            self.default_input_device = None
        
        logger.info("Loading ASR model...")
        self.asr_model = gigaam.load_model("v3_e2e_rnnt")
        logger.info("ASR model loaded")
        
        self.tts_provider = settings.tts_provider
        self._init_tts()
        
        self.buffer_size = int(settings.buffer_duration * self.rate / self.chunk)
        self.audio_buffer = deque(maxlen=self.buffer_size)
        
        self.silence_chunks = int(settings.silence_duration * self.rate / self.chunk)
        
        self.playback_audio = None
        self.stop_playback_flag = False
        self.playback_process = None
    
    def _init_tts(self):
        if hasattr(self, 'tts_model') and self.tts_model is not None:
            logger.info("Cleaning up old TTS model")
            try:
                if self.tts_provider == "xtts" and hasattr(self.tts_model, 'synthesizer'):
                    del self.tts_model
                self.tts_model = None
                self.synth = None
                import gc
                import torch
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as e:
                logger.warning(f"Error cleaning up TTS model: {e}")
        
        from config.settings import get_settings
        current_settings = get_settings()
        self.tts_provider = current_settings.tts_provider
        
        if self.tts_provider == "vosk":
            logger.info(f"Loading Vosk TTS model: {current_settings.tts_model_name}")
            from vosk_tts import Model, Synth
            self.tts_model = Model(model_name=current_settings.tts_model_name)
            self.synth = Synth(self.tts_model)
            logger.info("Vosk TTS model loaded")
        elif self.tts_provider == "xtts":
            logger.info("Loading XTTS v2 model...")
            from TTS.api import TTS
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
            self.synth = None
            logger.info(f"XTTS v2 model loaded on {device}")
        else:
            logger.error(f"Unknown TTS provider: {self.tts_provider}")
            self.tts_model = None
            self.synth = None
    
    def _calculate_amplitude(self, audio_data):
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        return np.abs(audio_array).mean()
    
    def _calculate_frequency_energy(self, audio_data):
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        frequencies, power_spectrum = signal.periodogram(audio_array, self.rate)
        
        freq_mask = (frequencies >= settings.min_frequency) & (frequencies <= settings.max_frequency)
        speech_energy = np.sum(power_spectrum[freq_mask])
        
        return speech_energy
    
    def check_for_speech(self, timeout: float = 1.5) -> bool:
        if not self.default_input_device:
            return False
        
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=self.default_input_device['index']
            )
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            return False
        
        start_time = time.time()
        speech_detected = False
        speech_frames = 0
        required_speech_frames = 3
        
        try:
            while time.time() - start_time < timeout:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    amplitude = self._calculate_amplitude(data)
                    freq_energy = self._calculate_frequency_energy(data)
                    
                    if amplitude > settings.silence_threshold * 1.5 and freq_energy > 2000:
                        speech_frames += 1
                        if speech_frames >= required_speech_frames:
                            speech_detected = True
                            break
                    else:
                        speech_frames = max(0, speech_frames - 1)
                            
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    break
        finally:
            stream.stop_stream()
            stream.close()
        
        return speech_detected
    
    def _save_buffer_to_file(self, frames):
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            wf = wave.open(temp_path, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return temp_path
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return None
    
    def listen_for_activation(self):
        if not self.default_input_device:
            logger.error("No input device available")
            return False
        
        while self.stop_playback_flag or (hasattr(self, 'playback_process') and self.playback_process is not None):
            import time
            time.sleep(0.1)
            
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=self.default_input_device['index']
            )
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            return False
        
        logger.info(f"Listening for activation phrase: '{settings.activation_phrase}'")
        
        activation_confidence_threshold = 0.7
        min_phrase_length = len(settings.activation_phrase) - 2
        
        try:
            while True:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    continue
                
                amplitude = self._calculate_amplitude(data)
                freq_energy = self._calculate_frequency_energy(data)
                
                if amplitude < settings.silence_threshold * 0.5 and freq_energy < 500:
                    continue
                    
                self.audio_buffer.append(data)
                
                if len(self.audio_buffer) >= self.buffer_size:
                    frames = list(self.audio_buffer)
                    audio_path = self._save_buffer_to_file(frames)
                    
                    if not audio_path:
                        continue
                    
                    try:
                        text = self.asr_model.transcribe(audio_path).strip().lower()
                        
                        if len(text) >= min_phrase_length and settings.activation_phrase in text:
                            phrase_words = settings.activation_phrase.split()
                            text_words = text.split()
                            
                            max_extra_words = 5
                            
                            if len(text_words) <= len(phrase_words) + max_extra_words:
                                activation_index = text.find(settings.activation_phrase)
                                text_after_activation = text[activation_index + len(settings.activation_phrase):].strip()
                                
                                words_after = text_after_activation.split()
                                if len(words_after) <= max_extra_words:
                                    logger.info(f"Activation detected: {text}")
                                    try:
                                        os.unlink(audio_path)
                                    except:
                                        pass
                                    stream.stop_stream()
                                    stream.close()
                                    
                                    self.audio_buffer.clear()
                                    
                                    return True
                        
                    except Exception as e:
                        logger.error(f"Transcription error: {e}")
                    finally:
                        if os.path.exists(audio_path):
                            try:
                                os.unlink(audio_path)
                            except:
                                pass
        
        except KeyboardInterrupt:
            stream.stop_stream()
            stream.close()
            return False

    def record_command(self):
        if not self.default_input_device:
            logger.error("No input device available")
            return None
            
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=self.default_input_device['index']
            )
        except Exception as e:
            logger.error(f"Failed to open audio stream for recording: {e}")
            return None
        
        logger.info("Recording command...")
        frames = []
        silence_counter = 0
        has_speech = False
        
        try:
            while True:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    break
                    
                frames.append(data)
                
                amplitude = self._calculate_amplitude(data)
                freq_energy = self._calculate_frequency_energy(data)
                
                if amplitude > settings.silence_threshold and freq_energy > 1000:
                    has_speech = True
                    silence_counter = 0
                elif amplitude < settings.silence_threshold and freq_energy < 1000:
                    silence_counter += 1
                else:
                    silence_counter = 0
                
                if has_speech and silence_counter >= self.silence_chunks:
                    logger.info("End of speech detected")
                    break
                
                if len(frames) > self.rate / self.chunk * 10:
                    logger.info("Max recording time reached")
                    break
        
        finally:
            stream.stop_stream()
            stream.close()
        
        if not has_speech:
            logger.warning("No speech detected during recording")
            return None
        
        audio_path = self._save_buffer_to_file(frames)
        return audio_path
    
    def transcribe(self, audio_path):
        if not audio_path:
            return ""
            
        try:
            full_text = self.asr_model.transcribe(audio_path).strip().lower()
            
            if settings.activation_phrase in full_text:
                activation_index = full_text.find(settings.activation_phrase)
                text_after_activation = full_text[activation_index + len(settings.activation_phrase):].strip()
                
                punctuation = '.,!?;:'
                text_after_activation = text_after_activation.lstrip(punctuation).strip()
                
                logger.info(f"Transcribed (after activation): {text_after_activation}")
                return text_after_activation if text_after_activation else full_text
            
            logger.info(f"Transcribed: {full_text}")
            return full_text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
        finally:
            if audio_path and os.path.exists(audio_path):
                max_attempts = 5
                for attempt in range(max_attempts):
                    try:
                        time.sleep(0.1)
                        os.unlink(audio_path)
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.2)
                        else:
                            logger.warning(f"Could not delete temp file after {max_attempts} attempts: {audio_path}")
                    except Exception as e:
                        logger.error(f"Error deleting temp file: {e}")
                        break
    
    def _text_to_number_words(self, text: str) -> str:
        ones = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
        tens = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят', 'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
        teens = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']
        hundreds = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот', 'шестьсот', 'семьсот', 'восемьсот', 'девятьсот']
        
        def number_to_words(n: int) -> str:
            if n == 0:
                return 'ноль'
            
            if n < 0:
                return 'минус ' + number_to_words(-n)
            
            if n < 10:
                return ones[n]
            
            if 10 <= n < 20:
                return teens[n - 10]
            
            if 20 <= n < 100:
                return (tens[n // 10] + ' ' + ones[n % 10]).strip()
            
            if 100 <= n < 1000:
                return (hundreds[n // 100] + ' ' + number_to_words(n % 100)).strip()
            
            if 1000 <= n < 1000000:
                thousands = n // 1000
                remainder = n % 1000
                
                if thousands % 10 == 1 and thousands % 100 != 11:
                    thousand_word = 'тысяча'
                elif thousands % 10 in [2, 3, 4] and thousands % 100 not in [12, 13, 14]:
                    thousand_word = 'тысячи'
                else:
                    thousand_word = 'тысяч'
                
                thousand_ones = ['', 'одна', 'две', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
                
                def thousands_to_words(k: int) -> str:
                    if k == 0:
                        return ''
                    if k < 10:
                        return thousand_ones[k]
                    if 10 <= k < 20:
                        return teens[k - 10]
                    if 20 <= k < 100:
                        return (tens[k // 10] + ' ' + thousand_ones[k % 10]).strip()
                    if 100 <= k < 1000:
                        return (hundreds[k // 100] + ' ' + thousands_to_words(k % 100)).strip()
                    return str(k)
                
                result = thousands_to_words(thousands) + ' ' + thousand_word
                if remainder > 0:
                    result += ' ' + number_to_words(remainder)
                return result.strip()
            
            if 1000000 <= n < 1000000000:
                millions = n // 1000000
                remainder = n % 1000000
                
                if millions % 10 == 1 and millions % 100 != 11:
                    million_word = 'миллион'
                elif millions % 10 in [2, 3, 4] and millions % 100 not in [12, 13, 14]:
                    million_word = 'миллиона'
                else:
                    million_word = 'миллионов'
                
                result = number_to_words(millions) + ' ' + million_word
                if remainder > 0:
                    result += ' ' + number_to_words(remainder)
                return result.strip()
            
            return str(n)
        
        def replace_time(match):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            return f"{number_to_words(hours)} {number_to_words(minutes)}"
        
        text = re.sub(r'\b(\d{1,2}):(\d{2})\b', replace_time, text)
        
        def replace_number(match):
            num_str = match.group(0)
            if ',' in num_str or '.' in num_str:
                return num_str
            return number_to_words(int(num_str))
        
        text = re.sub(r'\b\d+\b', replace_number, text)
        
        return text
    
    def _clean_text_for_tts(self, text: str) -> str:
        if self.tts_provider == "vosk":
            text = re.sub(r'(\d+)[.,](\d+)', lambda m: f"{m.group(1)} запятая {m.group(2)}", text)
            
            text = re.sub(r'(\d+)\s*%', lambda m: f"{m.group(1)} процентов", text)
            
            text = re.sub(r'(\d+)\s*м/с', lambda m: f"{m.group(1)} метров в секунду", text)
            
            text = re.sub(r'(\d+)\s*мм рт\.?\s*ст\.?', lambda m: f"{m.group(1)} миллиметров ртутного столба", text)
            
            text = re.sub(r'[–−—]\s*(\d+)', r'минус \1', text)
            
            text = re.sub(r'°C|°С|℃|градусов Цельсия|градуса Цельсия|градус Цельсия', ' градусов цельсия', text, flags=re.IGNORECASE)
            text = re.sub(r'°C|°С|°c|°с', ' градусов', text)
            text = re.sub(r'°', ' градусов', text)
            
            
            text = self._text_to_number_words(text)
            
            text = text.replace('—', '-')
            text = text.replace('–', '-')
            text = re.sub(r'\.\.\.', ' ', text)
            text = re.sub(r'…', ' ', text)
            
            allowed_pattern = re.compile('[^а-яА-ЯёЁ0-9!.,:?\s-]')
            text = allowed_pattern.sub('', text)
            
            text = re.sub(r'\s+', ' ', text)
        
        elif self.tts_provider == "xtts":
            text = re.sub(r'[–−—]\s*(\d+)', r'минус \1', text)
            
            text = re.sub(r'°C|°С|℃', ' градусов Цельсия', text, flags=re.IGNORECASE)
            text = re.sub(r'°', ' градусов', text)
            
            text = re.sub(r'\.\.\.', ' ', text)
            text = re.sub(r'…', ' ', text)
            
            text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def speak(self, text):
        if not self.tts_model:
            logger.info(f"TTS unavailable. Text: {text}")
            return
            
        temp_audio_path = None
        try:
            cleaned_text = self._clean_text_for_tts(text)
            
            if not cleaned_text:
                logger.warning("Text became empty after cleaning")
                return
            
            temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            logger.info(f"Speaking: {cleaned_text}")
            
            if self.tts_provider == "vosk":
                self.synth.synth(cleaned_text, temp_audio_path, speaker_id=settings.tts_speaker_id)
            elif self.tts_provider == "xtts":
                self.tts_model.tts_to_file(
                    text=cleaned_text,
                    speaker=settings.tts_xtts_speaker,
                    language=settings.tts_xtts_language,
                    file_path=temp_audio_path
                )
            
            self._play_audio(temp_audio_path)
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                max_attempts = 5
                for attempt in range(max_attempts):
                    try:
                        time.sleep(0.3)
                        os.unlink(temp_audio_path)
                        break
                    except PermissionError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.2)
                        else:
                            logger.warning(f"Could not delete temp file after {max_attempts} attempts: {temp_audio_path}")
                    except Exception as e:
                        logger.error(f"Error deleting temp audio file: {e}")
                        break
    
    def _play_audio(self, file_path):
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                try:
                    import pygame
                    
                    if not hasattr(self, 'pygame_initialized') or not self.pygame_initialized:
                        pygame.mixer.init()
                        self.pygame_initialized = True
                    else:
                        pygame.mixer.music.stop()
                    
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy() and not self.stop_playback_flag:
                        import time
                        time.sleep(0.1)
                    
                    if self.stop_playback_flag:
                        pygame.mixer.music.stop()
                    
                    time.sleep(0.5)
                        
                except ImportError:
                    logger.warning("pygame not available, trying winmm")
                    try:
                        import winsound
                        import threading
                        
                        def play_with_winsound():
                            winsound.PlaySound(file_path, winsound.SND_FILENAME)
                        
                        play_thread = threading.Thread(target=play_with_winsound, daemon=True)
                        play_thread.start()
                        
                        while play_thread.is_alive() and not self.stop_playback_flag:
                            import time
                            time.sleep(0.1)
                        
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"winsound failed: {e}")
                    
            elif system == "Darwin":
                self.playback_process = subprocess.Popen(
                    ['afplay', file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                while self.playback_process.poll() is None and not self.stop_playback_flag:
                    import time
                    time.sleep(0.1)
                if self.stop_playback_flag and self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process = None
                time.sleep(0.5)
            else:
                self.playback_process = subprocess.Popen(
                    ['mpg123', file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                while self.playback_process.poll() is None and not self.stop_playback_flag:
                    import time
                    time.sleep(0.1)
                if self.stop_playback_flag and self.playback_process:
                    self.playback_process.terminate()
                    self.playback_process = None
                time.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self.playback_process = None
    
    def cleanup(self):
        try:
            if hasattr(self, 'playback_audio') and self.playback_audio:
                self.playback_audio.terminate()
                self.playback_audio = None
                
            if hasattr(self, 'audio') and self.audio:
                self.audio.terminate()
                
            logger.info("Voice handler cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


    def speak_streaming(self, text_iterator, buffer_size: int = 50):
        """Synthesize and play audio in parallel with text generation"""
        import queue
        from threading import Thread
        
        text_queue = queue.Queue(maxsize=5)
        stop_event = threading.Event()
        
        def text_collector():
            buffer = ""
            for chunk in text_iterator:
                buffer += chunk
                
                if len(buffer) >= buffer_size:
                    last_space = buffer.rfind(' ', 0, len(buffer))
                    if last_space > 0:
                        to_speak = buffer[:last_space].strip()
                        if to_speak:
                            text_queue.put(to_speak)
                        buffer = buffer[last_space:].strip()
            
            if buffer.strip():
                text_queue.put(buffer.strip())
            
            text_queue.put(None)
        
        def audio_player():
            while not stop_event.is_set():
                try:
                    text = text_queue.get(timeout=0.1)
                    if text is None:
                        break
                    
                    temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_audio_path = temp_audio.name
                    temp_audio.close()
                    
                    try:
                        self.synth.synth(text, temp_audio_path, speaker_id=settings.tts_speaker_id)
                        self._play_audio(temp_audio_path)
                    finally:
                        if os.path.exists(temp_audio_path):
                            try:
                                time.sleep(0.2)
                                os.unlink(temp_audio_path)
                            except:
                                pass
                            
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in audio player: {e}")
        
        collector_thread = Thread(target=text_collector, daemon=True)
        player_thread = Thread(target=audio_player, daemon=True)
        
        collector_thread.start()
        player_thread.start()
        
        collector_thread.join()
        player_thread.join()