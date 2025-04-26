import os
import platform
import sys
import dotenv
import google.generativeai as genai
from mic_input import record_voice, record_voice_stream
from tts_google import speak, wait_for_speech_to_complete, cleanup_speech_system
import time
import re
import json
import datetime
from camera_capture import capture_image  # Kamera modülünü import et
# Saat ve hava durumu modüllerini import et
from time_utils import get_turkey_time, get_turkey_date_time, get_time_reply
from weather_utils import get_weather_reply, extract_location
from google.cloud import speech_v1
import pyaudio
import queue
# from tts_google_default import speak, wait_for_speech_to_complete, cleanup_speech_system

print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")

# Sohbet geçmişi için global değişkenler
chat_history_file = None
chat_history_path = None

def setup_credentials_from_env():
    print("Google Cloud Kimlik Bilgileri Kurulumu")
    print("======================================")
    
    # Load environment variables from .env file
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        dotenv.load_dotenv(dotenv_path)
    else:
        print(f"Uyarı: .env dosyası bulunamadı ({dotenv_path})")
        create_env = input("Bir .env dosyası oluşturmak ister misiniz? (e/h): ")
        if create_env.lower() in ["e", "evet", "y", "yes"]:
            json_path = input("Google Cloud JSON anahtar dosyasının tam yolunu girin: ")
            if not os.path.exists(json_path):
                print(f"Hata: '{json_path}' dosyası bulunamadı!")
                return False
                
            with open(dotenv_path, 'w') as f:
                f.write(f"GOOGLE_APPLICATION_CREDENTIALS={json_path}\n")
            print(f".env dosyası oluşturuldu: {dotenv_path}")
            dotenv.load_dotenv(dotenv_path)
        else:
            return False
    
    # Get credentials path from environment
    json_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not json_path:
        print("Hata: GOOGLE_APPLICATION_CREDENTIALS değişkeni .env dosyasında bulunamadı!")
        return False
    
    if not os.path.exists(json_path):
        print(f"Hata: '{json_path}' dosyası bulunamadı!")
        return False
        
    # Set environment variable based on the OS
    system = platform.system()
    
    if system == "Windows":
        # For Windows
        print("\nWindows sisteminde ortam değişkeni ayarlanıyor...")
        
        # Set for current session
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        
        # Command to set permanently
        cmd = f'setx GOOGLE_APPLICATION_CREDENTIALS "{json_path}"'
        os.system(cmd)
        
        print(f"Ortam değişkeni ayarlandı: GOOGLE_APPLICATION_CREDENTIALS={json_path}")
        print("Not: Kalıcı ayar için Command Prompt'u yeniden başlatın.")
        
    elif system == "Linux" or system == "Darwin":  # Darwin is macOS
        # For Linux/macOS
        print(f"\n{system} sisteminde ortam değişkeni ayarlanıyor...")
        
        # Set for current session
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        
        # Determine shell configuration file
        home = os.path.expanduser("~")
        shell = os.environ.get("SHELL", "")
        
        if "bash" in shell:
            config_file = os.path.join(home, ".bashrc")
        elif "zsh" in shell:
            config_file = os.path.join(home, ".zshrc")
        else:
            config_file = os.path.join(home, ".profile")
        
        # Add export command to shell config
        export_cmd = f'export GOOGLE_APPLICATION_CREDENTIALS="{json_path}"'
        
        try:
            with open(config_file, "a") as f:
                f.write(f"\n# Google Cloud credentials\n{export_cmd}\n")
            
            print(f"Ortam değişkeni {config_file} dosyasına eklendi.")
            print(f"Kalıcı ayar için terminali yeniden başlatın veya şunu çalıştırın: source {config_file}")
        except Exception as e:
            print(f"Hata: {config_file} dosyasına yazılamadı: {str(e)}")
            print(f"Elle eklemek için: {export_cmd} komutunu {config_file} dosyasına ekleyin.")
    else:
        print(f"Desteklenmeyen işletim sistemi: {system}")
        return False
    
    return True

