import os
import pyaudio
import queue
import threading
from google.cloud import speech
import time
import numpy as np

# Import TTS module to check speaking status - use both flags now
from tts_google import is_speaking, tts_active, is_tts_active

class MicrophoneStream:
    """Professional audio stream optimized for speech recognition in various environments."""

    def __init__(self, rate=16000, chunk=1024):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True
        self._audio = None
        self._stream = None
        
        # Optimize for both accuracy and speed
        self.silence_threshold = 250       # Base silence threshold
        self.speech_energy_threshold = 320 # Speech detection threshold
        self.end_of_speech = 15            # Frames of silence to detect end of speech (~0.45s)
        self.long_pause = 25               # Longer pause detection (~0.75s) for better sentence completion
        self.min_speech_duration = 0.5     # Minimum speech duration (seconds)
        self.max_speech_duration = 8.0     # Maximum speech duration (seconds) - longer for complex sentences
        
        # Speech quality tracking variables
        self.silence_frames = 0
        self.speech_detected = False
        self.speech_start_time = 0
        self.last_significant_audio_time = time.time()
        self.energy_readings = []
        self.energy_window = 30            # Energy history window
        self.recent_speech_quality = []    # Track recent speech quality
        self.speech_quality_window = 5     # Quality history window
        self.speech_quality_threshold = 0.6 # Minimum acceptable speech quality
        self.last_sentence_pause = 0       # Track natural pauses in speech
        self.likely_sentence_end = False   # Flag for probable sentence completion
        
        # Speech echo cancellation
        self.tts_cooldown = 1.0            # Time to ignore audio input after TTS finishes (seconds)
        self.last_tts_time = 0             # Last time TTS was active

    def __enter__(self):
        print("🎤 Mikrofon başlatılıyor...")
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        print("✓ Mikrofon hazır")
        return self

    def __exit__(self, type, value, traceback):
        print("🔄 Mikrofon kapatılıyor...")
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        self.closed = True
        self._buff.put(None)
        if self._audio:
            self._audio.terminate()

    def _update_energy_average(self, rms):
        """Update rolling average of audio energy"""
        self.energy_readings.append(rms)
        if len(self.energy_readings) > self.energy_window:
            self.energy_readings.pop(0)
        
    def _update_speech_quality(self, quality):
        """Update speech quality metrics"""
        self.recent_speech_quality.append(quality)
        if len(self.recent_speech_quality) > self.speech_quality_window:
            self.recent_speech_quality.pop(0)
    
    def _get_average_speech_quality(self):
        """Get average speech quality from recent readings"""
        if not self.recent_speech_quality:
            return 0
        return sum(self.recent_speech_quality) / len(self.recent_speech_quality)
        
    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Listen to audio stream with professional-grade speech detection"""
        # Check if TTS is currently speaking or in cooldown period after speaking
        # If TTS is active in any way, ignore audio input to prevent self-triggering
        if is_tts_active():
            self._buff.put(in_data)  # Still add audio to buffer but don't process it
            return None, pyaudio.paContinue
        
        audio_array = np.frombuffer(in_data, dtype=np.int16)
        
        # Calculate RMS energy safely
        square_sum = np.mean(np.square(audio_array))
        rms = np.sqrt(square_sum) if square_sum > 0 else 0
        
        # Update energy metrics
        self._update_energy_average(rms)
        
        # Adaptive noise threshold adjustment
        if len(self.energy_readings) > 15:
            # Analyze environment noise characteristics
            noise_floor = np.percentile(self.energy_readings, 15)    # Background noise level
            noise_ceiling = np.percentile(self.energy_readings, 85)  # Typical high levels
            
            # Adjust thresholds based on environment
            noise_range = noise_ceiling - noise_floor
            if noise_range < 100:  # Quiet environment
                self.silence_threshold = max(noise_floor * 1.2, 200)
                self.speech_energy_threshold = max(noise_floor * 1.5, 250)
                self.end_of_speech = 12    # Faster response in quiet
                self.long_pause = 20
            elif noise_range < 500:  # Normal environment
                self.silence_threshold = max(noise_floor * 1.3, 250)
                self.speech_energy_threshold = max(noise_floor * 1.7, 300)
                self.end_of_speech = 15
                self.long_pause = 25
            else:  # Noisy environment
                self.silence_threshold = max(noise_floor * 1.4, 280)
                self.speech_energy_threshold = max(noise_floor * 2.0, 350)
                self.end_of_speech = 18    # More cautious in noise
                self.long_pause = 30
            
            # Limit thresholds to reasonable ranges
            self.silence_threshold = min(self.silence_threshold, 400)
            self.speech_energy_threshold = min(self.speech_energy_threshold, 500)
        
        # Speech detection logic
        if rms > self.speech_energy_threshold or (self.speech_detected and rms > self.silence_threshold):
            # Meaningful speech detected
            speech_quality = min(1.0, rms / (self.speech_energy_threshold * 2))
            self._update_speech_quality(speech_quality)
            
            self.last_significant_audio_time = current_time
            self.silence_frames = 0
            self.last_sentence_pause = 0
            self.likely_sentence_end = False
            
            if not self.speech_detected:
                self.speech_detected = True
                self.speech_start_time = current_time
                print("\r🎙️ Konuşma algılandı", end="", flush=True)
        else:
            # Silence or pause detected
            if self.speech_detected:
                self.silence_frames += 1
                self.last_sentence_pause += 1
                speech_duration = current_time - self.speech_start_time
                avg_quality = self._get_average_speech_quality()
                
                # End of speech detection scenarios
                if speech_duration > self.min_speech_duration:
                    # Natural sentence completion detection
                    if self.last_sentence_pause > 8 and self.last_sentence_pause < self.end_of_speech:
                        self.likely_sentence_end = True
                
                    # 1. Full end of speech after sufficient silence
                    if self.silence_frames > self.end_of_speech:
                        print("\r✓ Konuşma tamamlandı - işleniyor", end="", flush=True)
                        self._buff.put(b"END_OF_SPEECH_MARKER")
                        self.speech_detected = False
                        self.speech_start_time = 0
                    
                    # 2. Long speech with natural pause and good quality
                    elif speech_duration > 2.0 and self.likely_sentence_end and avg_quality > self.speech_quality_threshold:
                        print("\r✓ Doğal cümle sonu - işleniyor", end="", flush=True)
                        self._buff.put(b"SENTENCE_END_MARKER") 
                        # Don't reset speech_detected here, allow continuation
                        self.likely_sentence_end = False
                        self.last_sentence_pause = 0
                    
                    # 3. Very long speech with longer pause - assume speaker is thinking
                    elif speech_duration > 3.5 and self.silence_frames > self.long_pause:
                        print("\r✓ Uzun duraklatma - işleniyor", end="", flush=True)
                        self._buff.put(b"SENTENCE_END_MARKER")
                        # Don't reset speech_detected, allow continuation
                        self.last_sentence_pause = 0
                    
                    # 4. Maximum speech duration exceeded - force processing
                    elif speech_duration > self.max_speech_duration:
                        print("\r⌛ Maksimum konuşma süresi - işleniyor", end="", flush=True)
                        self._buff.put(b"END_OF_SPEECH_MARKER")
                        self.speech_detected = False
                        self.speech_start_time = 0
                
                # Very long silence - reset speech state
                elif self.silence_frames > 45:  # ~1.4 seconds silence
                    self.speech_detected = False
                    self.speech_start_time = 0
            
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        """Generate audio stream with intelligent speech segmentation"""
        speech_ended = False
        sentence_ended = False
        data_buffer = []
        last_sent_time = time.time()
        
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
                
            # Skip processing if TTS is active (speaking or in cooldown)
            if is_tts_active():
                # Clear the buffer to avoid processing accumulated audio during TTS
                data_buffer = []
                continue
                
            # Check for special markers
            if chunk == b"END_OF_SPEECH_MARKER":
                speech_ended = True
                if len(data_buffer) > 0:
                    continue  # Process remaining buffer before ending
                else:
                    speech_ended = False
                    continue
            elif chunk == b"SENTENCE_END_MARKER":
                sentence_ended = True
                if len(data_buffer) > 0:
                    continue  # Process remaining buffer before ending sentence
                else:
                    sentence_ended = False
                    continue
                
            data_buffer.append(chunk)
            current_time = time.time()
            
            # Data sending conditions
            buffer_full = len(data_buffer) >= 15      # ~0.5s of audio  
            time_elapsed = current_time - last_sent_time > 0.5  # Regular updates
            
            if speech_ended or sentence_ended or buffer_full or time_elapsed:
                if len(data_buffer) > 0:
                    audio_chunk = b''.join(data_buffer)
                    data_buffer = []  # Reset buffer
                    last_sent_time = current_time
                    
                    yield audio_chunk
                    
                    # Signal end of utterance or sentence
                    if speech_ended:
                        yield b"STREAMING_LIMIT_REACHED"
                        speech_ended = False
                    elif sentence_ended:
                        yield b"SENTENCE_BOUNDARY"
                        sentence_ended = False

def listen_print_loop(responses, callback=None):
    """Process API responses with optimized real-time transcription"""
    interim_transcript = ""
    final_transcript = ""
    last_interim_time = time.time()
    transcript_start_time = None
    last_transcript_change_time = time.time()
    last_transcript_length = 0
    last_significant_change_time = time.time()
    word_count = 0
    previous_word_count = 0
    processing_complete = False
    sentence_boundary_received = False
    
    # Timeout settings optimized for natural speech
    no_new_words_timeout = 1.2      # Time with no new words before processing (seconds)
    no_transcript_timeout = 3.0     # Timeout for completely unintelligible speech
    dead_air_start = time.time()    # Last time meaningful audio was detected
    stability_threshold = 0.85      # Stability threshold for interim results
    
    for response in responses:
        current_time = time.time()
        
        # Skip processing if TTS is active to avoid self-triggering
        if is_tts_active():
            continue
            
        # Check for timeout with no meaningful transcript
        if current_time - dead_air_start > no_transcript_timeout and not interim_transcript:
            print("\n⏱️ Anlamlı konuşma algılanamadı")
            return None
            
        # Handle sentence boundary markers for long speech
        if hasattr(response, 'speech_event_type') and response.speech_event_type:
            if response.speech_event_type == speech.StreamingRecognizeResponse.SpeechEventType.END_OF_SINGLE_UTTERANCE:
                sentence_boundary_received = True
                if interim_transcript and len(interim_transcript.strip()) > 3:
                    print(f"\n⏱️ Cümle sınırı algılandı - işleniyor: {interim_transcript.strip()}")
                    if callback:
                        return callback(interim_transcript)
        
        if not response.results:
            # No results, but we have a good interim transcript and no new words
            if interim_transcript and len(interim_transcript.strip()) > 3:
                # Process after no new words for a while
                if current_time - last_transcript_change_time > no_new_words_timeout:
                    print(f"\n⏱️ Konuşma duraklaması - işleniyor: {interim_transcript.strip()}")
                    if callback:
                        return callback(interim_transcript)
            continue
        
        # Reset dead air timer whenever we get results
        dead_air_start = current_time
        
        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript
        
        # Calculate speech metrics
        current_word_count = len(transcript.strip().split())
        transcript_changed = transcript != interim_transcript
        words_added = current_word_count > previous_word_count
        stability = getattr(result, 'stability', 0)
        
        # Update timing variables when transcript changes
        if transcript_changed:
            last_interim_time = current_time
            
            # Track new words being added
            if words_added:
                last_transcript_change_time = current_time
                last_significant_change_time = current_time
                previous_word_count = current_word_count
                
            if not transcript_start_time:
                transcript_start_time = current_time
                
            # Track transcript length for growth detection
            last_transcript_length = len(transcript)
        
        if result.is_final:
            # Final result - process immediately
            final_transcript = transcript
            print(f"\n✓ Final sonuç: {final_transcript.strip()}")
            processing_complete = True
            if callback and len(final_transcript.strip()) > 0:
                return callback(final_transcript)
        else:
            # Interim result processing with intelligent handling
            interim_transcript = transcript
            transcript_age = current_time - transcript_start_time if transcript_start_time else 0
            
            # Display current transcript with length indicator
            word_count = len(transcript.strip().split())
            quality_indicator = "🟢" if stability > stability_threshold else "🟡" if stability > 0.5 else "🔴"
            print(f"\r{quality_indicator} {interim_transcript} [{word_count}]", end="", flush=True)
            
            # Interim result processing strategy
            if len(interim_transcript.strip()) > 3 and not processing_complete:
                # Detect conditions for processing interim results:
                
                # 1. No new words for a while (speaker paused)
                words_stopped = current_time - last_transcript_change_time > no_new_words_timeout
                
                # 2. Overall transcript is stable with no updates
                no_updates = current_time - last_interim_time > 1.0 and stability > stability_threshold
                
                # 3. Long transcript with good stability
                long_transcript = transcript_age > 2.0 and len(interim_transcript) > 10 and stability > 0.75
                
                # 4. Natural sentence ending detected
                sentence_end = any(mark in interim_transcript[-5:] for mark in ['.', '!', '?', ',']) and stability > 0.7
                
                # 5. Sentence boundary detected by the API
                if sentence_boundary_received:
                    print(f"\n⏱️ API cümle sonu - işleniyor: {interim_transcript.strip()}")
                    sentence_boundary_received = False
                    if callback:
                        return callback(interim_transcript)
                
                # Process interim result if conditions met
                elif words_stopped or no_updates or long_transcript or sentence_end:
                    reason = "konuşma duraklaması" if words_stopped else \
                             "kararlı transcript" if no_updates else \
                             "uzun transcript" if long_transcript else "cümle sonu"
                    
                    print(f"\n⚡ İşleniyor ({reason}): {interim_transcript.strip()}")
                    if callback:
                        return callback(interim_transcript)
    
    # If we have a good interim result but no final result, use it
    if len(interim_transcript.strip()) > 3 and not processing_complete:
        print(f"\n⚡ Son transcript kullanılıyor: {interim_transcript.strip()}")
        if callback:
            return callback(interim_transcript)
            
    return None

def record_voice_stream(callback=None, language="tr-TR"):
    """Professional-grade speech recognition optimized for natural conversation"""
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language,
        enable_automatic_punctuation=True,
        model="command_and_search",
        use_enhanced=True,       # Enhanced noise filtering
    )
    
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,    # Get real-time results
    )

    print("\n🎤 Sizi dinliyorum...")
    
    with MicrophoneStream(16000, 1024) as stream:
        audio_generator = stream.generator()
        
        # Generate API requests with intelligent speech segmentation
        def generate_requests():
            for content in audio_generator:
                # Skip generating requests if TTS is active
                if is_tts_active():
                    continue
                    
                # Check for special markers
                if content == b"STREAMING_LIMIT_REACHED":
                    print("\n✅ Konuşma işleniyor")
                    yield speech.StreamingRecognizeRequest(
                        streaming_config=streaming_config,
                        audio_content=b'')  # Empty request to signal end
                    return
                elif content == b"SENTENCE_BOUNDARY":
                    # Signal a sentence boundary but continue streaming
                    continue
                    
                # Send audio content
                request = speech.StreamingRecognizeRequest(audio_content=content)
                yield request
                
        # Process requests and handle responses
        try:
            responses = client.streaming_recognize(streaming_config, generate_requests())
            return listen_print_loop(responses, callback)
        except Exception as e:
            print(f"\n❌ API hatası: {str(e)}")
            if "exceeded maximum allowed stream duration" in str(e).lower():
                print("💡 İpucu: Çok uzun süre sessiz kalındı veya konuşma algılanamadı.")
            return None

def record_voice(callback=None):
    """Backward compatibility function"""
    return record_voice_stream(callback)

# For direct testing
if __name__ == "__main__":
    print("🎯 Ses algılama testi başlatılıyor...")
    
    def process_text(text):
        print(f"✅ İşlenen metin: {text}")
        # Return "stop" to stop listening if you say "bitir"
        if "bitir" in text.lower():
            return "stop"
        return None
    
    result = record_voice_stream(process_text)
    print(f"Son sonuç: {result}")