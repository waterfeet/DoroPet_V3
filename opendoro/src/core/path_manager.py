"""
路径管理器 - 专门处理中文路径问题的核心模块
Path Manager - Core module for handling Chinese path issues
"""
import os
import sys
import ctypes
from pathlib import Path
from typing import Optional


class PathManager:
    """
    路径管理器类，用于统一处理所有路径相关操作
    特别优化了中文路径的支持
    """
    
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
        
        # 获取脚本所在目录（支持中文路径）
        self._script_dir = self._get_script_directory()
        
        # 初始化基础路径为项目根目录（opendoro 目录）
        # 从 src\core 向上两级到 opendoro
        self._base_dir = self.get_parent_dir(self._script_dir, levels=2)
        
        # 设置 UTF-8 编码支持（Windows）
        self._setup_windows_utf8_support()
        
    def _get_script_directory(self) -> str:
        """
        获取脚本所在目录，正确处理中文路径
        Returns the script directory, properly handling Chinese paths
        """
        try:
            # PyInstaller 打包后的路径
            if getattr(sys, 'frozen', False):
                base_path = sys.executable
                if hasattr(sys, '_MEIPASS'):
                    return sys._MEIPASS
            else:
                # 开发环境的脚本路径
                base_path = os.path.abspath(__file__)
            
            # 使用 Path 对象处理路径（更好的 Unicode 支持）
            script_dir = Path(base_path).parent.resolve()
            return str(script_dir)
            
        except Exception as e:
            # 回退方案
            return os.getcwd()
    
    def _setup_windows_utf8_support(self):
        """
        在 Windows 上设置 UTF-8 支持，解决中文路径问题
        Setup UTF-8 support on Windows for Chinese path handling
        """
        if sys.platform == 'win32':
            try:
                # 设置控制台代码页为 UTF-8 (65001)
                ctypes.windll.kernel32.SetConsoleOutputCP(65001)
                
                # 尝试设置进程默认代码页为 UTF-8（Windows 10 1903+）
                try:
                    ctypes.windll.kernel32.SetProcessDefaultLayout(0x00000004)
                except:
                    pass
                    
            except Exception as e:
                pass  # 静默失败，不影响程序运行
    
    def get_base_dir(self) -> str:
        """获取项目基础目录"""
        return self._base_dir
    
    def get_script_dir(self) -> str:
        """获取脚本所在目录"""
        return self._script_dir
    
    def join(self, *parts) -> str:
        """
        安全地连接路径，支持中文
        Safely join path parts with Chinese character support
        """
        # 使用 pathlib.Path 处理路径，确保 Unicode 支持
        if not parts:
            return self._base_dir
        
        # 如果第一个部分是绝对路径，直接使用
        if Path(parts[0]).is_absolute():
            return str(Path(*parts).resolve())
        
        # 否则相对于基础目录
        return str((Path(self._base_dir) / Path(*parts)).resolve())
    
    def get_resource_path(self, relative_path: str) -> str:
        """
        获取资源文件的绝对路径，支持中文路径
        Get absolute path to resource file with Chinese path support
        
        Args:
            relative_path: 相对于项目根目录的路径
            
        Returns:
            资源的绝对路径
        """
        # 使用 Path 对象处理，确保 Unicode 支持
        return str((Path(self._base_dir) / relative_path).resolve())
    
    def get_data_path(self, relative_path: str) -> str:
        """获取 data 目录下的路径"""
        return self.get_resource_path(os.path.join("data", relative_path))
    
    def get_models_path(self, relative_path: str) -> str:
        """获取 models 目录下的路径"""
        return self.get_resource_path(os.path.join("models", relative_path))
    
    def get_themes_path(self, relative_path: str) -> str:
        """获取 themes 目录下的路径"""
        return self.get_resource_path(os.path.join("themes", relative_path))
    
    def get_plugin_path(self, relative_path: str) -> str:
        """获取 plugin 目录下的路径"""
        return self.get_resource_path(os.path.join("plugin", relative_path))
    
    def get_tools_path(self, relative_path: str) -> str:
        """获取 tools 目录下的路径"""
        return self.get_resource_path(os.path.join("tools", relative_path))
    
    def get_runtime_path(self, relative_path: str) -> str:
        """获取 runtime 目录下的路径"""
        return self.get_resource_path(os.path.join("runtime", relative_path))
    
    def file_exists(self, path: str) -> bool:
        """
        检查文件是否存在，支持中文路径
        Check if file exists with Chinese path support
        """
        try:
            return Path(path).exists() and Path(path).is_file()
        except:
            return False
    
    def dir_exists(self, path: str) -> bool:
        """
        检查目录是否存在，支持中文路径
        Check if directory exists with Chinese path support
        """
        try:
            return Path(path).exists() and Path(path).is_dir()
        except:
            return False
    
    def ensure_dir_exists(self, path: str) -> str:
        """
        确保目录存在，如果不存在则创建，支持中文路径
        Ensure directory exists, create if not, with Chinese path support
        
        Returns:
            目录路径
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return str(Path(path).resolve())
        except Exception as e:
            raise RuntimeError(f"Failed to create directory: {path}. Error: {e}")
    
    def get_absolute_path(self, path: str) -> str:
        """
        获取绝对路径，支持中文
        Get absolute path with Chinese support
        """
        return str(Path(path).resolve())
    
    def normalize_path(self, path: str) -> str:
        """
        规范化路径（统一分隔符等），支持中文
        Normalize path (unify separators, etc.) with Chinese support
        """
        return str(Path(path).resolve())
    
    def get_parent_dir(self, path: str, levels: int = 1) -> str:
        """
        获取父目录
        Get parent directory
        
        Args:
            path: 路径
            levels: 向上几级
        """
        p = Path(path)
        for _ in range(levels):
            p = p.parent
        return str(p.resolve())
    
    def get_relative_path(self, path: str, start: Optional[str] = None) -> str:
        """
        获取相对路径
        Get relative path
        
        Args:
            path: 目标路径
            start: 起始路径（默认为 base_dir）
        """
        if start is None:
            start = self._base_dir
        
        return str(Path(path).relative_to(Path(start)))
    
    def list_dir(self, path: str, pattern: str = "*") -> list:
        """
        列出目录内容，支持中文文件名
        List directory contents with Chinese filename support
        
        Args:
            path: 目录路径
            pattern: 匹配模式（如 "*.txt"）
            
        Returns:
            文件名列表
        """
        try:
            p = Path(path)
            if pattern == "*":
                return [str(item) for item in p.iterdir()]
            else:
                return [str(item) for item in p.glob(pattern)]
        except Exception as e:
            return []
    
    def walk_dir(self, path: str, recursive: bool = True) -> list:
        """
        遍历目录，支持中文路径和文件名
        Walk through directory with Chinese path/filename support
        
        Args:
            path: 目录路径
            recursive: 是否递归遍历子目录
            
        Returns:
            文件路径列表
        """
        try:
            p = Path(path)
            if recursive:
                return [str(item) for item in p.rglob("*") if item.is_file()]
            else:
                return [str(item) for item in p.glob("*") if item.is_file()]
        except Exception as e:
            return []


# 全局单例
_path_manager: Optional[PathManager] = None


def get_path_manager() -> PathManager:
    """获取路径管理器单例"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


