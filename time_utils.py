import datetime
import pytz
import os
import sys
import importlib

def check_pytz_installed():
    """pytz kütüphanesinin yüklü olup olmadığını kontrol eder"""
    try:
        import pytz
        return True
    except ImportError:
        print("pytz kütüphanesi bulunamadı. Yükleniyor...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])
            print("✅ pytz başarıyla yüklendi!")
            import pytz  # Yeniden içe aktar
            return True
        except Exception as e:
            print(f"❌ pytz yüklenirken hata: {str(e)}")
            print("Lütfen manuel olarak yükleyin: pip install pytz")
            return False

def get_turkey_time(formatted=True):
    """
    Türkiye'deki mevcut saati döndürür
    
    Args:
        formatted (bool): True ise formatlanmış string döner, False ise datetime nesnesi
        
    Returns:
        str veya datetime: Mevcut Türkiye saati
    """
    # pytz kütüphanesi yüklü değilse yüklemeye çalış
    if not check_pytz_installed():
        if formatted:
            return "Saat bilgisi alınamadı"
        else:
            return None
    
    # Türkiye saat dilimini tanımla
    turkey_timezone = pytz.timezone('Europe/Istanbul')
    
    # Şu anki UTC zamanını al ve Türkiye saat dilimine çevir
    current_time_utc = datetime.datetime.now(pytz.UTC)
    current_time_turkey = current_time_utc.astimezone(turkey_timezone)
    
    # Formatlanmış saat isteniyorsa string olarak döndür
    if formatted:
        hour = current_time_turkey.hour
        minute = current_time_turkey.minute
        
        # Doğal dil için saat formatı
        time_str = f"{hour}:{minute:02d}"
        return time_str
    
    # Datetime nesnesi olarak döndür
    return current_time_turkey

def get_turkey_date_time(natural_language=True):
    """
    Türkiye'deki mevcut tarih ve saati döndürür
    
    Args:
        natural_language (bool): True ise doğal dil formatında döner
        
    Returns:
        str: Mevcut Türkiye tarih ve saati
    """
    # pytz kütüphanesi yüklü değilse yüklemeye çalış
    if not check_pytz_installed():
        return "Tarih ve saat bilgisi alınamadı"
    
    # Türkiye saat dilimini tanımla
    turkey_timezone = pytz.timezone('Europe/Istanbul')
    
    # Şu anki UTC zamanını al ve Türkiye saat dilimine çevir
    current_time_utc = datetime.datetime.now(pytz.UTC)
    current_time_turkey = current_time_utc.astimezone(turkey_timezone)
    
    # Doğal dil formatı
    if natural_language:
        # Türkçe ay isimleri
        months_tr = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
            7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        
        # Türkçe gün isimleri
        days_tr = {
            0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 
            4: "Cuma", 5: "Cumartesi", 6: "Pazar"
        }
        
        # Tarih ve saat bilgilerini ayır
        day = current_time_turkey.day
        month = months_tr[current_time_turkey.month]
        year = current_time_turkey.year
        weekday = days_tr[current_time_turkey.weekday()]
        hour = current_time_turkey.hour
        minute = current_time_turkey.minute
        
        # Doğal dil için tarih ve saat formatı
        date_time_str = f"{day} {month} {year}, {weekday}, saat {hour}:{minute:02d}"
        return date_time_str
    
    # Standart format
    return current_time_turkey.strftime("%d/%m/%Y %H:%M")

def get_time_reply(query):
    """
    Saat sorgusu için uygun yanıtı oluşturur
    
    Args:
        query (str): Kullanıcı sorusu
        
    Returns:
        str: Saat sorusuna yanıt
    """
    query = query.lower()
    
    # Tam tarih ve saat isteniyorsa
    if any(phrase in query for phrase in ["tam tarih", "bugün ne", "bugün hangi", "bugün ayın", "tarih"]):
        date_time = get_turkey_date_time()
        return f"Bugün {date_time}."
    
    # Sadece saat isteniyorsa
    else:
        time_str = get_turkey_time()
        return f"Şu anda Türkiye'de saat {time_str}."

if __name__ == "__main__":
    # Test için
    print("Türkiye Saat Modülü Testi")
    print("-----------------------")
    print(f"Mevcut saat: {get_turkey_time()}")
    print(f"Tam tarih ve saat: {get_turkey_date_time()}")
    print(f"Standart format: {get_turkey_date_time(False)}")
    
    # Örnek sorgular
    test_queries = [
        "Saat kaç?",
        "Saati söyler misin?",
        "Bugün ayın kaçı?",
        "Tarih nedir?",
        "bugün hangi gün?",
        "Tam tarih nedir?",
        "Bugün hangi ay?",
        "Bugün ne var?",
        "Saat kaç oldu?",
        "Saat kaç oldu acaba?",
        "Saat kaç oldu merak ettim.",
        "Saat kaç oldu biliyor musun?",
        "Saat kaç oldu acaba biliyor musun?",
        "Saat kaç oldu öğrenebilir miyim?",
        "Saat kaç oldu acaba öğrenebilir miyim?",
        "Saat kaç oldu öğrenebilir misin?",
        "Saat kaç oldu acaba öğrenebilir misin?",
        "Saat kaç oldu öğrenebilir misin lütfen?",
        "bugünün tarihi nedir?",
        "bugünün tarihi nedir acaba?",
        "bugünün tarihi nedir öğrenebilir miyim?",
        "bugünün tarihi nedir öğrenebilir misin?",
        "bugünün tarihi nedir öğrenebilir misin lütfen?",
    ]
    
    print("\nÖrnek Sorgular:")
    for query in test_queries:
        print(f"Soru: {query}")
        print(f"Yanıt: {get_time_reply(query)}")
        print()