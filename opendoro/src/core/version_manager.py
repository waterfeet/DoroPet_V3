import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable
from enum import Enum
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import requests
from bs4 import BeautifulSoup
from src.core.logger import logger


__version__ = "3.2.6"
__app_name__ = "DoroPet"

GITEE_API_BASE = "https://gitee.com/api/v5"
GITEE_REPO_OWNER = "waterfeet"
GITEE_REPO_NAME = "DoroPet_V3"
GITEE_RELEASES_URL = "https://gitee.com/waterfeet/DoroPet_V3/releases"
GITEE_BASE_URL = "https://gitee.com"

WEB_CRAWLER_MAX_RETRIES = 3
WEB_CRAWLER_RETRY_DELAY = 2
WEB_CRAWLER_TIMEOUT = 30


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
    asset_name: str = ""
    
    def __post_init__(self):
        if isinstance(self.release_type, str):
            self.release_type = ReleaseType(self.release_type)
    
    @property
    def version_tuple(self) -> tuple:
        try:
            parts = self.version.lstrip('v').split('.')
            return tuple(map(int, parts))
        except (ValueError, AttributeError):
            return (0, 0, 0)
    
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
    try:
        p1 = v1.lstrip('v').split('.')
        p2 = v2.lstrip('v').split('.')
        t1 = tuple(map(int, p1))
        t2 = tuple(map(int, p2))
        
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
    except (ValueError, AttributeError):
        return 0


def parse_release_type_from_tag(tag: str) -> ReleaseType:
    tag_lower = tag.lower()
    if 'alpha' in tag_lower:
        return ReleaseType.ALPHA
    elif 'beta' in tag_lower:
        return ReleaseType.BETA
    return ReleaseType.STABLE


class GiteeWebCrawlerWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, parent=None, max_retries: int = WEB_CRAWLER_MAX_RETRIES):
        super().__init__(parent)
        self._max_retries = max_retries
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        logger.info("[WebCrawler] Starting version fetch via web crawler")
        
        for attempt in range(1, self._max_retries + 1):
            if self._is_cancelled:
                logger.info("[WebCrawler] Request cancelled by user")
                self.error.emit("请求已取消")
                return
            
            try:
                logger.debug(f"[WebCrawler] Attempt {attempt}/{self._max_retries}")
                versions = self._fetch_releases_with_retry(attempt)
                if versions:
                    logger.info(f"[WebCrawler] Successfully fetched {len(versions)} versions")
                    self.finished.emit(versions)
                    return
            except requests.exceptions.Timeout:
                error_msg = f"请求超时 (尝试 {attempt}/{self._max_retries})"
                logger.warning(f"[WebCrawler] {error_msg}")
                if attempt < self._max_retries:
                    time.sleep(WEB_CRAWLER_RETRY_DELAY)
                    continue
                self.error.emit("请求超时，请检查网络连接")
                return
            except requests.exceptions.ConnectionError as e:
                error_msg = f"网络连接失败 (尝试 {attempt}/{self._max_retries})"
                logger.warning(f"[WebCrawler] {error_msg}: {e}")
                if attempt < self._max_retries:
                    time.sleep(WEB_CRAWLER_RETRY_DELAY)
                    continue
                self.error.emit("网络连接失败，请检查网络设置")
                return
            except Exception as e:
                error_msg = f"获取版本信息失败: {str(e)}"
                logger.error(f"[WebCrawler] Error on attempt {attempt}: {e}")
                if attempt < self._max_retries:
                    time.sleep(WEB_CRAWLER_RETRY_DELAY)
                    continue
                self.error.emit(error_msg)
                return
        
        self.error.emit("获取版本信息失败，已达到最大重试次数")
    
    def _fetch_releases_with_retry(self, attempt: int) -> List[VersionInfo]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://gitee.com/',
            'Cache-Control': 'no-cache'
        }
        
        logger.debug(f"[WebCrawler] Fetching URL: {GITEE_RELEASES_URL}")
        response = requests.get(
            GITEE_RELEASES_URL, 
            timeout=WEB_CRAWLER_TIMEOUT, 
            headers=headers,
            allow_redirects=True
        )
        
        if response.status_code == 403:
            raise PermissionError("服务器访问受限(403)，可能是由于请求频率限制")
        elif response.status_code == 404:
            raise FileNotFoundError("未找到版本仓库页面")
        
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        logger.debug(f"[WebCrawler] Response status: {response.status_code}, length: {len(response.text)}")
        
        versions = self._parse_releases_html(response.text)
        
        if not versions:
            logger.warning("[WebCrawler] No versions found via standard parsing, trying fallback")
            versions = self._fallback_parse(response.text)
        
        versions.sort(key=lambda v: v.version_tuple, reverse=True)
        return versions
    
    def _parse_releases_html(self, html: str) -> List[VersionInfo]:
        versions = []
        seen_versions = set()
        soup = BeautifulSoup(html, 'html.parser')
        
        release_items = soup.select('.release-list-item, .release-item, .release__item')
        
        if not release_items:
            release_items = soup.select('div.release')
        
        if not release_items:
            release_items = soup.find_all('div', class_=re.compile(r'release[-_]?item|release[-_]?entry', re.I))
        
        if not release_items:
            all_links = soup.find_all('a', href=re.compile(r'/releases/'))
            for link in all_links:
                href = link.get('href', '')
                version_match = re.search(r'/releases/(v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)', href)
                if version_match:
                    version = version_match.group(1).lstrip('v')
                    if version not in seen_versions and re.match(r'^\d+\.\d+\.\d+', version):
                        seen_versions.add(version)
                        parent = link.find_parent('div', class_=re.compile(r'release|version|item', re.I))
                        changelog = ""
                        release_date = ""
                        if parent:
                            changelog = self._extract_changelog_from_element(parent)
                            release_date = self._extract_date_from_element(parent)
                        versions.append(VersionInfo(
                            version=version,
                            release_type=parse_release_type_from_tag(version),
                            release_date=release_date,
                            changelog=changelog or "暂无更新说明",
                            download_url=f"{GITEE_RELEASES_URL}/{version}",
                            file_size=0,
                            asset_name=""
                        ))
            return versions
        
        logger.debug(f"[WebCrawler] Found {len(release_items)} release items")
        
        for item in release_items:
            if self._is_cancelled:
                break
            try:
                version_info = self._parse_single_release(item)
                if version_info and version_info.version not in seen_versions:
                    seen_versions.add(version_info.version)
                    versions.append(version_info)
            except Exception as e:
                logger.debug(f"[WebCrawler] Failed to parse release item: {e}")
                continue
        
        return versions
    
    def _extract_changelog_from_element(self, element) -> str:
        changelog_selectors = [
            '.markdown-body', '.release-body', '.description', 
            '.content', '.release-content', '.notes'
        ]
        for selector in changelog_selectors:
            desc_elem = element.select_one(selector)
            if desc_elem:
                text = desc_elem.get_text('\n', strip=True)
                text = re.sub(r'\n{3,}', '\n\n', text)
                return text[:1000]
        
        text_content = element.get_text('\n', strip=True)
        lines = text_content.split('\n')
        content_lines = []
        skip_patterns = [
            r'^\s*$', r'^下载', r'^Assets', r'^\d+\s*(KB|MB|GB|B)',
            r'^最后提交', r'^提交', r'^\.zip', r'^http',
            r'^Source code', r'^\(', r'^\)'
        ]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if any(re.match(p, line, re.I) for p in skip_patterns):
                continue
            if re.match(r'^v?\d+\.\d+\.\d+', line):
                continue
            content_lines.append(line)
            if len(content_lines) >= 10:
                break
        
        return '\n'.join(content_lines)[:1000] if content_lines else ""
    
    def _extract_date_from_element(self, element) -> str:
        date_selectors = ['time', '.date', '.release-date', '.time']
        for selector in date_selectors:
            date_elem = element.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}-\d{2}-\d{2})', date_text)
                if date_match:
                    return date_match.group(1)
                if date_text and len(date_text) < 30:
                    return date_text
        
        text = element.get_text()
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{4}/\d{2}/\d{2})',
            r'(\d{4}年\d{1,2}月\d{1,2}日)'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return ""
    
    def _parse_single_release(self, item) -> Optional[VersionInfo]:
        version = ""
        changelog = ""
        download_url = ""
        file_size = 0
        asset_name = ""
        release_date = ""
        
        title_elem = item.select_one('.release-title a, .title a, h3 a, a[href*="/releases/"], .release__title a, .release-name')
        if title_elem:
            version = title_elem.get_text(strip=True)
        
        if not version:
            version_elem = item.select_one('.release-tag, .tag, .version, .release__tag')
            if version_elem:
                version = version_elem.get_text(strip=True)
        
        if not version:
            link_elem = item.find('a', href=re.compile(r'/releases/'))
            if link_elem:
                href = link_elem.get('href', '')
                version_match = re.search(r'/releases/(v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)', href)
                if version_match:
                    version = version_match.group(1)
        
        if not version:
            return None
        
        version = version.lstrip('v')
        
        if not re.match(r'^\d+\.\d+\.\d+', version):
            return None
        
        changelog = self._extract_changelog_from_element(item)
        release_date = self._extract_date_from_element(item)
        
        download_link = item.select_one('a[href$=".zip"], a[href*="download"], a.btn-download')
        if download_link:
            href = download_link.get('href', '')
            if href:
                if href.startswith('/'):
                    download_url = GITEE_BASE_URL + href
                elif href.startswith('http'):
                    download_url = href
                else:
                    download_url = GITEE_BASE_URL + '/' + href
                
                asset_name = href.split('/')[-1] if '/' in href else href
        
        size_elem = item.select_one('.file-size, .size')
        if size_elem:
            size_text = size_elem.get_text(strip=True)
            file_size = self._parse_file_size(size_text)
        
        return VersionInfo(
            version=version,
            release_type=parse_release_type_from_tag(version),
            release_date=release_date,
            changelog=changelog or "暂无更新说明",
            download_url=download_url,
            file_size=file_size,
            asset_name=asset_name
        )
    
    def _parse_file_size(self, size_text: str) -> int:
        size_text = size_text.upper().strip()
        match = re.match(r'([\d.]+)\s*(KB|MB|GB|B)?', size_text, re.I)
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = (match.group(2) or 'B').upper()
        
        multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        return int(value * multipliers.get(unit, 1))
    
    def _fallback_parse(self, html: str) -> List[VersionInfo]:
        versions = []
        seen_versions = set()
        soup = BeautifulSoup(html, 'html.parser')
        
        release_sections = soup.find_all(['div', 'section', 'article'], class_=re.compile(r'release|version|update', re.I))
        
        for section in release_sections:
            version = ""
            
            version_elem = section.find(['h1', 'h2', 'h3', 'h4', 'a', 'span'], string=re.compile(r'v?\d+\.\d+\.\d+', re.I))
            if version_elem:
                version_match = re.search(r'v?(\d+\.\d+\.\d+(?:-[a-zA-Z]+)?)', version_elem.get_text(), re.I)
                if version_match:
                    version = version_match.group(1)
            
            if not version:
                link_elem = section.find('a', href=re.compile(r'/releases/'))
                if link_elem:
                    href = link_elem.get('href', '')
                    version_match = re.search(r'/releases/(v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)', href)
                    if version_match:
                        version = version_match.group(1).lstrip('v')
            
            if not version:
                continue
            
            if version in seen_versions:
                continue
            seen_versions.add(version)
            
            changelog = self._extract_changelog_from_element(section)
            release_date = self._extract_date_from_element(section)
            
            download_url = ""
            download_link = section.find('a', href=re.compile(r'\.zip$|download', re.I))
            if download_link:
                href = download_link.get('href', '')
                if href.startswith('/'):
                    download_url = GITEE_BASE_URL + href
                elif href.startswith('http'):
                    download_url = href
            
            versions.append(VersionInfo(
                version=version,
                release_type=parse_release_type_from_tag(version),
                release_date=release_date,
                changelog=changelog or "暂无更新说明",
                download_url=download_url or f"{GITEE_RELEASES_URL}/{version}",
                file_size=0,
                asset_name=""
            ))
        
        if not versions:
            all_links = soup.find_all('a', href=re.compile(r'/releases/'))
            for link in all_links:
                href = link.get('href', '')
                version_match = re.search(r'/releases/(v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9]+)?)', href)
                if version_match:
                    version = version_match.group(1).lstrip('v')
                    if version not in seen_versions and re.match(r'^\d+\.\d+\.\d+', version):
                        seen_versions.add(version)
                        versions.append(VersionInfo(
                            version=version,
                            release_type=parse_release_type_from_tag(version),
                            release_date="",
                            changelog="暂无更新说明",
                            download_url=f"{GITEE_RELEASES_URL}/{version}",
                            file_size=0,
                            asset_name=""
                        ))
        
        logger.debug(f"[WebCrawler] Fallback parse found {len(versions)} versions")
        return versions


class GiteeApiWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, owner: str, repo: str, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self._is_cancelled = False
    
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        logger.info("[API] Starting version fetch via Gitee API")
        
        try:
            url = f"{GITEE_API_BASE}/repos/{self.owner}/{self.repo}/releases"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://gitee.com/'
            }
            
            logger.debug(f"[API] Fetching URL: {url}")
            response = requests.get(url, timeout=15, headers=headers, allow_redirects=True)
            
            if self._is_cancelled:
                logger.info("[API] Request cancelled by user")
                self.error.emit("请求已取消")
                return
            
            if response.status_code == 403:
                logger.warning("[API] Server returned 403 Forbidden")
                self.error.emit("服务器访问受限(403)，可能是由于请求频率限制。请稍后重试。")
                return
            elif response.status_code == 404:
                logger.warning("[API] Repository not found (404)")
                self.error.emit("未找到版本仓库")
                return
            
            response.raise_for_status()
            
            releases = response.json()
            versions = []
            
            for release in releases:
                if self._is_cancelled:
                    break
                    
                if release.get('draft'):
                    continue
                
                zip_asset = None
                for asset in release.get('assets', []):
                    if asset.get('name', '').endswith('.zip'):
                        zip_asset = asset
                        break
                
                if not zip_asset:
                    continue
                
                tag_name = release.get('tag_name', '').lstrip('v')
                if not tag_name:
                    continue
                
                release_date = release.get('created_at', '')
                if release_date:
                    try:
                        dt = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S%z')
                        release_date = dt.strftime('%Y-%m-%d')
                    except:
                        pass
                
                version_info = VersionInfo(
                    version=tag_name,
                    release_type=parse_release_type_from_tag(release.get('tag_name', '')),
                    release_date=release_date,
                    changelog=release.get('body', '无更新说明'),
                    download_url=zip_asset.get('browser_download_url', ''),
                    file_size=zip_asset.get('size', 0),
                    asset_name=zip_asset.get('name', '')
                )
                versions.append(version_info)
            
            versions.sort(key=lambda v: v.version_tuple, reverse=True)
            logger.info(f"[API] Successfully fetched {len(versions)} versions")
            self.finished.emit(versions)
            
        except requests.exceptions.Timeout:
            logger.error("[API] Request timeout")
            self.error.emit("请求超时，请检查网络连接")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[API] Connection error: {e}")
            self.error.emit("网络连接失败，请检查网络设置")
        except requests.exceptions.HTTPError as e:
            logger.error(f"[API] HTTP error: {e}")
            self.error.emit(f"服务器错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"[API] Unexpected error: {e}")
            self.error.emit(f"获取版本信息失败: {str(e)}")


class GiteeSpecificVersionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    
    def __init__(self, owner: str, repo: str, tag: str, parent=None):
        super().__init__(parent)
        self.owner = owner
        self.repo = repo
        self.tag = tag
    
    def run(self):
        try:
            url = f"{GITEE_API_BASE}/repos/{self.owner}/{self.repo}/releases/tags/{self.tag}"
            headers = {'User-Agent': 'DoroPet-Update-Checker/1.0'}
            response = requests.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            
            release = response.json()
            
            if release.get('draft'):
                self.error.emit("该版本为草稿版本")
                return
            
            zip_asset = None
            for asset in release.get('assets', []):
                if asset.get('name', '').endswith('.zip'):
                    zip_asset = asset
                    break
            
            if not zip_asset:
                self.error.emit("未找到 ZIP 格式的下载包")
                return
            
            tag_name = release.get('tag_name', '').lstrip('v')
            release_date = release.get('created_at', '')
            if release_date:
                try:
                    dt = datetime.strptime(release_date, '%Y-%m-%dT%H:%M:%S%z')
                    release_date = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            version_info = VersionInfo(
                version=tag_name,
                release_type=parse_release_type_from_tag(release.get('tag_name', '')),
                release_date=release_date,
                changelog=release.get('body', '无更新说明'),
                download_url=zip_asset.get('browser_download_url', ''),
                file_size=zip_asset.get('size', 0),
                asset_name=zip_asset.get('name', '')
            )
            
            self.finished.emit(version_info)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                self.error.emit(f"未找到版本: {self.tag}")
            else:
                self.error.emit(f"服务器错误: {e.response.status_code}")
        except requests.exceptions.Timeout:
            self.error.emit("请求超时，请检查网络连接")
        except requests.exceptions.ConnectionError:
            self.error.emit("网络连接失败，请检查网络设置")
        except Exception as e:
            self.error.emit(f"获取版本信息失败: {str(e)}")


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int, int, str)
    completed = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, version: VersionInfo, save_dir: str, parent=None):
        super().__init__(parent)
        self.version = version
        self.save_dir = save_dir
        self._is_cancelled = False
    
    def run(self):
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            
            filename = self.version.asset_name or f"DoroPet_v{self.version.version}.zip"
            file_path = os.path.join(self.save_dir, filename)
            
            url = self.version.download_url
            headers = {'User-Agent': 'DoroPet-Update-Downloader/1.0'}
            
            self.progress.emit(0, self.version.file_size, "正在连接...")
            
            response = requests.get(url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', self.version.file_size))
            downloaded = 0
            block_size = 8192
            
            start_time = time.time()
            last_progress_time = start_time
            
            with open(file_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    if self._is_cancelled:
                        f.close()
                        os.remove(file_path)
                        self.error.emit("下载已取消")
                        return
                    
                    f.write(data)
                    downloaded += len(data)
                    
                    current_time = time.time()
                    if current_time - last_progress_time >= 0.1:
                        if total_size > 0:
                            percent = int(downloaded / total_size * 100)
                        else:
                            percent = 0
                        
                        elapsed = current_time - start_time
                        if elapsed > 0:
                            speed = downloaded / elapsed / (1024 * 1024)
                            speed_str = f"{speed:.2f} MB/s"
                        else:
                            speed_str = "计算中..."
                        
                        self.progress.emit(percent, total_size, speed_str)
                        last_progress_time = current_time
            
            self.progress.emit(100, total_size, "下载完成")
            logger.info(f"Download completed: {file_path}")
            self.completed.emit(file_path)
            
        except requests.exceptions.Timeout:
            self.error.emit("下载超时，请重试")
        except requests.exceptions.ConnectionError:
            self.error.emit("网络连接中断")
        except Exception as e:
            self.error.emit(f"下载失败: {str(e)}")
    
    def cancel(self):
        self._is_cancelled = True


class UpdateInstallWorker(QThread):
    progress = pyqtSignal(str, int)
    completed = pyqtSignal()
    error = pyqtSignal(str)
    
    STEP_EXTRACT = 10
    STEP_PREPARE = 30
    STEP_COPY = 60
    STEP_FINALIZE = 90
    STEP_DONE = 100
    
    def __init__(self, zip_path: str, version: str, parent=None):
        super().__init__(parent)
        self.zip_path = zip_path
        self.version = version
        self._is_cancelled = False
        
        self.app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_root = os.path.dirname(self.app_dir)
        self.temp_dir = tempfile.gettempdir()
    
    def run(self):
        try:
            self.progress.emit("正在解压更新包...", self.STEP_EXTRACT)
            
            extract_dir = os.path.join(self.temp_dir, f"DoroPet_Update_{self.version}")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                zf.extractall(extract_dir)
            
            if self._is_cancelled:
                shutil.rmtree(extract_dir)
                self.error.emit("安装已取消")
                return
            
            self.progress.emit("正在准备安装...", self.STEP_PREPARE)
            
            items = os.listdir(extract_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                source_dir = os.path.join(extract_dir, items[0])
            else:
                source_dir = extract_dir
            
            self.progress.emit("正在复制文件...", self.STEP_COPY)
            
            python_exe = sys.executable
            main_script = os.path.join(self.app_dir, "main.py")
            restart_cmd = f'start "" /b "{python_exe}" "{main_script}"'
            
            script_content = f'''@echo off
chcp 65001 >nul
set "SOURCE={source_dir}"
set "TARGET={self.project_root}"

timeout /t 3 /nobreak >nul

xcopy "%SOURCE%\\*" "%TARGET%\\" /E /Y /I /Q >nul 2>&1

if %errorlevel% neq 0 (
    exit /b 1
)

{restart_cmd}

exit /b 0
'''
            
            script_path = os.path.join(self.temp_dir, "DoroPet_Updater.bat")
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            if self._is_cancelled:
                os.remove(script_path)
                shutil.rmtree(extract_dir)
                self.error.emit("安装已取消")
                return
            
            self.progress.emit("正在完成安装...", self.STEP_FINALIZE)
            
            subprocess.Popen(
                ['cmd', '/c', script_path],
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            )
            
            self.progress.emit("安装完成，即将重启...", self.STEP_DONE)
            self.completed.emit()
            
        except zipfile.BadZipFile:
            self.error.emit("更新包文件损坏，请重新下载")
        except PermissionError:
            self.error.emit("权限不足，无法写入文件")
        except Exception as e:
            logger.error(f"Install failed: {e}")
            self.error.emit(f"安装失败: {str(e)}")
    
    def cancel(self):
        self._is_cancelled = True


class UpdateInstaller:
    def __init__(self):
        self.app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.project_root = os.path.dirname(self.app_dir)
        self.temp_dir = tempfile.gettempdir()
    
    def prepare_installation(self, zip_path: str, version: str) -> str:
        extract_dir = os.path.join(self.temp_dir, f"DoroPet_Update_{version}")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir)
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        items = os.listdir(extract_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            source_dir = os.path.join(extract_dir, items[0])
        else:
            source_dir = extract_dir
        
        return source_dir
    
    def create_updater_script(self, source_dir: str, target_dir: str, restart_cmd: str, silent: bool = True) -> str:
        if silent:
            script_content = f'''@echo off
chcp 65001 >nul
set "SOURCE={source_dir}"
set "TARGET={target_dir}"

timeout /t 2 /nobreak >nul

xcopy "%SOURCE%\\*" "%TARGET%\\" /E /Y /I /Q >nul 2>&1

if %errorlevel% neq 0 (
    exit /b 1
)

{restart_cmd}

exit /b 0
'''
        else:
            script_content = f'''@echo off
chcp 65001 >nul
echo ========================================
echo   DoroPet 自动更新程序
echo ========================================
echo.

set "SOURCE={source_dir}"
set "TARGET={target_dir}"

echo 正在等待程序退出...
timeout /t 2 /nobreak >nul

echo 正在复制文件...
xcopy "%SOURCE%\\*" "%TARGET%\\" /E /Y /I

if %errorlevel% neq 0 (
    echo.
    echo 更新失败！请手动下载更新包。
    pause
    exit /b 1
)

echo.
echo 更新完成！
echo 正在启动程序...

{restart_cmd}

exit /b 0
'''
        script_path = os.path.join(self.temp_dir, "DoroPet_Updater.bat")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return script_path
    
    def execute_update(self, zip_path: str, version: str, silent: bool = True) -> bool:
        try:
            source_dir = self.prepare_installation(zip_path, version)
            
            python_exe = sys.executable
            main_script = os.path.join(self.app_dir, "main.py")
            
            if silent:
                restart_cmd = f'start "" /b "{python_exe}" "{main_script}"'
            else:
                restart_cmd = f'cd /d "{self.app_dir}" & "{python_exe}" "{main_script}"'
            
            script_path = self.create_updater_script(source_dir, self.project_root, restart_cmd, silent)
            
            if silent:
                subprocess.Popen(
                    ['cmd', '/c', script_path],
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                )
            else:
                subprocess.Popen(
                    ['cmd', '/c', script_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to prepare update: {e}")
            return False


class VersionManager(QObject):
    check_completed = pyqtSignal(object)
    versions_loaded = pyqtSignal(list)
    load_error = pyqtSignal(str)
    download_progress = pyqtSignal(int, int, str)
    download_completed = pyqtSignal(str)
    download_error = pyqtSignal(str)
    install_progress = pyqtSignal(str, int)
    install_completed = pyqtSignal()
    install_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_version = __version__
        self._versions: List[VersionInfo] = []
        self._cached_versions: List[VersionInfo] = []
        self._crawler_worker: Optional[GiteeWebCrawlerWorker] = None
        self._api_worker: Optional[GiteeApiWorker] = None
        self._download_worker: Optional[UpdateDownloadWorker] = None
        self._install_worker: Optional[UpdateInstallWorker] = None
        self._installer = UpdateInstaller()
        self._current_download_version: VersionInfo = None
        self._auto_install = True
        self._fetch_method = "crawler"
    
    def get_current_version(self) -> str:
        return self.current_version
    
    def fetch_remote_versions(self):
        logger.info(f"[VersionManager] Starting version fetch using method: {self._fetch_method}")
        self._start_crawler_fetch()
    
    def _start_crawler_fetch(self):
        if self._crawler_worker and self._crawler_worker.isRunning():
            self._crawler_worker.cancel()
            self._crawler_worker.wait()
        
        self._crawler_worker = GiteeWebCrawlerWorker(self)
        self._crawler_worker.finished.connect(self._on_crawler_success)
        self._crawler_worker.error.connect(self._on_crawler_error)
        self._crawler_worker.start()
    
    def _on_crawler_success(self, versions: List[VersionInfo]):
        logger.info(f"[VersionManager] Web crawler fetch successful, got {len(versions)} versions")
        self._versions = versions
        self._cached_versions = versions.copy()
        self.versions_loaded.emit(versions)
    
    def _on_crawler_error(self, error_msg: str):
        logger.warning(f"[VersionManager] Web crawler failed: {error_msg}, falling back to API")
        self._start_api_fetch()
    
    def _start_api_fetch(self):
        if self._api_worker and self._api_worker.isRunning():
            self._api_worker.cancel()
            self._api_worker.wait()
        
        self._api_worker = GiteeApiWorker(GITEE_REPO_OWNER, GITEE_REPO_NAME, self)
        self._api_worker.finished.connect(self._on_api_success)
        self._api_worker.error.connect(self._on_api_error)
        self._api_worker.start()
    
    def _on_api_success(self, versions: List[VersionInfo]):
        logger.info(f"[VersionManager] API fetch successful, got {len(versions)} versions")
        self._versions = versions
        self._cached_versions = versions.copy()
        self.versions_loaded.emit(versions)
    
    def _on_api_error(self, error_msg: str):
        logger.warning(f"[VersionManager] API fetch failed: {error_msg}")
        
        if self._cached_versions:
            logger.info("[VersionManager] Using cached versions as fallback")
            self._versions = self._cached_versions
            self.versions_loaded.emit(self._versions)
        else:
            logger.info("[VersionManager] No cached versions, using hardcoded fallback")
            self._versions = self._get_fallback_versions()
            self.load_error.emit(error_msg)
            self.versions_loaded.emit(self._versions)
    
    def fetch_specific_version(self, tag: str, callback: Callable[[Optional[VersionInfo]], None]):
        worker = GiteeSpecificVersionWorker(GITEE_REPO_OWNER, GITEE_REPO_NAME, tag, self)
        
        def on_finished(version_info):
            callback(version_info)
        
        def on_error(msg):
            logger.error(f"Failed to fetch version {tag}: {msg}")
            callback(None)
        
        worker.finished.connect(on_finished)
        worker.error.connect(on_error)
        worker.start()
    
    def _on_versions_loaded(self, versions: List[VersionInfo]):
        self._versions = versions
        self.versions_loaded.emit(versions)
    
    def _on_load_error(self, error_msg: str):
        self.load_error.emit(error_msg)
        if not self._versions:
            self._versions = self._get_fallback_versions()
            self.versions_loaded.emit(self._versions)
    
    def get_all_versions(self) -> List[VersionInfo]:
        if not self._versions:
            if self._cached_versions:
                self._versions = self._cached_versions
            else:
                self._versions = self._get_fallback_versions()
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
    
    def download_update(self, version: VersionInfo, save_dir: str, auto_install: bool = True):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
            self._download_worker.wait()
        
        self._current_download_version = version
        self._auto_install = auto_install
        
        self._download_worker = UpdateDownloadWorker(version, save_dir, self)
        self._download_worker.progress.connect(self.download_progress.emit)
        self._download_worker.completed.connect(self._on_download_completed)
        self._download_worker.error.connect(self.download_error.emit)
        self._download_worker.start()
    
    def _on_download_completed(self, file_path: str):
        self.download_completed.emit(file_path)
        
        if self._auto_install and self._current_download_version:
            self.start_installation(file_path, self._current_download_version)
    
    def start_installation(self, zip_path: str, version: VersionInfo):
        if self._install_worker and self._install_worker.isRunning():
            self._install_worker.cancel()
            self._install_worker.wait()
        
        self._install_worker = UpdateInstallWorker(zip_path, version.version, self)
        self._install_worker.progress.connect(self.install_progress.emit)
        self._install_worker.completed.connect(self._on_install_completed)
        self._install_worker.error.connect(self.install_error.emit)
        self._install_worker.start()
    
    def _on_install_completed(self):
        self.install_completed.emit()
    
    def install_update(self, zip_path: str, version: VersionInfo) -> bool:
        return self._installer.execute_update(zip_path, version.version)
    
    def cancel_download(self):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.cancel()
            logger.info("Download cancelled")
    
    def cancel_installation(self):
        if self._install_worker and self._install_worker.isRunning():
            self._install_worker.cancel()
            logger.info("Installation cancelled")
    
    def cancel_fetch(self):
        if self._crawler_worker and self._crawler_worker.isRunning():
            self._crawler_worker.cancel()
            logger.info("Crawler fetch cancelled")
        if self._api_worker and self._api_worker.isRunning():
            self._api_worker.cancel()
            logger.info("API fetch cancelled")
    
    def _get_fallback_versions(self) -> List[VersionInfo]:
        return [
            VersionInfo(
                version="3.1.0",
                release_type=ReleaseType.STABLE,
                release_date=datetime.now().strftime('%Y-%m-%d'),
                changelog="当前版本\n\n无法连接到更新服务器，请检查网络连接。",
                download_url="",
                file_size=0,
                asset_name=""
            ),
        ]


def format_changelog(changelog: str) -> str:
    return changelog


def get_version_type_display(release_type: ReleaseType) -> str:
    type_map = {
        ReleaseType.STABLE: "正式版",
        ReleaseType.BETA: "测试版",
        ReleaseType.ALPHA: "开发版"
    }
    return type_map.get(release_type, "未知")
