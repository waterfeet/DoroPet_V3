import os
import sys
import ast
import importlib.util
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QStackedWidget, QLabel, QMessageBox, QFrame, QListWidgetItem)
from PyQt5.QtCore import Qt
from qfluentwidgets import (SubtitleLabel, PrimaryPushButton, FluentIcon)

class PluginInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("PluginInterface")
        
        # Main Layout
        self.h_layout = QHBoxLayout(self)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.h_layout.setSpacing(0)
        
        # --- Left Panel: Plugin List ---
        self.left_panel = QFrame(self)
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setFixedWidth(250)
        # Optional: Add border/background style via QSS if needed
        self.left_panel.setStyleSheet("QFrame#leftPanel { border-right: 1px solid #E0E0E0; background-color: transparent; }")
        
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(10, 20, 10, 20)
        self.left_layout.setSpacing(10)
        
        self.lbl_title = SubtitleLabel("插件列表", self)
        
        self.btn_refresh = PrimaryPushButton("刷新插件", self)
        self.btn_refresh.setIcon(FluentIcon.SYNC)
        self.btn_refresh.clicked.connect(self.load_plugins)
        
        self.plugin_list = QListWidget()
        self.plugin_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background-color: transparent;
            }
            QListWidget::item {
                height: 35px;
                padding-left: 10px;
            }
            QListWidget::item:selected {
                background-color: #009FAA;
                color: white;
                border-radius: 4px;
            }
            QListWidget::item:hover:!selected {
                background-color: #F0F0F0;
                border-radius: 4px;
            }
        """)
        self.plugin_list.currentRowChanged.connect(self.on_plugin_selected)
        
        self.left_layout.addWidget(self.lbl_title)
        self.left_layout.addWidget(self.btn_refresh)
        self.left_layout.addWidget(self.plugin_list)
        
        # --- Right Panel: Plugin Display Area ---
        self.right_panel = QStackedWidget(self)
        self.right_panel.setStyleSheet("background-color: transparent;")
        
        # Default Welcome Page
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_lbl = SubtitleLabel("请从左侧选择一个插件", self.welcome_widget)
        welcome_lbl.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(welcome_lbl)
        self.right_panel.addWidget(self.welcome_widget)
        
        # Add panels to main layout
        self.h_layout.addWidget(self.left_panel)
        self.h_layout.addWidget(self.right_panel)
        
        self.loaded_plugins = {} # filename/plugin_id -> widget instance
        
        # Initial Load
        self.load_plugins()

    def get_plugin_name(self, file_path):
        """
        Parses the python file to find 'class Plugin' and its 'name' attribute.
        Returns the name if found, otherwise None.
        Using AST to avoid executing code.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == "Plugin":
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "name":
                                    if isinstance(item.value, ast.Constant): # Python 3.8+
                                        return item.value.value
                                    elif isinstance(item.value, ast.Str): # Python 3.7
                                        return item.value.s
        except Exception:
            pass # Fail silently and use fallback
        return None

    def load_plugins(self):
        """Scans the ./plugin directory and populates the list."""
        self.plugin_list.clear()
        
        # Note: We don't clear right_panel widgets here to preserve state if possible,
        # or we could clear them to force reload. Let's clear for now to ensure updates apply.
        # But clearing widgets is tricky if they are active.
        # Simple approach: Clear internal cache, let user re-click to re-load.
        self.loaded_plugins = {}
            
        plugin_dir = os.path.join(os.getcwd(), "plugin")
        if not os.path.exists(plugin_dir):
            try:
                os.makedirs(plugin_dir)
            except Exception as e:
                self.show_error(f"无法创建插件目录: {e}")
                return
            
        # Scan for plugins
        valid_plugins = []
        try:
            items = os.listdir(plugin_dir)
            for item in items:
                item_path = os.path.join(plugin_dir, item)
                
                # Case 1: Directory based plugin (must have main.py)
                if os.path.isdir(item_path):
                    main_py = os.path.join(item_path, "main.py")
                    if os.path.exists(main_py):
                        valid_plugins.append({
                            "type": "dir",
                            "name": item,
                            "path": item_path,
                            "entry": main_py
                        })
                        
                # Case 2: Legacy single file plugin
                elif item.endswith(".py") and item != "__init__.py":
                    valid_plugins.append({
                        "type": "file",
                        "name": item,
                        "path": item_path,
                        "entry": item_path
                    })

            # Sort by directory/filename first
            valid_plugins.sort(key=lambda x: x["name"])
            
            for p in valid_plugins:
                display_name = self.get_plugin_name(p["entry"])
                if not display_name:
                    display_name = p["name"] # Fallback to filename/dirname
                
                list_item = QListWidgetItem(display_name)
                # Store the plugin info in UserRole
                list_item.setData(Qt.UserRole, p)
                self.plugin_list.addItem(list_item)
                
            if not valid_plugins:
                self.plugin_list.addItem("暂无插件")
                self.plugin_list.item(0).setFlags(Qt.NoItemFlags) # Disable selection
        except Exception as e:
            self.show_error(f"扫描插件目录失败: {e}")

    def on_plugin_selected(self, row):
        if row < 0:
            return
            
        item = self.plugin_list.item(row)
        # Check if it's the placeholder
        if item.flags() & Qt.NoItemFlags:
            return

        plugin_info = item.data(Qt.UserRole)
        if not plugin_info:
            return
            
        plugin_id = plugin_info["name"] # Use directory/filename as unique ID
        
        # If already loaded, show it
        if plugin_id in self.loaded_plugins:
            try:
                self.right_panel.setCurrentWidget(self.loaded_plugins[plugin_id])
                return
            except RuntimeError:
                # Widget might have been deleted
                del self.loaded_plugins[plugin_id]

        # Load module dynamically
        try:
            entry_point_file = plugin_info["entry"]
            module_name_suffix = ""
            
            if plugin_info["type"] == "dir":
                module_name_suffix = f"{plugin_info['name']}.main"
            else:
                module_name_suffix = plugin_info["name"][:-3]

            # 1. Load module spec
            spec = importlib.util.spec_from_file_location(module_name_suffix, entry_point_file)
            if spec is None:
                 self.show_error(f"无法加载模块规范: {entry_point_file}")
                 return
                 
            module = importlib.util.module_from_spec(spec)
            
            # 2. Add to sys.modules (optional, but helps with imports within plugin)
            module_name = f"plugin.{module_name_suffix}"
            sys.modules[module_name] = module 
            
            # 3. Execute module
            spec.loader.exec_module(module)
            
            # 4. Look for 'Plugin' class
            if hasattr(module, "Plugin"):
                plugin_class = getattr(module, "Plugin")
                if issubclass(plugin_class, QWidget):
                    # Instantiate
                    widget = plugin_class()
                    self.right_panel.addWidget(widget)
                    self.right_panel.setCurrentWidget(widget)
                    self.loaded_plugins[plugin_id] = widget
                else:
                    self.show_error(f"Error: {plugin_info['name']} 中的 'Plugin' 类必须继承自 QWidget")
            else:
                self.show_error(f"Error: {plugin_info['name']} 未定义 'Plugin' 类")
                
        except Exception as e:
            self.show_error(f"加载插件 {plugin_info['name']} 失败:\n{str(e)}")
            import traceback
            traceback.print_exc()

    def show_error(self, message):
        """Displays an error message in the right panel."""
        error_widget = QWidget()
        layout = QVBoxLayout(error_widget)
        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: red; font-size: 14px;")
        layout.addWidget(lbl)
        
        self.right_panel.addWidget(error_widget)
        self.right_panel.setCurrentWidget(error_widget)
