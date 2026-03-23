from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from src.services.extended_music_service import SongInfo
from src.core.logger import logger


class GlobalMusicPlayer(QObject):
    """全局音乐播放器，用于在多个界面间共享播放状态"""
    
    playback_state_changed = pyqtSignal(bool)
    current_song_changed = pyqtSignal(object)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    
    _instance = None
    
    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None:
            cls._instance = GlobalMusicPlayer(parent)
        return cls._instance
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.player = QMediaPlayer()
        self.player.setVolume(50)
        
        self._current_song: SongInfo = None
        self._playlist = []
        self._current_index = -1
        self._retry_count = 0
        self._max_retry = 3
        
        self.player.stateChanged.connect(self._on_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.error.connect(self._on_error)
    
    def play(self, song: SongInfo, playlist: list = None, index: int = 0):
        """播放歌曲"""
        if playlist:
            self._playlist = playlist
            self._current_index = index
        
        self._current_song = song
        
        if song.play_url:
            self._play_url(song.play_url)
        else:
            logger.warning(f"Song {song.name} has no play_url")
        
        self.current_song_changed.emit(song)
    
    def _play_url(self, url: str):
        """播放 URL"""
        if url.startswith('http'):
            media_content = QMediaContent(QUrl(url))
        else:
            media_content = QMediaContent(QUrl.fromLocalFile(url))
        
        self.player.setMedia(media_content)
        self.player.play()
        logger.info(f"[GlobalPlayer] Playing: {url[:50]}...")
    
    def pause(self):
        """暂停"""
        self.player.pause()
    
    def resume(self):
        """继续播放"""
        self.player.play()
    
    def stop(self):
        """停止"""
        self.player.stop()
    
    def toggle_play(self):
        """切换播放/暂停"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def play_next(self):
        """播放下一首"""
        if not self._playlist:
            return
        
        next_index = (self._current_index + 1) % len(self._playlist)
        self.play(self._playlist[next_index], self._playlist, next_index)
    
    def play_previous(self):
        """播放上一首"""
        if not self._playlist:
            return
        
        prev_index = (self._current_index - 1) % len(self._playlist)
        self.play(self._playlist[prev_index], self._playlist, prev_index)
    
    def set_volume(self, volume: int):
        """设置音量"""
        self.player.setVolume(volume)
    
    def get_volume(self) -> int:
        """获取音量"""
        return self.player.volume()
    
    def set_position(self, position: int):
        """设置播放位置"""
        self.player.setPosition(position)
    
    def get_position(self) -> int:
        """获取播放位置"""
        return self.player.position()
    
    def get_duration(self) -> int:
        """获取歌曲时长"""
        return self.player.duration()
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self.player.state() == QMediaPlayer.PlayingState
    
    def get_current_song(self) -> SongInfo:
        """获取当前歌曲"""
        return self._current_song
    
    def get_playlist(self) -> list:
        """获取播放列表"""
        return self._playlist
    
    def get_current_index(self) -> int:
        """获取当前播放索引"""
        return self._current_index
    
    def set_playlist(self, playlist: list, index: int = 0):
        """设置播放列表"""
        self._playlist = playlist
        self._current_index = index
        if playlist and 0 <= index < len(playlist):
            self.play(playlist[index], playlist, index)
    
    def _on_state_changed(self, state):
        """播放状态变化"""
        is_playing = state == QMediaPlayer.PlayingState
        if is_playing:
            self._retry_count = 0
        self.playback_state_changed.emit(is_playing)
    
    def _on_position_changed(self, position):
        """播放位置变化"""
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration):
        """时长变化"""
        self.duration_changed.emit(duration)
    
    def _on_error(self):
        """播放错误"""
        error_string = self.player.errorString()
        logger.error(f"[GlobalPlayer] Error: {error_string}")
        
        if self._retry_count < self._max_retry and self._current_song:
            self._retry_count += 1
            logger.info(f"[GlobalPlayer] 尝试重新加载 ({self._retry_count}/{self._max_retry})")
            
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, self._retry_current)
        else:
            logger.warning(f"[GlobalPlayer] 重试失败，停止播放")
            self._retry_count = 0
    
    def _retry_current(self):
        """重试当前歌曲"""
        if self._current_song and self._current_song.play_url:
            self._play_url(self._current_song.play_url)
    
    def close(self):
        """关闭播放器"""
        self.player.stop()
