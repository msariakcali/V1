import pyaudio
import numpy as np
import wave
import os
import time
import threading
import sys
import platform

# Ses verileri RAM'de audio_buffer değişkeninde tutulur
# Bu veriye get_current_audio_data() fonksiyonu ile erişebilirsiniz
# Ağız animasyonu için en kullanışlı değer get_current_amplitude() ile alınan genlik değeridir (0-1 arası)

# Global değişkenler
current_amplitude = 0.0
is_recording = False
audio_buffer = np.zeros(100)  # Son 100 ses örneğini tutacak

def get_loopback_device():
    """
    Sistem sesini yakalayabilecek bir loopback/stereo mix cihazı arar
    Windows'ta genellikle "Stereo Mix" veya "What U Hear"
    Linux'ta genellikle "pulse" veya "monitor"
    
    Returns:
        int: Bulunan cihazın ID'si veya varsayılan ID
    """
    p = pyaudio.PyAudio()
    
    # Kullanılabilir giriş cihazlarını listele
    info = p.get_host_api_info_by_index(0)
    num_devices = info.get('deviceCount')
    
    print("Kullanılabilir ses cihazları:")
    device_id = None
    
    system_name = platform.system()
    
    for i in range(0, num_devices):
        device_info = p.get_device_info_by_host_api_device_index(0, i)
        device_name = device_info.get('name', '')
        
        # Windows için "Stereo Mix" veya "What U Hear" gibi cihazları ara
        if system_name == "Windows":
            print(f"Device {i}: {device_name}")
            if (device_info.get('maxInputChannels') > 0 and
                any(keyword in device_name.lower() for keyword in 
                   ["stereo mix", "what u hear", "what you hear", "loopback", "monitor"])):
                device_id = i
                print(f"✅ Windows loopback cihazı bulundu: {device_name} (ID: {device_id})")
                break
        
        # Linux için "pulse" veya "monitor" içeren cihazları ara
        elif system_name == "Linux":
            print(f"Device {i}: {device_name}")
            if (device_info.get('maxInputChannels') > 0 and
                any(keyword in device_name.lower() for keyword in 
                   ["pulse", "monitor", "loopback"])):
                device_id = i
                print(f"✅ Linux loopback cihazı bulundu: {device_name} (ID: {device_id})")
                break
        
        # macOS için "BlackHole" veya "Soundflower" gibi sanal ses cihazlarını ara
        elif system_name == "Darwin":  # macOS
            if (device_info.get('maxInputChannels') > 0 and
                any(keyword in device_name.lower() for keyword in 
                   ["blackhole", "soundflower", "loopback"])):
                device_id = i
                print(f"✅ macOS loopback cihazı bulundu: {device_name} (ID: {device_id})")
                break
    
    # Eğer hiçbir loopback cihazı bulunamadıysa
    if device_id is None:
        print("⚠️ Sistem sesini yakalayabilen bir loopback cihazı bulunamadı!")
        print("ℹ️ Windows için 'Stereo Mix'i etkinleştirmeniz gerekebilir.")
        print("ℹ️ Linux için 'pactl load-module module-loopback' komutunu çalıştırabilirsiniz.")
        print("ℹ️ macOS için 'BlackHole' gibi bir sanal ses cihazı kurmanız gerekebilir.")
        print("⚠️ Şimdilik varsayılan mikrofon kullanılacak")
        
        # Varsayılan cihazı kullan
        try:
            device_id = p.get_default_input_device_info()['index']
            print(f"Varsayılan giriş cihazı kullanılıyor (ID: {device_id})")
        except:
            # Hiçbir giriş cihazı bulunamazsa 0'ı kullan
            device_id = 0
            print(f"Varsayılan ID kullanılıyor: {device_id}")
    
    p.terminate()
    return device_id

