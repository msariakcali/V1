import speech_recognition as sr

def record_voice():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Konuşun...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language="tr-TR")
        print("🗣️ Algılanan:", text)
        return text
    except sr.UnknownValueError:
        print("🤷 Anlaşılamadı.")
        return None