def resource_path(relative_path: str) -> str:
    """
    兼容旧代码的资源路径获取函数
    Legacy-compatible resource path getter
    
    Args:
        relative_path: 相对路径
        
    Returns:
        绝对路径
    """
    return get_path_manager().get_resource_path(relative_path)


# 初始化路径管理器
def initialize_path_manager():
    """初始化路径管理器（在应用启动时调用）"""
    return get_path_manager()


"""
使用示例 - Usage Examples:

1. 基本使用 - Basic Usage:
   ```python
   from src.core.path_manager import get_path_manager
   
   pm = get_path_manager()
   
   # 获取项目根目录
   base_dir = pm.get_base_dir()
   
   # 连接路径
   config_path = pm.join("data", "config.json")
   
   # 获取资源路径
   icon_path = pm.get_resource_path("data/icons/app.png")
   
   # 检查文件是否存在
   if pm.file_exists(icon_path):
       print("图标存在")
   ```

2. 获取特定目录路径 - Get Specific Directory Paths:
   ```python
   pm = get_path_manager()
   
   # Data 目录
   data_file = pm.get_data_path("icons/logo.png")
   
   # Models 目录
   model_file = pm.get_models_path("Doro/Doro.model3.json")
   
   # Themes 目录
   theme_file = pm.get_themes_path("dark.qss")
   
   # Plugin 目录
   plugin_file = pm.get_plugin_path("memo/main.py")
   
   # Tools 目录
   tool_file = pm.get_tools_path("download_model.py")
   
   # Runtime 目录
   runtime_file = pm.get_runtime_path("python.exe")
   ```

3. 目录操作 - Directory Operations:
   ```python
   pm = get_path_manager()
   
   # 确保目录存在
   save_dir = pm.ensure_dir_exists("data/saves")
   
   # 列出目录内容
   files = pm.list_dir("data/icons", "*.png")
   
   # 递归遍历目录
   all_files = pm.walk_dir("data", recursive=True)
   
   # 获取父目录
   parent = pm.get_parent_dir("/path/to/file", levels=2)
   ```

4. 兼容旧代码 - Legacy Code Compatibility:
   ```python
   # 使用新的 resource_path 函数（推荐）
   from src.core.path_manager import resource_path
   path = resource_path("data/icons/app.png")
   
   # 或使用旧的 resource_utils（仍然可用）
   from src.resource_utils import resource_path
   path = resource_path("data/icons/app.png")
   ```

5. 路径转换 - Path Conversion:
   ```python
   pm = get_path_manager()
   
   # 获取绝对路径
   abs_path = pm.get_absolute_path("./relative/path")
   
   # 规范化路径
   norm_path = pm.normalize_path(".\\mixed\\path")
   
   # 获取相对路径
   rel_path = pm.get_relative_path("/absolute/path", start="/other/path")
   ```

注意事项 - Notes:
- 所有路径操作都使用 pathlib.Path，确保 Unicode/中文支持
- 路径管理器是单例模式，多次调用 get_path_manager() 返回同一实例
- 自动处理 Windows 和 Unix 路径分隔符
- 在 Windows 上自动设置 UTF-8 代码页
"""
