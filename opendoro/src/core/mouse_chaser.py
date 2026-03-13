import math
import time
import random
from typing import Optional, Tuple, Callable
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication


class MouseChaser(QObject):
    """
    鼠标追逐控制器
    
    实现模型追逐鼠标的功能，包含：
    - 正弦波速度系统（与跑动动画同步）
    - 方向向量计算
    - 动画状态管理
    - 边界检测
    - 属性变化（能量消耗、心情提升）
    """
    
    # 能量耗尽信号，用于通知 widget 停止追逐模式
    energy_exhausted = pyqtSignal()
    
    MIN_UPDATE_INTERVAL = 33
    ENERGY_LOW_THRESHOLD = 30.0
    
    def __init__(self, model, widget, attr_manager=None):
        super().__init__()
        self.model = model
        self.widget = widget
        self.attr_manager = attr_manager
        
        self._is_active = False
        self._timer: Optional[QTimer] = None
        
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._current_direction = 0
        
        self._max_speed = 350.0
        self._base_max_speed = 350.0
        self._min_speed_ratio = 0.3
        self._deceleration_distance = 150.0
        self._stop_distance = 30.0
        
        self._sin_time = 0.0
        self._sin_period = 2.19
        self._motion_delay = 0.15
        self._last_update_time = 0.0
        
        self._is_mirrored = False
        self._is_running = False
        
        self._on_direction_changed: Optional[Callable[[bool], None]] = None
        self._on_running_changed: Optional[Callable[[bool], None]] = None
        
        self._running_motion_group: Optional[str] = None
        self._motion_priority = 3
        self._motion_check_timer: Optional[QTimer] = None
        self._animation_loop_enabled = True
        
        self._energy_drain_rate = 2.0
        self._mood_boost_rate = 1.5
        self._hunger_drain_rate = 1.0
        self._last_attr_update_time = 0.0
        self._attr_update_interval = 1.0
        
        self._low_energy_warned = False
        self._low_energy_dialogues = [
            "我跑不动啦~",
            "我想吃欧润吉~",
            "好累好累...",
            "需要休息一下...",
            "能量不足啦~"
        ]
        
    def set_physics_params(
        self,
        max_speed: float = 350.0,
        min_speed_ratio: float = 0.3,
        deceleration_distance: float = 150.0,
        stop_distance: float = 30.0,
        sin_period: float = 0.8
    ):
        """
        设置物理参数
        
        :param max_speed: 最大速度 (像素/秒)
        :param min_speed_ratio: 正弦波最低速度比例 (0-1)
        :param deceleration_distance: 开始减速的距离
        :param stop_distance: 停止距离
        :param sin_period: 正弦波周期 (秒)
        """
        self._max_speed = max_speed
        self._min_speed_ratio = min_speed_ratio
        self._deceleration_distance = deceleration_distance
        self._stop_distance = stop_distance
        self._sin_period = sin_period
        
    def set_running_motion(self, group_name: str, priority: int = 3):
        """
        设置跑动动画
        
        :param group_name: 动画组名称 (如 "跑")
        :param priority: 动画优先级
        """
        self._running_motion_group = group_name
        self._motion_priority = priority
        
    def set_callbacks(
        self,
        on_direction_changed: Optional[Callable[[bool], None]] = None,
        on_running_changed: Optional[Callable[[bool], None]] = None
    ):
        """
        设置回调函数
        
        :param on_direction_changed: 方向改变回调，参数为是否向右
        :param on_running_changed: 跑动状态改变回调，参数为是否在跑动
        """
        self._on_direction_changed = on_direction_changed
        self._on_running_changed = on_running_changed
        
    def start(self):
        """启动追逐模式"""
        if self._is_active:
            return
            
        self._is_active = True
        self._animation_loop_enabled = True
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._sin_time = 0.0
        self._last_update_time = time.time()
        self._last_attr_update_time = time.time()
        self._low_energy_warned = False
        self._running_motion_group = None
        
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._update)
            
        self._timer.start(self.MIN_UPDATE_INTERVAL)
        
    def stop(self):
        """停止追逐模式"""
        if not self._is_active:
            return
            
        self._is_active = False
        
        if self._timer:
            self._timer.stop()
            
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._sin_time = 0.0
        self._low_energy_warned = False
        
        self._is_running = False
        self._stop_running_animation()
        
    def is_active(self) -> bool:
        """检查是否处于追逐模式"""
        return self._is_active
        
    def set_attr_manager(self, attr_manager):
        """设置属性管理器"""
        self.attr_manager = attr_manager
        
    def _update(self):
        """更新追逐状态 (每帧调用)"""
        if not self._is_active:
            return
            
        current_time = time.time()
        dt = current_time - self._last_update_time
        self._last_update_time = current_time
        
        self._update_attributes(current_time)
        self._check_energy_state()
        
        if not self._is_active:
            return
            
        mouse_pos = QCursor.pos()
        
        widget_pos = self.widget.pos()
        widget_size = self.widget.size()
        center_x = widget_pos.x() + widget_size.width() // 2
        center_y = widget_pos.y() + widget_size.height() // 2
        
        dx = mouse_pos.x() - center_x
        dy = mouse_pos.y() - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < self._stop_distance:
            self._velocity_x *= 0.8
            self._velocity_y *= 0.8
            if abs(self._velocity_x) < 1 and abs(self._velocity_y) < 1:
                self._velocity_x = 0
                self._velocity_y = 0
                self._sin_time = 0.0
                self._set_running_state(False)
                return
        else:
            self._update_velocity_sin_wave(dx, dy, distance, dt)
            self._set_running_state(True)
            
        self._update_direction(dx)
        
        new_x = widget_pos.x() + self._velocity_x * dt
        new_y = widget_pos.y() + self._velocity_y * dt
        
        new_x, new_y = self._apply_boundary(new_x, new_y, widget_size)
        
        self.widget.move(int(new_x), int(new_y))
        
    def _update_attributes(self, current_time: float):
        """
        更新属性值
        
        :param current_time: 当前时间
        """
        if not self.attr_manager or not self._is_running:
            return
            
        if current_time - self._last_attr_update_time < self._attr_update_interval:
            return
            
        self._last_attr_update_time = current_time
        
        from src.core.pet_constants import ATTR_ENERGY, ATTR_MOOD, ATTR_HUNGER
        
        self.attr_manager.update_attribute(ATTR_ENERGY, -self._energy_drain_rate)
        self.attr_manager.update_attribute(ATTR_MOOD, self._mood_boost_rate)
        
        energy = self.attr_manager.get_attribute(ATTR_ENERGY)
        if energy < self.ENERGY_LOW_THRESHOLD:
            self.attr_manager.update_attribute(ATTR_HUNGER, -self._hunger_drain_rate)
        
    def _check_energy_state(self):
        """检查能量状态并处理低能量情况"""
        if not self.attr_manager:
            return
            
        from src.core.pet_constants import ATTR_ENERGY
        
        energy = self.attr_manager.get_attribute(ATTR_ENERGY)
        
        if energy <= 0:
            self._trigger_exhausted_dialogue()
            self.stop()
            return
        
        if energy < self.ENERGY_LOW_THRESHOLD:
            speed_factor = max(0.3, energy / self.ENERGY_LOW_THRESHOLD)
            self._max_speed = self._base_max_speed * speed_factor
            
            if not self._low_energy_warned:
                self._low_energy_warned = True
                self._trigger_low_energy_dialogue()
        else:
            self._max_speed = self._base_max_speed
            self._low_energy_warned = False
            
    def _trigger_exhausted_dialogue(self):
        """触发能量耗尽对话和黑脸表情"""
        self._animation_loop_enabled = False
        
        # 发射信号，通知 widget 停止追逐模式
        self.energy_exhausted.emit()
            
        if hasattr(self.widget, 'talk'):
            exhausted_dialogues = [
                "彻底没力气了...",
                "我要休息...",
                "跑不动了...",
            ]
            dialogue = random.choice(exhausted_dialogues)
            self.widget.talk(dialogue, 3000, force=True)
            
        if hasattr(self.widget, 'set_expression_safe'):
            self.widget.set_expression_safe("黑脸")
            
    def _trigger_low_energy_dialogue(self):
        """触发低能量对话"""
        if hasattr(self.widget, 'talk'):
            dialogue = random.choice(self._low_energy_dialogues)
            self.widget.talk(dialogue, 3000, force=True)
        
    def _update_velocity_sin_wave(self, dx: float, dy: float, distance: float, dt: float):
        """
        使用正弦波更新速度向量
        
        :param dx: 目标方向的X分量
        :param dy: 目标方向的Y分量
        :param distance: 到目标的距离
        :param dt: 时间增量
        """
        if distance == 0:
            return
            
        dir_x = dx / distance
        dir_y = dy / distance
        
        self._sin_time += dt
        
        if self._sin_time < 0:
            delay_progress = 1 - (-self._sin_time / self._motion_delay)
            delay_speed = self._max_speed * 0.2 * delay_progress
            
            distance_factor = 1.0
            if distance < self._deceleration_distance:
                distance_factor = distance / self._deceleration_distance
                
            target_speed = delay_speed * distance_factor
            self._velocity_x = dir_x * target_speed
            self._velocity_y = dir_y * target_speed
            return
            
        if self._sin_time > self._sin_period:
            self._sin_time = self._sin_time % self._sin_period
        
        cos_value = math.cos(2 * math.pi * self._sin_time / self._sin_period)
        speed_ratio = self._min_speed_ratio + (1.0 - self._min_speed_ratio) * (cos_value + 1) / 2
        
        distance_factor = 1.0
        if distance < self._deceleration_distance:
            distance_factor = distance / self._deceleration_distance
            
        target_speed = self._max_speed * speed_ratio * distance_factor
        
        self._velocity_x = dir_x * target_speed
        self._velocity_y = dir_y * target_speed
        
    def reset_sin_phase(self):
        """重置正弦波相位（在动画开始时调用），带延迟"""
        self._sin_time = -self._motion_delay
        
    def _update_direction(self, dx: float):
        """
        更新朝向并触发镜像翻转
        
        :param dx: 目标方向的X分量
        """
        if abs(dx) < 5:
            return
            
        facing_right = dx > 0
        
        new_direction = 1 if facing_right else -1
        
        if new_direction != self._current_direction:
            self._current_direction = new_direction
            self._is_mirrored = facing_right
            
            if self._on_direction_changed:
                self._on_direction_changed(facing_right)
                
    def _set_running_state(self, is_running: bool):
        """
        设置跑动状态并控制动画
        
        :param is_running: 是否在跑动
        """
        if is_running == self._is_running:
            return
            
        self._is_running = is_running
        
        if self._on_running_changed:
            self._on_running_changed(is_running)
            
        if is_running:
            self._start_running_animation()
        else:
            self._stop_running_animation()
            
    def _start_running_animation(self):
        """开始跑动动画并持续循环"""
        if not self._animation_loop_enabled:
            self._animation_loop_enabled = True
            return
            
        if not self._running_motion_group:
            motion_groups = self.model.GetMotionGroups() if hasattr(self.model, 'GetMotionGroups') else {}
            for group in motion_groups.keys():
                if "跑" in group or "run" in group.lower():
                    self._running_motion_group = group
                    break
                    
        if self._running_motion_group:
            self._play_running_motion()
            if self._motion_check_timer is None:
                self._motion_check_timer = QTimer(self)
                self._motion_check_timer.timeout.connect(self._check_and_replay_motion)
            self._motion_check_timer.start(100)
                
    def _play_running_motion(self):
        """播放跑动动画并重置速度相位"""
        if self._running_motion_group and self._is_running:
            try:
                self.model.StartRandomMotion(self._running_motion_group, self._motion_priority)
                self.reset_sin_phase()
            except Exception:
                pass
                
    def _check_and_replay_motion(self):
        """检查动画是否结束，如果结束则重新播放"""
        if not self._is_running:
            if self._motion_check_timer:
                self._motion_check_timer.stop()
            return
            
        if hasattr(self.model, 'IsMotionFinished') and self.model.IsMotionFinished():
            self._play_running_motion()
                
    def _stop_running_animation(self):
        """停止跑动动画"""
        if self._motion_check_timer:
            self._motion_check_timer.stop()
        
        if hasattr(self.model, 'StopAllMotions'):
            try:
                self.model.StopAllMotions()
            except Exception:
                pass
        
    def _apply_boundary(self, x: float, y: float, size) -> Tuple[float, float]:
        """
        应用边界检测
        
        :param x: 目标X坐标
        :param y: 目标Y坐标
        :param size: 控件尺寸
        :return: 修正后的坐标
        """
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()
        
        margin = 10
        
        min_x = screen_geo.x() + margin
        max_x = screen_geo.x() + screen_geo.width() - size.width() - margin
        min_y = screen_geo.y() + margin
        max_y = screen_geo.y() + screen_geo.height() - size.height() - margin
        
        x = max(min_x, min(max_x, x))
        y = max(min_y, min(max_y, y))
        
        return x, y
        
    def get_current_velocity(self) -> Tuple[float, float]:
        """获取当前速度"""
        return self._velocity_x, self._velocity_y
        
    def get_current_direction(self) -> int:
        """获取当前方向 (1=右, -1=左)"""
        return self._current_direction
        
    def is_mirrored(self) -> bool:
        """获取是否镜像"""
        return self._is_mirrored
