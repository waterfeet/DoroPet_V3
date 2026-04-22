import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from src.core.logger import logger

PYAUDIOWPATCH_AVAILABLE = False
pyaudio = None

try:
    import pyaudiowpatch as pyaudio
    PYAUDIOWPATCH_AVAILABLE = True
    logger.info("[SpectrumAnalyzer] pyaudiowpatch loaded successfully")
except ImportError:
    logger.warning("[SpectrumAnalyzer] pyaudiowpatch not available, spectrum will be simulated")


class AudioSpectrumAnalyzer(QObject):
    spectrum_data_ready = pyqtSignal(list)

    _instance = None

    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None:
            cls._instance = AudioSpectrumAnalyzer(parent)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._num_bars = 32
        self._sample_rate = 44100
        self._fft_size = 2048
        self._audio_buffer = np.zeros(self._fft_size, dtype=np.float32)
        self._is_running = False
        self._stream = None
        self._pyaudio_instance = None
        self._loopback_device_index = None
        self._fallback_mode = not PYAUDIOWPATCH_AVAILABLE
        self._silence_count = 0

        if PYAUDIOWPATCH_AVAILABLE:
            self._find_loopback_device()

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._process_audio)

    def _find_loopback_device(self):
        try:
            self._pyaudio_instance = pyaudio.PyAudio()
            
            default_output = self._pyaudio_instance.get_default_output_device_info()
            default_output_name = default_output['name']
            logger.info(f"[SpectrumAnalyzer] Default output device: {default_output_name}")
            
            wasapi_index = None
            for i in range(self._pyaudio_instance.get_host_api_count()):
                api = self._pyaudio_instance.get_host_api_info_by_index(i)
                if 'WASAPI' in api.get('name', ''):
                    wasapi_index = i
                    break
            
            if wasapi_index is None:
                logger.warning("[SpectrumAnalyzer] WASAPI not found")
                self._fallback_mode = True
                self._pyaudio_instance.terminate()
                self._pyaudio_instance = None
                return
            
            loopback_devices = []
            for i in range(self._pyaudio_instance.get_device_count()):
                dev = self._pyaudio_instance.get_device_info_by_index(i)
                if dev['hostApi'] == wasapi_index and dev['maxInputChannels'] > 0:
                    name = dev['name']
                    if '[Loopback]' in name:
                        loopback_devices.append((i, dev))
                        base_name = name.replace(' [Loopback]', '').strip()
                        if base_name == default_output_name or default_output_name in name:
                            self._loopback_device_index = i
                            self._sample_rate = int(dev['defaultSampleRate'])
                            logger.info(f"[SpectrumAnalyzer] Found matching loopback: {name} @ {self._sample_rate}Hz")
                            return
            
            if loopback_devices:
                idx, dev = loopback_devices[0]
                self._loopback_device_index = idx
                self._sample_rate = int(dev['defaultSampleRate'])
                logger.info(f"[SpectrumAnalyzer] Using first loopback: {dev['name']} @ {self._sample_rate}Hz")
                return
            
            logger.warning("[SpectrumAnalyzer] No loopback device found")
            self._fallback_mode = True
            self._pyaudio_instance.terminate()
            self._pyaudio_instance = None

        except Exception as e:
            logger.warning(f"[SpectrumAnalyzer] Error finding loopback device: {e}")
            self._fallback_mode = True
            if self._pyaudio_instance:
                self._pyaudio_instance.terminate()
                self._pyaudio_instance = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if status:
            return (None, pyaudio.paAbort)
        
        try:
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            if len(audio_data) > 0:
                if len(audio_data) >= self._fft_size:
                    self._audio_buffer = audio_data[-self._fft_size:]
                else:
                    self._audio_buffer = np.roll(self._audio_buffer, -len(audio_data))
                    self._audio_buffer[-len(audio_data):] = audio_data
        except:
            pass
        
        return (in_data, pyaudio.paContinue)

    def start(self):
        if self._is_running:
            return

        try:
            if self._fallback_mode:
                logger.info("[SpectrumAnalyzer] Starting in fallback mode (simulated spectrum)")
                self._is_running = True
                self._update_timer.start(30)
                return

            self._start_loopback()
            self._is_running = True
            self._update_timer.start(30)
            logger.info("[SpectrumAnalyzer] Started")

        except Exception as e:
            logger.error(f"[SpectrumAnalyzer] Failed to start: {e}")
            self._fallback_mode = True
            self._is_running = True
            self._update_timer.start(30)

    def _start_loopback(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
            self._stream = None

        if self._loopback_device_index is None:
            logger.error("[SpectrumAnalyzer] No loopback device index")
            self._fallback_mode = True
            return

        try:
            dev_info = self._pyaudio_instance.get_device_info_by_index(self._loopback_device_index)
            channels = min(2, int(dev_info['maxInputChannels']))
            
            self._stream = self._pyaudio_instance.open(
                format=pyaudio.paFloat32,
                channels=channels,
                rate=int(self._sample_rate),
                input=True,
                input_device_index=self._loopback_device_index,
                frames_per_buffer=self._fft_size // 2,
                stream_callback=self._audio_callback
            )
            self._stream.start_stream()
            logger.info(f"[SpectrumAnalyzer] Stream started: {dev_info['name']}")
            
        except Exception as e:
            logger.error(f"[SpectrumAnalyzer] Failed to open stream: {e}")
            self._fallback_mode = True

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        self._update_timer.stop()

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except:
                pass
            self._stream = None

        logger.info("[SpectrumAnalyzer] Stopped")

    def _process_audio(self):
        if self._fallback_mode:
            self._generate_fallback_data()
            return

        try:
            audio_data = self._audio_buffer.copy()

            rms = np.sqrt(np.mean(audio_data ** 2))
            if rms < 0.001:
                self._silence_count += 1
                if self._silence_count > 10:
                    self._generate_fallback_data()
                    return
            else:
                self._silence_count = 0

            window = np.hanning(len(audio_data))
            windowed_data = audio_data * window

            fft_result = np.fft.rfft(windowed_data)
            magnitudes = np.abs(fft_result)

            frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self._sample_rate)

            spectrum = self._map_to_bars(magnitudes, frequencies)

            self.spectrum_data_ready.emit(spectrum)

        except Exception as e:
            logger.warning(f"[SpectrumAnalyzer] Error processing audio: {e}")
            self._generate_fallback_data()

    def _map_to_bars(self, magnitudes, frequencies):
        min_freq = 60
        max_freq = 16000

        log_min = np.log10(min_freq)
        log_max = np.log10(max_freq)
        log_freqs = np.logspace(log_min, log_max, self._num_bars + 1)

        spectrum = []
        for i in range(self._num_bars):
            low_freq = log_freqs[i]
            high_freq = log_freqs[i + 1]

            mask = (frequencies >= low_freq) & (frequencies < high_freq)
            if np.any(mask):
                band_magnitude = np.max(magnitudes[mask])
            else:
                band_magnitude = 0

            normalized = min(1.0, band_magnitude / 80.0)
            spectrum.append(normalized)

        return spectrum

    def _generate_fallback_data(self):
        import random
        import math

        spectrum = []
        for i in range(self._num_bars):
            weight = 1.0 - abs(i - self._num_bars / 2) / (self._num_bars / 2) * 0.4
            value = random.uniform(0.1, 0.8) * weight
            spectrum.append(max(0.05, min(1.0, value)))

        self.spectrum_data_ready.emit(spectrum)

    def set_num_bars(self, num_bars: int):
        self._num_bars = num_bars

    def is_running(self) -> bool:
        return self._is_running

    def close(self):
        self.stop()
        if self._pyaudio_instance:
            try:
                self._pyaudio_instance.terminate()
            except:
                pass
            self._pyaudio_instance = None
