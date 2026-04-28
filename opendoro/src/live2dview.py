import os
import random
import live2d.v3 as live2d
from live2d.v3 import clearBuffer
from live2d.utils.canvas import Canvas
try:
    import psutil
except ImportError:
    psutil = None
from PyQt5.QtCore import QTimerEvent, Qt, QTimer, QSettings, QPoint, QSize
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QCursor, QPixmap, QPainter, QPainterPath, QColor, QPen, QBrush
from PyQt5.QtWidgets import QOpenGLWidget, QLabel, QMenu, QAction, QApplication, QStyleOption, QStyle, QProgressBar, QWidget
from src.ui.main_window import MainWindow
from src.resource_utils import resource_path
from qfluentwidgets import isDarkTheme
from src.core.pet_attributes_manager import PetAttributesManager
from src.core.pet_constants import ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS
from src.ui.windows.pet_status_overlay import PetStatusOverlay
from src.core.mouse_chaser import MouseChaser
from src.core.random_wanderer import RandomWanderer

class SpeechBubble(QLabel):
    """
    自定义的气泡控件，用于显示对话文本
    """
    def __init__(self, parent=None):
        super().__init__(None)
        self.owner = parent
        self.setObjectName("speechBubble")
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        
        self.setContentsMargins(15, 15, 15, 30)
        
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
        
        bg_color = QColor(255, 255, 255)
        border_color = QColor(0, 0, 0)
        border_width = 3
        
        rect = self.rect()
        w = rect.width()
        h = rect.height()
        
        tail_height = 15
        body_h = h - tail_height
        
        margin = border_width / 2
        
        path = QPainterPath()
        
        r = 10
        
        path.moveTo(margin + r, margin)
        
        path.lineTo(w - margin - r, margin)
        
        path.quadTo(w - margin, margin, w - margin, margin + r)
        
        path.lineTo(w - margin, body_h - margin - r)
        
        path.quadTo(w - margin, body_h - margin, w - margin - r, body_h - margin)
        
        tail_width = 20
        tail_x_center = w / 3
        
        path.lineTo(tail_x_center + tail_width / 2, body_h - margin)
        path.lineTo(tail_x_center, h - margin)
        path.lineTo(tail_x_center - tail_width / 2, body_h - margin)
        
        path.lineTo(margin + r, body_h - margin)
        
        path.quadTo(margin, body_h - margin, margin, body_h - margin - r)
        
        path.lineTo(margin, margin + r)
        
        path.quadTo(margin, margin, margin + r, margin)
        
        path.closeSubpath()
        
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(bg_color))
        painter.drawPath(path)
        
        super().paintEvent(event)


