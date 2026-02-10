import os
import random
import pylive2d
try:
    import psutil
except ImportError:
    psutil = None
from PyQt5.QtCore import QTimerEvent, Qt, QTimer, QSize, QSettings
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QCursor, QPixmap
from PyQt5.QtWidgets import QOpenGLWidget, QLabel, QMenu, QAction, QApplication
from src.ui.main_window import MainWindow
from src.resource_utils import resource_path
from qfluentwidgets import isDarkTheme

class SpeechBubble(QLabel):
    """
    自定义的气泡控件，用于显示对话文本
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if isDarkTheme():
            bg = "rgba(43, 43, 43, 240)"
            border = "#454545"
            color = "#ffffff"
        else:
            bg = "rgba(255, 255, 255, 240)"
            border = "#e5e5e5"
            color = "#000000"

        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 10px;
                padding: 10px;
                color: {color};
                font-size: 14px;
            }}
        """)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.hide()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def show_text(self, text, duration=3000):
        self.setText(text)
        self.adjustSize()
        
        max_width = 200
        if self.width() > max_width:
            self.setFixedWidth(max_width)
            self.adjustSize()

        self.show()
        self.hide_timer.start(duration)

    def fade_out(self):
        self.hide()


class Live2DWidget(QOpenGLWidget):
    def __init__(self, *args, path: str, parent=None, **kwargs) -> None:
        self.path = path
        if not os.path.exists(path):
            self.path = resource_path("models/Doro/Doro.model3.json")

        super().__init__(parent)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        
        self.bubble = SpeechBubble(self)
        self.main_window = None 

        # 初始化列表，防止在GL初始化前访问报错
        self.expression_ids = []
        self.motion_ids = []
        
        # 锁定状态
        self.is_locked = False

        # Load and apply settings
        self.settings = QSettings("DoroPet", "Settings")
        
        # Scale
        scale_val = self.settings.value("scale", 100, type=int)
        base_w, base_h = 550, 500
        self.resize(int(base_w * scale_val / 100.0), int(base_h * scale_val / 100.0))
        
        # Bubble duration
        self.default_bubble_duration = self.settings.value("bubble_duration", 3000, type=int)
        
        # Mouse interact (locked)
        mouse_interact = self.settings.value("mouse_interact", True, type=bool)
        self.is_locked = not mouse_interact
        
        if self.is_locked:
            self.setMouseTracking(False)
            self.setCursor(Qt.ArrowCursor)
        else:
            # --- 【新增】初始化自定义鼠标 ---
            # 请将下面的路径替换为你自己的图片路径 (支持 png, jpg 等)
            self.init_custom_cursor(resource_path("data/icons/orange.ico"))

    def initializeGL(self) -> None:
        self.makeCurrent()
        self.model = pylive2d.Model(self.path, self.width(), self.height())
        self.expression_ids = self.model.expression_ids()
        self.motion_ids = self.model.motion_ids()
        self.refresh = self.startTimer(15)
        
        # 初始化系统监控
        self.init_system_monitor()

    def paintGL(self) -> None:
        self.model.draw(self.width(), self.height())

    def set_locked(self, locked: bool):
        """设置锁定状态"""
        self.is_locked = locked
        if locked:
            # 锁定被动：取消所有鼠标追踪，重置视线
            self.setMouseTracking(False)
            self.setCursor(Qt.ArrowCursor) # 或者隐藏鼠标？通常锁定后恢复普通鼠标
            # 重置视线到中心
            center_x = self.width() / 2
            center_y = self.height() / 2
            self.model.set_dragging(center_x, center_y)
            print(f"Locked at: {center_x, center_y}")
            self.update()
            self.talk("已锁定位置，解除请右键托盘图标~", 3000)
        else:
            self.setMouseTracking(True)
            # 恢复自定义鼠标（如果需要）
            self.init_custom_cursor(resource_path("data/icons/orange.ico"))
            self.talk("解锁啦！又可以一起玩了~", 3000)

    def timerEvent(self, event: QTimerEvent | None):
        if event.timerId() == self.refresh:
            if not self.is_locked:
                # 全屏鼠标跟随逻辑
                # 获取全局鼠标位置并转换为局部坐标
                global_pos = QCursor.pos()
                local_pos = self.mapFromGlobal(global_pos)
                self.model.set_dragging(local_pos.x(), local_pos.y())
            else:
                # 锁定时持续强制视线回到中心
                center_x = self.width() / 2
                center_y = self.height() / 2
                self.model.set_dragging(center_x, center_y)
            
            self.update()

    def talk(self, text: str, duration: int = None):
        # 如果设置了全局时长，优先使用
        if hasattr(self, 'default_bubble_duration'):
            duration = self.default_bubble_duration
        elif duration is None:
            duration = 4000
            
        self.bubble.show_text(text, duration)
        bubble_x = (self.width() - self.bubble.width()) // 2
        bubble_y = 50 
        bubble_x = max(0, bubble_x)
        bubble_y = max(0, bubble_y)
        self.bubble.move(bubble_x, bubble_y)

    # --- 【新增】自定义鼠标逻辑方法 ---
    def init_custom_cursor(self, image_path):
        """
        设置自定义鼠标样式
        :param image_path: 鼠标图片路径
        """
        if os.path.exists(image_path):
            # 1. 加载图片
            pixmap = QPixmap(image_path)
            
            # 2. 调整大小 (可选)
            # 鼠标图片通常不宜过大，一般建议 32x32 或 48x48
            target_size = QSize(32, 32) 
            pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # 3. 创建 Cursor 对象
            # QCursor(pixmap, hotX, hotY)
            # hotX, hotY 是鼠标点击的"热点"坐标。
            # -1, -1 表示中心，0, 0 表示左上角。
            # 如果你的图片是普通箭头，用 0, 0；如果是准心或手掌，可能需要 pixmap.width()/2
            cursor = QCursor(pixmap, 0, 0)
            
            # 4. 应用到当前控件
            self.setCursor(cursor)
        else:
            print(f"警告: 未找到鼠标图片 {image_path}，将使用默认鼠标。")
            self.setCursor(Qt.ArrowCursor)


    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        
        if isDarkTheme():
            style = """
                QMenu {
                    background-color: #2b2b2b;
                    border: 1px solid #454545;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 24px 6px 12px;
                    border-radius: 4px;
                    color: #ffffff;
                    margin: 2px;
                }
                QMenu::item:selected {
                    background-color: rgba(255, 255, 255, 0.06);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #454545;
                    margin: 4px;
                }
            """
        else:
            style = """
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e5e5e5;
                    border-radius: 8px;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 24px 6px 12px;
                    border-radius: 4px;
                    color: #000000;
                    margin: 2px;
                }
                QMenu::item:selected {
                    background-color: rgba(0, 0, 0, 0.06);
                }
                QMenu::separator {
                    height: 1px;
                    background-color: #e5e5e5;
                    margin: 4px;
                }
            """
        menu.setStyleSheet(style)

        action_talk = QAction("打个招呼", self)
        action_talk.triggered.connect(lambda: self.talk("你好呀！我是你的桌面宠物。", 3000))
        menu.addAction(action_talk)
        
        # --- 原有的随机表情 ---
        action_exp = QAction("随机表情", self)
        action_exp.triggered.connect(self.random_expression)
        menu.addAction(action_exp)

        # ==========================================
        # 【新增功能】指定表情子菜单
        # ==========================================
        if self.expression_ids:
            exp_menu = QMenu("切换表情", self)
            for exp_name in self.expression_ids:
                # 注意：这里使用 lambda 的默认参数 (name=exp_name) 来捕获循环变量
                action = QAction(str(exp_name), self)
                action.triggered.connect(lambda checked, name=exp_name: self.model.set_expression(name))
                exp_menu.addAction(action)
            menu.addMenu(exp_menu)

        # ==========================================
        # 【新增功能】指定动作子菜单
        # ==========================================
        if self.motion_ids:
            motion_menu = QMenu("播放动作", self)
            for motion_group in self.motion_ids:
                action = QAction(str(motion_group), self)
                #  pylive2d 的 set_motion 参数为 (id, sound_file = '', priority = 3)
                action.triggered.connect(lambda checked, group=motion_group: self.model.set_motion(group))
                motion_menu.addAction(action)
            menu.addMenu(motion_menu)
        
        menu.addSeparator()

        action_reset = QAction("重置大小", self)
        action_reset.triggered.connect(lambda: self.resize(550, 500))
        menu.addAction(action_reset)

        action_open_ui = QAction("打开主界面", self)
        action_open_ui.triggered.connect(self.open_main_window)
        menu.addAction(action_open_ui)

        # --- 【新增功能】镜像翻转 ---
        # action_mirror = QAction("左右镜像", self)
        # action_mirror.setCheckable(True)
        # action_mirror.setChecked(getattr(self, "is_mirrored", False))
        # action_mirror.triggered.connect(self.toggle_mirror)
        # menu.addAction(action_mirror)

        menu.addSeparator()

        action_quit = QAction("退出", self)
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        menu.exec_(global_pos)

    def open_main_window(self):
        if self.main_window is None:
            self.main_window = MainWindow()
            self.main_window.set_live2d_widget(self)
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    # def toggle_mirror(self, checked):
    #     self.is_mirrored = checked
    #     scale_x = -1.0 if checked else 1.0
    #     if hasattr(self.model, "set_scale"):
    #         self.model.set_scale(scale_x, 1.0)  # 实际上并没有这个函数
    #     else:
    #         print("set_scale not available in pylive2d.Model")

    # --- 【新增】交互逻辑 ---
    def on_click(self, x, y):
        """处理点击事件"""
        # 获取点击区域
        hit_area = self.model.hit_area(x, y)
        print(f"Hit Area (Native): '{hit_area}'") # Debug console

        # 优先尝试触发“摸摸”动作
        # motion_ids 中的名称格式通常为 "GroupName_Index" (例如 "摸摸_0")
        touch_motions = [m for m in self.motion_ids if m.startswith("摸摸_")]
        
        # 兼容性：如果没有找到中文"摸摸"，尝试找"Touch"
        if not touch_motions:
            touch_motions = [m for m in self.motion_ids if m.lower().startswith("touch_")]
        
        # 根据点击区域做出不同反应
        if hit_area == "Face":
            # 点击 Face -> 投喂欧润吉
            responses = [
                "谢谢‘人’的欧润吉！好甜呀~", 
                "啊呜~ 欧润吉最好吃啦！", 
                "还要更多欧润吉！", 
                "欧润吉补充能量中... 滴！"
            ]
            self.talk(random.choice(responses), 3000)
            
            # 投喂时随机切换一个开心表情
            happy_exps = ["星星眼", "吐舌", "默认"]
            # 过滤出存在的表情
            available_happy = [e for e in happy_exps if e in self.expression_ids]
            if available_happy:
                self.model.set_expression(random.choice(available_happy))

        elif hit_area == "Body":
             # 点击身体 -> 概率触发表情对话，或者普通摸摸
            
            # 60% 概率触发表情对话
            if random.random() < 0.6 and self.expression_ids:
                # 定义表情与对话的映射
                exp_dialogues = {
                    "星星眼": ["哇！这是什么好东西？", "眼睛里有星星哦~", "好期待呀！"],
                    "吐舌": ["略略略~", "不告诉你~", "皮一下很开心！"],
                    "黑脸": ["哼，人又乱摸了...", "谁戳我了？", "奇怪的感觉..."],
                    "无语": ["...", "我竟无言以对。", "认真点好吗？"],
                    "感叹号": ["被发现了！", "吓我一跳！", "有新情况！"],
                    "问号": ["嗯？你说什么？", "我不太明白...", "这是为什么呢？"],
                    "墨镜": ["我是最酷的！", "墨镜一戴，谁都不爱~", "Cool~"],
                    "袋子": ["你看不到我...", "我是个袋子。", "潜伏中..."],
                    "思考": ["让我想想...", "这个问题很深奥。", "唔..."],
                    "失去高光": ["累了...", "感觉身体被掏空...", "不想动了..."]
                }
                
                # 筛选出当前模型实际拥有的表情
                available_map = {k:v for k,v in exp_dialogues.items() if k in self.expression_ids}
                
                if available_map:
                    # 随机选一个表情
                    chosen_exp = random.choice(list(available_map.keys()))
                    self.model.set_expression(chosen_exp)
                    
                    # 说对应的话
                    dialogues = available_map[chosen_exp]
                    self.talk(random.choice(dialogues), 3000)
                    return
            
            # 如果没触发表情对话，或者没有可用表情，执行摸摸动作
            if touch_motions:
                motion_name = random.choice(touch_motions)
                self.model.set_motion(motion_name)
                responses = ["那是我的肚子吗~", "人，在干什么呢？", "嘿嘿好痒呀~"]
                self.talk(random.choice(responses), 2000)

        elif hit_area in ["Head", "Hair"]: 
            # 如果点击头部/头发
            if touch_motions:
                motion_name = random.choice(touch_motions)
                self.model.set_motion(motion_name)
                # 随机触发对话
                responses = ["好痒呀~", "在干嘛呢？", "摸摸头~"]
                self.talk(random.choice(responses), 2000)
            else:
                self.random_expression()
                self.talk("干嘛盯着我看？", 2000)

        else:
            # 其他情况（未命中特定区域），不做反应，或者只在调试时打印
            pass

    def init_system_monitor(self):
        """初始化系统资源监控"""
        if psutil:
            self.monitor_timer = QTimer(self)
            self.monitor_timer.timeout.connect(self.check_system_status)
            self.monitor_timer.start(30000) # 每30秒检查一次
    
    def check_system_status(self):
        """检查系统状态并触发反应"""
        if not psutil: return
        
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            if cpu > 80:
                self.talk(f"CPU好烫 ({cpu}%)！我要融化了...", 4000)
                if "失去高光" in self.expression_ids:
                    self.model.set_expression("失去高光")
            elif mem > 90:
                self.talk(f"内存快满了 ({mem}%)！", 4000)
                if "无语" in self.expression_ids:
                    self.model.set_expression("无语")
        except Exception as e:
            print(f"System monitor error: {e}")

    def random_expression(self):
        if self.expression_ids:
            idx = random.randrange(0, len(self.expression_ids))
            self.model.set_expression(self.expression_ids[idx])

    # --- 交互事件区域 ---

    def wheelEvent(self, event: QWheelEvent):
        if self.is_locked: return
        delta = event.angleDelta().y()
        step = 0.05
        if delta > 0:
            zoom_factor = 1 + step 
        else:
            zoom_factor = 1 - step

        current_rect = self.geometry()
        old_width = current_rect.width()
        old_height = current_rect.height()

        new_width = int(old_width * zoom_factor)
        new_height = int(old_height * zoom_factor)

        if new_width < 200 or new_width > 1500:
            return

        dx = (new_width - old_width) // 2
        dy = (new_height - old_height) // 2

        new_x = current_rect.x() - dx
        new_y = current_rect.y() - dy

        self.setGeometry(new_x, new_y, new_width, new_height)
        self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent | None):
        if self.is_locked: return
        if event and event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.drag_start_global = event.globalPos() # 记录拖拽起点
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent | None):
        """双击打开主界面"""
        if self.is_locked: return
        if event and event.button() == Qt.LeftButton:
            self.open_main_window()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent | None):
        if self.is_locked: return
        if event:
            if event.buttons() & Qt.LeftButton and hasattr(self, "drag_position"):
                self.move(event.globalPos() - self.drag_position)
            # self.model.set_dragging(event.x(), event.y()) # Moved to timerEvent for global tracking
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None):
        if self.is_locked: return
        if not event:
            return
            
        # 判断是否是点击（移动距离很小）
        is_click = False
        if hasattr(self, "drag_start_global"):
            dist = (event.globalPos() - self.drag_start_global).manhattanLength()
            if dist < 5: # 移动小于5像素视为点击
                is_click = True
            else:
                # 拖拽结束，检查边缘吸附
                self.check_edge_docking()

            del self.drag_start_global

        if hasattr(self, "drag_position"):
            del self.drag_position
            
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())
        elif event.button() == Qt.LeftButton and is_click:
            self.on_click(event.x(), event.y())
            
        event.accept()

    def check_edge_docking(self):
        """检查并执行边缘吸附逻辑"""
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        
        # 窗口当前位置和大小
        rect = self.geometry()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        
        # 阈值：靠近边缘多少像素时触发吸附
        threshold = 30
        
        # 吸附后的露头宽度（只露出脑袋）
        # 假设脑袋在左边，大约占宽度的1/3或1/4
        peek_width = w // 3
        
        # 1. 右侧吸附
        # 如果窗口右边缘靠近屏幕右边缘
        if abs((x + w) - (screen_geo.x() + screen_geo.width())) < threshold:
            # 吸附到右侧，只留 peek_width 在屏幕内
            target_x = screen_geo.x() + screen_geo.width() - peek_width
            self.animate_move(target_x, y)
            self.is_docked = "right"
            self.normal_geometry = rect # 保存吸附前的位置（如果需要恢复）
            self.dock_hidden_offset = w - peek_width
            
        # 2. 左侧吸附 (暂时只做右侧，因为左侧需要翻转模型才自然)
        # 如果需要左侧吸附，可以类似处理
        # elif abs(x - screen_geo.x()) < threshold: ...
        
        # 3. 顶部吸附 (可选)
        # elif abs(y - screen_geo.y()) < threshold: ...

        else:
            self.is_docked = None

    def animate_move(self, target_x, target_y):
        """简单的移动动画（这里先直接移动，后续可加 QPropertyAnimation）"""
        self.move(target_x, target_y)

    def enterEvent(self, event):
        """鼠标移入：如果是吸附状态，弹出来"""
        if hasattr(self, "is_docked") and self.is_docked == "right":
            # 恢复完全显示
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            target_x = screen_geo.x() + screen_geo.width() - self.width()
            self.animate_move(target_x, self.y())
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标移出：如果是吸附状态，缩回去"""
        if hasattr(self, "is_docked") and self.is_docked == "right":
            # 缩回去，只露头
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            peek_width = self.width() // 3 # 保持一致
            target_x = screen_geo.x() + screen_geo.width() - peek_width
            self.animate_move(target_x, self.y())
        super().leaveEvent(event)