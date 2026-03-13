import os
import threading
from typing import List, Dict, Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QThread
from PyQt5.QtMultimedia import QMediaContent

from src.core.logger import logger


def get_user_data_dir():
    """
    Get user data directory for DoroPet.
    On Windows, this is %LOCALAPPDATA%\\DoroPet
    """
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()


class SongInfo:
    def __init__(self, song_id: str, name: str, singer: str, album: str = "", 
                 duration: int = 0, source: str = "", img_url: str = "", 
                 play_url: str = "", lyric: str = ""):
        self.song_id = song_id
        self.name = name
        self.singer = singer
        self.album = album
        self.duration = duration
        self.source = source
        self.img_url = img_url
        self.play_url = play_url
        self.lyric = lyric
    
    def to_dict(self) -> dict:
        return {
            'song_id': self.song_id,
            'name': self.name,
            'singer': self.singer,
            'album': self.album,
            'duration': self.duration,
            'source': self.source,
            'img_url': self.img_url,
            'play_url': self.play_url,
            'lyric': self.lyric
        }
    
    @classmethod
    def from_musicdl_result(cls, result: dict, source: str = "") -> 'SongInfo':
        return cls(
            song_id=str(result.get('id', '')),
            name=result.get('name', '未知'),
            singer=result.get('singer', '未知歌手'),
            album=result.get('album', ''),
            duration=result.get('duration', 0),
            source=source,
            img_url=result.get('img_url', '') or result.get('img', ''),
            play_url=result.get('play_url', '') or result.get('url', ''),
            lyric=result.get('lyric', '')
        )


class SearchWorker(QThread):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    
    def __init__(self, keyword: str, sources: list = None, parent=None):
        super().__init__(parent)
        self.keyword = keyword
        self.sources = sources or ['NeteaseMusicClient', 'QQMusicClient', 'KugouMusicClient']
    
    def run(self):
        try:
            from musicdl import musicdl
            
            musicdl_output_dir = os.path.join(get_user_data_dir(), "musicdl_outputs")
            os.makedirs(musicdl_output_dir, exist_ok=True)
            
            init_cfg = {}
            for source in self.sources:
                init_cfg[source] = {
                    'search_size_per_source': 5,
                    'work_dir': musicdl_output_dir
                }
            
            music_client = musicdl.MusicClient(
                music_sources=self.sources,
                init_music_clients_cfg=init_cfg
            )
            
            results = music_client.search(keyword=self.keyword)
            
            song_list = []
            for source, songs in results.items():
                for song in songs:
                    try:
                        song_info = SongInfo.from_musicdl_result(song, source)
                        song_list.append(song_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse song info: {e}")
                        continue
            
            self.search_completed.emit(song_list)
            
        except ImportError as e:
            self.search_failed.emit(f"musicdl 库未安装: {e}")
        except Exception as e:
            self.search_failed.emit(f"搜索失败: {str(e)}")


class PlayUrlWorker(QThread):
    url_obtained = pyqtSignal(str, str)
    url_failed = pyqtSignal(str)
    
    def __init__(self, song_info: SongInfo, quality: str = 'standard', parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self.quality = quality
    
    def run(self):
        try:
            from musicdl import musicdl
            
            source_map = {
                'NeteaseMusicClient': 'netease',
                'QQMusicClient': 'qq',
                'KugouMusicClient': 'kugou',
                'KuwoMusicClient': 'kuwo',
                'MiguMusicClient': 'migu',
            }
            
            musicdl_output_dir = os.path.join(get_user_data_dir(), "musicdl_outputs")
            os.makedirs(musicdl_output_dir, exist_ok=True)
            
            init_cfg = {self.song_info.source: {'work_dir': musicdl_output_dir}}
            
            music_client = musicdl.MusicClient(
                music_sources=[self.song_info.source],
                init_music_clients_cfg=init_cfg
            )
            
            song_dict = {
                'id': self.song_info.song_id,
                'name': self.song_info.name,
                'singer': self.song_info.singer,
                'album': self.song_info.album,
                'source': source_map.get(self.song_info.source, self.song_info.source)
            }
            
            download_info = music_client.download(song_infos=[song_dict])
            
            if download_info:
                for info in download_info:
                    if 'url' in info and info['url']:
                        self.url_obtained.emit(self.song_info.song_id, info['url'])
                        return
            
            if self.song_info.play_url:
                self.url_obtained.emit(self.song_info.song_id, self.song_info.play_url)
            else:
                self.url_failed.emit(self.song_info.song_id)
                
        except Exception as e:
            logger.error(f"Failed to get play URL: {e}")
            if self.song_info.play_url:
                self.url_obtained.emit(self.song_info.song_id, self.song_info.play_url)
            else:
                self.url_failed.emit(self.song_info.song_id)


class MusicService(QObject):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    play_url_obtained = pyqtSignal(str, str)
    play_url_failed = pyqtSignal(str)
    
    DEFAULT_SOURCES = ['NeteaseMusicClient', 'QQMusicClient', 'KugouMusicClient']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._search_worker = None
        self._url_worker = None
        self._current_songs: List[SongInfo] = []
        self._url_cache: Dict[str, str] = {}
    
    def search(self, keyword: str, sources: list = None):
        if not keyword.strip():
            self.search_failed.emit("搜索关键词不能为空")
            return
        
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
        
        self._search_worker = SearchWorker(keyword, sources, self)
        self._search_worker.search_completed.connect(self._on_search_completed)
        self._search_worker.search_failed.connect(self.search_failed)
        self._search_worker.start()
    
    def _on_search_completed(self, songs: list):
        self._current_songs = songs
        self.search_completed.emit(songs)
    
    def get_play_url(self, song_info: SongInfo, quality: str = 'standard'):
        if song_info.song_id in self._url_cache:
            self.play_url_obtained.emit(song_info.song_id, self._url_cache[song_info.song_id])
            return
        
        if self._url_worker and self._url_worker.isRunning():
            self._url_worker.terminate()
        
        self._url_worker = PlayUrlWorker(song_info, quality, self)
        self._url_worker.url_obtained.connect(self._on_url_obtained)
        self._url_worker.url_failed.connect(self.play_url_failed)
        self._url_worker.start()
    
    def _on_url_obtained(self, song_id: str, url: str):
        self._url_cache[song_id] = url
        self.play_url_obtained.emit(song_id, url)
    
    def get_current_songs(self) -> List[SongInfo]:
        return self._current_songs
    
    def get_song_by_id(self, song_id: str) -> Optional[SongInfo]:
        for song in self._current_songs:
            if song.song_id == song_id:
                return song
        return None
    
    def create_media_content(self, url: str) -> QMediaContent:
        if url.startswith('http'):
            return QMediaContent(QUrl(url))
        else:
            return QMediaContent(QUrl.fromLocalFile(url))
    
    def clear_cache(self):
        self._url_cache.clear()
        self._current_songs.clear()
