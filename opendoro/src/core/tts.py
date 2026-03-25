import os
import hashlib
import requests
import json
import shutil
import threading
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QUrl, QTimer
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from src.core.logger import logger

try:
    import pygame
    pygame.mixer.init()
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False
    pygame = None

def get_user_data_dir():
    """
    Get user data directory for DoroPet.
    On Windows, this is %LOCALAPPDATA%\\DoroPet
    """
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()

class EdgeTTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, voice, text, cache_path):
        super().__init__()
        self.voice = voice
        self.text = text
        self.cache_path = cache_path

    def run(self):
        try:
            if os.path.exists(self.cache_path):
                self.finished.emit(self.cache_path)
                return

            try:
                import edge_tts
            except ImportError:
                self.error.emit("edge-tts 未安装，请运行：pip install edge-tts")
                return

            # 验证音色是否有效
            if not self.voice:
                self.error.emit("未指定 TTS 音色，请在配置中选择有效的音色")
                return
            
            communicate = edge_tts.Communicate(self.text, self.voice)
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(communicate.save(tmp_path))
            except ValueError as ve:
                # 音色无效时会抛出 ValueError
                error_msg = str(ve)
                if "invalid voice" in error_msg.lower() or "not found" in error_msg.lower():
                    self.error.emit(f"音色 '{self.voice}' 无效或不存在，请使用 '获取可用语音' 按钮获取最新音色列表")
                else:
                    self.error.emit(f"Edge TTS 合成失败：{error_msg}")
                return
            except Exception as e:
                self.error.emit(f"Edge TTS 合成失败：{str(e)}")
                return
            finally:
                loop.close()
            
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            shutil.move(tmp_path, self.cache_path)
            
            self.finished.emit(self.cache_path)
        except Exception as e:
            self.error.emit(str(e))

class OpenAITTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, voice, text, cache_path):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.voice = voice
        self.text = text
        self.cache_path = cache_path

    def run(self):
        try:
            if os.path.exists(self.cache_path):
                self.finished.emit(self.cache_path)
                return

            url = self.base_url
            if not url.endswith("/audio/speech"):
                if url.endswith("/"):
                    url = url + "audio/speech"
                else:
                    url = url + "/audio/speech"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "input": self.text,
                "voice": self.voice
            }
            
            response = requests.post(url, headers=headers, json=data, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                with open(self.cache_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                self.finished.emit(self.cache_path)
            else:
                self.error.emit(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            self.error.emit(str(e))


class QwenTTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, voice, text, cache_path):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.voice = voice
        self.text = text
        self.cache_path = cache_path

    def run(self):
        try:
            if os.path.exists(self.cache_path):
                self.finished.emit(self.cache_path)
                return

            try:
                import dashscope
                from dashscope import MultiModalConversation
            except ImportError:
                self.error.emit("dashscope 未安装，请运行：pip install dashscope")
                return

            if self.base_url:
                dashscope.base_http_api_url = self.base_url

            api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                self.error.emit("请配置阿里云百炼 API Key 或设置环境变量 DASHSCOPE_API_KEY")
                return

            model = self.model or "qwen3-tts-flash"
            voice = self.voice or "Cherry"

            response = MultiModalConversation.call(
                model=model,
                api_key=api_key,
                text=self.text,
                voice=voice
            )

            if response.status_code != 200:
                error_msg = response.message if hasattr(response, 'message') else str(response)
                self.error.emit(f"Qwen TTS API 错误: {error_msg}")
                return

            audio_url = None
            if hasattr(response, 'output') and response.output:
                output = response.output
                if hasattr(output, 'audio') and output.audio:
                    audio_info = output.audio
                    if hasattr(audio_info, 'url') and audio_info.url:
                        audio_url = audio_info.url

            if not audio_url:
                self.error.emit("Qwen TTS 未返回有效的音频数据")
                return

            audio_response = requests.get(audio_url)
            if audio_response.status_code != 200:
                self.error.emit(f"下载音频失败: HTTP {audio_response.status_code}")
                return

            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            cache_path_wav = os.path.splitext(self.cache_path)[0] + '.wav'
            with open(cache_path_wav, 'wb') as f:
                f.write(audio_response.content)
            
            self.finished.emit(cache_path_wav)
        except Exception as e:
            self.error.emit(str(e))


class GradioTTSWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    DEFAULT_PROMPT_AUDIO = "https://github.com/gradio-app/gradio/raw/main/test/test_files/audio_sample.wav"
    DEFAULT_PROMPT_TEXT = "Hello"

    def __init__(self, base_url, voice, api_name, text, cache_path, prompt_audio=None, prompt_text=None):
        super().__init__()
        self.base_url = base_url
        self.voice = voice
        self.api_name = api_name
        self.text = text
        self.cache_path = cache_path
        self.prompt_audio = prompt_audio
        self.prompt_text = prompt_text

    def run(self):
        try:
            if os.path.exists(self.cache_path):
                self.finished.emit(self.cache_path)
                return

            try:
                from gradio_client import Client, handle_file
            except ImportError:
                self.error.emit("gradio_client 未安装，请运行：pip install gradio_client")
                return

            client = Client(self.base_url)
            
            api_endpoint = self.api_name or "/tts_request"
            
            result = None
            
            # 准备参考音频和文本
            prompt_audio = self.prompt_audio if (self.prompt_audio and os.path.exists(self.prompt_audio)) else self.DEFAULT_PROMPT_AUDIO
            prompt_text = self.prompt_text if self.prompt_text else self.DEFAULT_PROMPT_TEXT
            
            logger.info(f"调用 GSV TTS API: {self.base_url}{api_endpoint}")
            logger.info(f"参考音频：{prompt_audio}, 参考文本：{prompt_text}")
            
            try:
                # 根据 GSV TTS WebUI 的 API 要求，传递所有必需参数
                result = client.predict(
                    multi_spk_files=[handle_file(prompt_audio)],
                    spk_weights=self.voice if self.voice else "1.0",
                    prompt_audio=handle_file(prompt_audio),
                    prompt_text=prompt_text,
                    text=self.text,
                    top_k=15,
                    top_p=1,
                    temperature=1,
                    rep_penalty=1.35,
                    noise_scale=0.5,
                    speed=1,
                    enable_enhance=True,
                    is_cut_text=True,
                    cut_punds='{"。", ".", "?", "？", "!", "！", ",", "，", ":", "：", ";", "；", "、"}',
                    cut_minlen=10,
                    cut_mute=0.2,
                    cut_mute_scale_map='{"。": 1.5, ".": 1.5, "？": 1.5, "?": 1.5, "！": 1.5, "!": 1.5, "，": 0.8, ",": 0.8, "、": 0.6}',
                    sovits_batch_size=10,
                    api_name=api_endpoint
                )
                logger.info("GSV TTS API 调用成功")
                    
            except Exception as e:
                logger.warning(f"GSV TTS API 调用失败：{e}，尝试回退到简单调用")
                try:
                    result = client.predict(self.text, api_name=api_endpoint)
                except Exception as e2:
                    self.error.emit(f"Gradio TTS 调用失败：{str(e2)}\n\n请检查:\n1. API 端点是否正确 (当前：{api_endpoint})\n2. WebUI 是否正常运行\n3. 查看 WebUI 控制台的详细错误信息")
                    return
            
            audio_path = None
            if isinstance(result, str):
                if os.path.exists(result):
                    audio_path = result
            elif isinstance(result, tuple):
                for item in result:
                    if isinstance(item, str) and os.path.exists(item):
                        audio_path = item
                        break
            
            if audio_path:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                
                actual_ext = os.path.splitext(audio_path)[1].lower()
                if actual_ext and actual_ext in ['.wav', '.mp3', '.ogg', '.flac']:
                    cache_path_with_ext = os.path.splitext(self.cache_path)[0] + actual_ext
                else:
                    cache_path_with_ext = self.cache_path
                
                shutil.copy(audio_path, cache_path_with_ext)
                self.finished.emit(cache_path_with_ext)
            else:
                self.error.emit(f"Gradio TTS 返回了无效的结果：{type(result)}")
                
            try:
                client.close()
            except:
                pass
                
        except Exception as e:
            self.error.emit(str(e))

class TTSManager(QObject):
    playback_started = pyqtSignal(int)
    playback_stopped = pyqtSignal(int)
    playback_error = pyqtSignal(int, str)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_msg_id = None
        self.cache_dir = os.path.join(get_user_data_dir(), "cache", "tts")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.worker = None
        self._use_pygame = HAS_PYGAME
        self._pygame_playing = False
        self._playback_timer = QTimer()
        self._playback_timer.timeout.connect(self._check_pygame_playback)
        
        if not self._use_pygame:
            self.player = QMediaPlayer()
            self.player.stateChanged.connect(self._on_qm_state_changed)
            self.player.error.connect(self._on_qm_error)
            self.player.durationChanged.connect(self._on_qm_duration_changed)
            self.player.positionChanged.connect(self._on_qm_position_changed)
            self._is_playing = False
            self._audio_duration = 0
            self._has_ended_normally = False
            self._last_position = 0
            self._retry_count = 0
            self._max_retries = 3
        
    def speak(self, msg_id, text):
        if self._use_pygame and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            self._pygame_playing = False
        elif not self._use_pygame and self.player.state() == QMediaPlayer.PlayingState:
            previous_msg_id = self.current_msg_id
            self.player.stop()
            self._is_playing = False
            if previous_msg_id == msg_id:
                return

        self.current_msg_id = msg_id
        
        config = self.db.get_active_tts_model()
        if not config:
            self.playback_error.emit(msg_id, "请先在配置页设置并激活 TTS 模型")
            self.current_msg_id = None
            return
        
        if len(config) >= 12:
            provider_id, _, provider, api_key, base_url, model_name, voice, _, proxy, api_name, prompt_audio, prompt_text = config
        elif len(config) >= 9:
            provider_id, _, provider, api_key, base_url, model_name, voice, _, api_name = config[:9]
            prompt_audio = ""
            prompt_text = ""
        else:
            provider_id, _, provider, api_key, base_url, model_name, voice, _ = config[:8]
            api_name = "/tts_request"
            prompt_audio = ""
            prompt_text = ""
        
        content_hash = hashlib.md5(f"{text}{provider}{voice}".encode()).hexdigest()
        cache_base = os.path.join(self.cache_dir, content_hash)
        
        cached_file = None
        for ext in ['.wav', '.mp3', '.ogg', '.flac']:
            test_path = cache_base + ext
            if os.path.exists(test_path):
                cached_file = test_path
                break
        
        if cached_file:
            self.play_file(cached_file)
        else:
            file_path = cache_base + '.mp3'
            if provider == "edge_tts":
                self.worker = EdgeTTSWorker(voice or "zh-CN-XiaoxiaoNeural", text, file_path)
            elif provider == "gradio_tts":
                self.worker = GradioTTSWorker(base_url, voice, api_name, text, file_path, prompt_audio, prompt_text)
            elif provider == "qwen_tts":
                self.worker = QwenTTSWorker(api_key, base_url, model_name, voice, text, file_path)
            else:
                self.worker = OpenAITTSWorker(api_key, base_url, model_name, voice, text, file_path)
            
            self.worker.finished.connect(lambda path: self.play_file(path))
            self.worker.error.connect(lambda err: self.on_worker_error(msg_id, err))
            self.worker.start()
            
    def play_file(self, path):
        if not self.current_msg_id:
            return
        
        if not os.path.exists(path):
            self.playback_error.emit(self.current_msg_id, f"音频文件不存在: {path}")
            self.current_msg_id = None
            return
        
        logger.info(f"播放音频: {path}, 使用 {'pygame' if self._use_pygame else 'QMediaPlayer'}")
        
        if self._use_pygame:
            self._play_pygame(path)
        else:
            self._play_qmediaplayer(path)

    def _play_pygame(self, path):
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            self._pygame_playing = True
            self._playback_timer.start(100)
            self.playback_started.emit(self.current_msg_id)
        except Exception as e:
            logger.error(f"pygame 播放失败: {e}")
            self.playback_error.emit(self.current_msg_id, f"播放失败: {str(e)}")
            self.current_msg_id = None

    def _check_pygame_playback(self):
        if not pygame.mixer.music.get_busy() and self._pygame_playing:
            self._pygame_playing = False
            self._playback_timer.stop()
            if self.current_msg_id:
                msg_id = self.current_msg_id
                self.current_msg_id = None
                self.playback_stopped.emit(msg_id)

    def _play_qmediaplayer(self, path):
        self._is_playing = True
        self._audio_duration = 0
        self._has_ended_normally = False
        self._last_position = 0
        self._retry_count = 0
        
        url = QUrl.fromLocalFile(path)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()
        self.playback_started.emit(self.current_msg_id)

    def stop(self):
        if self._use_pygame:
            pygame.mixer.music.stop()
            self._pygame_playing = False
            self._playback_timer.stop()
        else:
            self._is_playing = False
            self._has_ended_normally = True
            self.player.stop()
        
        if self.current_msg_id:
            self.playback_stopped.emit(self.current_msg_id)
            self.current_msg_id = None

    def _on_qm_duration_changed(self, duration):
        self._audio_duration = duration
        logger.debug(f"Audio duration: {duration}ms")

    def _on_qm_position_changed(self, position):
        if self._is_playing:
            self._last_position = position

    def _on_qm_error(self):
        if self.current_msg_id:
            error_string = self.player.errorString()
            logger.error(f"QMediaPlayer error: {error_string}")
            self.playback_error.emit(self.current_msg_id, f"播放错误: {error_string}")
            self._is_playing = False
            self.current_msg_id = None

    def _on_qm_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self._is_playing = True
        elif state == QMediaPlayer.StoppedState:
            if self._is_playing and not self._has_ended_normally:
                duration = self.player.duration()
                position = self._last_position
                if duration > 0 and position < duration - 500 and self._retry_count < self._max_retries:
                    self._retry_count += 1
                    logger.warning(f"播放提前结束: position={position}, duration={duration}, 重试({self._retry_count}/{self._max_retries})")
                    self.player.setPosition(position)
                    self.player.play()
                    return
                elif self._retry_count >= self._max_retries:
                    logger.error(f"播放重试次数已达上限，放弃重试")
            self._is_playing = False
            if self.current_msg_id:
                msg_id = self.current_msg_id
                self.current_msg_id = None
                self.playback_stopped.emit(msg_id)
            
    def on_worker_error(self, msg_id, err):
        self.playback_error.emit(msg_id, err)
        if self.current_msg_id == msg_id:
            self.current_msg_id = None
            self.playback_stopped.emit(msg_id)
