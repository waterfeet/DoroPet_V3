import os
import sys
import time
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

from src.services.extended_music_service import SongInfo, ExtendedMusicService
from src.core.logger import logger

VLC_AVAILABLE = False
vlc = None

def _get_vlc_paths():
    """获取 VLC 可能的路径列表"""
    paths = []
    
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths.append(os.path.join(src_dir, 'vlc'))
    
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        paths.append(os.path.join(application_path, 'vlc'))
        paths.append(os.path.join(application_path, 'src', 'vlc'))
        
        if hasattr(sys, '_MEIPASS'):
            paths.append(os.path.join(sys._MEIPASS, 'vlc'))
            paths.append(os.path.join(sys._MEIPASS, 'src', 'vlc'))
    
    project_root = os.path.dirname(src_dir)
    paths.append(os.path.join(project_root, 'vlc'))
    
    if sys.platform == 'win32':
        paths.extend([
            r'C:\Program Files\VideoLAN\VLC',
            r'C:\Program Files (x86)\VideoLAN\VLC',
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'VideoLAN', 'VLC'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'VideoLAN', 'VLC'),
        ])
    
    return paths

def _setup_vlc_path():
    """设置 VLC DLL 路径（必须在 import vlc 之前调用）"""
    if sys.platform != 'win32':
        return None
    
    vlc_paths = _get_vlc_paths()
    
    for vlc_path in vlc_paths:
        if os.path.exists(vlc_path):
            libvlc = os.path.join(vlc_path, 'libvlc.dll')
            if os.path.exists(libvlc):
                os.environ['PYTHON_VLC_MODULE_PATH'] = vlc_path
                if vlc_path not in os.environ.get('PATH', ''):
                    try:
                        os.add_dll_directory(vlc_path)
                    except (OSError, AttributeError):
                        pass
                logger.info(f"[VLC] Found VLC at: {vlc_path}")
                return vlc_path
    
    logger.warning("[VLC] VLC not found in any path")
    return None

_vlc_path = _setup_vlc_path()

try:
    import vlc as vlc_module
    vlc = vlc_module
    
    test_instance = vlc.Instance('--stereo-mode=1')
    if test_instance:
        test_instance.release()
        VLC_AVAILABLE = True
        logger.info("[VLC] VLC initialized successfully")
    
except Exception as e:
    logger.warning(f"[VLC] VLC not available: {e}")
    VLC_AVAILABLE = False
    vlc = None


class VLCMusicPlayer:
    """基于 VLC 的音乐播放器"""
    
    def __init__(self):
        if not VLC_AVAILABLE:
            raise RuntimeError("VLC not available")
        
        self.instance = vlc.Instance('--stereo-mode=1')
        self.player = self.instance.media_player_new()

        if hasattr(self.player, 'audio_set_channel'):
            try:
                self.player.audio_set_channel(1)
            except Exception:
                pass
        
        self._volume = 100
        self._is_playing = False
        
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._check_position)
        
        self._duration = 0
        self._last_position = 0
        self._playback_end_detected = False
        self._on_playback_finished = None
    
    def set_volume(self, volume: int):
        """设置音量"""
        self._volume = volume
        self.player.audio_set_volume(volume)
    
    def get_volume(self) -> int:
        """获取音量"""
        vol = self.player.audio_get_volume()
        if vol < 0:
            return self._volume
        return vol
    
    def play(self, url: str):
        """播放 URL 或本地文件"""
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        
        self._playback_end_detected = False
        self._is_playing = True
        
        time.sleep(0.1)
        
        self.player.audio_set_volume(self._volume)

        if hasattr(self.player, 'audio_set_channel'):
            try:
                self.player.audio_set_channel(1)
            except Exception:
                pass

        self._duration = self.player.get_length()
        
        self._update_timer.start(100)
    
    def pause(self):
        """暂停"""
        self.player.pause()
        self._is_playing = False
    
    def resume(self):
        """继续播放"""
        self.player.play()
        self._is_playing = True
    
    def stop(self):
        """停止"""
        self._update_timer.stop()
        self.player.stop()
        self._is_playing = False
    
    def toggle_play(self):
        """切换播放/暂停"""
        if self._is_playing:
            self.player.pause()
            self._is_playing = False
        else:
            self.player.play()
            self._is_playing = True
    
    def set_position(self, position: int):
        """设置播放位置（毫秒）"""
        self.player.set_time(position)
    
    def get_position(self) -> int:
        """获取播放位置（毫秒）"""
        return self.player.get_time()
    
    def get_duration(self) -> int:
        """获取时长（毫秒）"""
        return self.player.get_length()
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing
    
    def get_state(self):
        """获取播放状态"""
        return self.player.get_state()
    
    def _check_position(self):
        """检查播放位置，用于检测播放结束"""
        if not self._playback_end_detected:
            current_pos = self.player.get_time()
            duration = self.player.get_length()
            
            if duration > 0 and current_pos > 0:
                if duration - current_pos < 500:
                    self._playback_end_detected = True
                    self._is_playing = False
                    self._update_timer.stop()
                    if self._on_playback_finished:
                        self._on_playback_finished()
    
    def set_on_finished(self, callback):
        """设置播放结束回调"""
        self._on_playback_finished = callback
    
    def close(self):
        """关闭播放器"""
        self._update_timer.stop()
        self.player.stop()
        self._is_playing = False
        self.player.release()
        self.instance.release()


