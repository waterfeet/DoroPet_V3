import os
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

from src.core.logger import logger


class ImageCacheManager:
    _instance = None
    _initialized = False

    CACHE_DIR_NAME = "cached_images"
    MAX_CACHE_SIZE_MB = 500
    MAX_CACHE_AGE_DAYS = 7
    CLEANUP_THRESHOLD_RATIO = 0.8

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ImageCacheManager._initialized:
            return

        self._cache_dir = os.path.join(os.getcwd(), self.CACHE_DIR_NAME)
        self._memory_cache: Dict[str, str] = {}
        self._ensure_cache_dir()
        ImageCacheManager._initialized = True

    def _ensure_cache_dir(self):
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)
            logger.info(f"[ImageCacheManager] 创建缓存目录: {self._cache_dir}")

    @property
    def cache_dir(self) -> str:
        return self._cache_dir

    def get_cached_path(self, url: str) -> Optional[str]:
        logger.debug(f"[ImageCacheManager] 查找缓存：url={url[:100]}...")
        
        if url in self._memory_cache:
            cached_path = self._memory_cache[url]
            if os.path.exists(cached_path):
                logger.debug(f"[ImageCacheManager] 内存缓存命中：{cached_path}")
                return cached_path
            else:
                logger.debug(f"[ImageCacheManager] 内存缓存存在但文件已删除：{cached_path}")
                del self._memory_cache[url]

        url_hash = self._generate_url_hash(url)
        logger.debug(f"[ImageCacheManager] URL hash: {url_hash}")
        
        potential_paths = list(self._memory_cache.values())
        logger.debug(f"[ImageCacheManager] 内存缓存中的路径数：{len(potential_paths)}")

        for cached_path in potential_paths:
            if url_hash in cached_path and os.path.exists(cached_path):
                logger.debug(f"[ImageCacheManager] 通过 hash 找到缓存：{cached_path}")
                return cached_path

        logger.debug(f"[ImageCacheManager] 缓存未命中")
        return None

    def add_to_cache(self, url: str, local_path: str):
        logger.debug(f"[ImageCacheManager] 添加到缓存：url={url[:100]}... -> {local_path}")
        self._memory_cache[url] = local_path
        self._maybe_cleanup()

    def _generate_url_hash(self, url: str) -> str:
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _get_cache_size(self) -> int:
        total_size = 0
        if not os.path.exists(self._cache_dir):
            return 0

        for dirpath, dirnames, filenames in os.walk(self._cache_dir):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except OSError:
                    pass

        return total_size

    def _get_cache_size_mb(self) -> float:
        return self._get_cache_size() / (1024 * 1024)

    def _get_cached_files(self) -> list:
        files = []
        if not os.path.exists(self._cache_dir):
            return files

        for filename in os.listdir(self._cache_dir):
            filepath = os.path.join(self._cache_dir, filename)
            if os.path.isfile(filepath):
                try:
                    mtime = os.path.getmtime(filepath)
                    size = os.path.getsize(filepath)
                    files.append({
                        'path': filepath,
                        'mtime': mtime,
                        'size': size,
                        'age_days': (time.time() - mtime) / 86400
                    })
                except OSError:
                    pass

        return files

    def _maybe_cleanup(self):
        size_mb = self._get_cache_size_mb()
        if size_mb > self.MAX_CACHE_SIZE_MB * self.CLEANUP_THRESHOLD_RATIO:
            logger.info(f"[ImageCacheManager] 缓存大小 {size_mb:.1f}MB 超过阈值，开始清理")
            self._evict_by_size()

        self._cleanup_expired()

    def _evict_by_size(self):
        target_size = int(self.MAX_CACHE_SIZE_MB * self.CLEANUP_THRESHOLD_RATIO * 1024 * 1024)
        current_size = self._get_cache_size()

        if current_size <= target_size:
            return

        files = self._get_cached_files()
        files.sort(key=lambda x: x['mtime'])

        for file_info in files:
            if current_size <= target_size:
                break

            try:
                os.remove(file_info['path'])
                current_size -= file_info['size']
                self._remove_from_memory_cache(file_info['path'])
                logger.debug(f"[ImageCacheManager] 删除缓存文件: {file_info['path']}")
            except OSError as e:
                logger.warning(f"[ImageCacheManager] 删除缓存文件失败: {e}")

        logger.info(f"[ImageCacheManager] 清理完成，当前大小: {current_size / (1024 * 1024):.1f}MB")

    def _cleanup_expired(self):
        files = self._get_cached_files()
        expired_files = [f for f in files if f['age_days'] > self.MAX_CACHE_AGE_DAYS]

        if not expired_files:
            return

        for file_info in expired_files:
            try:
                os.remove(file_info['path'])
                self._remove_from_memory_cache(file_info['path'])
                logger.debug(f"[ImageCacheManager] 删除过期缓存: {file_info['path']}")
            except OSError as e:
                logger.warning(f"[ImageCacheManager] 删除过期缓存失败: {e}")

        logger.info(f"[ImageCacheManager] 清理了 {len(expired_files)} 个过期缓存文件")

    def _remove_from_memory_cache(self, path: str):
        urls_to_remove = [url for url, cached_path in self._memory_cache.items() if cached_path == path]
        for url in urls_to_remove:
            del self._memory_cache[url]

    def clear_all(self):
        files = self._get_cached_files()
        for file_info in files:
            try:
                os.remove(file_info['path'])
            except OSError:
                pass

        self._memory_cache.clear()
        logger.info(f"[ImageCacheManager] 清空所有缓存")

    def get_cache_stats(self) -> Dict:
        files = self._get_cached_files()
        total_size = sum(f['size'] for f in files)
        oldest = min(files, key=lambda x: x['mtime']) if files else None
        newest = max(files, key=lambda x: x['mtime']) if files else None

        return {
            'file_count': len(files),
            'total_size_mb': total_size / (1024 * 1024),
            'max_size_mb': self.MAX_CACHE_SIZE_MB,
            'oldest_file': oldest['path'] if oldest else None,
            'oldest_age_days': oldest['age_days'] if oldest else 0,
            'newest_file': newest['path'] if newest else None,
            'newest_age_days': newest['age_days'] if newest else 0
        }

    def add_image(self, url: str, local_path: str) -> str:
        self.add_to_cache(url, local_path)
        return local_path

    def has_image(self, url: str) -> bool:
        return self.get_cached_path(url) is not None


def get_image_cache_manager() -> ImageCacheManager:
    return ImageCacheManager()
