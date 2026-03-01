import os
import random
import pylive2d
try:
    import psutil
except ImportError:
    psutil = None
from PyQt5.QtCore import QTimerEvent, Qt, QTimer, QSize, QSettings, QPoint
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QCursor, QPixmap, QPainter, QPainterPath, QColor, QPen, QBrush
from PyQt5.QtWidgets import QOpenGLWidget, QLabel, QMenu, QAction, QApplication, QStyleOption, QStyle, QProgressBar, QWidget
from src.ui.main_window import MainWindow
from src.resource_utils import resource_path
from qfluentwidgets import isDarkTheme
from src.core.pet_attributes_manager import PetAttributesManager
from src.core.pet_constants import ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS
from src.ui.pet_status_overlay import PetStatusOverlay

class SpeechBubble(QLabel):
    """
    自定义的气泡控件，用于显示对话文本
    """
    def __init__(self, parent=None):
        super().__init__(None) # 设置为无父对象，使其成为独立顶层窗口
        self.owner = parent
        self.setObjectName("speechBubble")
        
        # 设置窗口标志：无边框 | 置顶 | 工具窗口(不在任务栏显示)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating) # 显示时不抢占焦点
        
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        
        # 设置内容边距，留出气泡尾巴的空间 (左, 上, 右, 下)
        self.setContentsMargins(15, 15, 15, 30)
        
        # 设置样式
        self.setStyleSheet("color: black; font-family: 'Microsoft YaHei'; font-size: 14px; font-weight: bold;")
        
        self.hide()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def show_text(self, text, duration=3000):
        self.setText(text)
        self.adjustSize()
        
        max_width = 250
        if self.width() > max_width:
            self.setFixedWidth(max_width)
            self.adjustSize()

        self.show()
        self.hide_timer.start(duration)

    def fade_out(self):
        self.hide()

    def paintEvent(self, event):
        """
        绘制漫画风格的气泡
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 气泡样式配置
        bg_color = QColor(255, 255, 255)
        border_color = QColor(0, 0, 0)
        border_width = 3
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        # 留给尾巴的高度 (需与 setContentsMargins 的底部边距配合)
        tail_height = 15
        # 气泡主体的高度
        body_h = h - tail_height
        
        # 调整绘制区域，避免边框被裁剪
        margin = border_width / 2
        
        path = QPainterPath()
        
        # 圆角半径
        r = 10
        
        # --- 绘制路径 (顺时针) ---
        
        # 1. 左上角起点
        path.moveTo(margin + r, margin)
        
        # 2. 上边
        path.lineTo(w - margin - r, margin)
        
        # 3. 右上圆角
        path.quadTo(w - margin, margin, w - margin, margin + r)
        
        # 4. 右边
        path.lineTo(w - margin, body_h - margin - r)
        
        # 5. 右下圆角
        path.quadTo(w - margin, body_h - margin, w - margin - r, body_h - margin)
        
        # 6. 底部 (含尾巴)
        tail_width = 20
        # tail_x_center = w / 2  # 居中
        tail_x_center = w / 3    # 偏左 1/3
        
        # 右底边 -> 尾巴右侧
        path.lineTo(tail_x_center + tail_width / 2, body_h - margin)
        # 尾巴尖端 (指向下方)
        path.lineTo(tail_x_center, h - margin)
        # 尾巴左侧
        path.lineTo(tail_x_center - tail_width / 2, body_h - margin)
        
        # 左底边
        path.lineTo(margin + r, body_h - margin)
        
        # 7. 左下圆角
        path.quadTo(margin, body_h - margin, margin, body_h - margin - r)
        
        # 8. 左边
        path.lineTo(margin, margin + r)
        
        # 9. 左上圆角
        path.quadTo(margin, margin, margin + r, margin)
        
        path.closeSubpath()
        
        # 绘制
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        # 绘制文本
        super().paintEvent(event)


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

        # ==================== 属性管理系统 ====================
        self.attr_manager = PetAttributesManager()
        
        # 属性浮窗
        self.status_overlay = PetStatusOverlay(self.attr_manager, None)
        self.status_overlay.hide()
        
        # 连接属性信号
        self.attr_manager.status_changed.connect(self._on_status_changed)
        self.attr_manager.interaction_triggered.connect(self._on_interaction_triggered)
        
        # 启动属性衰减定时器
        self.attr_manager.start_decay_timer(60000)
        # ====================================================

        # Load and apply settings
        self.settings = QSettings("DoroPet", "Settings")
        
        # Show pet status overlay setting (default hidden, show via context menu)
        # show_pet_status setting controls whether it can be shown via menu
        
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

    def set_locked(self, locked: bool, silent: bool = False):
        """设置锁定状态"""
        self.is_locked = locked
        if locked:
            # 锁定被动：取消鼠标追踪（防止窗口拖拽），但视线跟随在 timerEvent 中继续
            self.setMouseTracking(False)
            self.setCursor(Qt.ArrowCursor) 
            self.update()
            if not silent:
                self.talk("已锁定位置，解除请右键托盘图标~", 3000)
        else:
            self.setMouseTracking(True)
            # 恢复自定义鼠标（如果需要）
            self.init_custom_cursor(resource_path("data/icons/orange.ico"))
            if not silent:
                self.talk("解锁啦！又可以一起玩了~", 3000)

    def timerEvent(self, event: QTimerEvent | None):
        if event.timerId() == self.refresh:
            # 无论锁定与否，都执行鼠标跟随
            # 获取全局鼠标位置
            global_pos = QCursor.pos()
            
            # 获取窗口中心点的全局坐标
            center_local = QPoint(self.width() // 2, self.height() // 2)
            center_global = self.mapToGlobal(center_local)
            
            # 计算鼠标相对于窗口中心的偏移量
            dx = global_pos.x() - center_global.x()
            dy = global_pos.y() - center_global.y()
            
            # 获取屏幕尺寸 (用于归一化映射)
            screen = QApplication.screenAt(global_pos)
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.geometry()
            
            # 计算最大可能的偏移量 (使用屏幕尺寸的一半作为参考)
            max_dx = screen_geo.width() / 2
            max_dy = screen_geo.height() / 2
            
            # 计算归一化比例 (-1.0 到 1.0)
            ratio_x = max(-1.0, min(1.0, dx / max_dx))
            ratio_y = max(-1.0, min(1.0, dy / max_dy))
            
            # 映射回模型内部坐标系
            # 模型通常以窗口中心为基准，范围是窗口宽高
            # 映射公式: target = center + ratio * (width / 2)
            target_x = center_local.x() + ratio_x * (self.width() / 2)
            target_y = center_local.y() + ratio_y * (self.height() / 2)
            
            self.model.set_dragging(target_x, target_y)
            self.update()

    def talk(self, text: str, duration: int = None):
        # 如果设置了全局时长，优先使用
        if hasattr(self, 'default_bubble_duration'):
            duration = self.default_bubble_duration
        elif duration is None:
            duration = 4000
            
        self.bubble.show_text(text, duration)
        self.update_bubble_position()

    def update_bubble_position(self):
        """更新气泡位置，使其跟随模型并在上方显示"""
        if not self.bubble.isVisible(): return
        
        # 计算全局位置
        global_pos = self.mapToGlobal(QPoint(0, 0))
        
        # 水平居中
        x = global_pos.x() + (self.width() - self.bubble.width()) // 2
        
        # 放置在模型上方 (预留20px间距)
        y = global_pos.y() - self.bubble.height() - 20
        
        # 边界检查：如果超出屏幕顶部，则放置在模型内部顶部
        screen = QApplication.screenAt(global_pos)
        if not screen: screen = QApplication.primaryScreen()
        
        if y < screen.availableGeometry().top():
            y = global_pos.y() + 20
            
        self.bubble.move(x, y)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'bubble'):
            self.update_bubble_position()
        if hasattr(self, 'status_overlay'):
            self.status_overlay.follow_pet(
                self.mapToGlobal(QPoint(0, 0)),
                self.size()
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'bubble'):
            self.bubble.hide()

    def closeEvent(self, event):
        super().closeEvent(event)
        if hasattr(self, 'bubble'):
            self.bubble.close()

        # ==================== 属性管理系统 ====================
        if hasattr(self, 'attr_manager'):
            self.attr_manager.stop_decay_timer()
        # ====================================================

    # ==================== 属性管理系统 ====================
    def _on_status_changed(self, attr_name: str, new_status: str, old_status: str):
        """属性状态变化时触发表情"""
        if new_status == "critical":
            if attr_name == ATTR_HUNGER:
                self.talk("好饿啊...我要饿晕了...", 4000)
                if "失去高光" in self.expression_ids:
                    self.model.set_expression("失去高光")
            elif attr_name == ATTR_MOOD:
                self.talk("好难过啊...", 3000)
                if "黑脸" in self.expression_ids:
                    self.model.set_expression("黑脸")
            elif attr_name == ATTR_CLEANLINESS:
                self.talk("身上好脏啊...", 3000)
            elif attr_name == "energy":
                self.talk("好困啊...", 3000)
                if "困" in self.expression_ids:
                    self.model.set_expression("困")
        elif new_status == "warning":
            if attr_name == ATTR_HUNGER:
                if random.random() < 0.3:
                    self.talk("有点饿了...", 2500)
                    if "感叹号" in self.expression_ids:
                        self.model.set_expression("感叹号")
            elif attr_name == ATTR_MOOD:
                if random.random() < 0.2:
                    self.talk("有点无聊...", 2500)

    def _on_interaction_triggered(self, attr_name: str, interaction_type: str):
        """互动反馈：触发对话和动作"""
        responses = {
            "feed": [
                "谢谢投喂！好好吃~",
                "啊呜~ 太美味了！",
                "还要更多！",
                "补充能量中...滴！"
            ],
            "play": [
                "太好玩了！",
                "再陪我玩会儿嘛~",
                "开心！",
                "哈哈好痒！"
            ],
            "clean": [
                "洗香香啦~",
                "好干净！",
                "舒服~",
                "闪闪发光！"
            ],
            "rest": [
                "休息中...",
                "充能中...",
                "zzz...",
                "精神多了！"
            ]
        }
        
        if interaction_type in responses:
            self.talk(random.choice(responses[interaction_type]), 3000)
            
            if interaction_type in ["play", "feed"]:
                happy_exps = ["星星眼", "吐舌", "默认"]
                available_happy = [e for e in happy_exps if e in self.expression_ids]
                if available_happy:
                    self.model.set_expression(random.choice(available_happy))
            
            if self.motion_ids:
                self.model.set_motion(random.choice(self.motion_ids))
    
    def feed_pet(self, food_name: str = "欧润吉"):
        """投喂宠物（兼容旧接口）"""
        self.attr_manager.perform_interaction("feed")
    # ====================================================

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
        # Theme handling is now done via global QSS

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
        
        action_show_status = QAction("隐藏属性栏" if self.status_overlay.isVisible() else "显示属性栏", self)
        action_show_status.triggered.connect(self._toggle_status_overlay)
        menu.addAction(action_show_status)

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

    def _toggle_status_overlay(self):
        show_pet_status = self.settings.value("show_pet_status", True, type=bool)
        if not show_pet_status:
            return
        
        if self.status_overlay.isVisible():
            self.status_overlay._fade_out()
        else:
            self.status_overlay._fade_in()

    def open_main_window(self):
        try:
            if self.main_window is None:
                self.main_window = MainWindow()
                self.main_window.set_live2d_widget(self)
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            import traceback
            traceback.print_exc()
            from src.core.logger import logger
            logger.error(f"Failed to open main window: {e}")
            logger.error(traceback.format_exc())

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
            self.feed_pet("欧润吉")

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
            self.monitor_timer.start(3000) # 每30秒检查一次
    
    def check_system_status(self):
        """检查系统状态并触发反应"""
        if not psutil: return
        
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            if cpu > 50:
                self.talk(f"CPU好烫 ({cpu}%)！我要融化了...", 4000)
                if "失去高光" in self.expression_ids:
                    self.model.set_expression("失去高光")
            elif mem > 80:
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
        """鼠标移入：如果是吸附状态则弹出来"""
        if hasattr(self, "is_docked") and self.is_docked == "right":
            screen = QApplication.screenAt(QCursor.pos())
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            target_x = screen_geo.x() + screen_geo.width() - self.width()
            self.animate_move(target_x, self.y())
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标移出：如果是吸附状态则缩回去"""
        if hasattr(self, "is_docked") and self.is_docked == "right":
            screen = QApplication.screenAt(QCursor.pos())
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            peek_width = self.width() // 3
            target_x = screen_geo.x() + screen_geo.width() - peek_width
            self.animate_move(target_x, self.y())
        super().leaveEvent(event)