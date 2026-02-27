import os
import hashlib
import requests
import json
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

class TTSWorker(QThread):
    finished = pyqtSignal(str) # path
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
            # Check cache first (double check for safety)
            if os.path.exists(self.cache_path):
                self.finished.emit(self.cache_path)
                return

            # Ensure base_url doesn't end with slash if we append /audio/speech, 
            # or handle it gracefully. 
            # SiliconFlow: https://api.siliconflow.cn/v1/audio/speech
            # If user provides https://api.siliconflow.cn/v1, we append /audio/speech
            
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
            
            # print(f"DEBUG: TTS Request to {url} with model={self.model}, voice={self.voice}")
            
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
    # Signals
    playback_started = pyqtSignal(int) # msg_id
    playback_stopped = pyqtSignal(int) # msg_id
    playback_error = pyqtSignal(int, str) # msg_id, error

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.player = QMediaPlayer()
        self.player.stateChanged.connect(self.on_state_changed)
        self.current_msg_id = None
        self.cache_dir = os.path.join(os.getcwd(), "cache", "tts")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.worker = None # Keep reference
        
    def speak(self, msg_id, text):
        # Stop current if playing
        if self.player.state() == QMediaPlayer.PlayingState:
            previous_msg_id = self.current_msg_id
            self.player.stop()
            # If same message was clicked, we just stop (toggle).
            # Note: player.stop() triggers on_state_changed which sets self.current_msg_id to None
            # So we compare with the captured previous_msg_id
            if previous_msg_id == msg_id:
                # The on_state_changed will handle the reset/emit
                # We just ensure we don't start it again
                return

        self.current_msg_id = msg_id
        
        # Get active TTS config
        config = self.db.get_active_tts_model()
        if not config:
            self.playback_error.emit(msg_id, "请先在配置页设置并激活 TTS 模型")
            self.current_msg_id = None
            return
            
        # config: id, name, provider, api_key, base_url, model_name, voice
        _, _, _, api_key, base_url, model_name, voice = config
        
        # Determine cache path
        # Hash based on content + model + voice to allow re-gen if config changes
        content_hash = hashlib.md5(f"{text}{model_name}{voice}".encode()).hexdigest()
        file_path = os.path.join(self.cache_dir, f"{content_hash}.mp3")
        
        if os.path.exists(file_path):
            self.play_file(file_path)
        else:
            # Generate
            self.worker = TTSWorker(api_key, base_url, model_name, voice, text, file_path)
            self.worker.finished.connect(lambda path: self.play_file(path))
            self.worker.error.connect(lambda err: self.on_worker_error(msg_id, err))
            self.worker.start()
            
    def play_file(self, path):
        if not self.current_msg_id:
            return # Maybe stopped before download finished
            
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
            # If it stopped naturally (EndOfMedia) or forced stop
            # We can check mediaStatus if needed, but simple stop signal is enough
            msg_id = self.current_msg_id
            self.current_msg_id = None
            self.playback_stopped.emit(msg_id)
            
    def on_worker_error(self, msg_id, err):
        self.playback_error.emit(msg_id, err)
        if self.current_msg_id == msg_id:
            self.current_msg_id = None
            self.playback_stopped.emit(msg_id) # Ensure UI resets
