import os
import platform
import sys
import dotenv
import google.generativeai as genai
from mic_input import record_voice
from tts_google import speak, wait_for_speech_to_complete, cleanup_speech_system
import time
import re
import json
import datetime
from camera_capture import capture_image  # Kamera modülünü import et
# Saat ve hava durumu modüllerini import et
from time_utils import get_turkey_time, get_turkey_date_time, get_time_reply
from weather_utils import get_weather_reply, extract_location

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

def run_application():
    GEMINI_API_KEY = "AIzaSyCCvDK_NXzvwuVVn7-LSInbqT7vYl6S9b8"
    genai.configure(api_key=GEMINI_API_KEY)

    # Yeni bir sohbet geçmişi dosyası oluştur
    create_new_chat_history()

    # Sistem promptu - Türkçe, kısa cevaplar ve görüntü analizi için güncellendi
    system_prompt = """
    Sen kullanıcılara yardımcı olan bir yapay zeka asistanısın. 
    Adın Orbit. Ve seni NCT Robotik geliştirdi.
    Çok kısa ve öz cevaplar ver, gereksiz tekrarlar yapma.
    Her zaman Türkçe yanıt ver.
    Görüntülü sorularda
    1.Sadece türkçe yanıt ver.
    2.kısaca açıkla kısa cümleler kur 
    """

    # Multimodal model kullan - görüntü ve metin birlikte işlenebilen model
    model = genai.GenerativeModel("gemini-1.5-pro",
                                  generation_config={
                                      "temperature": 0.2,  # Daha tutarlı yanıtlar için düşük sıcaklık
                                      "max_output_tokens": 100,  # Daha kısa yanıtlar
                                      "top_p": 0.95
                                  })
    chat = model.start_chat(history=[])
    
    # Sistem promptunu chat başlangıcında gönder
    chat.send_message(f"Sistem: {system_prompt}")
    add_message_to_history("system", system_prompt)
    
    def respond_with_image(prompt, img_base64):
        """Kullanıcı sorusunu ve kameradan alınan görüntüyü modele gönderir"""
        sentence_buffer = ""
        print("🤖 (Görüntü ile) Cevap: ", end="", flush=True)
        
        try:
            # Kullanıcı renk soruyorsa özel bir talimat ekleyelim
            if "renk" in prompt.lower() or "reng" in prompt.lower():
                custom_prompt = f"{prompt} (Lütfen sadece görseldeki nesnenin veya nesnelerin rengini kısaca Türkçe açıkla)"
            else:
                custom_prompt = prompt
            
            # Sohbet geçmişine kullanıcı mesajını kaydet
            add_message_to_history("user", prompt + " [görüntü ile]")
            
            # Doğru görüntü gönderme formatı - Google Gemini API'ye uygun
            parts = [
                {"text": custom_prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img_base64
                    }
                }
            ]
            
            # Modele içeriği gönder - parts parametresi kullanarak
            response = model.generate_content(parts, stream=True)
            full_response = ""
            
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    print(chunk.text, end="", flush=True)
                    sentence_buffer += chunk.text
                    full_response += chunk.text
                    
                    # Cümleleri noktalama işaretlerine göre böl ve konuşmaya gönder
                    sentences = re.split(r'([.!?]+\s+|\n+)', sentence_buffer)
                    if len(sentences) > 1:
                        # En azından bir cümle tamamlandı
                        for i in range(0, len(sentences)-1, 2):
                            if i+1 < len(sentences):
                                complete_sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                                if complete_sentence.strip():
                                    speak(complete_sentence)
                        
                        # Kalan kısmı sakla
                        sentence_buffer = sentences[-1] if len(sentences) % 2 == 1 else ""
            
            # Kalan cümle parçasını konuşma
            if sentence_buffer.strip():
                speak(sentence_buffer)
            
            # Sohbet geçmişine asistan cevabını kaydet
            add_message_to_history("assistant", full_response)
                
        except Exception as e:
            error_msg = f"Görüntü işleme hatası: {str(e)}"
            print(f"\n❌ {error_msg}")
            speak("Üzgünüm, görüntüyü işlerken bir hata oluştu.")
            add_message_to_history("error", f"Görüntü işleme hatası: {str(e)}")
            
        print()  # Yeni satır ekle
        
        # Konuşma tamamen bitene kadar bekle
        wait_for_speech_to_complete()

    def respond(prompt):
        """Sadece metin kullanarak yanıt verir"""
        sentence_buffer = ""
        print("🤖 Cevap: ", end="", flush=True)
        
        # Sohbet geçmişine kullanıcı mesajını kaydet
        add_message_to_history("user", prompt)
        
        full_response = ""
        for chunk in chat.send_message(prompt, stream=True):
            if chunk.text:
                print(chunk.text, end="", flush=True)
                sentence_buffer += chunk.text
                full_response += chunk.text
                
                # Cümleleri noktalama işaretlerine göre böl ve kuyruğa ekle
                sentences = re.split(r'([.!?]+\s+|\n+)', sentence_buffer)
                if len(sentences) > 1:
                    # En azından bir cümle tamamlandı
                    for i in range(0, len(sentences)-1, 2):
                        if i+1 < len(sentences):
                            complete_sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                            if complete_sentence.strip():
                                speak(complete_sentence)
                    
                    # Kalan kısmı sakla
                    sentence_buffer = sentences[-1] if len(sentences) % 2 == 1 else ""
        
        # Kalan cümle parçasını konuşma
        if sentence_buffer.strip():
            speak(sentence_buffer)
        
        # Sohbet geçmişine asistan cevabını kaydet
        add_message_to_history("assistant", full_response)
            
        print()  # Yeni satır ekle
        
        # Konuşma tamamen bitene kadar bekle
        wait_for_speech_to_complete()
    
    def passive_listening():
        """Pasif mod: Sadece "orbit" kelimesini dinler"""
        print("😴 Pasif modda bekleniyor. 'Merhaba' diyerek aktif moda geçebilirsiniz...")
        while True:
            user_input = record_voice()
            if user_input:
                user_input_lower = user_input.lower().strip()
                if "merhaba" in user_input_lower:
                    print("🔆 Aktif moda geçiliyor...")
                    speak("Evet, sizi dinliyorum.")
                    add_message_to_history("system", "Aktif moda geçildi.")
                    return "active"
            # Kısa bir bekleme ekleyerek sürekli dinleme yapmayı önle
            time.sleep(0.5)
    
    def active_listening():
        """Aktif mod: Normal sohbet modu"""
        print("🔆 Aktif modda dinleniyor. 'Pasif moda geç' diyerek pasif moda geçebilirsiniz.")
        
        # Selamlamayı sadece sesli olarak söyle, sohbet geçmişine veya API'ye gönderme
        speak("Aktif moddayım.")
        # Selamlama sesinin tamamlanmasını bekle
        wait_for_speech_to_complete()
        
        while True:
            user_input = record_voice()
            if user_input:
                user_input_lower = user_input.lower().strip()
                
                # Kapatma komutu
                if user_input_lower in ["kapat", "güle güle", "hoşçakal", "uygulamayı kapat"]:
                    print("🛑 Sistem kapatılıyor...")
                    speak("Sistem kapatılıyor. Hoşçakal.")
                    add_message_to_history("system", "Uygulama kapatıldı")
                    wait_for_speech_to_complete()  # Son konuşmanın tamamlanmasını bekle
                    return "exit"
                
                # Pasif moda geçiş komutu
                if "pasif mod" in user_input_lower or "pasif moda geç" in user_input_lower:
                    print("😴 Pasif moda geçiliyor...")
                    speak("Pasif moda geçiyorum. İhtiyacınız olduğunda 'Merhaba' diyebilirsiniz.")
                    add_message_to_history("system", "Pasif moda geçildi")
                    wait_for_speech_to_complete()  # Konuşmanın tamamlanmasını bekle
                    return "passive"
                
                # Saat sorgusu kontrolü
                if any(time_query in user_input_lower for time_query in 
                       ["saat kaç", "saati söyle", "şu an saat", "şimdiki saat", 
                        "saat kaçtır", "saati söyler misin", "saati göster", 
                        "bugün ne", "bugün günlerden ne", "bugün ayın kaçı", 
                        "tarih ne", "bugün tarih", "tarih göster"]):
                    
                    print("⏰ Saat/tarih sorgusu algılandı...")
                    # time_utils modülünü kullanarak yanıt oluştur
                    time_response = get_time_reply(user_input)
                    
                    print(f"🤖 Cevap: {time_response}")
                    
                    # Sohbet geçmişine ekle
                    add_message_to_history("user", user_input)
                    add_message_to_history("assistant", time_response)
                    
                    # Sesli yanıt ver
                    speak(time_response)
                    wait_for_speech_to_complete()
                    continue
                
                # Hava durumu sorgusu kontrolü
                if any(weather_query in user_input_lower for weather_query in 
                       ["hava durumu", "hava nasıl", "havalar nasıl", "hava raporu", 
                        "yağmur yağacak mı", "bugün hava", "yarın hava", 
                        "hava sıcaklığı", "sıcaklık kaç", "derece kaç"]):
                    
                    print("🌤️ Hava durumu sorgusu algılandı...")
                    print(f"Algılanan konum: {extract_location(user_input)}")
                    
                    try:
                        # weather_utils modülünü kullanarak yanıt oluştur
                        weather_response = get_weather_reply(user_input)
                        print(f"🤖 Cevap: {weather_response}")
                        
                        # Sohbet geçmişine ekle
                        add_message_to_history("user", user_input)
                        add_message_to_history("assistant", weather_response)
                        
                        # Sesli yanıt ver
                        speak(weather_response)
                        wait_for_speech_to_complete()
                    except Exception as e:
                        error_msg = f"Hava durumu sorgulanırken bir hata oluştu: {str(e)}"
                        print(f"❌ {error_msg}")
                        speak("Üzgünüm, hava durumu bilgisini alırken bir hata oluştu.")
                        wait_for_speech_to_complete()
                    continue
                
                # Görüntü ile işleme tetikleyicileri - renk algılama özellikleri için eklendi
                vision_triggers = [
                    "görüyor musun", "görebiliyor musun", "görsene", "bakabilir misin", 
                    "bak bakalım", "gör bakalım", "kameradan bak", "fotoğraf", "resim", "kamera",
                    "rengi ne", "renk", "renkli", "ne renk", "hangi renk"
                ]
                
                is_vision_request = any(trigger in user_input_lower for trigger in vision_triggers)
                
                if is_vision_request:
                    # Kameradan görüntü al - kaydetme işlemi yok
                    print("📸 Görüntü isteniyor, kamera etkinleştiriliyor...")
                    
                    # Renk sorgusu için özel mesaj
                    if any(keyword in user_input_lower for keyword in ["rengi ne", "renk", "renkli", "ne renk", "hangi renk"]):
                        speak("Hemen bakıyorum, bir saniye lütfen.")
                    else:
                        speak("Hemen bakıyorum,bir saniye lütfen.")
                    
                    # Görüntüyü çek ve base64 kodlanmış olarak al
                    img_base64, _ = capture_image()
                    
                    if img_base64:
                        # Modele görüntü ve metni birlikte gönder
                        respond_with_image(user_input, img_base64)
                    else:
                        # Kamera hatası durumunda - hata mesajını sadece konuş, sohbete ekleme
                        print("❌ Kamera hatası: Görüntü alınamadı")
                        speak("Üzgünüm, kameradan görüntü alamadım. Kamera bağlantınızı kontrol edin.")
                        # Konuşmanın bitmesini bekle
                        wait_for_speech_to_complete()
                else:
                    # Normal sohbet
                    respond(user_input)

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