import cv2
import base64
import time
import os
import platform
import subprocess

def get_camera_device_id():
    """
    İşletim sistemine göre uygun kamera aygıt ID'sini döndürür
    
    Returns:
        int: Kamera aygıt ID'si
    """
    os_name = platform.system()
    
    if os_name == "Linux":
        # Linux'ta kamera cihazlarını kontrol et
        try:
            # v4l2-ctl komutu varsa kamera cihazlarını listele
            result = subprocess.run(["v4l2-ctl", "--list-devices"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   text=True,
                                   timeout=3)
            
            if result.returncode == 0:
                output = result.stdout
                print(f"Tespit edilen kamera cihazları:\n{output}")
                
                # /dev/video2 veya /dev/video3 içeren satırları ara
                if "/dev/video2" in output:
                    print("Kamera cihazı /dev/video2 kullanılıyor")
                    return 2
                elif "/dev/video3" in output:
                    print("Kamera cihazı /dev/video3 kullanılıyor")
                    return 3
                else:
                    # Diğer Linux video cihazlarını dene
                    for i in range(5):  # 0'dan 4'e kadar deney
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            cap.release()
                            print(f"Çalışan kamera bulundu: /dev/video{i}")
                            return i
        except Exception as e:
            print(f"Kamera tespitinde hata: {e}")
        
        # Varsayılan olarak /dev/video2'yi dene
        print("Varsayılan olarak /dev/video2 kullanılıyor")
        return 2
    else:
        # Windows veya macOS için varsayılan 0 ID'sini kullan
        return 0

def capture_image(save_path=None):
    """
    Kameradan görüntü çeker ve base64 kodlanmış metin olarak döndürür
    
    Args:
        save_path: Artık kullanılmıyor. Geriye uyumluluk için korundu.
        
    Returns:
        tuple: (base64 kodlanmış görüntü metni, ham görüntü array'i)
        Hata durumunda (None, None) döner
    """
    try:
        # İşletim sistemine göre uygun kamera ID'sini al
        camera_id = get_camera_device_id()
        
        # Kamerayı açmaya çalış
        print(f"Kamera açılıyor (ID: {camera_id})...")
        cap = cv2.VideoCapture(camera_id)
        
        # İlk deneme başarısız olursa diğer ID'leri dene
        if not cap.isOpened() and platform.system() == "Linux":
            print(f"Kamera ID {camera_id} açılamadı, alternatifler deneniyor...")
            for alt_id in [3, 0, 1, 4, 5]:  # Alternatif ID'leri dene
                if alt_id != camera_id:
                    print(f"Alternatif kamera ID {alt_id} deneniyor...")
                    cap.release()  # Önceki denemeyi serbest bırak
                    cap = cv2.VideoCapture(alt_id)
                    if cap.isOpened():
                        print(f"Kamera ID {alt_id} başarıyla açıldı!")
                        break
        
        if not cap.isOpened():
            print("❌ Kamera açılamadı! Hiçbir kamera cihazına erişilemiyor.")
            return None, None
            
        # Kamera ayarlarını yap
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        print("📸 Görüntü çekiliyor...")
        # Kameranın ısınmasını bekle
        time.sleep(0.3)  # Bekleme süresini kısalttık
        
        # Görüntüyü oku
        ret, frame = cap.read()
        cap.release()
        
        if not ret or frame is None:
            print("❌ Görüntü alınamadı!")
            return None, None
            
        print("✅ Görüntü başarıyla çekildi!")
        
        # Görüntüyü JPEG'e çevir ve base64 kodla
        _, buffer = cv2.imencode('.jpg', frame)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return img_base64, frame
        
    except Exception as e:
        print(f"❌ Kamera hatası: {str(e)}")
        return None, None

def test_camera():
    """Kamera fonksiyonunu test eder"""
    print("Kamera test ediliyor...")
    img_base64, frame = capture_image()
    
    if img_base64:
        print(f"Base64 görüntü uzunluğu: {len(img_base64)} karakter")
        # Eğer istiyorsanız test amaçlı bir görüntü kaydedin
        if frame is not None:
            test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "camera_test")
            os.makedirs(test_dir, exist_ok=True)
            test_path = os.path.join(test_dir, f"test_camera_{time.strftime('%Y%m%d_%H%M%S')}.jpg")
            cv2.imwrite(test_path, frame)
            print(f"Test görüntüsü kaydedildi: {test_path}")
        return True
    else:
        return False

if __name__ == "__main__":
    if test_camera():
        print("✅ Kamera testi başarılı!")
    else:
        print("❌ Kamera testi başarısız!")