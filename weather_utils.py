import os
import sys
import json
import requests
from datetime import datetime
import importlib
import re
import unicodedata

# WeatherAPI.com API anahtarınızı burada belirtin veya .env dosyasından yükleyin
# API_KEY = "sizin_api_anahtarınız"
API_KEY = None

# Türkiye'nin 81 ili listesi
TURKEY_CITIES = [
    "adana", "adıyaman", "afyonkarahisar", "afyon", "ağrı", "agri", "aksaray", "amasya", "ankara", 
    "antalya", "ardahan", "artvin", "aydın", "aydin", "balıkesir", "balikesir", "bartın", "bartin", "batman", "bayburt", 
    "bilecik", "bingöl", "bingol", "bitlis", "bolu", "burdur", "bursa", "çanakkale", "canakkale", "çankırı", "cankiri", 
    "çorum", "corum", "denizli", "diyarbakır", "diyarbakir", "düzce", "duzce", "edirne", "elazığ", "elazig", "erzincan", "erzurum", 
    "eskişehir", "eskisehir", "gaziantep", "giresun", "gümüşhane", "gumushane", "hakkari", "hatay", "ığdır", "igdir", "ısparta", "isparta", 
    "istanbul", "Izmir", "kahramanmaraş", "kahramanmaras", "maraş", "maras", "karabük", "karabuk", "karaman", "kars", "kastamonu", 
    "kayseri", "kilis", "kırıkkale", "kirikkale", "kırklareli", "kirklareli", "kırşehir", "kirsehir", "kocaeli", "izmit", "konya", 
    "kütahya", "kutahya", "malatya", "manisa", "mardin", "mersin", "içel", "icel", "muğla", "mugla", "muş", "mus", "nevşehir", "nevsehir", 
    "niğde", "nigde", "ordu", "osmaniye", "rize", "sakarya", "adapazarı", "adapazari", "samsun", "şanlıurfa", "sanliurfa", "urfa", 
    "siirt", "sinop", "şırnak", "sirnak", "sivas", "tekirdağ", "tekirdag", "tokat", "trabzon", "tunceli", "uşak", "usak", 
    "van", "yalova", "yozgat", "zonguldak"
]

# Yaygın dünya şehirleri
COMMON_WORLD_CITIES = [
    "londra", "paris", "roma", "berlin", "madrid", "barselona", "amsterdam", "brüksel", "bruksel",
    "vienna", "viyana", "prag", "atina", "budapeşte", "budapeste", "kopenhag", "stockholm", "oslo", 
    "helsinki", "tallinn", "riga", "vilnius", "varşova", "varsova", "minsk", "kiev", "moskova", 
    "bern", "zürih", "zurih", "cenevre", "lizbon", "dublin", "edinburg", "sofya", "bükreş", "bukres", 
    "belgrad", "zagrep", "saraybosna", "tiran", "üsküp", "uskup", "priştine", "pristine", "podgorica", 
    "new york", "newyork", "los angeles", "losangeles", "chicago", "washington", "boston", 
    "toronto", "montreal", "vancouver", "mexico", "meksiko", "rio", "sao paulo", 
    "buenos aires", "santiago", "lima", "bogota", "tokyo", "osaka", "pekin", 
    "beijing", "şangay", "sangay", "shanghai", "hong kong", "taipei", "seul", "bangkok", "singapore", 
    "singapur", "kuala lumpur", "cakarta", "manila", "sydney", "melbourne", "dubai", 
    "abu dabi", "doha", "muskat", "kahire", "tunus", "kazablanka", "cape town", 
    "johannesburg", "lagos", "nairobi", "addis ababa", "addisababa", "kiev", "lviv", "odessa"
]

