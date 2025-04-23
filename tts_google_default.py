import importlib.util
import subprocess
import sys
import os
import pygame
import io
import threading
import time
import queue
import numpy as np
from pydub import AudioSegment
from google.cloud import texttospeech

# Gerekli paketleri yükle
def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"{package} not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("numpy")
install_and_import("pydub")

# Google Cloud TTS istemcisi
client = texttospeech.TextToSpeechClient()

# pygame başlat
pygame.init()
pygame.mixer.init()

# Konuşma kuyruğu
speech_queue = queue.Queue()
is_speaking = False
speech_end_event = threading.Event()
thread_running = True

# Amplitüd serisini çıkart
def extract_amplitude_series(audio_bytes, frame_duration_ms=30):
    try:
        sound = AudioSegment.from_file(audio_bytes, format="mp3")
        amplitudes = []
        for i in range(0, len(sound), frame_duration_ms):
            frame = sound[i:i + frame_duration_ms]
            samples = np.array(frame.get_array_of_samples())

            if frame.channels == 2:
                samples = samples.reshape((-1, 2))
                samples = samples.mean(axis=1)

            samples = samples / np.iinfo(samples.dtype).max
            amp = np.mean(np.abs(samples))
            amplitudes.append(amp)

        return amplitudes, len(sound) / 1000.0  # saniye
    except Exception as e:
        print(f"Amplitüd çıkarma hatası: {str(e)}")
        return [], 0

# Amplitüd verisini yazdır
def sync_amplitude_visuals(amplitudes, interval=0.03):
    def run():
        max_amp = max(amplitudes) if amplitudes else 1.0  # Bölme hatasını önle

        for amp in amplitudes:
            normalized = amp / max_amp
            scaled_amp = float(normalized * 120)  # 0-120 aralığına çek
            print(f"Anlık amplitüd: {scaled_amp:.2f}")
            time.sleep(interval)
    threading.Thread(target=run, daemon=True).start()

# Konuşmayı oynatan işçi thread
def speak_worker():
    global is_speaking
    while thread_running:
        try:
            try:
                audio_data, amplitudes = speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if audio_data is None:
                speech_queue.task_done()
                break

            is_speaking = True

            try:
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()

                # Amplitüd verisini senkronize et
                sync_amplitude_visuals(amplitudes)

                while pygame.mixer.music.get_busy() and thread_running:
                    time.sleep(0.1)

            except Exception as e:
                print(f"Ses çalma hatası: {str(e)}")

            is_speaking = False
            speech_queue.task_done()

        except Exception as e:
            print(f"speak_worker hatası: {str(e)}")
            is_speaking = False
            if not speech_queue.empty():
                speech_queue.task_done()

# Konuşma thread'i başlat
speech_thread = threading.Thread(target=speak_worker, daemon=True)
speech_thread.start()

# Konuşma fonksiyonu
def speak(text, lang="tr-TR", voice_name="tr-TR-Standard-C"):
    try:
        if len(text) < 5 and not text.endswith(('.', '!', '?')):
            if not speech_queue.empty() or is_speaking:
                return

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=lang,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        audio_bytes = io.BytesIO(response.audio_content)

        # Amplitüd verilerini çıkar
        amplitudes, duration = extract_amplitude_series(io.BytesIO(response.audio_content))
        print(f"{len(amplitudes)} adet amplitüd değeri çıkarıldı. Süre: {duration:.2f}s")

        # Kuyruğa ses ve amplitüd verisini birlikte koy
        speech_queue.put((audio_bytes, amplitudes))

    except Exception as e:
        print(f"TTS hatası: {str(e)}")

# Bekle
def wait_for_speech_to_complete():
    try:
        speech_queue.join()
        while is_speaking or pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"Bekleme hatası: {str(e)}")

# Temizle
def cleanup_speech_system():
    global thread_running
    try:
        print("TTS sistemi kapatılıyor...")
        thread_running = False
        while not speech_queue.empty():
            try:
                speech_queue.get_nowait()
                speech_queue.task_done()
            except:
                pass

        speech_queue.put((None, None))

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        if speech_thread.is_alive():
            speech_thread.join(timeout=1.0)

        pygame.mixer.quit()
        print("TTS sistemi kapatıldı.")
    except Exception as e:
        print(f"Kapatma hatası: {str(e)}")

# Örnek kullanım
if __name__ == "__main__":
    speak("AMR, bulunduğu ortamda kendi başına gezinme, engellerden kaçınma ve belirli görevleri yerine getirme yeteneğine sahip mobil robotlardır.")
    wait_for_speech_to_complete()
    cleanup_speech_system()
