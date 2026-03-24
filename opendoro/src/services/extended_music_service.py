from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
import os
import json
import threading
from PyQt5.QtCore import QObject, QThread, pyqtSignal, QUrl
from PyQt5.QtMultimedia import QMediaContent

from src.core.logger import logger


def get_user_data_dir():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()


def get_music_data_dir():
    data_dir = os.path.join(get_user_data_dir(), "music")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_download_dir():
    download_dir = os.path.join(get_music_data_dir(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    return download_dir


def get_playlist_file():
    return os.path.join(get_music_data_dir(), "playlists.json")


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
    quality: str = "standard"
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
            'lyric': self.lyric,
            'quality': self.quality
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SongInfo':
        return cls(
            song_id=data.get('song_id', ''),
            name=data.get('name', ''),
            singer=data.get('singer', ''),
            album=data.get('album', ''),
            duration=data.get('duration', 0),
            source=data.get('source', ''),
            img_url=data.get('img_url', ''),
            play_url=data.get('play_url', ''),
            lyric=data.get('lyric', ''),
            quality=data.get('quality', 'standard'),
            raw_data=data.get('raw_data', {})
        )
    
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


@dataclass
class Playlist:
    id: str
    name: str
    songs: List[SongInfo] = field(default_factory=list)
    cover_url: str = ""
    description: str = ""
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'songs': [s.to_dict() for s in self.songs],
            'cover_url': self.cover_url,
            'description': self.description,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Playlist':
        songs = [SongInfo.from_dict(s) for s in data.get('songs', [])]
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            songs=songs,
            cover_url=data.get('cover_url', ''),
            description=data.get('description', ''),
            created_at=data.get('created_at', '')
        )


MUSIC_SOURCES = {
    'netease': {
        'client': 'NeteaseMusicClient',
        'name': '网易云音乐',
        'icon': '🎵'
    },
    'qq': {
        'client': 'QQMusicClient',
        'name': 'QQ音乐',
        'icon': '🎶'
    },
    'kugou': {
        'client': 'KugouMusicClient',
        'name': '酷狗音乐',
        'icon': '🎧'
    },
    'kuwo': {
        'client': 'KuwoMusicClient',
        'name': '酷我音乐',
        'icon': '📻'
    },
    'migu': {
        'client': 'MiguMusicClient',
        'name': '咪咕音乐',
        'icon': '🎤'
    },
    'bilibili': {
        'client': 'BilibiliMusicClient',
        'name': 'B站音乐',
        'icon': '📺'
    },
    'spotify': {
        'client': 'SpotifyMusicClient',
        'name': 'Spotify',
        'icon': '🌐'
    },
    'youtube': {
        'client': 'YouTubeMusicClient',
        'name': 'YouTube Music',
        'icon': '▶️'
    },
}


QUALITY_OPTIONS = {
    'standard': {'name': '标准音质', 'value': 'standard'},
    'high': {'name': '高品质', 'value': 'high'},
    'lossless': {'name': '无损音质', 'value': 'lossless'},
}


class SearchWorker(QThread):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    search_progress = pyqtSignal(str)
    
    def __init__(self, keyword: str, sources: list = None, page: int = 0, parent=None):
        super().__init__(parent)
        self.keyword = keyword
        self.sources = sources or ['NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient']
        self.page = page
    
    def run(self):
        try:
            from musicdl import musicdl
            
            musicdl_output_dir = get_download_dir()
            
            init_music_clients_cfg = {}
            for source in self.sources:
                init_music_clients_cfg[source] = {
                    'search_size_per_source': 20,
                    'search_size_per_page': 20,
                    'strict_limit_search_size_per_page': False,
                    'work_dir': musicdl_output_dir
                }
            
            self.search_progress.emit("正在连接音乐平台...")
            
            music_client = musicdl.MusicClient(
                music_sources=self.sources,
                init_music_clients_cfg=init_music_clients_cfg
            )
            
            self.search_progress.emit("正在搜索...")
            
            results = music_client.search(keyword=self.keyword)
            
            self.search_progress.emit("正在处理结果...")
            
            songs = []
            total_sources = len(results) if results else 0
            processed = 0
            
            for source, song_list in results.items():
                for song in song_list:
                    try:
                        song_info = SongInfo.from_musicdl_result(song, source)
                        songs.append(song_info)
                    except Exception as e:
                        logger.warning(f"Failed to parse song: {e}")
                
                processed += 1
                self.search_progress.emit(f"已处理 {source}")
            
            self.search_completed.emit(songs)
            
        except ImportError as e:
            self.search_failed.emit(f"musicdl 库未安装: {e}")
        except Exception as e:
            logger.error(f"Search error: {e}")
            self.search_failed.emit(f"搜索失败: {str(e)}")


class DownloadWorker(QThread):
    download_completed = pyqtSignal(str, str)
    download_failed = pyqtSignal(str, str)
    download_progress = pyqtSignal(str, int)
    
    def __init__(self, song_info: SongInfo, quality: str = 'standard', parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self.quality = quality
    
    def run(self):
        try:
            from musicdl import musicdl
            
            download_dir = get_download_dir()
            
            self.download_progress.emit(self.song_info.song_id, 10)
            
            client_name = self.song_info.source
            if client_name not in [s['client'] for s in MUSIC_SOURCES.values()]:
                client_name = 'NeteaseMusicClient'
            
            init_cfg = {client_name: {'work_dir': download_dir}}
            music_client = musicdl.MusicClient(
                music_sources=[client_name],
                init_music_clients_cfg=init_cfg
            )
            
            self.download_progress.emit(self.song_info.song_id, 30)
            
            raw_data = self.song_info.raw_data if self.song_info.raw_data else {}
            song_info_for_download = dict(raw_data)
            song_info_for_download['save_path'] = download_dir
            
            self.download_progress.emit(self.song_info.song_id, 50)
            
            download_results = music_client.download(song_infos=[song_info_for_download])
            
            self.download_progress.emit(self.song_info.song_id, 80)
            
            if download_results:
                for result in download_results:
                    if isinstance(result, dict):
                        file_path = result.get('savedpath', '')
                        if file_path and os.path.exists(file_path):
                            self.download_completed.emit(self.song_info.song_id, file_path)
                            return
                    elif isinstance(result, str) and result:
                        if os.path.exists(result):
                            self.download_completed.emit(self.song_info.song_id, result)
                            return
            
            for f in os.listdir(download_dir):
                if f.lower().endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
                    file_path = os.path.join(download_dir, f)
                    self.download_completed.emit(self.song_info.song_id, file_path)
                    return
            
            self.download_failed.emit(self.song_info.song_id, "下载失败：未找到下载文件")
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            self.download_failed.emit(self.song_info.song_id, str(e))


class LyricWorker(QThread):
    lyric_completed = pyqtSignal(str, str)
    lyric_failed = pyqtSignal(str)
    
    def __init__(self, song_info: SongInfo, parent=None):
        super().__init__(parent)
        self.song_info = song_info
    
    def run(self):
        try:
            if self.song_info.lyric:
                self.lyric_completed.emit(self.song_info.song_id, self.song_info.lyric)
                return
            
            if self.song_info.raw_data and self.song_info.raw_data.get('lyric'):
                self.lyric_completed.emit(self.song_info.song_id, self.song_info.raw_data['lyric'])
                return
            
            self.lyric_failed.emit(self.song_info.song_id)
            
        except Exception as e:
            logger.error(f"Lyric fetch error: {e}")
            self.lyric_failed.emit(self.song_info.song_id)


class PlayUrlWorker(QThread):
    url_obtained = pyqtSignal(str, str)
    url_failed = pyqtSignal(str)
    
    def __init__(self, song_info: SongInfo, quality: str = 'standard', parent=None):
        super().__init__(parent)
        self.song_info = song_info
        self.quality = quality
    
    def run(self):
        try:
            if self.song_info.play_url:
                self.url_obtained.emit(self.song_info.song_id, self.song_info.play_url)
                return
            
            raw_url = self.song_info.raw_data.get('url', '') if self.song_info.raw_data else ''
            if raw_url and raw_url.startswith('http'):
                self.url_obtained.emit(self.song_info.song_id, raw_url)
                return
            
            from musicdl import musicdl
            
            download_dir = get_download_dir()
            
            client_name = self.song_info.source
            if client_name not in [s['client'] for s in MUSIC_SOURCES.values()]:
                client_name = 'NeteaseMusicClient'
            
            init_cfg = {client_name: {'work_dir': download_dir}}
            music_client = musicdl.MusicClient(
                music_sources=[client_name],
                init_music_clients_cfg=init_cfg
            )
            
            raw_data = self.song_info.raw_data if self.song_info.raw_data else {}
            song_info_for_download = dict(raw_data)
            song_info_for_download['save_path'] = download_dir
            
            download_results = music_client.download(song_infos=[song_info_for_download])
            
            if download_results:
                for result in download_results:
                    if isinstance(result, dict):
                        url = result.get('url', '')
                        file_path = result.get('savedpath', '')
                        if file_path and os.path.exists(file_path):
                            self.url_obtained.emit(self.song_info.song_id, file_path)
                            return
                        if url:
                            self.url_obtained.emit(self.song_info.song_id, url)
                            return
                    elif isinstance(result, str) and result:
                        if os.path.exists(result):
                            self.url_obtained.emit(self.song_info.song_id, result)
                            return
                        elif result.startswith('http'):
                            self.url_obtained.emit(self.song_info.song_id, result)
                            return
            
            for f in os.listdir(download_dir):
                if f.lower().endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
                    file_path = os.path.join(download_dir, f)
                    self.url_obtained.emit(self.song_info.song_id, file_path)
                    return
            
            self.url_failed.emit(self.song_info.song_id)
            
        except Exception as e:
            logger.error(f"Play URL fetch error: {e}")
            self.url_failed.emit(self.song_info.song_id)


class ExtendedMusicService(QObject):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    search_progress = pyqtSignal(str)
    
    play_url_obtained = pyqtSignal(str, str)
    play_url_failed = pyqtSignal(str)
    
    download_completed = pyqtSignal(str, str)
    download_failed = pyqtSignal(str, str)
    download_progress = pyqtSignal(str, int)
    
    lyric_completed = pyqtSignal(str, str)
    lyric_failed = pyqtSignal(str)
    
    playlists_loaded = pyqtSignal(list)
    playlist_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_songs: List[SongInfo] = []
        self._url_cache: dict = {}
        self._search_worker = None
        self._url_worker = None
        self._download_worker = None
        self._lyric_worker = None
        self._playlists: List[Playlist] = []
        self._load_playlists()
    
    def get_available_sources(self) -> Dict[str, dict]:
        return MUSIC_SOURCES
    
    def get_quality_options(self) -> Dict[str, dict]:
        return QUALITY_OPTIONS
    
    def search(self, keyword: str, sources: list = None, page: int = 0):
        if not keyword.strip():
            self.search_failed.emit("搜索关键词不能为空")
            return
        
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
        
        self._search_worker = SearchWorker(keyword, sources, page, self)
        self._search_worker.search_completed.connect(self._on_search_completed)
        self._search_worker.search_failed.connect(self.search_failed)
        self._search_worker.search_progress.connect(self.search_progress)
        self._search_worker.start()
    
    def _on_search_completed(self, songs: list):
        self._current_songs = songs
        self.search_completed.emit(songs)
    
    def get_play_url(self, song_info: SongInfo, quality: str = 'standard'):
        cache_key = f"{song_info.song_id}_{quality}"
        if cache_key in self._url_cache:
            self.play_url_obtained.emit(song_info.song_id, self._url_cache[cache_key])
            return
        
        if song_info.play_url:
            self._url_cache[cache_key] = song_info.play_url
            self.play_url_obtained.emit(song_info.song_id, song_info.play_url)
            return
        
        if self._url_worker and self._url_worker.isRunning():
            self._url_worker.terminate()
        
        self._url_worker = PlayUrlWorker(song_info, quality, self)
        self._url_worker.url_obtained.connect(lambda sid, url: self._on_url_obtained(sid, url, quality))
        self._url_worker.url_failed.connect(self.play_url_failed)
        self._url_worker.start()
    
    def _on_url_obtained(self, song_id: str, url: str, quality: str = 'standard'):
        cache_key = f"{song_id}_{quality}"
        self._url_cache[cache_key] = url
        self.play_url_obtained.emit(song_id, url)
    
    def download_song(self, song_info: SongInfo, quality: str = 'standard'):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.terminate()
        
        self._download_worker = DownloadWorker(song_info, quality, self)
        self._download_worker.download_completed.connect(self.download_completed)
        self._download_worker.download_failed.connect(self.download_failed)
        self._download_worker.download_progress.connect(self.download_progress)
        self._download_worker.start()
    
    def get_lyric(self, song_info: SongInfo):
        if self._lyric_worker and self._lyric_worker.isRunning():
            self._lyric_worker.terminate()
        
        self._lyric_worker = LyricWorker(song_info, self)
        self._lyric_worker.lyric_completed.connect(self.lyric_completed)
        self._lyric_worker.lyric_failed.connect(self.lyric_failed)
        self._lyric_worker.start()
    
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
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.terminate()
        if self._lyric_worker and self._lyric_worker.isRunning():
            self._lyric_worker.terminate()
    
    def get_local_songs(self, directory: str = None) -> List[SongInfo]:
        if directory is None:
            directory = get_music_data_dir()
        
        songs = []
        supported_formats = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma')
        
        if os.path.exists(directory):
            try:
                for root, dirs, files in os.walk(directory):
                    for f in files:
                        if f.lower().endswith(supported_formats):
                            file_path = os.path.join(root, f)
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
    
    def _load_playlists(self):
        playlist_file = get_playlist_file()
        if os.path.exists(playlist_file):
            try:
                with open(playlist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._playlists = [Playlist.from_dict(p) for p in data]
            except Exception as e:
                logger.error(f"Failed to load playlists: {e}")
                self._playlists = []
        else:
            self._playlists = []
        
        self.playlists_loaded.emit(self._playlists)
    
    def save_playlists(self):
        playlist_file = get_playlist_file()
        try:
            with open(playlist_file, 'w', encoding='utf-8') as f:
                json.dump([p.to_dict() for p in self._playlists], f, ensure_ascii=False, indent=2)
            self.playlist_saved.emit()
        except Exception as e:
            logger.error(f"Failed to save playlists: {e}")
    
    def get_playlists(self) -> List[Playlist]:
        return self._playlists
    
    def create_playlist(self, name: str, description: str = "") -> Playlist:
        import uuid
        from datetime import datetime
        
        playlist = Playlist(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            created_at=datetime.now().isoformat()
        )
        self._playlists.append(playlist)
        self.save_playlists()
        return playlist
    
    def add_to_playlist(self, playlist_id: str, song: SongInfo):
        for playlist in self._playlists:
            if playlist.id == playlist_id:
                if not any(s.song_id == song.song_id for s in playlist.songs):
                    playlist.songs.append(song)
                    self.save_playlists()
                break
    
    def remove_from_playlist(self, playlist_id: str, song_id: str):
        for playlist in self._playlists:
            if playlist.id == playlist_id:
                playlist.songs = [s for s in playlist.songs if s.song_id != song_id]
                self.save_playlists()
                break
    
    def delete_playlist(self, playlist_id: str):
        self._playlists = [p for p in self._playlists if p.id != playlist_id]
        self.save_playlists()
    
    def get_playlist_by_id(self, playlist_id: str) -> Optional[Playlist]:
        for playlist in self._playlists:
            if playlist.id == playlist_id:
                return playlist
        return None
