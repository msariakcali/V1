# Gerçek Zamanlı Sesli Asistan

Bu proje, Google Gemini API ve Google Cloud Text-to-Speech kullanarak gerçek zamanlı sesli asistan oluşturur.

## Özellikler

- 🎤 Mikrofon ile sesli giriş
- 🤖 Google Gemini AI ile gerçek zamanlı yanıt
- 🔊 Google Text-to-Speech (WaveNet) ile sesli çıkış
- ⚡ Gerçek zamanlı yanıt akışı
- 🔈 Direkt ses çalma özelliği (geçici dosya kullanımı olmadan)
- 🗣️ Sesli yanıt döngüsü (AI Studio benzeri deneyim)
- 📸 Kamera entegrasyonu ile görüntü işleme
- 👁️ Gemini Pro Vision ile görüntü analizi

## Kurulum

### 1. Gerekli Araçlar

1. Python 3.9 veya üzeri kurulu olmalı
2. Gerekli paketleri yüklemek için install_requirements.py betiğini kullanın:

```bash
python install_requirements.py
```

Bu betik aşağıdaki paketleri otomatik olarak yükleyecektir:
- google-generativeai
- google-cloud-texttospeech
- SpeechRecognition
- pygame (ses oynatma için)
- pyaudio
- opencv-python (kamera işlemleri için)
- python-dotenv

### 2. API Anahtarları

#### Google Gemini API Anahtarı
1. [Google MakerSuite](https://makersuite.google.com/app/apikey) adresine gidin
2. API Anahtarı alın
3. Bu anahtarı `main.py` dosyasındaki `GEMINI_API_KEY` değişkenine ekleyin

#### Google Cloud Text-to-Speech Anahtarı
1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. Yeni bir proje oluşturun
3. "API'ler ve Hizmetler" → "Kitaplık" → Text-to-Speech API'yi etkinleştirin
4. "Kimlik Bilgileri" → "Hizmet Hesabı" oluşturun
5. JSON anahtar oluşturun ve indirin

### 3. Ortam Değişkeni Ayarlama

Google Cloud kimlik bilgilerinizi ayarlamak için `setup.py` betiğini kullanın:

```bash
python setup.py
```

Bu betik:
- Google Cloud JSON anahtar dosyasının yolunu sorar
- İşletim sisteminize göre gerekli ortam değişkenini ayarlar
- İsterseniz uygulamayı doğrudan başlatır

## Kullanım

Ortam değişkenlerini ayarladıktan sonra:

```bash
python main.py
```

- Mikrofon etkinleştiğinde "🎤 Konuşun..." mesajını göreceksiniz
- Sorunuzu söyleyin
- Asistan yanıtı gerçek zamanlı olarak gösterecek ve seslendirecektir

### Görüntü İşleme Özelliği

Asistanın kamera kullanarak görüntü analizi yapabilmesi için aşağıdaki tetikleyici ifadelerden birini kullanın:

- "görüyor musun"
- "görebiliyor musun"
- "görsene"
- "bakabilir misin"
- "bak bakalım"
- "gör bakalım"
- "kameradan bak"

Örnek sorular:
- "Bu nesne nedir, görüyor musun?"
- "Önümdeki yazıyı okuyabilir misin, bak bakalım."
- "Bu resimde ne var, görebiliyor musun?"

Tetikleyici ifadeyi algıladığında, asistan otomatik olarak kamerayı etkinleştirecek, bir görüntü çekecek ve Gemini Pro Vision modeli kullanarak analiz edecektir.

## Proje Yapısı

```
realtime_voice_assistant/
│
├── main.py                  # Ana program döngüsü
├── mic_input.py             # Mikrofon giriş işlemleri
├── tts_google.py            # Google TTS entegrasyonu (pygame ile)
├── camera_capture.py        # Kamera görüntü yakalama modülü
├── setup.py                 # Ortam değişkeni ayarlama betiği
├── install_requirements.py  # Gerekli paketleri yüklemek için betik
├── images/                  # Yakalanan kamera görüntüleri için klasör
└── README.md                # Bu dosya
```