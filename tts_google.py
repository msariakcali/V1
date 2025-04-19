import importlib.util
import subprocess
import sys

# Check if numpy is installed, if not install it
def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"{package} not found, installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install required packages
install_and_import("numpy")

# Now import numpy
import numpy as np

from google.cloud import texttospeech
import os
import pygame
import io
import threading
import time
import queue

client = texttospeech.TextToSpeechClient()
pygame.init()
pygame.mixer.init()

# Konuşma parçalarının tutulacağı kuyruk
speech_queue = queue.Queue()
# Konuşmacı durumu
is_speaking = False
# Konuşma bittiğinde kullanılacak olay
speech_end_event = threading.Event()
# Thread kontrolünü sağlamak için bayrak
thread_running = True

def speak_worker():
    """Kuyrukta bekleyen konuşma parçalarını sürekli çalar"""
    global is_speaking
    
    while thread_running:
        try:
            # timeout ile get, thread_running bayrağını kontrol etmek için fırsat verir
            try:
                audio_data = speech_queue.get(timeout=0.5)
            except queue.Empty:
                continue
                
            if audio_data is None:  # None değeri, thread'i sonlandırmak için işaret
                speech_queue.task_done()
                break
                
            is_speaking = True
            # Ses verisini çal
            try:
                pygame.mixer.music.load(audio_data)
                pygame.mixer.music.play()
                
                # Müzik çalışırken bir sonraki parçanın hazırlanması için kısa bekle
                while pygame.mixer.music.get_busy() and thread_running:
                    time.sleep(0.1)  # 100ms aralıklarla kontrol et
            except Exception as e:
                print(f"Ses çalma sırasında hata: {str(e)}")
            
            is_speaking = False
            speech_queue.task_done()
            
        except Exception as e:
            print(f"Ses çalma hatası (speak_worker): {str(e)}")
            is_speaking = False
            if not speech_queue.empty():
                speech_queue.task_done()

# Konuşma işçi thread'ini başlat
speech_thread = threading.Thread(target=speak_worker, daemon=True)
speech_thread.start()

def speak(text, lang="tr-TR", voice_name="tr-TR-Standard-C"):
    """Metni TTS ile sese çevirir ve kuyruğa ekler"""
    try:
        # Çok kısa metinleri birleştir (bu, çok küçük parçalar için gereksiz API çağrıları önler)
        if len(text) < 5 and not text.endswith(('.', '!', '?')):
            # Kuyrukta eleman varsa ve konuşma devam ediyorsa, çok kısa metni atlayalım
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

        # Ses verisini kuyruğa ekle
        audio_data = io.BytesIO(response.audio_content)
        speech_queue.put(audio_data)

    except Exception as e:
        print(f"TTS hatası: {str(e)}")

def wait_for_speech_to_complete():
    """Tüm konuşma parçaları bitene kadar bekler"""
    try:
        speech_queue.join()
        # Son parçanın çalması bitene kadar bekle
        while is_speaking or pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"Konuşma tamamlanma kontrolü sırasında hata: {str(e)}")

def cleanup_speech_system():
    """Ses sistemini temiz bir şekilde kapatır"""
    global thread_running
    
    try:
        print("TTS sistemi kapatılıyor...")
        # Thread'i durdurmak için bayrağı değiştir
        thread_running = False
        
        # Kuyruğu temizle
        while not speech_queue.empty():
            try:
                speech_queue.get_nowait()
                speech_queue.task_done()
            except:
                pass
        
        # None ekleyerek işçi thread'inin çıkmasını sağla
        speech_queue.put(None)
        
        # Müziği durdur
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        # Thread'in kapanmasını bekle
        if speech_thread.is_alive():
            speech_thread.join(timeout=1.0)
            
        # Pygame mixer'ı kapat
        pygame.mixer.quit()
        
        print("TTS sistemi başarıyla kapatıldı.")
    except Exception as e:
        print(f"TTS sistemi kapatılırken hata: {str(e)}")