import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from src.core.logger import logger

__version__ = "3.1.0"
__app_name__ = "DoroPet"

class ReleaseType(Enum):
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"

@dataclass
class VersionInfo:
    version: str
    release_type: ReleaseType = ReleaseType.STABLE
    release_date: str = ""
    changelog: str = ""
    download_url: str = ""
    file_size: int = 0
    file_hash: str = ""
    min_version: str = ""
    
    def __post_init__(self):
        if isinstance(self.release_type, str):
            self.release_type = ReleaseType(self.release_type)
    
    @property
    def version_tuple(self) -> tuple:
        return tuple(map(int, self.version.split('.')))
    
    @property
    def file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)
    
    @property
    def display_size(self) -> str:
        if self.file_size >= 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024 * 1024):.2f} GB"
        elif self.file_size >= 1024 * 1024:
            return f"{self.file_size_mb:.2f} MB"
        elif self.file_size >= 1024:
            return f"{self.file_size / 1024:.2f} KB"
        return f"{self.file_size} B"

def compare_versions(v1: str, v2: str) -> int:
    """
    比较两个版本号
    返回: 1 如果 v1 > v2, -1 如果 v1 < v2, 0 如果相等
    """
    t1 = tuple(map(int, v1.split('.')))
    t2 = tuple(map(int, v2.split('.')))
    
    for a, b in zip(t1, t2):
        if a > b:
            return 1
        elif a < b:
            return -1
    
    if len(t1) > len(t2):
        return 1
    elif len(t1) < len(t2):
        return -1
    return 0

class VersionManager(QObject):
    check_completed = pyqtSignal(object)
    download_progress = pyqtSignal(int, int)
    download_completed = pyqtSignal(str)
    download_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_version = __version__
        self._versions: List[VersionInfo] = []
        self._download_thread: Optional[QThread] = None
    
    def get_current_version(self) -> str:
        return self.current_version
    
    def get_all_versions(self) -> List[VersionInfo]:
        if not self._versions:
            self._versions = self._get_mock_versions()
        return self._versions
    
    def get_latest_version(self, include_beta: bool = False) -> Optional[VersionInfo]:
        versions = self.get_all_versions()
        if not versions:
            return None
        
        eligible = [v for v in versions if include_beta or v.release_type == ReleaseType.STABLE]
        if not eligible:
            return None
        
        return max(eligible, key=lambda v: v.version_tuple)
    
    def check_for_updates(self, include_beta: bool = False) -> Optional[VersionInfo]:
        latest = self.get_latest_version(include_beta)
        if latest and compare_versions(latest.version, self.current_version) > 0:
            return latest
        return None
    
    def get_versions_newer_than(self, version: str, include_beta: bool = False) -> List[VersionInfo]:
        versions = self.get_all_versions()
        result = []
        for v in versions:
            if compare_versions(v.version, version) > 0:
                if include_beta or v.release_type == ReleaseType.STABLE:
                    result.append(v)
        return sorted(result, key=lambda v: v.version_tuple, reverse=True)
    
    def _get_mock_versions(self) -> List[VersionInfo]:
        return [
            VersionInfo(
                version="3.2.0",
                release_type=ReleaseType.STABLE,
                release_date="2026-03-15",
                changelog="## 新功能\n- 新增软件更新模块\n- 优化Live2D性能\n- 添加更多表情支持\n\n## 修复\n- 修复内存泄漏问题\n- 修复语音识别偶发崩溃",
                download_url="https://github.com/example/DoroPet/releases/v3.2.0",
                file_size=150 * 1024 * 1024,
                file_hash="abc123def456"
            ),
            VersionInfo(
                version="3.1.5",
                release_type=ReleaseType.BETA,
                release_date="2026-03-10",
                changelog="## 测试版更新\n- 实验性功能：多模型切换\n- 新UI界面预览\n\n注意：此版本可能不稳定",
                download_url="https://github.com/example/DoroPet/releases/v3.1.5-beta",
                file_size=148 * 1024 * 1024,
                file_hash="def456ghi789"
            ),
            VersionInfo(
                version="3.1.0",
                release_type=ReleaseType.STABLE,
                release_date="2026-02-20",
                changelog="## 新功能\n- 全新界面设计\n- 支持技能系统\n- 添加插件管理\n\n## 改进\n- 优化启动速度\n- 改进对话体验",
                download_url="https://github.com/example/DoroPet/releases/v3.1.0",
                file_size=145 * 1024 * 1024,
                file_hash="ghi789jkl012"
            ),
            VersionInfo(
                version="3.0.0",
                release_type=ReleaseType.STABLE,
                release_date="2026-01-15",
                changelog="## 重大更新\n- 架构重构\n- 新增Live2D支持\n- AI对话系统升级",
                download_url="https://github.com/example/DoroPet/releases/v3.0.0",
                file_size=140 * 1024 * 1024,
                file_hash="jkl012mno345"
            ),
            VersionInfo(
                version="2.5.0",
                release_type=ReleaseType.STABLE,
                release_date="2025-12-01",
                changelog="## 功能更新\n- 基础桌宠功能\n- 简单对话支持",
                download_url="https://github.com/example/DoroPet/releases/v2.5.0",
                file_size=80 * 1024 * 1024,
                file_hash="mno345pqr678"
            ),
        ]
    
    def fetch_remote_versions(self, callback: Callable[[List[VersionInfo]], None]):
        def _fetch():
            try:
                versions = self._get_mock_versions()
                self._versions = versions
                callback(versions)
            except Exception as e:
                logger.error(f"Failed to fetch versions: {e}")
                callback([])
        
        import threading
        thread = threading.Thread(target=_fetch, daemon=True)
        thread.start()
    
    def download_update(self, version: VersionInfo, save_path: str):
        def _download():
            try:
                import time
                total_size = version.file_size
                for progress in range(0, 101, 10):
                    time.sleep(0.1)
                    self.download_progress.emit(progress, total_size)
                
                mock_file = os.path.join(save_path, f"DoroPet_v{version.version}_setup.exe")
                with open(mock_file, 'w') as f:
                    f.write(f"Mock installer for version {version.version}")
                
                self.download_completed.emit(mock_file)
                logger.info(f"Download completed: {mock_file}")
            except Exception as e:
                self.download_error.emit(str(e))
                logger.error(f"Download error: {e}")
        
        self._download_thread = QThread()
        self._download_thread.run = _download
        self._download_thread.start()
    
    def cancel_download(self):
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.terminate()
            self._download_thread = None
            logger.info("Download cancelled")

def format_changelog(changelog: str) -> str:
    return changelog

def get_version_type_display(release_type: ReleaseType) -> str:
    type_map = {
        ReleaseType.STABLE: "正式版",
        ReleaseType.BETA: "测试版",
        ReleaseType.ALPHA: "开发版"
    }
    return type_map.get(release_type, "未知")
