import os
import sys
import time
import requests
import tarfile
from PyQt5.QtCore import QThread, pyqtSignal

class ModelDownloader(QThread):
    progress_updated = pyqtSignal(str, int, str) # current_task, percent, speed
    download_finished = pyqtSignal(bool, str) # success, message
    
    def __init__(self, download_tasks, parent=None):
        """
        download_tasks: list of dicts with:
            - name: str (Display name)
            - filename: str (Target filename)
            - urls: list of str (Mirrors)
            - extract_to: str (Directory to extract to, optional)
        """
        super().__init__(parent)
        self.tasks = download_tasks
        self.is_cancelled = False

    def run(self):
        try:
            for task in self.tasks:
                if self.is_cancelled:
                    break
                    
                name = task.get('name', 'Unknown')
                filename = task.get('filename')
                urls = task.get('urls', [])
                extract_to = task.get('extract_to')
                
                # Check if already exists (optional, maybe check before calling)
                
                success = self.download_file(urls, filename, name)
                if not success:
                    self.download_finished.emit(False, f"Failed to download {name}")
                    return

                if extract_to and os.path.exists(filename):
                    self.progress_updated.emit(f"Extracting {name}...", 100, "")
                    try:
                        with tarfile.open(filename, "r:bz2") as tar:
                            tar.extractall(path=extract_to)
                        # Delete archive after extraction
                        os.remove(filename)
                    except Exception as e:
                        self.download_finished.emit(False, f"Failed to extract {name}: {str(e)}")
                        return

            if not self.is_cancelled:
                self.download_finished.emit(True, "All downloads completed successfully!")
            else:
                self.download_finished.emit(False, "Download cancelled.")
                
        except Exception as e:
            self.download_finished.emit(False, f"An error occurred: {str(e)}")

    def download_file(self, urls, filename, name):
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        for i, url in enumerate(urls):
            if self.is_cancelled: return False
            
            try:
                self.progress_updated.emit(f"Downloading {name} (Mirror {i+1}/{len(urls)})...", 0, "0 MB/s")
                
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, stream=True, timeout=15, headers=headers)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                wrote = 0
                start_time = time.time()
                
                with open(filename, 'wb') as f:
                    for data in response.iter_content(block_size):
                        if self.is_cancelled:
                            f.close()
                            os.remove(filename)
                            return False
                            
                        wrote += len(data)
                        f.write(data)
                        
                        if total_size > 0:
                            percent = int(wrote / total_size * 100)
                            elapsed = time.time() - start_time
                            speed_mb = wrote / (elapsed + 1e-6) / (1024 * 1024)
                            speed_str = f"{speed_mb:.2f} MB/s"
                            self.progress_updated.emit(f"Downloading {name}...", percent, speed_str)
                            
                return True
                
            except Exception as e:
                print(f"Error downloading from {url}: {e}")
                if os.path.exists(filename):
                    os.remove(filename)
                continue
                
        return False

    def cancel(self):
        self.is_cancelled = True
