import os
import platform
import sys
import shutil

def setup_redirect():
    print("Google Cloud Kimlik Bilgileri Kurulumu")
    print("======================================")
    print("Not: Kimlik bilgileri artık main.py üzerinden .env dosyası kullanılarak yönetiliyor.")
    
    # Create .env file if it doesn't exist
    env_example = os.path.join(os.path.dirname(__file__), '.env.example')
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_file) and os.path.exists(env_example):
        try:
            shutil.copy(env_example, env_file)
            print(f".env.example dosyası .env olarak kopyalandı. Lütfen içindeki değerleri düzenleyin.")
        except Exception as e:
            print(f"Hata: .env dosyası oluşturulamadı: {str(e)}")
    
    print("\nKuruluma devam etmek için main.py dosyasını çalıştırın.")
    
    run_now = input("Şimdi main.py'yi çalıştırmak ister misiniz? (e/h): ")
    if run_now.lower() in ["e", "evet", "y", "yes"]:
        print("\nUygulama başlatılıyor...\n")
        os.system(f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'main.py')}")
    
    return True

if __name__ == "__main__":
    setup_redirect()