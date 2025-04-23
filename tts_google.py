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

# TTS durum değişkenleri - global olarak diğer modüllere açık
is_speaking = False  # TTS konuşma durumu 
tts_active = False   # Genel TTS aktiflik durumu (konuşma + cooldown)
COOLDOWN_AFTER_TTS = 0.5  # TTS bitiminden sonra dinlemeyi engelleme süresi (saniye)
EARLY_LISTEN_START = 0.09  # Konuşma bitmeden bu kadar süre önce dinlemeye başla (saniye)
last_speech_end_time = 0  # TTS'in en son bitiş zamanı
speech_duration = 0        # Mevcut konuşmanın tahmini süresi
speech_start_time = 0      # Mevcut konuşmanın başlangıç zamanı

# Konuşma bittiğinde kullanılacak olay
speech_end_event = threading.Event()
# Thread kontrolünü sağlamak için bayrak
thread_running = True

def speak_worker():
    """Kuyrukta bekleyen konuşma parçalarını sürekli çalar"""
    global is_speaking, tts_active, last_speech_end_time, speech_duration, speech_start_time
    
    while thread_running:
        try:
            # timeout ile get, thread_running bayrağını kontrol etmek için fırsat verir
            try:
                audio_data = speech_queue.get(timeout=0.5)
            except queue.Empty:
                # Konuşma yoksa kontrol et: cooldown süresi bitti mi?
                if tts_active and not is_speaking and time.time() - last_speech_end_time > COOLDOWN_AFTER_TTS:
                    tts_active = False  # Cooldown süresi bitti, TTS tamamen pasif
                    print("\r✅ Dinleme aktif edildi        ", end="", flush=True)
                continue
                
            if audio_data is None:  # None değeri, thread'i sonlandırmak için işaret
                speech_queue.task_done()
                break
                
            is_speaking = True
            tts_active = True
            speech_start_time = time.time()
            print("\r🔊 Asistan konuşuyor - dinleme devre dışı", end="", flush=True)
            
            # Ses verisini çal
            try:
                # Ses dosyasını yükle
                pygame.mixer.music.load(audio_data)
                
                # Ses dosyasını tekrar pozisyonla başa ve süreyi hesapla
                audio_data.seek(0)  # Audio data'yı başa rewinding
                
                # Süre hesaplama için güvenli yöntem
                try:
                    # Geçici ses dosyasını kaydet
                    temp_audio_file = "temp_audio.mp3"
                    with open(temp_audio_file, 'wb') as f:
                        f.write(audio_data.getvalue())
                    
                    # Dosyadan ses nesnesini oluştur ve süresini al
                    sound = pygame.mixer.Sound(temp_audio_file)
                    speech_duration = sound.get_length()
                    
                    # Geçici dosyayı temizle
                    try:
                        os.remove(temp_audio_file)
                    except:
                        pass
                except:
                    # Süreyi tahmin et - ortalama konuşma hızı
                    speech_duration = 2.0  # Varsayılan 2 saniye
                
                # Çalmayı başlat
                pygame.mixer.music.play()
                
                # Başlangıç zamanı ve süre bilgisini görüntüle
                # print(f"\r🔊 Konuşma: {speech_duration:.1f}s", end="", flush=True)
                
                # Müzik çalışırken takip et ve erken dinleme başlatma için kontrol et
                start_time = time.time()
                while pygame.mixer.music.get_busy() and thread_running:
                    current_time = time.time()
                    elapsed_time = current_time - start_time
                    
                    # Eğer konuşmanın sonuna yaklaştıysak erken dinlemeyi aktifleştir
                    remaining_time = speech_duration - elapsed_time
                    if remaining_time <= EARLY_LISTEN_START:
                        # Erken dinleme başlat
                        if tts_active:
                            tts_active = False  # Dinlemeyi aktifleştir ama is_speaking'i tutmaya devam et
                            print(f"\r🔊→🎤 Dinlemeye erken başlanıyor ({EARLY_LISTEN_START}s)", end="", flush=True)
                    
                    time.sleep(0.05)  # 50ms aralıklarla kontrol et
            except Exception as e:
                print(f"\nSes çalma sırasında hata: {str(e)}")
            
            is_speaking = False
            last_speech_end_time = time.time()  # Konuşma bitiş zamanını kaydet
            print("\r✓ Konuşma tamamlandı                 ", end="", flush=True)
            speech_queue.task_done()
            
            # Eğer cooldown süresi isteniyorsa ekle, aksi halde hemen dinlemeye geç
            if tts_active and COOLDOWN_AFTER_TTS > 0:  # Eğer erken dinleme başlatılmadıysa
                time.sleep(COOLDOWN_AFTER_TTS)
                tts_active = False
                print("\r✅ Dinleme aktif edildi               ", end="", flush=True)
            
        except Exception as e:
            print(f"\nSes çalma hatası (speak_worker): {str(e)}")
            is_speaking = False
            tts_active = False  # Hata durumunda dinlemeyi aktifleştir
            last_speech_end_time = time.time()
            if not speech_queue.empty():
                speech_queue.task_done()

# Konuşma işçi thread'ini başlat
speech_thread = threading.Thread(target=speak_worker, daemon=True)
speech_thread.start()

def is_tts_active():
    """TTS'in aktif olup olmadığını kontrol eder (konuşma veya cooldown durumu)"""
    return tts_active

def speak(text, lang="tr-TR", voice_name="tr-TR-Standard-C"):
    """Metni TTS ile sese çevirir ve kuyruğa ekler"""
    global tts_active
    
    try:
        # Çok kısa metinleri birleştir (bu, çok küçük parçalar için gereksiz API çağrıları önler)
        if len(text) < 5 and not text.endswith(('.', '!', '?')):
            # Kuyrukta eleman varsa ve konuşma devam ediyorsa, çok kısa metni atlayalım
            if not speech_queue.empty() or is_speaking:
                return
        
        # TTS aktif olduğunu işaretle
        tts_active = True
        
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
    """Tüm konuşma parçaları ve cooldown süresi bitene kadar bekler"""
    try:
        speech_queue.join()
        # Son parçanın çalması bitene kadar bekle
        while is_speaking or pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        # Cooldown süresinin bitmesini de bekle
        cooldown_start = time.time()
        while time.time() - cooldown_start < COOLDOWN_AFTER_TTS:
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Konuşma tamamlanma kontrolü sırasında hata: {str(e)}")

def cleanup_speech_system():
    """Ses sistemini temiz bir şekilde kapatır"""
    global thread_running, tts_active, is_speaking
    
    try:
        print("TTS sistemi kapatılıyor...")
        # Thread'i durdurmak için bayrağı değiştir
        thread_running = False
        tts_active = False
        is_speaking = False
        
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