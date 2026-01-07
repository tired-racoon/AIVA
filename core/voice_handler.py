import os
import sys

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
        self.asr_model = gigaam.load_model("v2_rnnt")
        logger.info("ASR model loaded")
        
        logger.info(f"Loading TTS model: {settings.tts_model_name}")
        self.tts_model = Model(model_name=settings.tts_model_name)
        self.synth = Synth(self.tts_model)
        logger.info("TTS model loaded")
        
        self.buffer_size = int(settings.buffer_duration * self.rate / self.chunk)
        self.audio_buffer = deque(maxlen=self.buffer_size)
        
        self.silence_chunks = int(settings.silence_duration * self.rate / self.chunk)
        
        self.playback_audio = None
    
    def _calculate_amplitude(self, audio_data):
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        return np.abs(audio_array).mean()
    
    def _calculate_frequency_energy(self, audio_data):
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        frequencies, power_spectrum = signal.periodogram(audio_array, self.rate)
        
        freq_mask = (frequencies >= settings.min_frequency) & (frequencies <= settings.max_frequency)
        speech_energy = np.sum(power_spectrum[freq_mask])
        
        return speech_energy
    
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
        
        try:
            while True:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    continue
                    
                self.audio_buffer.append(data)
                
                if len(self.audio_buffer) >= self.buffer_size:
                    frames = list(self.audio_buffer)
                    audio_path = self._save_buffer_to_file(frames)
                    
                    if not audio_path:
                        continue
                    
                    try:
                        text = self.asr_model.transcribe(audio_path).strip().lower()
                        
                        if settings.activation_phrase in text:
                            logger.info(f"Activation detected: {text}")
                            try:
                                os.unlink(audio_path)
                            except:
                                pass
                            stream.stop_stream()
                            stream.close()
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
        frames = list(self.audio_buffer)
        silence_counter = 0
        
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
                
                if amplitude < settings.silence_threshold and freq_energy < 1000:
                    silence_counter += 1
                else:
                    silence_counter = 0
                
                if silence_counter >= self.silence_chunks:
                    logger.info("End of speech detected")
                    break
                
                if len(frames) > self.rate / self.chunk * 10:
                    logger.info("Max recording time reached")
                    break
        
        finally:
            stream.stop_stream()
            stream.close()
        
        audio_path = self._save_buffer_to_file(frames)
        return audio_path
    
    def transcribe(self, audio_path):
        if not audio_path:
            return ""
            
        try:
            text = self.asr_model.transcribe(audio_path)
            logger.info(f"Transcribed: {text}")
            return text.strip()
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    import time
                    time.sleep(0.05)
                    os.unlink(audio_path)
                except Exception as e:
                    logger.error(f"Error deleting temp file: {e}")
    
    def speak(self, text):
        if not self.synth:
            logger.info(f"TTS unavailable. Text: {text}")
            return
            
        temp_audio_path = None
        try:
            temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            logger.info(f"Speaking: {text}")
            self.synth.synth(text, temp_audio_path, speaker_id=settings.tts_speaker_id)
            
            self._play_audio(temp_audio_path)
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    import time
                    time.sleep(0.2)
                    os.unlink(temp_audio_path)
                except Exception as e:
                    logger.error(f"Error deleting temp audio file: {e}")
    
    def _play_audio(self, audio_path):
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                wf = wave.open(audio_path, 'rb')
                
                if self.playback_audio is None:
                    self.playback_audio = pyaudio.PyAudio()
                
                stream = self.playback_audio.open(
                    format=self.playback_audio.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True
                )
                
                chunk_size = 1024
                data = wf.readframes(chunk_size)
                
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk_size)
                
                stream.stop_stream()
                stream.close()
                wf.close()
                    
            elif system == "Darwin":
                import subprocess
                subprocess.run(['afplay', audio_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import subprocess
                subprocess.run(['aplay', audio_path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
    
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