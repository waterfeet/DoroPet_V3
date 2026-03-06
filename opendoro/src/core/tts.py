import os
import hashlib
import requests
import json
import shutil
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

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
                self.error.emit("edge-tts 未安装，请运行: pip install edge-tts")
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

class TTSManager(QObject):
    playback_started = pyqtSignal(int)
    playback_stopped = pyqtSignal(int)
    playback_error = pyqtSignal(int, str)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.player = QMediaPlayer()
        self.player.stateChanged.connect(self.on_state_changed)
        self.current_msg_id = None
        self.cache_dir = os.path.join(get_user_data_dir(), "cache", "tts")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.worker = None
        
    def speak(self, msg_id, text):
        if self.player.state() == QMediaPlayer.PlayingState:
            previous_msg_id = self.current_msg_id
            self.player.stop()
            if previous_msg_id == msg_id:
                return

        self.current_msg_id = msg_id
        
        config = self.db.get_active_tts_model()
        if not config:
            self.playback_error.emit(msg_id, "请先在配置页设置并激活 TTS 模型")
            self.current_msg_id = None
            return
            
        provider_id, _, provider, api_key, base_url, model_name, voice, _ = config
        
        content_hash = hashlib.md5(f"{text}{provider}{voice}".encode()).hexdigest()
        file_path = os.path.join(self.cache_dir, f"{content_hash}.mp3")
        
        if os.path.exists(file_path):
            self.play_file(file_path)
        else:
            if provider == "edge_tts":
                self.worker = EdgeTTSWorker(voice or "zh-CN-XiaoxiaoNeural", text, file_path)
            else:
                self.worker = OpenAITTSWorker(api_key, base_url, model_name, voice, text, file_path)
            
            self.worker.finished.connect(lambda path: self.play_file(path))
            self.worker.error.connect(lambda err: self.on_worker_error(msg_id, err))
            self.worker.start()
            
    def play_file(self, path):
        if not self.current_msg_id:
            return
            
        url = QUrl.fromLocalFile(path)
        content = QMediaContent(url)
        self.player.setMedia(content)
        self.player.play()
        self.playback_started.emit(self.current_msg_id)

    def stop(self):
        self.player.stop()
        if self.current_msg_id:
            self.playback_stopped.emit(self.current_msg_id)
            self.current_msg_id = None

    def on_state_changed(self, state):
        if state == QMediaPlayer.StoppedState and self.current_msg_id:
            msg_id = self.current_msg_id
            self.current_msg_id = None
            self.playback_stopped.emit(msg_id)
            
    def on_worker_error(self, msg_id, err):
        self.playback_error.emit(msg_id, err)
        if self.current_msg_id == msg_id:
            self.current_msg_id = None
            self.playback_stopped.emit(msg_id)
