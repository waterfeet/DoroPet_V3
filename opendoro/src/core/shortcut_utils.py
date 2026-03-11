import os
import subprocess
from src.core.logger import logger


def create_desktop_shortcut(shortcut_name: str = "DoroPet", replace_existing: bool = False) -> tuple[bool, str]:
    """
    在桌面创建快捷方式
    
    Args:
        shortcut_name: 快捷方式名称
        replace_existing: 是否替换已存在的快捷方式
        
    Returns:
        (success, message): 成功状态和消息
    """
    try:
        app_dir = _get_app_directory()
        if not app_dir:
            return False, "无法确定应用程序目录"
        
        bat_path = os.path.join(app_dir, "start_app_background.bat")
        icon_path = os.path.join(app_dir, "data", "icons", "app.ico")
        
        if not os.path.exists(bat_path):
            return False, f"启动脚本不存在: {bat_path}"
        
        desktop_path = _get_desktop_path()
        if not desktop_path:
            return False, "无法获取桌面路径"
        
        shortcut_path = os.path.join(desktop_path, f"{shortcut_name}.lnk")
        
        # 如果快捷方式已存在且不允许替换，返回错误
        if os.path.exists(shortcut_path) and not replace_existing:
            return False, "快捷方式已存在"
        
        icon_arg = ""
        if os.path.exists(icon_path):
            icon_arg = f'-IconLocation "{icon_path}"'
        
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{bat_path}"
$Shortcut.WorkingDirectory = "{app_dir}"
$Shortcut.Description = "DoroPet Desktop Pet"
{f'$Shortcut.IconLocation = "{icon_path}"' if os.path.exists(icon_path) else ''}
$Shortcut.Save()
'''
        
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        
        if result.returncode == 0:
            action = "创建" if not os.path.exists(shortcut_path) else "替换"
            logger.info(f"Desktop shortcut {action}: {shortcut_path}")
            return True, f"快捷方式已{action}: {shortcut_path}"
        else:
            error_msg = result.stderr.strip() if result.stderr else "未知错误"
            logger.error(f"Failed to create shortcut: {error_msg}")
            return False, f"创建快捷方式失败: {error_msg}"
            
    except Exception as e:
        logger.error(f"Error creating desktop shortcut: {e}")
        return False, f"创建快捷方式时出错: {str(e)}"


def remove_desktop_shortcut(shortcut_name: str = "DoroPet") -> tuple[bool, str]:
    """
    删除桌面快捷方式
    
    Args:
        shortcut_name: 快捷方式名称
        
    Returns:
        (success, message): 成功状态和消息
    """
    try:
        desktop_path = _get_desktop_path()
        if not desktop_path:
            return False, "无法获取桌面路径"
        
        shortcut_path = os.path.join(desktop_path, f"{shortcut_name}.lnk")
        
        if not os.path.exists(shortcut_path):
            return True, "快捷方式不存在"
        
        os.remove(shortcut_path)
        logger.info(f"Desktop shortcut removed: {shortcut_path}")
        return True, "快捷方式已删除"
        
    except Exception as e:
        logger.error(f"Error removing desktop shortcut: {e}")
        return False, f"删除快捷方式时出错: {str(e)}"


def shortcut_exists(shortcut_name: str = "DoroPet") -> bool:
    """
    检查桌面快捷方式是否存在
    
    Args:
        shortcut_name: 快捷方式名称
        
    Returns:
        是否存在
    """
    desktop_path = _get_desktop_path()
    if not desktop_path:
        return False
    
    shortcut_path = os.path.join(desktop_path, f"{shortcut_name}.lnk")
    return os.path.exists(shortcut_path)


def _get_desktop_path() -> str | None:
    """获取桌面路径"""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def _get_app_directory() -> str | None:
    """获取应用程序目录（项目根目录）"""
    try:
        current_file = os.path.abspath(__file__)
        src_core_dir = os.path.dirname(current_file)
        src_dir = os.path.dirname(src_core_dir)
        app_root = os.path.dirname(src_dir)
        return app_root
    except Exception:
        return None
