from dataclasses import dataclass, field
from typing import Optional, List
import os
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QUrl
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


@dataclass
class SongInfo:
    song_id: str
    name: str
    singer: str
    album: str = ""
    duration: int = 0
    source: str = ""
    img_url: str = ""
    play_url: str = ""
    lyric: str = ""
    raw_data: dict = field(default_factory=dict)
    
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
    def from_musicdl_result(cls, result, source: str = "") -> 'SongInfo':
        if hasattr(result, '__dict__'):
            musicdl_song_info = result
            song_id = getattr(musicdl_song_info, 'identifier', '')
            name = getattr(musicdl_song_info, 'song_name', '')
            singer = getattr(musicdl_song_info, 'singers', '')
            album = getattr(musicdl_song_info, 'album', '')
            duration = getattr(musicdl_song_info, 'duration_s', 0)
            img_url = getattr(musicdl_song_info, 'cover_url', '')
            play_url = getattr(musicdl_song_info, 'download_url', '')
            lyric = getattr(musicdl_song_info, 'lyric', '')
            raw_data = musicdl_song_info.__dict__.copy() if hasattr(musicdl_song_info, '__dict__') else {}
        else:
            song_id = str(result.get('id', ''))
            name = result.get('name', '')
            singer = result.get('singer', '')
            album = result.get('album', '')
            duration = result.get('duration', 0)
            img_url = result.get('img', '')
            play_url = result.get('url', '')
            lyric = result.get('lyric', '')
            raw_data = result if isinstance(result, dict) else {}
        
        return cls(
            song_id=song_id,
            name=name,
            singer=singer,
            album=album,
            duration=duration,
            source=source,
            img_url=img_url,
            play_url=play_url,
            lyric=lyric,
            raw_data=raw_data
        )


