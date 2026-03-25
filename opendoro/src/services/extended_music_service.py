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
    download_dir = os.path.join(get_user_data_dir(), "music", "downloads")
    os.makedirs(download_dir, exist_ok=True)
    return download_dir


def get_playlist_file():
    return os.path.join(get_user_data_dir(), "music", "playlists.json")


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
        'name': '奈缇斯',
        'icon': '🎵'
    },
    'qq': {
        'client': 'QQMusicClient',
        'name': '咕嘎',
        'icon': '🎶'
    },
    'kugou': {
        'client': 'KugouMusicClient',
        'name': '酷汪',
        'icon': '🎧'
    },
    'kuwo': {
        'client': 'KuwoMusicClient',
        'name': '酷me',
        'icon': '📻'
    },
    'migu': {
        'client': 'MiguMusicClient',
        'name': '咪咕',
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


class SearchWorker(QThread):
    search_completed = pyqtSignal(list)
    search_failed = pyqtSignal(str)
    search_progress = pyqtSignal(str)
    
    def __init__(self, keyword: str, sources: list = None, page: int = 0, search_size: int = 20, parent=None):
        super().__init__(parent)
        self.keyword = keyword
        self.sources = sources or ['NeteaseMusicClient', 'QQMusicClient', 'KuwoMusicClient']
        self.page = page
        self.search_size = search_size
    
    def run(self):
        try:
            from musicdl import musicdl
            
            musicdl_output_dir = get_download_dir()
            
            init_music_clients_cfg = {}
            for source in self.sources:
                init_music_clients_cfg[source] = {
                    'search_size_per_source': self.search_size,
                    'search_size_per_page': self.search_size,
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
    
    def __init__(self, song_info: SongInfo, parent=None):
        super().__init__(parent)
        self.song_info = song_info
    
    def run(self):
        try:
            from musicdl import musicdl
            from musicdl.modules.utils import SongInfo as MusicdlSongInfo
            from pathvalidate import sanitize_filename
            
            song_id_str = str(self.song_info.song_id)
            
            self.download_progress.emit(song_id_str, 10)
            
            base_download_dir = get_download_dir()
            
            singer = self.song_info.singer or "未知歌手"
            song_name = self.song_info.name or "未知歌曲"
            folder_name = sanitize_filename(f"{singer} - {song_name}")
            song_download_dir = os.path.join(base_download_dir, folder_name)
            os.makedirs(song_download_dir, exist_ok=True)
            
            self.download_progress.emit(song_id_str, 20)
            
            source_mapping = {
                'netease': 'NeteaseMusicClient',
                'qq': 'QQMusicClient',
                'kugou': 'KugouMusicClient',
                'kuwo': 'KuwoMusicClient',
                'baidu': 'BaiduMusicClient',
                'migu': 'MiguMusicClient',
                'joox': 'JooxClient',
            }
            
            song_source = self.song_info.source or 'netease'
            if song_source in source_mapping:
                client_name = source_mapping[song_source]
            elif song_source.endswith('Client'):
                client_name = song_source
            else:
                client_name = 'NeteaseMusicClient'
            
            init_cfg = {client_name: {'work_dir': song_download_dir}}
            music_client = musicdl.MusicClient(
                music_sources=[client_name],
                init_music_clients_cfg=init_cfg
            )
            
            self.download_progress.emit(song_id_str, 30)
            
            raw_data = self.song_info.raw_data if self.song_info.raw_data else {}
            if 'source' not in raw_data or not raw_data['source']:
                raw_data['source'] = song_source
            
            if not raw_data.get('download_url') and self.song_info.play_url:
                raw_data['download_url'] = self.song_info.play_url
            
            if not raw_data.get('download_url'):
                try:
                    search_keyword = f"{singer} {song_name}"
                    search_results = music_client.search(search_keyword)
                    if search_results:
                        for result in search_results:
                            if hasattr(result, 'song_name') and hasattr(result, 'singers'):
                                result_name = result.song_name or ''
                                result_singers = result.singers or ''
                                if song_name.lower() in result_name.lower() or singer.lower() in result_singers.lower():
                                    raw_data = result.todict() if hasattr(result, 'todict') else raw_data
                                    break
                except Exception as e:
                    logger.debug(f"Search for download URL failed: {e}")
            
            musicdl_song_info = MusicdlSongInfo.fromdict(raw_data)
            musicdl_song_info.work_dir = song_download_dir
            
            if not musicdl_song_info.source:
                musicdl_song_info.source = song_source
            if not musicdl_song_info.song_name:
                musicdl_song_info.song_name = song_name
            if not getattr(musicdl_song_info, 'singers', None):
                musicdl_song_info.singers = singer
            if not musicdl_song_info.ext:
                musicdl_song_info.ext = '.mp3'
            if not musicdl_song_info.identifier:
                musicdl_song_info.identifier = song_id_str
            
            if self.song_info.img_url:
                musicdl_song_info.cover_url = self.song_info.img_url
            if self.song_info.lyric:
                musicdl_song_info.lyric = self.song_info.lyric
            
            self.download_progress.emit(song_id_str, 50)
            
            download_results = music_client.download(song_infos=[musicdl_song_info])
            
            self.download_progress.emit(song_id_str, 80)
            
            downloaded_file = None
            if download_results:
                for result in download_results:
                    if hasattr(result, 'save_path') and result.save_path and os.path.exists(result.save_path):
                        downloaded_file = result.save_path
                        break
                    elif isinstance(result, dict):
                        file_path = result.get('savedpath', '') or result.get('save_path', '')
                        if file_path and os.path.exists(file_path):
                            downloaded_file = file_path
                            break
            
            if not downloaded_file:
                for f in os.listdir(song_download_dir):
                    if f.lower().endswith(('.mp3', '.m4a', '.flac', '.wav', '.ogg')):
                        downloaded_file = os.path.join(song_download_dir, f)
                        break
            
            if downloaded_file:
                self._embed_cover_and_lyric(downloaded_file, self.song_info.img_url, self.song_info.lyric)
                self.download_completed.emit(song_id_str, downloaded_file)
            else:
                self.download_failed.emit(song_id_str, "下载失败：未找到下载文件")
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.download_failed.emit(str(self.song_info.song_id), str(e))
    
    def _embed_cover_and_lyric(self, file_path: str, cover_url: str, lyric: str):
        try:
            import requests
            from mutagen import File
            from mutagen.id3 import ID3, APIC, USLT
            from mutagen.mp4 import MP4, MP4Cover
            from mutagen.flac import FLAC, Picture
            
            if cover_url and not cover_url.startswith('data:'):
                try:
                    response = requests.get(cover_url, timeout=10)
                    if response.status_code == 200:
                        cover_data = response.content
                        self._embed_cover(file_path, cover_data)
                except Exception as e:
                    logger.debug(f"Failed to download cover: {e}")
            elif cover_url and cover_url.startswith('data:image'):
                import base64
                try:
                    base64_data = cover_url.split(',', 1)[1]
                    cover_data = base64.b64decode(base64_data)
                    self._embed_cover(file_path, cover_data)
                except Exception as e:
                    logger.debug(f"Failed to decode cover: {e}")
            
            if lyric:
                self._embed_lyric(file_path, lyric)
                
        except Exception as e:
            logger.debug(f"Failed to embed cover/lyric: {e}")
    
    def _embed_cover(self, file_path: str, cover_data: bytes):
        from mutagen import File
        from mutagen.id3 import ID3, APIC
        from mutagen.mp4 import MP4, MP4Cover
        from mutagen.flac import FLAC, Picture
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.mp3':
                audio = ID3(file_path)
                mime_type = 'image/jpeg' if cover_data[:2] == b'\xff\xd8' else 'image/png'
                audio.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=cover_data
                ))
                audio.save()
            elif ext in ('.m4a', '.mp4'):
                audio = MP4(file_path)
                fmt = MP4Cover.FORMAT_JPEG if cover_data[:2] == b'\xff\xd8' else MP4Cover.FORMAT_PNG
                audio['covr'] = [MP4Cover(cover_data, imageformat=fmt)]
                audio.save()
            elif ext == '.flac':
                audio = FLAC(file_path)
                picture = Picture()
                picture.type = 3
                picture.mime = 'image/jpeg' if cover_data[:2] == b'\xff\xd8' else 'image/png'
                picture.data = cover_data
                audio.add_picture(picture)
                audio.save()
        except Exception as e:
            logger.debug(f"Failed to embed cover to {ext}: {e}")
    
    def _embed_lyric(self, file_path: str, lyric: str):
        from mutagen import File
        from mutagen.id3 import ID3, USLT
        from mutagen.mp4 import MP4
        from mutagen.flac import FLAC
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.mp3':
                audio = ID3(file_path)
                audio.add(USLT(encoding=3, lang='chi', desc='', text=lyric))
                audio.save()
            elif ext in ('.m4a', '.mp4'):
                audio = MP4(file_path)
                audio['\xa9lyr'] = lyric
                audio.save()
            elif ext == '.flac':
                audio = FLAC(file_path)
                audio['LYRICS'] = lyric
                audio.save()
            
            lrc_path = os.path.splitext(file_path)[0] + '.lrc'
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyric)
        except Exception as e:
            logger.debug(f"Failed to embed lyric to {ext}: {e}")


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
    
    def __init__(self, song_info: SongInfo, parent=None):
        super().__init__(parent)
        self.song_info = song_info
    
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
    all_downloads_completed = pyqtSignal(int, int)
    
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
        self._lyric_worker = None
        self._playlists: List[Playlist] = []
        self._download_workers: dict = {}
        self._download_queue: list = []
        self._total_downloads = 0
        self._completed_downloads = 0
        self._failed_downloads = 0
        self._load_playlists()
    
    def get_available_sources(self) -> Dict[str, dict]:
        return MUSIC_SOURCES
    
    def search(self, keyword: str, sources: list = None, page: int = 0, search_size: int = 20):
        if not keyword.strip():
            self.search_failed.emit("搜索关键词不能为空")
            return
        
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
        
        self._search_worker = SearchWorker(keyword, sources, page, search_size, self)
        self._search_worker.search_completed.connect(self._on_search_completed)
        self._search_worker.search_failed.connect(self.search_failed)
        self._search_worker.search_progress.connect(self.search_progress)
        self._search_worker.start()
    
    def stop_search(self):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.terminate()
            self._search_worker = None
            self.search_failed.emit("搜索已取消")
    
    def _on_search_completed(self, songs: list):
        self._current_songs = songs
        self.search_completed.emit(songs)
    
    def get_play_url(self, song_info: SongInfo):
        cache_key = song_info.song_id
        if cache_key in self._url_cache:
            self.play_url_obtained.emit(song_info.song_id, self._url_cache[cache_key])
            return
        
        if song_info.play_url:
            self._url_cache[cache_key] = song_info.play_url
            self.play_url_obtained.emit(song_info.song_id, song_info.play_url)
            return
        
        if self._url_worker and self._url_worker.isRunning():
            self._url_worker.terminate()
        
        self._url_worker = PlayUrlWorker(song_info, self)
        self._url_worker.url_obtained.connect(lambda sid, url: self._on_url_obtained(sid, url))
        self._url_worker.url_failed.connect(self.play_url_failed)
        self._url_worker.start()
    
    def _on_url_obtained(self, song_id: str, url: str):
        cache_key = song_id
        self._url_cache[cache_key] = url
        self.play_url_obtained.emit(song_id, url)
    
    def download_song(self, song_info: SongInfo):
        song_id_str = str(song_info.song_id)
        if song_id_str in self._download_workers:
            return
        
        worker = DownloadWorker(song_info, self)
        worker.download_completed.connect(self._on_download_completed)
        worker.download_failed.connect(self._on_download_failed)
        worker.download_progress.connect(self.download_progress)
        worker.finished.connect(lambda: self._cleanup_download_worker(song_id_str))
        
        self._download_workers[song_id_str] = worker
        worker.start()
    
    def download_songs_batch(self, songs: List[SongInfo]):
        self._total_downloads = len(songs)
        self._completed_downloads = 0
        self._failed_downloads = 0
        
        for song in songs:
            if song.source != "local":
                self.download_song(song)
    
    def _on_download_completed(self, song_id: str, file_path: str):
        self._completed_downloads += 1
        self.download_completed.emit(song_id, file_path)
        self._check_all_downloads_done()
    
    def _on_download_failed(self, song_id: str, error_msg: str):
        self._failed_downloads += 1
        self.download_failed.emit(song_id, error_msg)
        self._check_all_downloads_done()
    
    def _check_all_downloads_done(self):
        total_done = self._completed_downloads + self._failed_downloads
        if total_done >= self._total_downloads and self._total_downloads > 0:
            self.all_downloads_completed.emit(self._completed_downloads, self._failed_downloads)
            self._total_downloads = 0
            self._completed_downloads = 0
            self._failed_downloads = 0
    
    def _cleanup_download_worker(self, song_id: str):
        if song_id in self._download_workers:
            del self._download_workers[song_id]
    
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
                            song_info = self._parse_audio_metadata(file_path)
                            songs.append(song_info)
            except Exception as e:
                logger.error(f"Failed to load local songs: {e}")
        
        return songs
    
    def _parse_audio_metadata(self, file_path: str) -> SongInfo:
        import base64
        from mutagen import File
        from mutagen.id3 import ID3
        from tinytag import TinyTag
        import re
        
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        song_name = file_name
        singer = "本地音乐"
        album = ""
        duration = 0
        img_url = ""
        lyric = ""
        
        def is_valid_title(title: str) -> bool:
            if not title or not title.strip():
                return False
            lower_title = title.lower().strip()
            track_patterns = [
                r'^track\s*\d+$',
                r'^track$',
                r'^\d+$',
                r'^unknown\s*title$',
                r'^untitled$',
                r'^no\s*title$',
                r'^title$',
            ]
            for pattern in track_patterns:
                if re.match(pattern, lower_title):
                    return False
            return True
        
        def clean_song_name_from_id(song_name: str, file_path: str) -> str:
            patterns_to_try = [
                r' - [a-f0-9]{32}$',
                r' - [a-f0-9]{40}$',
                r'_[a-f0-9]{32}$',
                r'_[a-f0-9]{40}$',
            ]
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            for pattern in patterns_to_try:
                match = re.search(pattern, base_name, re.IGNORECASE)
                if match:
                    cleaned = base_name[:match.start()].strip()
                    if cleaned:
                        return cleaned
            return song_name
        
        try:
            tag = TinyTag.get(file_path, image=True)
            if tag:
                if tag.title and is_valid_title(tag.title):
                    song_name = tag.title.strip()
                if tag.artist and tag.artist.strip():
                    singer = tag.artist.strip()
                if tag.album and tag.album.strip():
                    album = tag.album.strip()
                if tag.duration:
                    duration = int(tag.duration)
                
                image_data = tag.get_image()
                if image_data:
                    mime_type = "image/jpeg"
                    if image_data[:8].startswith(b'\x89PNG\r\n\x1a\n'):
                        mime_type = "image/png"
                    elif image_data[:22] == b'\xff\xd8\xff':
                        mime_type = "image/jpeg"
                    img_url = f"data:{mime_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
        except Exception as e:
            logger.debug(f"TinyTag parse failed for {file_path}: {e}")
        
        try:
            audio = File(file_path)
            if audio is not None:
                cls_name = audio.__class__.__name__
                
                if cls_name == "MP3":
                    try:
                        id3 = ID3(file_path)
                        for key in id3.keys():
                            if key.startswith("USLT"):
                                frame = id3[key]
                                if hasattr(frame, 'text') and frame.text:
                                    lyric = frame.text
                                    break
                    except Exception:
                        pass
                
                elif cls_name == "MP4":
                    tags = audio.tags or {}
                    if "\xa9lyr" in tags:
                        lrc_value = tags["\xa9lyr"]
                        if lrc_value:
                            lyric = lrc_value[0] if isinstance(lrc_value, list) else str(lrc_value)
                
                elif cls_name in {"FLAC", "OggVorbis", "OggOpus"}:
                    tags = audio.tags or {}
                    if "LYRICS" in tags:
                        lrc_value = tags["LYRICS"]
                        lyric = lrc_value[0] if isinstance(lrc_value, list) else str(lrc_value)
        except Exception as e:
            logger.debug(f"Mutagen parse failed for {file_path}: {e}")
        
        lrc_path = os.path.splitext(file_path)[0] + ".lrc"
        if os.path.exists(lrc_path):
            try:
                with open(lrc_path, 'r', encoding='utf-8') as lf:
                    lyric = lf.read()
            except Exception as e:
                logger.debug(f"Failed to read lrc file {lrc_path}: {e}")
        
        song_name = clean_song_name_from_id(song_name, file_path)
        
        return SongInfo(
            song_id=file_path,
            name=song_name,
            singer=singer,
            album=album,
            duration=duration,
            source="local",
            img_url=img_url,
            play_url=file_path,
            lyric=lyric
        )
    
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
