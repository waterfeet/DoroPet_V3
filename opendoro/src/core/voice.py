import os
import queue
import sys
import numpy as np
import sounddevice as sd
import sherpa_onnx
import sentencepiece as spm
from PyQt5.QtCore import QThread, pyqtSignal, QObject

class VoiceAssistant(QThread):
    wake_detected = pyqtSignal()
    text_recognized = pyqtSignal(str)
    listening_status = pyqtSignal(str) # "idle", "listening", "processing"
    error_occurred = pyqtSignal(str)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.running = False
        self.audio_queue = queue.Queue()
        self.sample_rate = 16000
        
        # Default paths
        self.kws_model_dir = os.path.join(os.getcwd(), "models", "voice", "sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01")
        self.asr_model_dir = os.path.join(os.getcwd(), "models", "voice", "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20")
        self.wake_word = "Hey Doro"

        # State
        self.state = "IDLE" # IDLE, LISTENING
        
        # Initialize models
        self.models_loaded = False
        # Models will be loaded in run()

    def update_keywords_file(self):
        if not os.path.exists(self.kws_model_dir):
            return
            
        keywords_path = os.path.join(self.kws_model_dir, "my_keywords.txt")
        bpe_model_path = os.path.join(self.kws_model_dir, "bpe.model")
        
        try:
            keyword_line = ""
            
            # Try to use BPE tokenizer if available (Best for GigaSpeech models)
            if os.path.exists(bpe_model_path):
                try:
                    sp = spm.SentencePieceProcessor(model_file=bpe_model_path)
                    # GigaSpeech models usually expect uppercase
                    text_upper = self.wake_word.upper()
                    tokens = sp.encode(text_upper, out_type=str)
                    keyword_line = " ".join(tokens)
                    print(f"Generated tokens for '{self.wake_word}': {keyword_line}")
                except Exception as e:
                    print(f"BPE tokenization failed: {e}")
            
            # Fallback to simple char-based if BPE failed or not available
            if not keyword_line:
                # "Hey Doro" -> "▁ H E Y ▁ D O R O"
                # Use simple heuristic that works for most English chars in this model
                tokens = []
                for word in self.wake_word.upper().split():
                    tokens.append("▁")
                    tokens.extend(list(word))
                keyword_line = " ".join(tokens)
                print(f"Using fallback tokens: {keyword_line}")

            # Write to file (without threshold to avoid parsing issues)
            with open(keywords_path, "w", encoding="utf-8") as f:
                f.write(f"{keyword_line}\n")
                
        except Exception as e:
            print(f"Failed to update keywords file: {e}")

    def init_kws(self):
        # Update keywords file before initializing
        self.update_keywords_file()
        
        self.kws = sherpa_onnx.KeywordSpotter(
            tokens=os.path.join(self.kws_model_dir, "tokens.txt"),
            encoder=os.path.join(self.kws_model_dir, "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
            decoder=os.path.join(self.kws_model_dir, "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
            joiner=os.path.join(self.kws_model_dir, "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"),
            keywords_file=os.path.join(self.kws_model_dir, "my_keywords.txt"),
            num_threads=1,
            provider="cpu",
            sample_rate=self.sample_rate,
            feature_dim=80
        )
        self.kws_stream = self.kws.create_stream()

    def init_asr(self):
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=os.path.join(self.asr_model_dir, "tokens.txt"),
            encoder=os.path.join(self.asr_model_dir, "encoder-epoch-99-avg-1.onnx"),
            decoder=os.path.join(self.asr_model_dir, "decoder-epoch-99-avg-1.onnx"),
            joiner=os.path.join(self.asr_model_dir, "joiner-epoch-99-avg-1.onnx"),
            num_threads=1,
            sample_rate=self.sample_rate,
            feature_dim=80,
            decoding_method="greedy_search",
            enable_endpoint_detection=True,
            rule1_min_trailing_silence=2.4,
            rule2_min_trailing_silence=1.2,
            rule3_min_utterance_length=20.0,
            provider="cpu"
        )
        self.asr_stream = self.recognizer.create_stream()

    def run(self):
        self.running = True
        
        # Load settings from DB if available
        if self.db:
            try:
                settings = self.db.get_voice_settings()
                if settings:
                    # is_enabled, wake_word, kws_path, asr_path
                    is_enabled = bool(settings[0])
                    if not is_enabled:
                        print("Voice assistant is disabled in settings.")
                        self.running = False
                        return
                        
                    if settings[1]: self.wake_word = settings[1]
                    if settings[2] and os.path.exists(settings[2]): self.kws_model_dir = settings[2]
                    if settings[3] and os.path.exists(settings[3]): self.asr_model_dir = settings[3]
            except Exception as e:
                print(f"Failed to load voice settings: {e}")

        if not self.models_loaded:
            print("Initializing voice models...")
            # Optional: Emit a status to UI
            # self.listening_status.emit("loading") 
            try:
                self.init_kws()
                self.init_asr()
                self.models_loaded = True
            except Exception as e:
                print(f"Failed to load voice models: {e}")
                self.error_occurred.emit(f"Voice model error: {e}")
                self.running = False
                return
        
        # Check if stopped during initialization
        if not self.running:
            return

        # Start audio stream
        
        # Start audio stream
        try:
            with sd.InputStream(channels=1, samplerate=self.sample_rate, blocksize=1024, callback=self.sd_callback):
                while self.running:
                    try:
                        samples = self.audio_queue.get(timeout=0.1)
                        self.process_audio(samples)
                    except queue.Empty:
                        continue
                    except Exception as e:
                        print(f"Error processing audio: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Microphone error: {e}")
            self.running = False

    def sd_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.audio_queue.put(indata.copy())

    def process_audio(self, samples):
        # samples is (N, 1) numpy array, float32
        # sherpa_onnx expects 1D float array
        samples = samples.flatten()
        
        if self.state == "IDLE":
            self.kws_stream.accept_waveform(self.sample_rate, samples)
            while self.kws.is_ready(self.kws_stream):
                self.kws.decode_stream(self.kws_stream)
                keyword = self.kws.get_result(self.kws_stream)
                if keyword:
                    print(f"Wake detected: {keyword}")
                    self.wake_detected.emit()
                    self.state = "LISTENING"
                    self.listening_status.emit("listening")
                    
                    # Reset ASR stream for fresh start
                    self.asr_stream = self.recognizer.create_stream()
                    # Feed the current chunk to ASR too? Maybe.
                    # Usually better to start ASR from now.
                    
        elif self.state == "LISTENING":
            self.asr_stream.accept_waveform(self.sample_rate, samples)
            while self.recognizer.is_ready(self.asr_stream):
                self.recognizer.decode_stream(self.asr_stream)
            
            is_endpoint = self.recognizer.is_endpoint(self.asr_stream)
            result = self.recognizer.get_result(self.asr_stream)
            
            # Real-time preview if needed
            if result:
                 pass # print(f"Partial: {result}")

            if is_endpoint:
                text = result.strip()
                if text:
                    print(f"Recognized: {text}")
                    self.text_recognized.emit(text)
                else:
                    print("Ignored empty/silence")
                
                self.state = "IDLE"
                self.listening_status.emit("idle")
                self.recognizer.reset(self.asr_stream)

    def stop(self):
        self.running = False
        self.wait()
