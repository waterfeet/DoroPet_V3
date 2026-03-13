import sys
import os
import time

try:
    import requests
except ImportError:
    print("Error: 'requests' library is missing. Please ensure requirements are installed.")
    sys.exit(1)

def download_file(urls, filename):
    # If urls is a single string, convert to list
    if isinstance(urls, str):
        urls = [urls]
        
    print(f"Target file: {os.path.basename(filename)}")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    
    for i, url in enumerate(urls):
        print(f"Attempt {i+1}/{len(urls)}: {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # Stream=True is important for large files
            response = requests.get(url, stream=True, timeout=15, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192 # 8KB
            wrote = 0
            start_time = time.time()
            
            with open(filename, 'wb') as f:
                for data in response.iter_content(block_size):
                    wrote += len(data)
                    f.write(data)
                    
                    # Progress bar
                    if total_size > 0:
                        percent = wrote / total_size * 100
                        bar_len = 40
                        filled_len = int(bar_len * wrote // total_size)
                        bar = '█' * filled_len + '-' * (bar_len - filled_len)
                        
                        elapsed = time.time() - start_time
                        speed = wrote / (elapsed + 1e-6) / (1024 * 1024) # MB/s
                        
                        # \r to overwrite line
                        sys.stdout.write(f'\r[{bar}] {percent:.1f}% | {wrote/(1024*1024):.1f}/{total_size/(1024*1024):.1f} MB | {speed:.2f} MB/s')
                        sys.stdout.flush()
                    else:
                        # If no content-length
                        sys.stdout.write(f'\rDownloaded: {wrote/(1024*1024):.1f} MB')
                        sys.stdout.flush()
                        
            print() # New line after done
            print("Download complete.")
            return True
            
        except KeyboardInterrupt:
            print("\nDownload canceled by user.")
            if os.path.exists(filename):
                os.remove(filename)
            return False
        except Exception as e:
            print(f"\nError downloading from {url}: {e}")
            if os.path.exists(filename):
                os.remove(filename)
            print("Trying next mirror...")
            continue
            
    print("All download attempts failed.")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python download_model.py <filename> <url1> [url2] [url3] ...")
        sys.exit(1)
        
    filename = sys.argv[1]
    urls = sys.argv[2:]
    
    if not download_file(urls, filename):
        sys.exit(1)
