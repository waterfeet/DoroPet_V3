from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from src.core.version_manager import (
    VersionManager, VersionInfo, __version__,
    GITEE_REPO_OWNER, GITEE_REPO_NAME
)
from src.core.logger import logger
import requests

class StartupUpdateChecker(QObject):
    update_available = pyqtSignal(object)
    check_failed = pyqtSignal(str)
    check_completed = pyqtSignal()

    MAX_RETRIES = 3
    RETRY_DELAY_MS = 5000
    CHECK_DELAY_MS = 2000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.version_manager = VersionManager(self)
        self._retry_count = 0
        self._is_checking = False
        self._main_window = None
        self._pending_update_info = None
        
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._do_retry)
        
        self._delay_timer = QTimer(self)
        self._delay_timer.setSingleShot(True)
        self._delay_timer.timeout.connect(self._do_check)
        
        self.version_manager.versions_loaded.connect(self._on_versions_loaded)
        self.version_manager.load_error.connect(self._on_load_error)

    def set_main_window(self, main_window):
        self._main_window = main_window
        if self._main_window and hasattr(self._main_window, 'update_interface'):
            versions = self.version_manager.get_all_versions()
            if versions:
                self._main_window.update_interface.set_versions(versions)

    def start_check(self, delay_ms=None):
        if delay_ms is None:
            delay_ms = self.CHECK_DELAY_MS
        
        logger.info(f"Startup update check scheduled in {delay_ms}ms")
        self._delay_timer.start(delay_ms)

    def _do_check(self):
        if self._is_checking:
            return
        
        self._is_checking = True
        self._retry_count = 0
        logger.info("Starting startup version check...")
        self.version_manager.fetch_remote_versions()

    def _on_versions_loaded(self, versions):
        self._is_checking = False
        
        latest = self.version_manager.check_for_updates(include_beta=False)
        
        if latest:
            logger.info(f"New version available: v{latest.version}")
            self._pending_update_info = latest
            self.update_available.emit(latest)
        else:
            logger.info("Application is up to date")
        
        self.check_completed.emit()

    def _on_load_error(self, error_msg):
        self._is_checking = False
        self._retry_count += 1
        
        logger.warning(f"Version check failed (attempt {self._retry_count}/{self.MAX_RETRIES}): {error_msg}")
        
        if self._retry_count < self.MAX_RETRIES:
            logger.info(f"Retrying in {self.RETRY_DELAY_MS / 1000} seconds...")
            self._retry_timer.start(self.RETRY_DELAY_MS)
        else:
            logger.error("Max retries reached, giving up version check")
            self.check_failed.emit(error_msg)
            self.check_completed.emit()

    def _do_retry(self):
        if self._retry_count >= self.MAX_RETRIES:
            return
        
        self._is_checking = True
        logger.info(f"Retrying version check (attempt {self._retry_count + 1})...")
        self.version_manager.fetch_remote_versions()

    def get_pending_update(self):
        return self._pending_update_info

    def get_version_manager(self):
        return self.version_manager

    def cancel(self):
        self._delay_timer.stop()
        self._retry_timer.stop()
        self._is_checking = False
        logger.info("Startup update check cancelled")
