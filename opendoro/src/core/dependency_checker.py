import sys
import os
import re
import subprocess
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DependencyMismatch:
    package_name: str
    required_version: str
    installed_version: str
    operator: str


@dataclass
class DependencyCheckResult:
    success: bool
    mismatches: List[DependencyMismatch]
    missing_packages: List[str]
    error_message: Optional[str] = None


def parse_requirements_file(requirements_path: str) -> Dict[str, Tuple[str, str]]:
    """
    解析 requirements.txt 文件，返回包名和版本要求的字典
    返回格式: {package_name: (operator, version)}
    """
    requirements = {}
    
    if not os.path.exists(requirements_path):
        return requirements
    
    with open(requirements_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*([=<>!~]+)\s*([^\s;#]+)', line)
            if match:
                package_name = match.group(1).lower()
                operator = match.group(2)
                version = match.group(3)
                requirements[package_name] = (operator, version)
            elif re.match(r'^[a-zA-Z0-9_-]+$', line):
                package_name = line.lower()
                requirements[package_name] = ('', '')
    
    return requirements


def get_installed_version(package_name: str) -> Optional[str]:
    """
    获取已安装包的版本
    """
    try:
        if sys.version_info >= (3, 8):
            from importlib.metadata import version, PackageNotFoundError
            try:
                normalized_name = package_name.replace('-', '_').lower()
                return version(normalized_name)
            except PackageNotFoundError:
                return None
        else:
            import pkg_resources
            try:
                return pkg_resources.get_distribution(package_name).version
            except pkg_resources.DistributionNotFound:
                return None
    except Exception:
        return None


def compare_versions(version1: str, version2: str, operator: str) -> bool:
    """
    比较两个版本号
    """
    try:
        from packaging import version as pkg_version
        
        v1 = pkg_version.parse(version1)
        v2 = pkg_version.parse(version2)
        
        if operator == '==':
            return v1 == v2
        elif operator == '>=':
            return v1 >= v2
        elif operator == '<=':
            return v1 <= v2
        elif operator == '>':
            return v1 > v2
        elif operator == '<':
            return v1 < v2
        elif operator == '~=':
            return v1 >= v2 and v1.release[:2] == v2.release[:2]
        elif operator == '!=':
            return v1 != v2
        else:
            return True
    except Exception:
        return True


def check_dependencies(requirements_path: str = None) -> DependencyCheckResult:
    """
    检查所有依赖库版本是否匹配
    
    Args:
        requirements_path: requirements.txt 文件路径，默认为 main.py 同目录下的 requirements.txt
    
    Returns:
        DependencyCheckResult: 检查结果
    """
    try:
        if requirements_path is None:
            main_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(main_dir))
            requirements_path = os.path.join(project_root, 'requirements.txt')
        
        if not os.path.exists(requirements_path):
            return DependencyCheckResult(
                success=True,
                mismatches=[],
                missing_packages=[],
                error_message=None
            )
        
        required_packages = parse_requirements_file(requirements_path)
        mismatches = []
        missing_packages = []
        
        for package_name, (operator, required_version) in required_packages.items():
            installed_version = get_installed_version(package_name)
            
            if installed_version is None:
                missing_packages.append(package_name)
            elif operator and required_version:
                if not compare_versions(installed_version, required_version, operator):
                    mismatches.append(DependencyMismatch(
                        package_name=package_name,
                        required_version=f"{operator}{required_version}",
                        installed_version=installed_version,
                        operator=operator
                    ))
        
        success = len(mismatches) == 0 and len(missing_packages) == 0
        
        return DependencyCheckResult(
            success=success,
            mismatches=mismatches,
            missing_packages=missing_packages,
            error_message=None
        )
        
    except Exception as e:
        return DependencyCheckResult(
            success=True,
            mismatches=[],
            missing_packages=[],
            error_message=f"依赖检查过程中发生错误: {str(e)}"
        )


def format_dependency_error(result: DependencyCheckResult) -> str:
    """
    格式化依赖错误信息
    """
    lines = []
    lines.append("=" * 60)
    lines.append("依赖库版本检查失败")
    lines.append("=" * 60)
    lines.append("")
    
    if result.mismatches:
        lines.append("以下依赖库版本不兼容:")
        lines.append("-" * 60)
        for mismatch in result.mismatches:
            lines.append(f"  {mismatch.package_name}:")
            lines.append(f"    当前安装版本: {mismatch.installed_version}")
            lines.append(f"    所需版本: {mismatch.required_version}")
        lines.append("")
    
    if result.missing_packages:
        lines.append("以下依赖库未安装:")
        lines.append("-" * 60)
        for package in result.missing_packages:
            lines.append(f"  - {package}")
        lines.append("")
    
    lines.append("解决方案:")
    lines.append("-" * 60)
    lines.append("  请运行以下命令更新依赖库:")
    lines.append("  pip install -r requirements.txt --upgrade")
    lines.append("")
    lines.append("  或者使用项目提供的安装脚本:")
    lines.append("  install_env.bat")
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def show_dependency_error_dialog(result: DependencyCheckResult):
    """
    显示依赖错误的图形界面对话框，并提供自动安装选项
    """
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton
        from PyQt5.QtCore import Qt
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        error_message = format_dependency_error(result)
        
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("依赖库版本检查失败")
        msg_box.setText("应用程序无法启动，检测到依赖库版本不兼容。")
        msg_box.setInformativeText("是否自动运行安装脚本修复依赖？")
        msg_box.setDetailedText(error_message)
        
        install_btn = msg_box.addButton("自动安装", QMessageBox.AcceptRole)
        exit_btn = msg_box.addButton("退出程序", QMessageBox.RejectRole)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                min-width: 500px;
            }
            QMessageBox QLabel {
                min-width: 450px;
            }
        """)
        msg_box.exec()
        
        if msg_box.clickedButton() == install_btn:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            install_script = os.path.join(project_root, "install_env.bat")
            
            if os.path.exists(install_script):
                subprocess.Popen(
                    ['cmd', '/c', install_script],
                    cwd=project_root,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                sys.exit(0)
            else:
                QMessageBox.critical(
                    None,
                    "错误",
                    f"找不到安装脚本：{install_script}\n请手动运行 install_env.bat"
                )
                sys.exit(1)
        else:
            sys.exit(1)
        
    except Exception as e:
        print(format_dependency_error(result))
        print(f"\n无法显示图形界面错误对话框: {e}")


def check_and_exit_on_failure(requirements_path: str = None) -> bool:
    """
    检查依赖版本，如果失败则显示错误并退出程序
    
    Args:
        requirements_path: requirements.txt 文件路径
    
    Returns:
        bool: 检查是否通过
    """
    result = check_dependencies(requirements_path)
    
    if not result.success:
        show_dependency_error_dialog(result)
        sys.exit(1)
        return False
    
    if result.error_message:
        print(f"警告: {result.error_message}")
    
    return True