def capture_assistant_audio(duration=5, sample_rate=44100):
    """
    Sistem ses çıkışını kaydeder ve float tipinde döndürür
    
    Args:
        duration: Kayıt süresi (saniye)
        sample_rate: Örnekleme hızı
    
    Returns:
        float64 numpy dizisi olarak ses verileri
    """
    p = pyaudio.PyAudio()
    
    # Loopback cihazını bul
    device_id = get_loopback_device()
    
    # Ses kayıt parametreleri
    chunk = 1024
    format = pyaudio.paFloat32  # Float32 formatında kayıt
    channels = 1  # Mono
    
    # Ses kaydını başlat
    try:
        stream = p.open(format=format,
                        channels=channels,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk,
                        input_device_index=device_id)
        
        print(f"Ses kaydediliyor (Cihaz ID: {device_id})...")
        frames = []
        
        for i in range(0, int(sample_rate / chunk * duration)):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
        
        print("Kayıt tamamlandı.")
        
        # Kaydı durdur
        stream.stop_stream()
        stream.close()
        
    except Exception as e:
        print(f"❌ Ses kaydı sırasında hata: {str(e)}")
        frames = []
    
    p.terminate()
    
    # Float32 formatındaki verileri numpy dizisine dönüştür
    if frames:
        audio_data = np.frombuffer(b''.join(frames), dtype=np.float32)
        return audio_data
    else:
        return np.zeros(100, dtype=np.float32)

def get_audio_amplitude(audio_data, frame_size=1024):
    """
    Float tipindeki ses verilerinin genlik değerlerini hesaplar
    Bu değerler ağız hareketlendirmesi için kullanılabilir
    
    Args:
        audio_data: Float tipinde ses verileri
        frame_size: Her bir çerçevenin boyutu
    
    Returns:
        Her çerçeve için genlik değerleri (0.0-1.0 arası)
    """
    amplitudes = []
    
    # Ses verilerini çerçevelere böl
    for i in range(0, len(audio_data), frame_size):
        frame = audio_data[i:i+frame_size]
        if len(frame) > 0:
            # Her bir çerçevenin RMS (Root Mean Square) değerini hesapla
            rms = np.sqrt(np.mean(np.square(frame)))
            # Değeri 0-1 arasına normalize et
            normalized_rms = min(1.0, rms * 3)  # 3 çarpanı ayarlanabilir
            amplitudes.append(normalized_rms)
    
    return np.array(amplitudes)

def save_audio_to_file(audio_data, filename="assistant_audio.wav", sample_rate=44100):
    """
    Float ses verisini WAV dosyasına kaydeder
    
    Args:
        audio_data: Float tipinde ses verileri
        filename: Kaydedilecek dosya adı
        sample_rate: Örnekleme hızı
    """
    # Float32 verisini Int16'ya dönüştür (WAV için)
    audio_int16 = (audio_data * 32767).astype(np.int16)
    
    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())
    wf.close()
    
    print(f"Ses dosyası kaydedildi: {filename}")

def visualize_audio(amplitude, width=50):
    """
    Terminal üzerinde ses genlik değerlerini görselleştirir
    
    Args:
        amplitude: 0-1 arası normalize edilmiş genlik değeri
        width: Çubuğun maksimum genişliği
    """
    bar_width = int(amplitude * width)
    bar = '█' * bar_width
    percentage = int(amplitude * 100)
    
    sys.stdout.write(f"\rAmplitude: [{bar:{width}}] {percentage:3d}% | Buffer Size: {len(audio_buffer)} samples")
    sys.stdout.flush()

