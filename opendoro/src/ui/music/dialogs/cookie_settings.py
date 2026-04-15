import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QScrollArea, QWidget, 
                             QHBoxLayout, QLabel, QMessageBox)
from qfluentwidgets import (CardWidget, PushButton, PrimaryPushButton, 
                           LineEdit, BodyLabel, StrongBodyLabel)

from src.core.cookie_manager import CookieManager
from ..constants import MUSIC_PLATFORMS


class CookieSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookie 设置")
        self.cookie_manager = CookieManager.get_instance()
        self.platforms = MUSIC_PLATFORMS
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        
        self.platform_tabs = {}
        self.cookie_inputs = {}
        
        for platform_key, platform_name, music_client_name in self.platforms:
            has_cookies = self.cookie_manager.has_cookies(platform_key)
            status = "✓ 已设置" if has_cookies else "✗ 未设置"
            
            card = CardWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)
            
            header_layout = QHBoxLayout()
            title_label = StrongBodyLabel(platform_name)
            header_layout.addWidget(title_label)
            
            self.platform_tabs[platform_key] = QLabel(status)
            self.platform_tabs[platform_key].setObjectName("statusLabel")
            header_layout.addWidget(self.platform_tabs[platform_key])
            header_layout.addStretch()
            
            card_layout.addLayout(header_layout)
            
            instruction_label = BodyLabel("请从浏览器开发者工具中复制 Cookie 字符串，格式为 name=value; 形式")
            instruction_label.setWordWrap(True)
            card_layout.addWidget(instruction_label)
            
            self.cookie_inputs[platform_key] = LineEdit()
            self.cookie_inputs[platform_key].setPlaceholderText("输入 Cookie 字符串...")
            existing_cookies = self.cookie_manager.get_cookies(platform_key)
            if existing_cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in existing_cookies.items()])
                self.cookie_inputs[platform_key].setText(cookie_str)
            card_layout.addWidget(self.cookie_inputs[platform_key])
            
            btn_layout = QHBoxLayout()
            save_btn = PrimaryPushButton("保存")
            save_btn.clicked.connect(lambda _, p=platform_key: self._save_cookies(p))
            btn_layout.addWidget(save_btn)
            
            test_btn = PushButton("测试")
            test_btn.clicked.connect(lambda _, p=platform_key: self._test_cookies(p))
            btn_layout.addWidget(test_btn)
            
            clear_btn = PushButton("清除")
            clear_btn.clicked.connect(lambda _, p=platform_key: self._clear_cookies(p))
            btn_layout.addWidget(clear_btn)
            
            card_layout.addLayout(btn_layout)
            content_layout.addWidget(card)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        close_btn = PrimaryPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        self.setMinimumSize(500, 500)
        self.setMaximumSize(600, 700)
    
    def _parse_cookie_string(self, cookie_str: str) -> dict:
        cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                name, value = part.split('=', 1)
                cookies[name.strip()] = value.strip()
        return cookies
    
    def _save_cookies(self, platform: str):
        cookie_str = self.cookie_inputs[platform].text()
        if cookie_str:
            cookies = self._parse_cookie_string(cookie_str)
            self.cookie_manager.set_cookies(platform, cookies)
            self.platform_tabs[platform].setText("✓ 已设置")
            QMessageBox.information(self, "成功", f"已保存 {self._get_platform_name(platform)} 的 Cookie\n\n注意：Cookie 是否有效取决于 Cookie 是否过期以及是否包含必要的登录信息。")
        else:
            self.cookie_manager.clear_cookies(platform)
            self.platform_tabs[platform].setText("✗ 未设置")
            QMessageBox.information(self, "成功", f"已清除 {self._get_platform_name(platform)} 的 Cookie")
    
    def _test_cookies(self, platform: str):
        cookies = self.cookie_manager.get_cookies(platform)
        if not cookies:
            QMessageBox.warning(self, "测试失败", f"【{self._get_platform_name(platform)}】\n\n当前没有设置 Cookie，请先保存 Cookie 后再测试。")
            return
        
        platform_name = self._get_platform_name(platform)
        music_client_name = self._get_music_client_name(platform)
        
        try:
            from musicdl import musicdl
            
            os.makedirs(os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'), exist_ok=True)
            
            init_cfg = {
                music_client_name: {
                    'work_dir': os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'DoroPet', 'musicdl_outputs'),
                    'default_search_cookies': cookies,
                    'default_parse_cookies': cookies,
                }
            }
            
            music_client = musicdl.MusicClient(
                music_sources=[music_client_name],
                init_music_clients_cfg=init_cfg
            )
            
            results = music_client.search(keyword="test")
            
            if results and any(results.values()):
                QMessageBox.information(self, "测试成功", f"【{platform_name}】\n\n✓ Cookie 配置有效！\n✓ 共获取到 {sum(len(songs) for songs in results.values())} 首测试歌曲。")
            else:
                QMessageBox.warning(self, "测试结果", f"【{platform_name}】\n\n⚠ Cookie 配置可能有效，但没有返回结果。\n⚠ 可能需要更长的登录 Cookie（包含登录 token）。")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"【{platform_name}】\n\n✗ 测试过程中发生错误：\n{str(e)}")
    
    def _clear_cookies(self, platform: str):
        self.cookie_manager.clear_cookies(platform)
        self.cookie_inputs[platform].clear()
        self.platform_tabs[platform].setText("✗ 未设置")
        QMessageBox.information(self, "成功", f"已清除 {self._get_platform_name(platform)} 的 Cookie")
    
    def _get_platform_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_name
        return platform
    
    def _get_music_client_name(self, platform: str) -> str:
        for p_key, p_name, p_client in self.platforms:
            if p_key == platform:
                return p_client
        return platform
