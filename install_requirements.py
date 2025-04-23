import subprocess
import sys

def install_requirements():
    packages = [
        "google-generativeai",
        "google-cloud-texttospeech",
        "SpeechRecognition",
        "pygame",
        "pyaudio",
        "opencv-python",  # Kamera işlemleri için eklendi
        "python-dotenv"  
        "google-cloud-speech" # .env dosyaları için eklendi
    ]
    
    print("📦 Gerekli paketler yükleniyor...")
    
    for package in packages:
        print(f"Yükleniyor: {package}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} başarıyla yüklendi!")
        except Exception as e:
            if package == "pyaudio":
                print("⚠️ PyAudio yüklenirken hata oluştu. Pipwin ile deneniyor...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "pipwin"])
                    subprocess.check_call([sys.executable, "-m", "pipwin", "install", "pyaudio"])
                    print("✅ PyAudio başarıyla yüklendi!")
                except Exception as e:
                    print(f"❌ PyAudio yüklenemedi: {str(e)}")
            else:
                print(f"❌ {package} yüklenemedi: {str(e)}")
    
    print("\n📋 Kurulum tamamlandı!")
    print("Şimdi main.py dosyasını çalıştırabilirsiniz.")

if __name__ == "__main__":
    install_requirements()