def realtime_audio_monitor(callback_func=None, stop_event=None):
    """
    Sistem ses çıkışını gerçek zamanlı olarak izler ve terminalde gösterir
    
    Args:
        callback_func: Her ses çerçevenin için çağrılacak opsiyonel fonksiyon
        stop_event: Kaydı durdurmak için threading.Event nesnesi
    """
    global current_amplitude, is_recording, audio_buffer
    
    if stop_event is None:
        stop_event = threading.Event()
    
    # Loopback cihazını bul - sistem sesini kaydetmek için
    device_id = get_loopback_device()
    
    p = pyaudio.PyAudio()
    
    # Ses kayıt parametreleri
    chunk = 1024
    format = pyaudio.paFloat32  # Float32 formatında kayıt
    channels = 1  # Mono
    sample_rate = 44100
    
    def audio_callback(in_data, frame_count, time_info, status):
        if stop_event.is_set():
            return (None, pyaudio.paComplete)
        
        # Float32 formatındaki verileri numpy dizisine dönüştür
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        # Ses verisini global buffer'a ekle
        global audio_buffer
        audio_buffer = np.concatenate((audio_buffer[len(audio_data):], audio_data))
        
        # RMS genlik değerini hesapla
        if len(audio_data) > 0:
            rms = np.sqrt(np.mean(np.square(audio_data)))
            # Değeri 0-1 arasına normalize et
            normalized_rms = min(1.0, rms * 3)  # 3 çarpanı ayarlanabilir
            
            global current_amplitude
            current_amplitude = normalized_rms
            
            # Terminal görselleştirmesi
            visualize_audio(normalized_rms)
            
            # Callback fonksiyonunu çağır
            if callback_func:
                callback_func(audio_data, normalized_rms)
        
        return (in_data, pyaudio.paContinue)
    
    # Ses kaydını başlat
    try:
        stream = p.open(format=format,
                      channels=channels,
                      rate=sample_rate,
                      input=True,
                      frames_per_buffer=chunk,
                      input_device_index=device_id,
                      stream_callback=audio_callback)
        
        print(f"\nGerçek zamanlı ses izleme başladı (Cihaz ID: {device_id})...")
        print("Bu program, hoparlör çıkışından gelen ses genliğini yakalar")
        print("Her genlik değeri (0-1 arası) ağız animasyonu için kullanılabilir")
        print("Çıkmak için Ctrl+C tuşlarına basın")
        is_recording = True
        
        while not stop_event.is_set():
            time.sleep(0.1)  # CPU kullanımını azaltmak için kısa bekle
            
    except Exception as e:
        print(f"\n❌ Ses izleme başlatılamadı: {str(e)}")
        print("Bu hatanın nedeni şunlar olabilir:")
        print("1. Seçilen ses cihazı kullanılamıyor olabilir")
        print("2. Başka bir program cihazı kullanıyor olabilir")
        print("3. Sistem hoparlör çıkışını yakalamak için özel ayar gerekebilir:")
        
        system_name = platform.system()
        if system_name == "Windows":
            print("   - Windows'ta 'Ses Ayarları > Kayıt cihazları'ndan 'Stereo Mix'i etkinleştirin")
        elif system_name == "Linux":
            print("   - Linux'ta: 'pactl load-module module-loopback' komutunu çalıştırın")
        elif system_name == "Darwin":  # macOS
            print("   - macOS'ta 'BlackHole' veya 'Soundflower' gibi bir sanal ses aracı yüklemeniz gerekir")
        
    except KeyboardInterrupt:
        print("\n⏹️ Kullanıcı tarafından durduruldu")
    finally:
        print("\n⏹️ İzleme durduruldu.")
        is_recording = False
        
        # Kaydı durdur
        if 'stream' in locals() and stream:
            stream.stop_stream()
            stream.close()
        p.terminate()

def get_current_audio_data():
    """
    Şu an kaydedilen ses verisini döndürür
    Bu veriyi doğrudan ağız animasyonu için kullanabilirsiniz
    """
    global audio_buffer
    return audio_buffer.copy()

def get_current_amplitude():
    """
    Son hesaplanan genlik değerini döndürür
    Bu değer ağız animasyonu için idealdir (0-1 arası)
    """
    global current_amplitude
    return current_amplitude

if __name__ == "__main__":
    print("🔊 Hoparlör Çıkışı Ses İzleme Aracı")
    print("Bu program, bilgisayarınızın hoparlör çıkışını izler ve ses genliğini ölçer")
    print("Ağız animasyonu için kullanışlı 0-1 arası değerler sağlar")
    print("Çıkmak için Ctrl+C tuşlarına basın")
    
    try:
        # Gerçek zamanlı ses izleme başlat
        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=realtime_audio_monitor,
            args=(None, stop_event),
            daemon=True
        )
        monitor_thread.start()
        
        # Ana thread çalışmaya devam etsin
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Program sonlandırılıyor...")
        stop_event.set()
        monitor_thread.join(timeout=1)