class SearchWorker(QThread):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    
    def __init__(self, keyword: str, sources: list = None, parent=None):
        super().__init__(parent)
        self.keyword = keyword
        self.sources = sources or ['NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient']
    
    def run(self):
        try:
            from musicdl import musicdl
            
            musicdl_output_dir = os.path.join(get_user_data_dir(), "musicdl_outputs")
            os.makedirs(musicdl_output_dir, exist_ok=True)
            
            init_music_clients_cfg = {}
            for source in self.sources:
                init_music_clients_cfg[source] = {
                    'search_size_per_source': 20,
                    'work_dir': musicdl_output_dir
                }
            
            music_client = musicdl.MusicClient(
                music_sources=self.sources,
                init_music_clients_cfg=init_music_clients_cfg
            )
            
            results = music_client.search(keyword=self.keyword)
            
            songs = []
            for source, song_list in results.items():
                for song in song_list:
                    try:
                        logger.debug(f"Raw song data from {source}: {song.keys() if isinstance(song, dict) else type(song)}")
                        if isinstance(song, dict):
                            logger.debug(f"Song url field: {song.get('url', 'NOT FOUND')}")
                        song_info = SongInfo.from_musicdl_result(song, source)
                        songs.append(song_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse song: {e}")
            
            self.search_completed.emit(songs)
            
        except ImportError as e:
            self.search_failed.emit(f"musicdl 库未安装: {e}")
        except Exception as e:
            self.search_failed.emit(f"搜索失败: {str(e)}")


class PlayUrlWorker(QThread):
    url_obtained = pyqtSignal(str, str)
    url_failed = pyqtSignal(str)
    
    SOURCE_CLIENT_MAP = {
        'NeteaseMusicClient': 'NeteaseMusicClient',
        'QQMusicClient': 'QQMusicClient',
        'KugouMusicClient': 'KugouMusicClient',
        'KuwoMusicClient': 'KuwoMusicClient',
        'MiguMusicClient': 'MiguMusicClient',
    }
    
    def __init__(self, song_info: SongInfo, quality: str = 'standard', parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self.quality = quality
    
    def run(self):
        try:
            if self.song_info.play_url:
                logger.debug(f"Using existing play_url: {self.song_info.play_url[:50]}...")
                self.url_obtained.emit(self.song_info.song_id, self.song_info.play_url)
                return
            
            raw_url = self.song_info.raw_data.get('url', '') if self.song_info.raw_data else ''
            if raw_url and raw_url.startswith('http'):
                logger.debug(f"Using raw_data url: {raw_url[:50]}...")
                self.url_obtained.emit(self.song_info.song_id, raw_url)
                return
            
            client_name = self.SOURCE_CLIENT_MAP.get(self.song_info.source)
            if not client_name:
                logger.error(f"Unknown source: {self.song_info.source}")
                self.url_failed.emit(self.song_info.song_id)
                return
            
            musicdl_output_dir = os.path.join(get_user_data_dir(), "musicdl_outputs")
            os.makedirs(musicdl_output_dir, exist_ok=True)
            
            try:
                from musicdl import musicdl
                
                init_cfg = {client_name: {'work_dir': musicdl_output_dir}}
                music_client = musicdl.MusicClient(
                    music_sources=[client_name],
                    init_music_clients_cfg=init_cfg
                )
                
                raw_data = self.song_info.raw_data if self.song_info.raw_data else {}
                
                song_info_for_download = dict(raw_data)
                song_info_for_download['save_path'] = musicdl_output_dir
                
                logger.debug(f"Downloading song to: {musicdl_output_dir}")
                logger.debug(f"Song info keys: {list(song_info_for_download.keys())}")
                
                download_results = music_client.download(song_infos=[song_info_for_download])
                
                logger.debug(f"Download results: {download_results}")
                
                if download_results:
                    for result in download_results:
                        if isinstance(result, dict):
                            url = result.get('url', '')
                            file_path = result.get('savedpath', '')
                            if file_path and os.path.exists(file_path):
                                logger.debug(f"Found downloaded file: {file_path}")
                                self.url_obtained.emit(self.song_info.song_id, file_path)
                                return
                            if url:
                                logger.debug(f"Found URL from result: {url[:50]}...")
                                self.url_obtained.emit(self.song_info.song_id, url)
                                return
                        elif isinstance(result, str) and result:
                            if os.path.exists(result):
                                logger.debug(f"Found file path: {result}")
                                self.url_obtained.emit(self.song_info.song_id, result)
                                return
                            elif result.startswith('http'):
                                logger.debug(f"Found URL string: {result[:50]}...")
                                self.url_obtained.emit(self.song_info.song_id, result)
                                return
                
                for f in os.listdir(musicdl_output_dir):
                    if f.lower().endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
                        file_path = os.path.join(musicdl_output_dir, f)
                        logger.debug(f"Found audio file in output dir: {file_path}")
                        self.url_obtained.emit(self.song_info.song_id, file_path)
                        return
                
                logger.error("No valid download result found")
                self.url_failed.emit(self.song_info.song_id)
                
            except Exception as e:
                logger.error(f"Download error: {e}")
                self.url_failed.emit(self.song_info.song_id)
                
        except Exception as e:
            logger.error(f"Failed to get play URL: {e}")
            import traceback
            traceback.print_exc()
            self.url_failed.emit(self.song_info.song_id)


class MusicService(QObject):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    play_url_obtained = pyqtSignal(str, str)
    play_url_failed = pyqtSignal(str)
    
    AVAILABLE_SOURCES = {
        'all': ['NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient', 'KugouMusicClient', 'MiguMusicClient'],
        'netease': ['NeteaseMusicClient'],
        'qq': ['QQMusicClient'],
        'kuwo': ['KuwoMusicClient'],
        'kugou': ['KugouMusicClient'],
        'migu': ['MiguMusicClient'],
    }
    
    SOURCE_NAMES = {
        'all': '全部平台',
        'netease': '网易云音乐',
        'qq': 'QQ音乐',
        'kuwo': '酷我音乐',
        'kugou': '酷狗音乐',
        'migu': '咪咕音乐',
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_songs: List[SongInfo] = []
        self._url_cache: dict = {}
        self._search_worker = None
        self._url_worker = None
    
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
        
        if song_info.play_url:
            self._url_cache[song_info.song_id] = song_info.play_url
            self.play_url_obtained.emit(song_info.song_id, song_info.play_url)
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
    
    def stop_workers(self):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
        if self._url_worker and self._url_worker.isRunning():
            self._url_worker.terminate()
    
    def get_local_songs(self, directory: str) -> List[SongInfo]:
        songs = []
        supported_formats = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
        
        if os.path.exists(directory):
            try:
                files = os.listdir(directory)
                for f in files:
                    if f.lower().endswith(supported_formats):
                        file_path = os.path.join(directory, f)
                        songs.append(SongInfo(
                            song_id=file_path,
                            name=os.path.splitext(f)[0],
                            singer="本地音乐",
                            album="",
                            duration=0,
                            source="local",
                            img_url="",
                            play_url=file_path,
                            lyric=""
                        ))
            except Exception as e:
                logger.error(f"Failed to load local songs: {e}")
        
        return songs
