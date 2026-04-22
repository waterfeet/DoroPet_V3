import os
import tempfile
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass
from src.core.logger import logger


def get_user_data_dir() -> str:
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()


@dataclass
class CacheInfo:
    name: str
    path: str
    size_bytes: int
    file_count: int
    is_safe_to_clear: bool
    description: str
    icon: str

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_mb:.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.1f} GB"


class CacheManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._user_data_dir = get_user_data_dir()

    def _get_dir_size(self, path: str) -> Tuple[int, int]:
        if not os.path.exists(path):
            return 0, 0
        
        total_size = 0
        file_count = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                        file_count += 1
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"[CacheManager] 计算目录大小失败: {path}, {e}")
        
        return total_size, file_count

    def _clear_dir(self, path: str) -> Tuple[int, int]:
        if not os.path.exists(path):
            return 0, 0
        
        deleted_count = 0
        freed_bytes = 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(path, topdown=False):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        freed_bytes += os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                    except OSError as e:
                        logger.warning(f"[CacheManager] 删除文件失败: {filepath}, {e}")
                
                for dirname in dirnames:
                    dirpath_full = os.path.join(dirpath, dirname)
                    try:
                        os.rmdir(dirpath_full)
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"[CacheManager] 清除目录失败: {path}, {e}")
        
        return deleted_count, freed_bytes

    def get_tts_cache_info(self) -> CacheInfo:
        path = os.path.join(self._user_data_dir, "cache", "tts")
        size, count = self._get_dir_size(path)
        return CacheInfo(
            name="TTS 语音缓存",
            path=path,
            size_bytes=size,
            file_count=count,
            is_safe_to_clear=True,
            description="AI 语音合成的音频缓存",
            icon="🔊"
        )

    def get_image_cache_info(self) -> CacheInfo:
        path = os.path.join(os.getcwd(), "cached_images")
        size, count = self._get_dir_size(path)
        return CacheInfo(
            name="网络图片缓存",
            path=path,
            size_bytes=size,
            file_count=count,
            is_safe_to_clear=True,
            description="聊天中加载的网络图片缓存",
            icon="🖼️"
        )

    def get_temp_images_cache_info(self) -> CacheInfo:
        path = os.path.join(tempfile.gettempdir(), "doropet_images")
        size, count = self._get_dir_size(path)
        return CacheInfo(
            name="临时图片",
            path=path,
            size_bytes=size,
            file_count=count,
            is_safe_to_clear=True,
            description="Base64 编码的临时图片文件",
            icon="📄"
        )

    def get_musicdl_cache_info(self) -> CacheInfo:
        path = os.path.join(self._user_data_dir, "musicdl_outputs")
        size, count = self._get_dir_size(path)
        return CacheInfo(
            name="musicdl 临时输出",
            path=path,
            size_bytes=size,
            file_count=count,
            is_safe_to_clear=True,
            description="音乐搜索产生的临时文件",
            icon="🎵"
        )

    def get_old_logs_info(self) -> CacheInfo:
        path = os.path.join(self._user_data_dir, "log")
        if not os.path.exists(path):
            return CacheInfo(
                name="旧日志文件",
                path=path,
                size_bytes=0,
                file_count=0,
                is_safe_to_clear=True,
                description="超过 7 天的日志文件",
                icon="📝"
            )
        
        seven_days_ago = time.time() - 7 * 24 * 60 * 60
        total_size = 0
        old_file_count = 0
        
        try:
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        if mtime < seven_days_ago:
                            total_size += os.path.getsize(filepath)
                            old_file_count += 1
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"[CacheManager] 计算旧日志大小失败: {e}")
        
        return CacheInfo(
            name="旧日志文件",
            path=path,
            size_bytes=total_size,
            file_count=old_file_count,
            is_safe_to_clear=True,
            description="超过 7 天的日志文件",
            icon="📝"
        )

    def get_music_downloads_info(self) -> CacheInfo:
        path = os.path.join(self._user_data_dir, "music", "downloads")
        size, count = self._get_dir_size(path)
        return CacheInfo(
            name="音乐下载",
            path=path,
            size_bytes=size,
            file_count=count,
            is_safe_to_clear=False,
            description="已下载的音乐文件（清除后需重新下载）",
            icon="⚠️"
        )

    def get_all_cache_info(self) -> List[CacheInfo]:
        return [
            self.get_tts_cache_info(),
            self.get_image_cache_info(),
            self.get_temp_images_cache_info(),
            self.get_musicdl_cache_info(),
            self.get_old_logs_info(),
            self.get_music_downloads_info(),
        ]

    def get_total_size(self) -> int:
        total = 0
        for info in self.get_all_cache_info():
            total += info.size_bytes
        return total

    def get_total_size_display(self) -> str:
        total = self.get_total_size()
        if total < 1024:
            return f"{total} B"
        elif total < 1024 * 1024:
            return f"{total / 1024:.1f} KB"
        elif total < 1024 * 1024 * 1024:
            return f"{total / (1024 * 1024):.1f} MB"
        else:
            return f"{total / (1024 * 1024 * 1024):.1f} GB"

    def clear_tts_cache(self) -> Tuple[int, int]:
        info = self.get_tts_cache_info()
        return self._clear_dir(info.path)

    def clear_image_cache(self) -> Tuple[int, int]:
        info = self.get_image_cache_info()
        deleted, freed = self._clear_dir(info.path)
        try:
            from src.core.image_cache_manager import get_image_cache_manager
            cache_mgr = get_image_cache_manager()
            cache_mgr._memory_cache.clear()
        except Exception:
            pass
        return deleted, freed

    def clear_temp_images_cache(self) -> Tuple[int, int]:
        info = self.get_temp_images_cache_info()
        return self._clear_dir(info.path)

    def clear_musicdl_cache(self) -> Tuple[int, int]:
        info = self.get_musicdl_cache_info()
        return self._clear_dir(info.path)

    def clear_old_logs(self) -> Tuple[int, int]:
        info = self.get_old_logs_info()
        if not os.path.exists(info.path):
            return 0, 0
        
        seven_days_ago = time.time() - 7 * 24 * 60 * 60
        deleted_count = 0
        freed_bytes = 0
        
        try:
            for filename in os.listdir(info.path):
                filepath = os.path.join(info.path, filename)
                if os.path.isfile(filepath):
                    try:
                        mtime = os.path.getmtime(filepath)
                        if mtime < seven_days_ago:
                            freed_bytes += os.path.getsize(filepath)
                            os.remove(filepath)
                            deleted_count += 1
                    except OSError as e:
                        logger.warning(f"[CacheManager] 删除日志文件失败: {filepath}, {e}")
        except Exception as e:
            logger.warning(f"[CacheManager] 清除旧日志失败: {e}")
        
        return deleted_count, freed_bytes

    def clear_music_downloads(self) -> Tuple[int, int]:
        info = self.get_music_downloads_info()
        return self._clear_dir(info.path)

    def clear_all_safe_caches(self) -> Tuple[int, int]:
        total_deleted = 0
        total_freed = 0
        
        safe_methods = [
            self.clear_tts_cache,
            self.clear_image_cache,
            self.clear_temp_images_cache,
            self.clear_musicdl_cache,
            self.clear_old_logs,
        ]
        
        for method in safe_methods:
            try:
                deleted, freed = method()
                total_deleted += deleted
                total_freed += freed
            except Exception as e:
                logger.error(f"[CacheManager] 清除缓存失败: {e}")
        
        return total_deleted, total_freed


def get_cache_manager() -> CacheManager:
    return CacheManager()
