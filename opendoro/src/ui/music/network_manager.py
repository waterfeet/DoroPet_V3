from typing import Optional, Callable
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtGui import QPixmap


class NetworkManager(QObject):
    _instance: Optional['NetworkManager'] = None
    
    @classmethod
    def get_instance(cls) -> 'NetworkManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._active_replies = []
    
    def fetch_image(self, url: str, callback: Callable[[QPixmap], None], error_callback: Callable[[], None] = None):
        if not url:
            if error_callback:
                error_callback()
            return
        
        request = QNetworkRequest(QUrl(url))
        reply = self._manager.get(request)
        self._active_replies.append(reply)
        
        def on_finished():
            self._active_replies.remove(reply)
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    callback(pixmap)
                elif error_callback:
                    error_callback()
            elif error_callback:
                error_callback()
            reply.deleteLater()
        
        reply.finished.connect(on_finished)
    
    def fetch_data(self, url: str, callback: Callable[[bytes], None], error_callback: Callable[[str], None] = None):
        if not url:
            if error_callback:
                error_callback("URL is empty")
            return
        
        request = QNetworkRequest(QUrl(url))
        reply = self._manager.get(request)
        self._active_replies.append(reply)
        
        def on_finished():
            self._active_replies.remove(reply)
            if reply.error() == QNetworkReply.NoError:
                data = reply.readAll()
                callback(bytes(data))
            elif error_callback:
                error_callback(reply.errorString())
            reply.deleteLater()
        
        reply.finished.connect(on_finished)
    
    def cancel_all(self):
        for reply in self._active_replies[:]:
            reply.abort()
            reply.deleteLater()
        self._active_replies.clear()