def normalize_turkish_text(text):
    """
    Türkçe metni normalize eder - büyük küçük harf duyarlılığını ve aksanlı karakterleri yönetir
    
    Args:
        text (str): Normalize edilecek metin
        
    Returns:
        str: Normalize edilmiş metin
    """
    if not text:
        return ""
    
    # Küçük harfe çevir
    text = text.lower()
    
    # Özel Türkçe karakter dönüşümleri
    replacements = {
        'İ': 'i', 'I': 'ı',
        'Ğ': 'ğ', 'Ü': 'ü',
        'Ş': 'ş', 'Ç': 'ç',
        'Ö': 'ö'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # NFKD normalizasyonu - aksanlı karakterleri ayrıştırır
    text = unicodedata.normalize('NFKD', text)
    
    return text

def check_requests_installed():
    """requests kütüphanesinin yüklü olup olmadığını kontrol eder"""
    try:
        import requests
        return True
    except ImportError:
        print("requests kütüphanesi bulunamadı. Yükleniyor...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
            print("✅ requests başarıyla yüklendi!")
            import requests  # Yeniden içe aktar
            return True
        except Exception as e:
            print(f"❌ requests yüklenirken hata: {str(e)}")
            print("Lütfen manuel olarak yükleyin: pip install requests")
            return False

def load_api_key():
    """API anahtarını .env dosyasından veya environment variable'dan yükler"""
    global API_KEY
    
    if API_KEY is not None:
        return API_KEY
    
    # Öncelikle environment variable'ı kontrol et
    api_key = os.environ.get("WEATHER_API_KEY")
    if api_key:
        API_KEY = api_key
        return API_KEY
    
    # .env dosyasını kontrol et
    try:
        dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(dotenv_path):
            # dotenv kütüphanesini kullanmaya çalış
            try:
                import dotenv
                dotenv.load_dotenv(dotenv_path)
                api_key = os.environ.get("WEATHER_API_KEY")
                if api_key:
                    API_KEY = api_key
                    return API_KEY
            except ImportError:
                # dotenv kütüphanesi yoksa manuel olarak oku
                with open(dotenv_path, 'r') as f:
                    for line in f:
                        if line.startswith('WEATHER_API_KEY='):
                            API_KEY = line.split('=')[1].strip().strip('"').strip("'")
                            return API_KEY
    except Exception as e:
        print(f"API anahtarı yüklenirken hata: {str(e)}")
    
    # API anahtarını kullanıcıdan al
    if not API_KEY:
        print("\n⚠️ WeatherAPI.com API anahtarı bulunamadı!")
        print("1. https://www.weatherapi.com adresinden ücretsiz bir hesap oluşturun")
        print("2. API anahtarınızı alın")
        print("3. Aşağıya API anahtarınızı girin veya .env dosyasına WEATHER_API_KEY=size_verilen_anahtar şeklinde ekleyin\n")
        
        api_key = input("WeatherAPI.com API anahtarınızı girin (atlamak için boş bırakın): ")
        if api_key:
            API_KEY = api_key
            
            # API anahtarını .env dosyasına kaydetmek ister misin?
            save = input("Bu API anahtarını .env dosyasına kaydetmek ister misiniz? (e/h): ")
            if save.lower() in ['e', 'evet', 'y', 'yes']:
                try:
                    env_file = os.path.join(os.path.dirname(__file__), '.env')
                    
                    # Dosya varsa, içeriğini oku
                    env_content = ""
                    if os.path.exists(env_file):
                        with open(env_file, 'r') as f:
                            env_content = f.read()
                    
                    # API_KEY satırı varsa güncelle, yoksa ekle
                    if "WEATHER_API_KEY=" in env_content:
                        lines = env_content.split('\n')
                        updated_lines = []
                        for line in lines:
                            if line.startswith("WEATHER_API_KEY="):
                                updated_lines.append(f"WEATHER_API_KEY={api_key}")
                            else:
                                updated_lines.append(line)
                        env_content = '\n'.join(updated_lines)
                    else:
                        if env_content and not env_content.endswith('\n'):
                            env_content += '\n'
                        env_content += f"WEATHER_API_KEY={api_key}\n"
                    
                    # Dosyaya yaz
                    with open(env_file, 'w') as f:
                        f.write(env_content)
                    
                    print(f"✅ API anahtarı .env dosyasına kaydedildi: {env_file}")
                    
                except Exception as e:
                    print(f"❌ API anahtarı kaydedilirken hata: {str(e)}")
    
    return API_KEY

def get_weather(location):
    """
    Belirtilen konumun hava durumunu alır
    
    Args:
        location (str): Hava durumu sorgulanacak konum (şehir, ülke, vs.)
        
    Returns:
        dict: Hava durumu bilgileri
    """
    # requests kütüphanesinin yüklü olduğundan emin ol
    if not check_requests_installed():
        return {"error": "Hava durumu modülü için gerekli kütüphaneler yüklenemedi."}
    
    # API anahtarını yükle
    api_key = load_api_key()
    if not api_key:
        return {"error": "WeatherAPI.com API anahtarı bulunamadı."}
    
    # API URL'ini oluştur
    url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no&lang=tr"
    
    try:
        # API isteği gönder
        response = requests.get(url)
        response.raise_for_status()  # 4xx, 5xx hataları için exception fırlat
        
        # JSON yanıtını döndür
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        if response.status_code == 400:
            # Konum bulunamadı
            try:
                error_data = response.json()
                if "error" in error_data and "message" in error_data["error"]:
                    return {"error": f"Konum bulunamadı: {error_data['error']['message']}"}
            except:
                pass
            return {"error": "Belirtilen konum bulunamadı."}
        elif response.status_code == 401:
            return {"error": "Geçersiz API anahtarı."}
        elif response.status_code == 403:
            return {"error": "API kullanım limitiniz aşıldı."}
        else:
            return {"error": f"HTTP hatası: {str(e)}"}
    
    except requests.exceptions.ConnectionError:
        return {"error": "Bağlantı hatası. İnternet bağlantınızı kontrol edin."}
    
    except Exception as e:
        return {"error": f"Hava durumu alınırken bir hata oluştu: {str(e)}"}

def parse_turkish_weather_condition(condition):
    """
    İngilizce hava durumu açıklamasını Türkçe'ye çevirir
    WeatherAPI zaten Türkçe desteği sunsa da, bazı durumlarda çeviriler eksik olabilir
    """
    conditions = {
        "sunny": "güneşli",
        "clear": "açık",
        "partly cloudy": "parçalı bulutlu",
        "cloudy": "bulutlu",
        "overcast": "kapalı",
        "mist": "sisli",
        "fog": "puslu",
        "freezing fog": "dondurucu sis",
        "patchy rain possible": "yer yer yağmur olasılığı",
        "patchy snow possible": "yer yer kar olasılığı",
        "patchy sleet possible": "yer yer karla karışık yağmur olasılığı",
        "patchy freezing drizzle possible": "yer yer dondurucu çisenti olasılığı",
        "thundery outbreaks possible": "gök gürültülü sağanak olasılığı",
        "blowing snow": "tipi",
        "blizzard": "kar fırtınası",
        "light rain": "hafif yağmur",
        "moderate rain": "orta şiddetli yağmur",
        "heavy rain": "şiddetli yağmur",
        "light snow": "hafif kar",
        "moderate snow": "orta şiddetli kar",
        "heavy snow": "yoğun kar",
    }
    
    # Koşulun kendisi Türkçe gelmiş olabilir, o zaman direkt döndür
    if condition.lower() in [v for v in conditions.values()]:
        return condition
    
    # İngilizce koşul varsa çevir
    return conditions.get(condition.lower(), condition)

def format_weather_reply(weather_data):
    """
    Hava durumu verilerini okunabilir bir mesaja dönüştürür
    
    Args:
        weather_data (dict): get_weather() fonksiyonundan dönen veri
        
    Returns:
        str: Hava durumu mesajı
    """
    if "error" in weather_data:
        return f"Üzgünüm, hava durumu bilgisini alamadım. {weather_data['error']}"
    
    try:
        location = weather_data["location"]
        current = weather_data["current"]
        
        city = location["name"]
        region = location["region"]
        country = location["country"]
        
        temp_c = current["temp_c"]
        condition = current["condition"]["text"]
        humidity = current["humidity"]
        wind_kph = current["wind_kph"]
        feelslike_c = current["feelslike_c"]
        
        # Türkçe hava durumu açıklaması
        condition_tr = parse_turkish_weather_condition(condition)
        
        # Yerel saat
        local_time = datetime.strptime(location["localtime"], "%Y-%m-%d %H:%M")
        time_str = local_time.strftime("%H:%M")
        
        # Yer bilgisini formatla
        if country == "Turkey" or country == "Türkiye":
            location_str = f"{city}"
            # Eğer bölge ve şehir aynı değilse bölgeyi ekle
            if region != city and region:
                location_str = f"{city}, {region}"
        else:
            location_str = f"{city}, {country}"
        
        # Hissedilen sıcaklık farklıysa belirt
        feels_like_str = ""
        if abs(temp_c - feelslike_c) >= 2:  # 2 derece veya daha fazla fark varsa
            feels_like_str = f", hissedilen {feelslike_c}°C"
        
        # Yanıt mesajını oluştur
        reply = f"{location_str}'da hava şu an {condition_tr}, sıcaklık {temp_c}°C{feels_like_str}. "
        reply += f"Nem oranı %{humidity}, rüzgar hızı {wind_kph} km/s."
        
        return reply
        
    except KeyError as e:
        return f"Üzgünüm, hava durumu verisini işlerken bir sorun oluştu: Eksik veri alanı."
    
    except Exception as e:
        return f"Üzgünüm, hava durumu verisini işlerken bir sorun oluştu: {str(e)}"

def extract_location(query):
    """
    Kullanıcı sorgusundan konum bilgisini çıkarır
    
    Args:
        query (str): Kullanıcı sorgusu
        
    Returns:
        str: Çıkarılan konum veya None
    """
    if not query:
        return "Denizli"  # Varsayılan şehir
    
    # Sorguyu normalize et
    normalized_query = normalize_turkish_text(query)
    
    # Direkt şehir adı söylenmesi durumunu kontrol et
    # "İstanbul hava durumu", "İzmir'de hava" gibi
    for city in TURKEY_CITIES + COMMON_WORLD_CITIES:
        if city in normalized_query:
            # Şehir adının bulunduğu konumu tespit et
            index = normalized_query.find(city)
            
            # Şehrin önündeki ve sonrasındaki 3 karakteri kontrol et
            before = normalized_query[max(0, index-3):index].strip()
            after = normalized_query[index+len(city):min(len(normalized_query), index+len(city)+3)].strip()
            
            # Eğer şehir adı kelime sınırlarında ise (tek başına bir kelime ise)
            # veya yaygın kalıpların bir parçası ise
            if (before == "" or before[-1] in " ,.'\"()") and (after == "" or after[0] in " ,.'\"()"):
                return city[0].upper() + city[1:]
    
    # "X'de/da", "X'deki", "X'teki" gibi kalıpları ara
    location_patterns = [
        r"(\w+)'[dt][ae]\s+hava",
        r"(\w+)'[dt][ae]ki\s+hava",
        r"(\w+)'[dt][ae]\s+bugün\s+hava",
        r"(\w+)'nin\s+hava",
        r"(\w+)'[iuı]n\s+hava",
        r"(\w+)'deki\s+hava\s+[nd]",
        r"(\w+)'un\s+hava\s+durumu",
        r"(\w+)\s+hava\s+durumu",
        r"(\w+)\s+şehrinin\s+hava",
        r"hava\s+durumu\s+(\w+)"
    ]
    
    for pattern in location_patterns:
        matches = re.search(pattern, normalized_query)
        if matches:
            location = matches.group(1)
            # Bulunan lokasyonu kontrol et
            for city in TURKEY_CITIES + COMMON_WORLD_CITIES:
                if city.startswith(location.lower()) or location.lower().startswith(city):
                    return city[0].upper() + city[1:]
            
            # İlk harfi büyüt ve döndür
            return location[0].upper() + location[1:]
    
    # "Hava durumu X'de nasıl?" gibi kalıpları ara
    if "hava durumu" in normalized_query:
        parts = normalized_query.split("hava durumu")
        
        # Hava durumu kelimesinden sonraki kısmı analiz et
        if len(parts) > 1 and parts[1].strip():
            after_part = parts[1].strip()
            
            # Önce direkt şehir ismi var mı kontrol et
            for city in TURKEY_CITIES + COMMON_WORLD_CITIES:
                if city in after_part.lower():
                    return city[0].upper() + city[1:]
            
            # Şehir ismi bulunamadıysa, cümleden lokasyon bulmaya çalış
            # "X'de", "X şehrinde" gibi kalıpları ara
            location_subpatterns = [
                r"(\w+)'[dt][ae]",
                r"(\w+)\s+şehrinde",
                r"(\w+)\s+ilinde",
                r"(\w+)\s+için"
            ]
            
            for subpattern in location_subpatterns:
                matches = re.search(subpattern, after_part)
                if matches:
                    location = matches.group(1)
                    return location[0].upper() + location[1:]
    
    # "X için hava durumu" gibi kalıpları ara
    matches = re.search(r"(\w+)\s+için\s+hava", normalized_query)
    if matches:
        location = matches.group(1)
        return location[0].upper() + location[1:]
    
    # Direk soruda şehir adı geçiyor mu diye son bir kontrol
    # "İstanbul nasıl?", "İzmir'de durum ne?" gibi
    words = normalized_query.split()
    for word in words:
        clean_word = word.strip("'.,!?():;")
        clean_word_lower = clean_word.lower()
        
        # Şehir listesinde var mı?
        for city in TURKEY_CITIES + COMMON_WORLD_CITIES:
            if clean_word_lower == city or (len(clean_word_lower) > 3 and 
                                          (clean_word_lower.startswith(city) or city.startswith(clean_word_lower))):
                return city[0].upper() + city[1:]
    
    # Varsayılan konum (belirtilmemişse)
    return "Istanbul"  # Varsayılan olarak İstanbul

def get_weather_reply(query):
    """
    Hava durumu sorgusu için uygun yanıtı oluşturur
    
    Args:
        query (str): Kullanıcı sorusu
        
    Returns:
        str: Hava durumu yanıtı
    """
    # Sorgudaki konumu tespit et
    location = extract_location(query)
    print(f"🔍 Tespit edilen konum: {location}")
    
    # Hava durumu bilgisini al
    weather_data = get_weather(location)
    
    # Bilgiyi okunabilir mesaja dönüştür
    return format_weather_reply(weather_data)

if __name__ == "__main__":
    # Test için
    print("Hava Durumu Modülü Testi")
    print("-----------------------")
    
    # API anahtarı kontrolü
    api_key = load_api_key()
    if not api_key:
        print("❌ API anahtarı bulunamadı. Test sonlandırılıyor.")
        sys.exit(1)
    
    # Örnek sorgular
    test_queries = [
        "Hava durumu nasıl?",
        "İstanbul'da hava nasıl?",
        "Ankara'daki hava durumu nedir?",
        "İzmir'de yarın hava nasıl olacak?",
        "Antalya'nın hava durumu",
        "Edirne için hava durumu ne?",
        "Hava Bursa'da nasıl?",
        "Diyarbakır şehrinde hava durumu",
        "Bugün Konya'da hava nasıl?",
        "Adana hava durumu",
        "Samsun'daki sıcaklık"
    ]
    
    print("\nÖrnek Sorgular:")
    for query in test_queries:
        print(f"Soru: {query}")
        print(f"Konum tespiti: {extract_location(query)}")
        print(f"Yanıt: {get_weather_reply(query)}")
        print()