class Live2DWidget(QOpenGLWidget):
    def __init__(self, *args, path: str, parent=None, **kwargs) -> None:
        self.path = path
        if not os.path.exists(path):
            self.path = resource_path("models/Doro/Doro.model3.json")

        super().__init__(parent)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setMouseTracking(True)
        
        format = self.format()
        format.setAlphaBufferSize(8)
        self.setFormat(format)
        
        self.bubble = SpeechBubble(self)
        self.main_window = None 

        self.expression_ids = []
        self.motion_groups = {}
        
        self.is_locked = False

        self.is_mirrored = False
        self.edge_docking_enabled = True
        
        self._border_overlay = QWidget(self)
        self._border_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._border_overlay.setStyleSheet("background: transparent;")
        self._border_opacity = 0.0
        self._border_flash_timer = QTimer(self)
        self._border_flash_timer.timeout.connect(self._fade_border)

        self.attr_manager = PetAttributesManager()
        
        self.status_overlay = PetStatusOverlay(self.attr_manager, None)
        self.status_overlay.hide()
        
        self.attr_manager.status_changed.connect(self._on_status_changed)
        self.attr_manager.interaction_triggered.connect(self._on_interaction_triggered)
        
        self.attr_manager.start_decay_timer(60000)

        self.settings = QSettings("DoroPet", "Settings")
        
        scale_val = self.settings.value("scale", 100, type=int)
        aspect_ratio_index = self.settings.value("aspect_ratio_index", 0, type=int)
        custom_width = self.settings.value("custom_aspect_width", 550, type=int)
        custom_height = self.settings.value("custom_aspect_height", 500, type=int)
        
        ASPECT_RATIOS = [
            1.0,
            4.0 / 3.0,
            3.0 / 4.0,
            16.0 / 9.0,
            9.0 / 16.0,
            16.0 / 10.0,
            10.0 / 16.0,
            -1,
        ]
        
        if aspect_ratio_index < 0 or aspect_ratio_index >= len(ASPECT_RATIOS):
            aspect_ratio_index = 0
        
        ratio = ASPECT_RATIOS[aspect_ratio_index]
        
        if ratio < 0:
            base_w, base_h = custom_width, custom_height
        else:
            base_size = 500
            if ratio >= 1:
                base_w = int(base_size * ratio)
                base_h = base_size
            else:
                base_w = base_size
                base_h = int(base_size / ratio)
        
        self.resize(int(base_w * scale_val / 100.0), int(base_h * scale_val / 100.0))
        
        self.default_bubble_duration = self.settings.value("bubble_duration", 3000, type=int)
        
        mouse_interact = self.settings.value("mouse_interact", True, type=bool)
        self.is_locked = not mouse_interact
        
        self.system_monitor_enabled = self.settings.value("system_monitor_enabled", True, type=bool)
        self.cpu_threshold = self.settings.value("cpu_threshold", 70, type=int)
        self.mem_threshold = self.settings.value("mem_threshold", 80, type=int)
        
        self.model_opacity = self.settings.value("window_opacity", 100, type=int)
        
        if self.is_locked:
            self.setMouseTracking(False)
            self.setCursor(Qt.ArrowCursor)
            self.setWindowFlag(Qt.WindowTransparentForInput, True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        else:
            self.init_custom_cursor(resource_path("data/icons/orange.ico"))

    def initializeGL(self) -> None:
        self.makeCurrent()
        
        live2d.init()
        live2d.glInit()
        
        self.model = live2d.LAppModel()
        self.model.LoadModelJson(self.path)
        self.model.Resize(self.width(), self.height())
        
        self.canvas = Canvas()
        self.canvas.SetSize(self.width(), self.height())
        self.canvas.SetOutputOpacity(self.model_opacity / 100.0)
        
        self.expression_ids = self.model.GetExpressionIds()
        self.motion_groups = self.model.GetMotionGroups()
        
        self.refresh = self.startTimer(15)
        
        self._init_mouse_chaser()
        self._init_random_wanderer()
        
        self.init_system_monitor()

    def reload_model(self, model_path: str) -> bool:
        """
        重新加载 Live2D 模型
        
        :param model_path: 模型配置文件路径 (.model3.json)
        :return: 是否加载成功
        """
        if not os.path.exists(model_path):
            print(f"Model file not found: {model_path}")
            return False
        
        try:
            self.makeCurrent()
            
            was_mirrored = self.is_mirrored
            
            if hasattr(self, 'mouse_chaser'):
                self.mouse_chaser.stop()
            if hasattr(self, 'random_wanderer'):
                self.random_wanderer.stop()
            
            self.model = live2d.LAppModel()
            self.model.LoadModelJson(model_path)
            self.model.Resize(self.width(), self.height())
            
            self.canvas = Canvas()
            self.canvas.SetSize(self.width(), self.height())
            self.canvas.SetOutputOpacity(self.model_opacity / 100.0)
            
            self.path = model_path
            
            self.expression_ids = self.model.GetExpressionIds()
            self.motion_groups = self.model.GetMotionGroups()
            
            self.is_mirrored = was_mirrored
            scale_x = -1.0 if was_mirrored else 1.0
            self.model.SetScaleX(scale_x)
            
            if hasattr(self, 'mouse_chaser'):
                self.mouse_chaser.model = self.model
            if hasattr(self, 'random_wanderer'):
                self.random_wanderer.model = self.model
            
            self.update()
            
            return True
            
        except Exception as e:
            print(f"Failed to reload model: {e}")
            return False

    def get_current_model_path(self) -> str:
        """获取当前模型路径"""
        return self.path
    
    def flash_border(self):
        """闪烁边框以提供视觉反馈"""
        self._border_opacity = 1.0
        self._border_overlay.setGeometry(0, 0, self.width(), self.height())
        self._border_overlay.show()
        self._border_overlay.raise_()
        self._fade_border()
    
    def _fade_border(self):
        """逐渐淡出边框"""
        self._border_opacity -= 0.08
        
        if self._border_opacity > 0:
            color = f"rgba(0, 180, 255, {self._border_opacity * 0.8})"
            self._border_overlay.setStyleSheet(f"""
                background: transparent;
                border: 4px solid {color};
                border-radius: 8px;
            """)
            self._border_flash_timer.start(40)
        else:
            self._border_overlay.setStyleSheet("background: transparent; border: none;")
            self._border_overlay.hide()
        
    def _init_mouse_chaser(self):
        """初始化鼠标追逐控制器"""
        self.mouse_chaser = MouseChaser(self.model, self, self.attr_manager)
        self.mouse_chaser.set_running_motion("跑")
        self.mouse_chaser.set_callbacks(
            on_direction_changed=self._on_chase_direction_changed,
            on_running_changed=self._on_chase_running_changed
        )
        # 连接能量耗尽信号，自动停止追逐模式
        self.mouse_chaser.energy_exhausted.connect(lambda: self.toggle_mouse_chase(False))
        
    def _on_chase_direction_changed(self, facing_right: bool):
        """追逐方向改变时的回调"""
        self.is_mirrored = facing_right
        scale_x = -1.0 if self.is_mirrored else 1.0
        self.model.SetScaleX(scale_x)
        self.update()
        
    def _on_chase_running_changed(self, is_running: bool):
        """追逐跑动状态改变时的回调"""
        pass
        
    def toggle_mouse_chase(self, enabled: bool = None, _internal: bool = False):
        """
        切换鼠标追逐模式
        
        :param enabled: True启用, False禁用, None切换当前状态
        :param _internal: 内部调用标志，切换模式时跳过模型重载
        """
        if not hasattr(self, 'mouse_chaser'):
            return
            
        if enabled is None:
            enabled = not self.mouse_chaser.is_active()
            
        if enabled:
            if hasattr(self, "is_docked") and self.is_docked:
                self.is_docked = None
                self._apply_dock_rotation(None)
            if self.is_random_wandering():
                self.toggle_random_wander(False, _internal=True)
            self.mouse_chaser.start()
            self.talk("来追你咯~", 2000, force=True)
        else:
            self.mouse_chaser.stop()
            self.talk("不追了不追了~", 2000, force=True)
            if not _internal:
                self.reload_model(self.path)
            
    def is_mouse_chasing(self) -> bool:
        """检查是否正在追逐鼠标"""
        if hasattr(self, 'mouse_chaser'):
            return self.mouse_chaser.is_active()
        return False

    def _init_random_wanderer(self):
        """初始化随机溜达控制器"""
        self.random_wanderer = RandomWanderer(self.model, self, self.attr_manager)
        self.random_wanderer.set_walking_motion("走")
        self.random_wanderer.set_callbacks(
            on_direction_changed=self._on_wander_direction_changed,
            on_running_changed=self._on_wander_running_changed
        )
        
    def _on_wander_direction_changed(self, facing_right: bool):
        """溜达方向改变时的回调"""
        self.is_mirrored = facing_right
        scale_x = -1.0 if self.is_mirrored else 1.0
        self.model.SetScaleX(scale_x)
        self.update()
        
    def _on_wander_running_changed(self, is_running: bool):
        """溜达跑动状态改变时的回调"""
        pass
        
    def toggle_random_wander(self, enabled: bool = None, _internal: bool = False):
        """
        切换随机溜达模式
        
        :param enabled: True启用, False禁用, None切换当前状态
        :param _internal: 内部调用标志，切换模式时跳过模型重载
        """
        if not hasattr(self, 'random_wanderer'):
            return
            
        if enabled is None:
            enabled = not self.random_wanderer.is_active()
            
        if enabled:
            if hasattr(self, "is_docked") and self.is_docked:
                self.is_docked = None
                self._apply_dock_rotation(None)
            if self.is_mouse_chasing():
                self.toggle_mouse_chase(False, _internal=True)
            self.random_wanderer.start()
        else:
            self.random_wanderer.stop()
            if not _internal:
                self.reload_model(self.path)
            
    def is_random_wandering(self) -> bool:
        """检查是否正在随机溜达"""
        if hasattr(self, 'random_wanderer'):
            return self.random_wanderer.is_active()
        return False

    def paintGL(self) -> None:
        self.model.Update()
        
        def on_draw():
            clearBuffer()
            self.model.Draw()
        
        # 清除帧缓冲区为透明
        clearBuffer(0.0, 0.0, 0.0, 0.0)
        
        if hasattr(self, 'canvas'):
            self.canvas.Draw(on_draw)
        else:
            on_draw()

    def resizeGL(self, w: int, h: int) -> None:
        if hasattr(self, 'model'):
            self.model.Resize(w, h)
        if hasattr(self, 'canvas'):
            self.canvas.SetSize(w, h)
    
    def set_model_opacity(self, opacity: float) -> None:
        """设置模型透明度"""
        if hasattr(self, 'canvas'):
            self.canvas.SetOutputOpacity(opacity)

    def set_locked(self, locked: bool, silent: bool = False):
        """设置锁定状态"""
        self.is_locked = locked
        
        was_visible = self.isVisible()
        
        if locked:
            self.setMouseTracking(False)
            self.setCursor(Qt.ArrowCursor)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.setWindowFlag(Qt.WindowTransparentForInput, True)
            if not silent:
                self.talk("已锁定位置，解除请右键托盘图标~", 3000)
        else:
            self.setMouseTracking(True)
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.setWindowFlag(Qt.WindowTransparentForInput, False)
            self.init_custom_cursor(resource_path("data/icons/orange.ico"))
            if not silent:
                self.talk("解锁啦！又可以一起玩了~", 3000)
        
        if was_visible:
            self.hide()
            self.show()
            self.activateWindow()

    def toggle_mirror(self, checked: bool):
        """切换镜像翻转状态"""
        self.is_mirrored = checked
        scale_x = -1.0 if checked else 1.0
        self.model.SetScaleX(scale_x)
        self.update()

    def toggle_edge_docking(self, checked: bool):
        """切换边缘吸附状态"""
        self.edge_docking_enabled = checked
        if not checked and hasattr(self, "is_docked") and self.is_docked:
            if hasattr(self, "normal_geometry"):
                self.animate_move(self.normal_geometry.x(), self.normal_geometry.y())
            self.is_docked = None
            self._apply_dock_rotation(None)

    def timerEvent(self, event: QTimerEvent | None):
        if event.timerId() == self.refresh:
            if hasattr(self, "is_docked") and self.is_docked:
                self.update()
                return
                
            if self.is_mouse_chasing():
                self.update()
                return
                
            if self.is_random_wandering():
                self.update()
                return
            
            global_pos = QCursor.pos()
            
            center_local = QPoint(self.width() // 2, self.height() // 2)
            center_global = self.mapToGlobal(center_local)
            
            dx = global_pos.x() - center_global.x()
            dy = global_pos.y() - center_global.y()
            
            screen = QApplication.screenAt(global_pos)
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.geometry()
            
            max_dx = screen_geo.width() / 2
            max_dy = screen_geo.height() / 2
            
            ratio_x = max(-1.0, min(1.0, dx / max_dx))
            ratio_y = max(-1.0, min(1.0, dy / max_dy))
            
            mirror_factor = -1.0 if self.is_mirrored else 1.0
            target_x = center_local.x() + ratio_x * (self.width() / 2) * mirror_factor
            target_y = center_local.y() + ratio_y * (self.height() / 2)
            
            self.model.Drag(target_x, target_y)
            self.update()

    def talk(self, text: str, duration: int = None, force: bool = False):
        if not self.isVisible():
            return
        if not force:
            if hasattr(self, "is_docked") and self.is_docked:
                return
            if self.is_mouse_chasing():
                return
        
        if hasattr(self, 'default_bubble_duration'):
            duration = self.default_bubble_duration
        elif duration is None:
            duration = 4000
            
        self.bubble.show_text(text, duration)
        self.update_bubble_position()

    def update_bubble_position(self):
        """更新气泡位置，使其跟随模型并在上方显示"""
        if not self.bubble.isVisible(): return
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        
        x = global_pos.x() + (self.width() - self.bubble.width()) // 2
        
        y = global_pos.y() - self.bubble.height() - 20
        
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

        if hasattr(self, 'attr_manager'):
            self.attr_manager.stop_decay_timer()
        
        if hasattr(self, 'model'):
            live2d.glRelease()
        live2d.dispose()

    def _on_status_changed(self, attr_name: str, new_status: str, old_status: str):
        """属性状态变化时触发表情"""
        if new_status == "critical":
            if attr_name == ATTR_HUNGER:
                self.talk("好饿啊...我要饿晕了...", 4000)
                if "失去高光" in self.expression_ids:
                    self.model.SetExpression("失去高光")
            elif attr_name == ATTR_MOOD:
                self.talk("好难过啊...", 3000)
                if "黑脸" in self.expression_ids:
                    self.model.SetExpression("黑脸")
            elif attr_name == ATTR_CLEANLINESS:
                self.talk("身上好脏啊...", 3000)
            elif attr_name == "energy":
                self.talk("好困啊...", 3000)
                if "困" in self.expression_ids:
                    self.model.SetExpression("困")
        elif new_status == "warning":
            if attr_name == ATTR_HUNGER:
                if random.random() < 0.3:
                    self.talk("有点饿了...", 2500)
                    if "感叹号" in self.expression_ids:
                        self.model.SetExpression("感叹号")
            elif attr_name == ATTR_MOOD:
                if random.random() < 0.2:
                    self.talk("有点无聊...", 2500)

    def _on_interaction_triggered(self, attr_name: str, interaction_type: str):
        """互动反馈：触发对话和动作"""
        if self.is_mouse_chasing() or (hasattr(self, "is_docked") and self.is_docked):
            return
            
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
                    self.model.SetExpression(random.choice(available_happy))
            
            if self.motion_groups:
                group = random.choice(list(self.motion_groups.keys()))
                self.model.StartRandomMotion(group, live2d.MotionPriority.NORMAL)
    
    def feed_pet(self, food_name: str = "欧润吉"):
        """投喂宠物"""
        self.attr_manager.perform_interaction("feed")
        
        if self.is_mouse_chasing():
            from src.core.pet_constants import ATTR_ENERGY
            self.attr_manager.update_attribute(ATTR_ENERGY, 30)
            self.talk(f"谢谢投喂{food_name}！我又有力气啦~", 3000, force=True)

    def init_custom_cursor(self, image_path):
        """
        设置自定义鼠标样式
        :param image_path: 鼠标图片路径
        """
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            
            target_size = QSize(32, 32) 
            pixmap = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            cursor = QCursor(pixmap, 0, 0)
            
            self.setCursor(cursor)
        else:
            print(f"警告: 未找到鼠标图片 {image_path}，将使用默认鼠标。")
            self.setCursor(Qt.ArrowCursor)


    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        # === 快捷操作区 ===
        quick_chat_action = QAction("💬 沉浸聊天", self)
        quick_chat_action.setToolTip("打开沉浸聊天窗口，快速与 Doro 对话")
        def open_quick_chat():
            from src.ui.windows.quick_chat_window import QuickChatWindow
            from src.core.database import DatabaseManager
            if not hasattr(self, 'quick_chat_window') or not self.quick_chat_window:
                db_manager = DatabaseManager()
                self.quick_chat_window = QuickChatWindow(
                    db=db_manager.chat,
                    persona_db=db_manager.personas,
                    live2d_widget=self
                )
            self.quick_chat_window.show()
            self.quick_chat_window.raise_()
            self.quick_chat_window.activateWindow()
        quick_chat_action.triggered.connect(open_quick_chat)
        menu.addAction(quick_chat_action)
        
        menu.addSeparator()

        # === 互动区 ===
        interact_menu = QMenu("🎭 互动", menu)
        
        action_exp = QAction("🎲 随机表情", self)
        action_exp.triggered.connect(self.random_expression)
        interact_menu.addAction(action_exp)

        if self.expression_ids:
            exp_menu = QMenu("切换表情", self)
            for exp_name in self.expression_ids:
                action = QAction(str(exp_name), self)
                action.triggered.connect(lambda checked, name=exp_name: self.model.SetExpression(name))
                exp_menu.addAction(action)
            interact_menu.addMenu(exp_menu)

        if self.motion_groups:
            motion_menu = QMenu("播放动作", self)
            for motion_group in self.motion_groups.keys():
                action = QAction(str(motion_group), self)
                action.triggered.connect(lambda checked, group=motion_group: self.model.StartRandomMotion(group, live2d.MotionPriority.NORMAL))
                motion_menu.addAction(action)
            interact_menu.addMenu(motion_menu)
        
        menu.addMenu(interact_menu)
        
        # === 行为设置区 ===
        behavior_menu = QMenu("⚙️ 行为设置", menu)
        
        action_mirror = QAction("左右镜像", self)
        action_mirror.setCheckable(True)
        action_mirror.setChecked(self.is_mirrored)
        action_mirror.triggered.connect(self.toggle_mirror)
        behavior_menu.addAction(action_mirror)
        
        action_chase = QAction("追逐鼠标", self)
        action_chase.setCheckable(True)
        action_chase.setChecked(self.is_mouse_chasing())
        action_chase.triggered.connect(lambda: self.toggle_mouse_chase())
        behavior_menu.addAction(action_chase)
        
        action_wander = QAction("随机溜达", self)
        action_wander.setCheckable(True)
        action_wander.setChecked(self.is_random_wandering())
        action_wander.triggered.connect(lambda: self.toggle_random_wander())
        behavior_menu.addAction(action_wander)
        
        action_edge_dock = QAction("边缘吸附", self)
        action_edge_dock.setCheckable(True)
        action_edge_dock.setChecked(self.edge_docking_enabled)
        action_edge_dock.triggered.connect(self.toggle_edge_docking)
        behavior_menu.addAction(action_edge_dock)
        
        menu.addMenu(behavior_menu)
        
        # === 显示设置区 ===
        display_menu = QMenu("📺 显示设置", menu)
        
        action_reset = QAction("🔄 重置大小", self)
        action_reset.triggered.connect(lambda: self.resize(550, 500))
        display_menu.addAction(action_reset)
        
        action_show_status = QAction("隐藏属性栏" if self.status_overlay.isVisible() else "显示属性栏", self)
        action_show_status.triggered.connect(self._toggle_status_overlay)
        display_menu.addAction(action_show_status)

        menu.addMenu(display_menu)
        
        menu.addSeparator()

        # === 界面管理区 ===
        action_open_ui = QAction("🖥️ 打开主界面", self)
        action_open_ui.triggered.connect(self.open_main_window)
        menu.addAction(action_open_ui)

        menu.addSeparator()

        # === 系统区 ===
        action_quit = QAction("❌ 退出", self)
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
                version_manager = None
                if hasattr(self, '_startup_checker') and self._startup_checker:
                    version_manager = self._startup_checker.get_version_manager()
                self.main_window = MainWindow(version_manager)
                self.main_window.set_live2d_widget(self)
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            if not self.main_window.isVisible():
                self.main_window.show()
            self.main_window.setWindowFlags(self.main_window.windowFlags() | Qt.WindowStaysOnTopHint)
            self.main_window.show()
            self.main_window.setWindowFlags(self.main_window.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        except Exception as e:
            import traceback
            traceback.print_exc()
            from src.core.logger import logger
            logger.error(f"Failed to open main window: {e}")
            logger.error(traceback.format_exc())

    def on_click(self, x, y):
        """处理点击事件"""
        self.makeCurrent()
        
        try:
            hit_parts = self.model.HitPart(x, y, True)
            hit_area = hit_parts[0] if hit_parts else ""
            print(f"Hit Parts: {hit_parts}, Primary: '{hit_area}'")
        except Exception as e:
            print(f"HitPart error: {e}")
            hit_area = ""
        
        if self.is_mouse_chasing() and (hit_area != "Face_group" and hit_area != "Mouth_group"):
            return

        touch_motions = []
        for group in self.motion_groups.keys():
            if "摸摸" in group or group.lower().startswith("touch"):
                touch_motions.append(group)
        
        if hit_area == "Face_group" or hit_area == "Mouth_group":
            self.feed_pet("欧润吉")
            return

        elif hit_area == "Body_group":
            if random.random() < 0.6 and self.expression_ids:
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
                
                available_map = {k:v for k,v in exp_dialogues.items() if k in self.expression_ids}
                
                if available_map:
                    chosen_exp = random.choice(list(available_map.keys()))
                    self.model.SetExpression(chosen_exp)
                    
                    dialogues = available_map[chosen_exp]
                    self.talk(random.choice(dialogues), 3000)
                    return
            
            if touch_motions:
                motion_name = random.choice(touch_motions)
                self.model.StartRandomMotion(motion_name, live2d.MotionPriority.NORMAL)
                responses = ["那是我的肚子吗~", "人，在干什么呢？", "嘿嘿好痒呀~"]
                self.talk(random.choice(responses), 2000)

        elif hit_area in ["Head_group", "Hair_front_group", "Hair_back_group"]: 
            if touch_motions:
                motion_name = random.choice(touch_motions)
                self.model.StartRandomMotion(motion_name, live2d.MotionPriority.NORMAL)
                responses = ["好痒呀~", "在干嘛呢？", "摸摸头~"]
                self.talk(random.choice(responses), 2000)
            else:
                self.random_expression()
                self.talk("干嘛盯着我看？", 2000)

        else:
            pass

    def init_system_monitor(self):
        """初始化系统资源监控"""
        if psutil and self.system_monitor_enabled:
            self.monitor_timer = QTimer(self)
            self.monitor_timer.timeout.connect(self.check_system_status)
            self.monitor_timer.start(3000)
    
    def set_system_monitor_enabled(self, enabled: bool):
        """设置系统监控是否启用"""
        self.system_monitor_enabled = enabled
        if enabled:
            if not hasattr(self, 'monitor_timer') and psutil:
                self.monitor_timer = QTimer(self)
                self.monitor_timer.timeout.connect(self.check_system_status)
                self.monitor_timer.start(3000)
            elif hasattr(self, 'monitor_timer'):
                self.monitor_timer.start(3000)
        else:
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
    
    def check_system_status(self):
        """检查系统状态并触发反应"""
        if not psutil or not self.system_monitor_enabled: 
            return
        
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            if cpu > self.cpu_threshold:
                self.talk(f"CPU好烫 ({cpu}%)！我要融化了...", 4000)
                if "失去高光" in self.expression_ids:
                    self.set_expression_safe("失去高光")
            elif mem > self.mem_threshold:
                self.talk(f"内存快满了 ({mem}%)！", 4000)
                if "无语" in self.expression_ids:
                    self.set_expression_safe("无语")
        except Exception as e:
            print(f"System monitor error: {e}")

    def set_expression_safe(self, expression_name: str):
        """线程安全地设置表情，确保在 OpenGL 上下文中执行"""
        if hasattr(self, '_pending_expression'):
            return
        self._pending_expression = expression_name
        QTimer.singleShot(0, self._execute_pending_expression)

    def _execute_pending_expression(self):
        """执行待处理的表情设置"""
        if not hasattr(self, '_pending_expression'):
            return
        expression_name = self._pending_expression
        del self._pending_expression
        
        self.makeCurrent()
        try:
            self.model.SetExpression(expression_name)
        except Exception as e:
            print(f"SetExpression error: {e}")

    def random_expression(self):
        if self.expression_ids:
            self.makeCurrent()
            try:
                self.model.SetRandomExpression()
            except Exception as e:
                print(f"SetRandomExpression error: {e}")

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
            self.drag_start_global = event.globalPos()
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
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent | None):
        if self.is_locked: return
        if not event:
            return
            
        is_click = False
        if hasattr(self, "drag_start_global"):
            dist = (event.globalPos() - self.drag_start_global).manhattanLength()
            if dist < 5:
                is_click = True
            else:
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
        """检查并执行四边边缘吸附逻辑"""
        if not self.edge_docking_enabled:
            return
        if self.is_mouse_chasing() or self.is_random_wandering():
            return
        
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        
        rect = self.geometry()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        
        threshold = max(w, h) // 3
        
        peek_w = w // 3
        peek_h = h // 3
        
        self.is_docked = None
        self.normal_geometry = rect
        
        dist_right = abs((x + w) - (screen_geo.x() + screen_geo.width()))
        dist_left = abs(x - screen_geo.x())
        dist_bottom = abs((y + h) - (screen_geo.y() + screen_geo.height()))
        dist_top = abs(y - screen_geo.y())
        
        min_dist = min(dist_right, dist_left, dist_bottom, dist_top)
        
        if min_dist < threshold:
            if min_dist == dist_right:
                target_x = screen_geo.x() + screen_geo.width() - peek_w
                
                self.animate_move(target_x, y)
                self.is_docked = "right"
                self.dock_hidden_offset = w - peek_w
                self._apply_dock_rotation("right")
            elif min_dist == dist_left:
                target_x = screen_geo.x() - w + peek_w
                self.animate_move(target_x, y)
                self.is_docked = "left"
                self.dock_hidden_offset = w - peek_w
                self._apply_dock_rotation("left")
            elif min_dist == dist_bottom:
                target_y = screen_geo.y() + screen_geo.height() - peek_h
                self.animate_move(x, target_y)
                self.is_docked = "bottom"
                self.dock_hidden_offset = h - peek_h
                self._apply_dock_rotation("bottom")
            elif min_dist == dist_top:
                target_y = screen_geo.y() - h + peek_h
                self.animate_move(x, target_y)
                self.is_docked = "top"
                self.dock_hidden_offset = h - peek_h
                self._apply_dock_rotation("top")
        else:
            self._apply_dock_rotation(None)

    def _apply_dock_rotation(self, dock_side):
        """根据吸附方向旋转模型，确保模型上方露出"""
        if not hasattr(self, 'model'):
            return
        
        rotation_map = {
            "right": 90,
            "left": -90,
            "top": 180,
            "bottom": 0,
            None: 0
        }
        
        degrees = rotation_map.get(dock_side, 0)
        self.model.Rotate(degrees)
        self.update()

    def animate_move(self, target_x, target_y):
        """简单的移动动画"""
        self.move(target_x, target_y)

    def enterEvent(self, event):
        """鼠标移入：如果是吸附状态则探出半个模型并触发问好"""
        if hasattr(self, "is_docked") and self.is_docked:
            screen = QApplication.screenAt(QCursor.pos())
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            
            half_w = self.width() // 2
            half_h = self.height() // 2
            
            if self.is_docked == "right":
                target_x = screen_geo.x() + screen_geo.width() - half_w
                self.animate_move(target_x, self.y())
            elif self.is_docked == "left":
                target_x = screen_geo.x() - self.width() + half_w
                self.animate_move(target_x, self.y())
            elif self.is_docked == "bottom":
                target_y = screen_geo.y() + screen_geo.height() - half_h
                self.animate_move(self.x(), target_y)
            elif self.is_docked == "top":
                target_y = screen_geo.y() - self.height() + half_h
                self.animate_move(self.x(), target_y)
            
            self._trigger_greeting()
        super().enterEvent(event)

    def _trigger_greeting(self):
        """触发表情"""
        if self.expression_ids:
            self.model.SetExpression("感叹号")
        else:
            self.model.SetRandomExpression()

    def leaveEvent(self, event):
        """鼠标移出：如果是吸附状态则缩回去"""
        if hasattr(self, "is_docked") and self.is_docked:
            screen = QApplication.screenAt(QCursor.pos())
            if not screen:
                screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            
            peek_w = self.width() // 3
            peek_h = self.height() // 3
            
            if self.is_docked == "right":
                target_x = screen_geo.x() + screen_geo.width() - peek_w
                self.animate_move(target_x, self.y())
            elif self.is_docked == "left":
                target_x = screen_geo.x() - self.width() + peek_w
                self.animate_move(target_x, self.y())
            elif self.is_docked == "bottom":
                target_y = screen_geo.y() + screen_geo.height() - peek_h
                self.animate_move(self.x(), target_y)
            elif self.is_docked == "top":
                target_y = screen_geo.y() - self.height() + peek_h
                self.animate_move(self.x(), target_y)
            
            if hasattr(self, 'model'):
                self.model.ResetExpression()
        super().leaveEvent(event)