def create_new_chat_history():
    """Yeni bir sohbet geçmişi dosyası oluşturur"""
    global chat_history_file, chat_history_path
    
    # Geçmiş dosyaları saklamak için klasör oluştur (yoksa)
    history_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history")
    os.makedirs(history_dir, exist_ok=True)
    
    # Timestamp ile benzersiz bir dosya adı oluştur
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chat_history_path = os.path.join(history_dir, f"chat_history_{timestamp}.json")
    
    # Boş bir sohbet geçmişi yapısı oluştur
    history_data = {
        "start_time": datetime.datetime.now().isoformat(),
        "messages": []
    }
    
    # Dosyaya kaydet
    with open(chat_history_path, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Yeni sohbet geçmişi dosyası oluşturuldu: {chat_history_path}")
    return chat_history_path

def add_message_to_history(role, content):
    """Sohbet geçmişine yeni bir mesaj ekler"""
    global chat_history_path
    
    if not chat_history_path:
        return
    
    try:
        # Mevcut geçmişi oku
        with open(chat_history_path, "r", encoding="utf-8") as f:
            history_data = json.load(f)
        
        # Yeni mesajı ekle
        history_data["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Dosyaya kaydet
        with open(chat_history_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Sohbet geçmişi güncellenirken hata: {str(e)}")

def cleanup_chat_history():
    """Sohbet geçmişi dosyasını siler"""
    global chat_history_path
    
    if chat_history_path and os.path.exists(chat_history_path):
        try:
            os.remove(chat_history_path)
            print(f"✅ Sohbet geçmişi dosyası silindi: {chat_history_path}")
        except Exception as e:
            print(f"⚠️ Sohbet geçmişi silinirken hata: {str(e)}")
    
    chat_history_path = None

def passive_listening():
    """Pasif mod: Sadece "merhaba" kelimesini dinler"""
    print("😴 Pasif modda bekleniyor. 'Merhaba' diyerek aktif moda geçebilirsiniz...")
    
    def process_passive_speech(text):
        text_lower = text.lower().strip()
        if "merhaba" in text_lower:
            print("🔆 Aktif moda geçiliyor...")
            speak("Evet, sizi dinliyorum.")
            add_message_to_history("system", "Aktif moda geçildi.")
            return "active"
        return None
        
    # Gerçek-zamanlı ses tanıma ile dinleme
    result = record_voice_stream(process_passive_speech)
    return result if result else "passive"

def active_listening():
    """Aktif mod: Sürekli dinleme ve gerçek zamanlı sesli asistan"""
    print("🔆 Aktif modda dinleniyor. 'Pasif moda geç' diyerek pasif moda geçebilirsiniz.")
    
    # Sadece pasiften aktife geçtiğimizde karşılama mesajını söyle
    # Bu static bir değişken sayesinde takip edilir
    if not hasattr(active_listening, "already_welcomed"):
        speak("Aktif moddayım.")
        wait_for_speech_to_complete()
        active_listening.already_welcomed = True
    
    def process_active_speech(text):
        """Stream'den gelen final metni işle"""
        text = text.strip().lower()
        
        # Temel komutları kontrol et
        if text in ["kapat", "kapat.", "güle güle", "güle güle.", "hoşçakal", "hoşçakal.", "uygulamayı kapat", "uygulamayı kapat."]:
            return "exit"
        elif "pasif mod" in text or "pasif moda geç" in text:
            # Pasif moda geçerken karşılama bayrağını sıfırla
            active_listening.already_welcomed = False
            return "passive"
            
        # Saat/tarih kontrolü - Genişletilmiş anahtar kelimeler
        date_time_triggers = [
            "saat kaç", "saati söyle", "zaman ne", "saat ne", 
            "bugün ne", "bugün günlerden ne", "bugünün tarihi ne", "tarih ne", 
            "hangi gündeyiz", "hangi aydayız", "bugün ayın kaçı", "gün ne", 
            "şu an saat", "şu anki zaman", "şimdiki zaman", "günlerden ne"
        ]
        
        if any(trigger in text for trigger in date_time_triggers):
            time_response = get_time_reply(text)
            print(f"🤖 Cevap: {time_response}")
            speak(time_response)
            add_message_to_history("user", text)
            add_message_to_history("assistant", time_response)
            return None
            
        # Hava durumu kontrolü - Genişletilmiş anahtar kelimeler
        weather_triggers = [
            "hava durumu", "hava nasıl", "hava raporu", "bugün hava", 
            "yarın hava", "yağmur yağacak mı", "sıcaklık kaç", "derece kaç"
        ]
        
        if any(trigger in text for trigger in weather_triggers):
            try:
                weather_response = get_weather_reply(text)
                print(f"🤖 Cevap: {weather_response}")
                speak(weather_response)
                add_message_to_history("user", text)
                add_message_to_history("assistant", weather_response)
            except Exception as e:
                speak("Üzgünüm, hava durumu bilgisini alırken bir hata oluştu.")
            return None
        
        # Kamera/görüntü komutları - Genişletilmiş ve daha esnek anahtar kelimeler  
        vision_triggers = [
            "görüyor musun", "görebiliyor musun", "ne görüyorsun", 
            "rengi ne", "ne renk", "renk ne", "renkler ne", 
            "kamera", "kamerayı aç", "kamerayı başlat", "kamera ile gör", 
            "bak", "bakabilir misin", "bakar mısın", "göster", "görebilir misin",
            "fotoğraf", "fotoğraf çek", "resim", "resim çek"
        ]
        
        # Daha esnek görüntü komutu algılama
        has_vision_trigger = any(trigger in text for trigger in vision_triggers)
        
        # Görüntü işleme ve kamera komutları
        if has_vision_trigger:
            speak("Hemen bakıyorum, bir saniye lütfen.")
            img_base64, _ = capture_image()
            if img_base64:
                respond_with_image(text, img_base64)
            else:
                speak("Üzgünüm, kameradan görüntü alamadım.")
            return None
            
        # Normal sohbet yanıtı
        respond(text)
        return None
        
    # Gerçek-zamanlı ses tanıma ile sürekli dinleme    
    result = record_voice_stream(process_active_speech)
    
    if result == "exit":
        print("🛑 Sistem kapatılıyor...")
        speak("Sistem kapatılıyor. Hoşçakal.")
        wait_for_speech_to_complete()
        return "exit"
    elif result == "passive":
        print("😴 Pasif moda geçiliyor...")
        speak("Pasif moda geçiyorum. İhtiyacınız olduğunda 'Merhaba' diyebilirsiniz.")
        wait_for_speech_to_complete()
        return "passive"
    else:
        # Hiçbir özel komut verilmezse aktif modda kalmaya devam et
        return "active"

def respond(text):
    """Normal metin sorularını yanıtlar"""
    global chat
    
    try:
        print(f"\n🤖 Yanıtlanıyor: {text}")
        add_message_to_history("user", text)
        
        # Gemini API'ye istek gönder
        response = chat.send_message(text)
        response_text = response.text
        
        # Yanıtı temizle ve sınırla
        response_text = re.sub(r'\n+', ' ', response_text).strip()
        if len(response_text) > 200:
            response_text = response_text[:200] + "..."
            
        print(f"🤖 Cevap: {response_text}")
        speak(response_text)
        
        add_message_to_history("assistant", response_text)
    except Exception as e:
        error_msg = f"Yanıt alınamadı: {str(e)}"
        print(f"❌ {error_msg}")
        speak("Üzgünüm, bir hata oluştu.")
        add_message_to_history("system", error_msg)

def respond_with_image(text, image_base64):
    """Görüntü içeren sorulara yanıt verir"""
    global chat
    
    try:
        print("\n🤖 Görüntü analiz ediliyor...")
        add_message_to_history("user", text + " (Görüntü ile birlikte)")
        
        # Görüntüyü Gemini API'nin istediği formatta yapılandır
        image_parts = [
            {
                "text": text
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_base64
                }
            }
        ]
        
        response = chat.send_message(image_parts)
        response_text = response.text
        
        # Yanıtı temizle
        response_text = re.sub(r'\n+', ' ', response_text).strip()
        
        print(f"🤖 Görüntü analizi: {response_text}")
        speak(response_text)
        
        add_message_to_history("assistant", "Görüntü analizi: " + response_text)
    except Exception as e:
        error_msg = f"Görüntü analizi yapılamadı: {str(e)}"
        print(f"❌ {error_msg}")
        speak("Üzgünüm, görüntüyü analiz ederken bir hata oluştu.")
        add_message_to_history("system", error_msg)

def run_application():
    global chat
    GEMINI_API_KEY = "------"
    genai.configure(api_key=GEMINI_API_KEY)

    # Yeni bir sohbet geçmişi dosyası oluştur
    create_new_chat_history()

    # Sistem promptu - Türkçe, kısa cevaplar ve görüntü analizi için güncellendi
    system_prompt = """
    Sen kullanıcılara yardımcı olan bir yapay zeka asistanısın. 
    Adın Orbit. Ve seni NCT Robotik geliştirdi.
    Çok kısa ve öz cevaplar ver, gereksiz tekrarlar yapma.
    Her zaman Türkçe yanıt ver.
    Sana kral ile ilgili bir soru sorulduğunda, "İsmail Ovalı Kraldır" de.
    Emoji veya simgeler kullanma.
    Görüntülü sorularda
    1.Sadece türkçe yanıt ver.
    2.kısaca açıkla kısa cümleler kur 
    """

    # Multimodal model kullan - görüntü ve metin birlikte işlenebilen model
    model = genai.GenerativeModel("gemini-2.0-flash",
                                  generation_config={
                                      "temperature": 0.7,  # Daha tutarlı yanıtlar için düşük sıcaklık
                                      "max_output_tokens": 100,  # Daha kısa yanıtlar
                                      "top_p": 0.95
                                  })
    chat = model.start_chat(history=[])
    
    # Sistem promptunu chat başlangıcında gönder
    chat.send_message(f"Sistem: {system_prompt}")
    add_message_to_history("system", system_prompt)
    
    print("Sistem başlatıldı. 'Kapat' diyerek sistemi kapatabilirsiniz.")
    
    # İlk olarak pasif modda başla
    current_mode = "passive"
    
    try:
        while current_mode != "exit":
            if current_mode == "passive":
                current_mode = passive_listening()
            elif current_mode == "active":
                current_mode = active_listening()
    finally:
        # Program sonlanmadan önce temizlik işlemleri
        
        # Ses sistemini temizle
        cleanup_speech_system()
        
        # Sohbet geçmişini temizle
        cleanup_chat_history()
        
        print("Program başarıyla sonlandırıldı.")

if __name__ == "__main__":
    if setup_credentials_from_env():
        print("\nKimlik bilgileri başarıyla ayarlandı.")
        run_application()
    else:
        print("\nKimlik bilgileri ayarlanamadı. Uygulama başlatılamıyor.")