class QtMusicPlayer:
    """基于 Qt Multimedia 的音乐播放器（后备方案）"""
    
    def __init__(self):
        self.player = QMediaPlayer()
        self.player.setVolume(100)
        
        self._on_playback_finished = None
        self._duration = 0
        
        self.player.stateChanged.connect(self._on_state_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
    
    def _on_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            if self._on_playback_finished:
                self._on_playback_finished()
    
    def _on_duration_changed(self, duration):
        self._duration = duration
    
    def set_volume(self, volume: int):
        self.player.setVolume(volume)
    
    def get_volume(self) -> int:
        return self.player.volume()
    
    def play(self, url: str):
        if url.startswith('http'):
            media_content = QMediaContent(QUrl(url))
        else:
            media_content = QMediaContent(QUrl.fromLocalFile(url))
        
        self.player.setMedia(media_content)
        self.player.play()
    
    def pause(self):
        self.player.pause()
    
    def resume(self):
        self.player.play()
    
    def stop(self):
        self.player.stop()
    
    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def set_position(self, position: int):
        self.player.setPosition(position)
    
    def get_position(self) -> int:
        return self.player.position()
    
    def get_duration(self) -> int:
        return self.player.duration()
    
    def is_playing(self) -> bool:
        return self.player.state() == QMediaPlayer.PlayingState
    
    def get_state(self):
        return self.player.state()
    
    def set_on_finished(self, callback):
        self._on_playback_finished = callback
    
    def close(self):
        self.player.stop()


class GlobalMusicPlayer(QObject):
    """全局音乐播放器，用于在多个界面间共享播放状态"""
    
    playback_state_changed = pyqtSignal(bool)
    playback_finished = pyqtSignal()
    current_song_changed = pyqtSignal(object)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    play_url_refreshed = pyqtSignal(object, str)
    volume_changed = pyqtSignal(int)
    
    _instance = None
    
    @classmethod
    def get_instance(cls, parent=None):
        if cls._instance is None:
            cls._instance = GlobalMusicPlayer(parent)
        return cls._instance
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if VLC_AVAILABLE:
            try:
                self.player = VLCMusicPlayer()
                self._backend = "VLC"
                logger.info("[GlobalPlayer] Using VLC backend")
            except Exception as e:
                logger.warning(f"[GlobalPlayer] VLC init failed, falling back to Qt: {e}")
                self.player = QtMusicPlayer()
                self._backend = "Qt"
        else:
            self.player = QtMusicPlayer()
            self._backend = "Qt"
            logger.info("[GlobalPlayer] Using Qt Multimedia backend (VLC not available)")
        
        self.player.set_volume(100)
        self.player.set_on_finished(self._on_playback_finished)
        
        self._position_timer = QTimer(self)
        self._position_timer.timeout.connect(self._emit_position)
        
        self._current_song: SongInfo = None
        self._playlist = []
        self._current_index = -1
        self._retry_count = 0
        self._max_retry = 3
        self._music_service: ExtendedMusicService = None
        self._is_starting_new_song = False
        self._state_reset_timer = QTimer(self)
        self._state_reset_timer.setSingleShot(True)
        self._state_reset_timer.timeout.connect(self._reset_starting_flag)
        
        self._position_timer.start(200)
    
    def get_backend(self) -> str:
        """获取当前使用的播放后端"""
        return self._backend
    
    def _reset_starting_flag(self):
        self._is_starting_new_song = False
        logger.info(f"[GlobalPlayer] _is_starting_new_song reset to False by timer")
    
    def _emit_position(self):
        """发射位置变化信号"""
        if self.player.is_playing():
            position = self.player.get_position()
            self.position_changed.emit(position)
            
            duration = self.player.get_duration()
            if duration > 0:
                self.duration_changed.emit(duration)
    
    def _on_playback_finished(self):
        """播放结束回调"""
        logger.info(f"[GlobalPlayer] Playback finished")
        self._position_timer.stop()
        self.playback_finished.emit()
        self._position_timer.start(200)
    
    def set_music_service(self, service: ExtendedMusicService):
        """设置音乐服务实例"""
        self._music_service = service
    
    def play(self, song: SongInfo, playlist: list = None, index: int = 0):
        """播放歌曲"""
        logger.info(f"[GlobalPlayer] play() called for: {song.name}")
        if playlist:
            self._playlist = playlist
            self._current_index = index
        
        self._current_song = song
        self._state_reset_timer.stop()
        self._is_starting_new_song = True
        logger.info(f"[GlobalPlayer] _is_starting_new_song set to True")
        
        if song.play_url:
            self._play_url(song.play_url)
        else:
            logger.warning(f"Song {song.name} has no play_url")
        
        self.current_song_changed.emit(song)
    
    def _play_url(self, url: str):
        """播放 URL"""
        self.player.play(url)
        logger.info(f"[GlobalPlayer] Playing: {url[:50]}...")
        
        self._retry_count = 0
        self._state_reset_timer.start(500)
        self.playback_state_changed.emit(True)
    
    def pause(self):
        """暂停"""
        self.player.pause()
    
    def resume(self):
        """继续播放"""
        self.player.resume()
    
    def stop(self):
        """停止"""
        self.player.stop()
    
    def toggle_play(self):
        """切换播放/暂停"""
        self.player.toggle_play()
        self.playback_state_changed.emit(self.player.is_playing())
    
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
        self.player.set_volume(volume)
        self.volume_changed.emit(volume)
    
    def get_volume(self) -> int:
        """获取音量"""
        return self.player.get_volume()
    
    def set_position(self, position: int):
        """设置播放位置"""
        self.player.set_position(position)
    
    def get_position(self) -> int:
        """获取播放位置"""
        return self.player.get_position()
    
    def get_duration(self) -> int:
        """获取歌曲时长"""
        return self.player.get_duration()
    
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self.player.is_playing()
    
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
    
    def _retry_current(self):
        """重试当前歌曲"""
        if self._current_song and self._current_song.play_url:
            self._play_url(self._current_song.play_url)
    
    def _refresh_play_url(self):
        """从平台重新获取播放链接"""
        if not self._music_service or not self._current_song:
            logger.warning("[GlobalPlayer] 无法重新获取播放链接：音乐服务未设置或当前歌曲为空")
            self._retry_current()
            return
        
        self._music_service.play_url_obtained.connect(self._on_url_refreshed)
        self._music_service.play_url_failed.connect(self._on_url_refresh_failed)
        self._music_service.get_play_url(self._current_song, self._current_song.quality)
    
    def _on_url_refreshed(self, song_id: str, url: str):
        """播放链接刷新成功"""
        try:
            self._music_service.play_url_obtained.disconnect(self._on_url_refreshed)
            self._music_service.play_url_failed.disconnect(self._on_url_refresh_failed)
        except:
            pass
        
        if self._current_song and self._current_song.song_id == song_id:
            logger.info(f"[GlobalPlayer] 成功重新获取播放链接")
            self._current_song.play_url = url
            self._play_url(url)
            self.play_url_refreshed.emit(self._current_song, url)
    
    def _on_url_refresh_failed(self, song_id: str):
        """播放链接刷新失败"""
        try:
            self._music_service.play_url_obtained.disconnect(self._on_url_refreshed)
            self._music_service.play_url_failed.disconnect(self._on_url_refresh_failed)
        except:
            pass
        
        logger.warning(f"[GlobalPlayer] 重新获取播放链接失败，尝试使用原链接重试")
        self._retry_current()
    
    def close(self):
        """关闭播放器"""
        self._position_timer.stop()
        self.player.close()
