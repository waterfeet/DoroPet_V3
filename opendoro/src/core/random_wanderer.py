import math
import time
import random
from typing import Optional, Tuple, Callable
from PyQt5.QtCore import QTimer, QObject, pyqtSignal, QPoint
from PyQt5.QtWidgets import QApplication


class RandomWanderer(QObject):
    """
    随机溜达控制器
    
    宠物在屏幕上随机溜达，不消耗能量
    - 随机生成目标点
    - 到达目标后停顿
    - 停顿后选择新目标继续溜达
    """
    
    wandering_changed = pyqtSignal(bool)
    target_reached = pyqtSignal()
    
    MIN_UPDATE_INTERVAL = 33
    
    def __init__(self, model, widget, attr_manager=None):
        super().__init__()
        self.model = model
        self.widget = widget
        self.attr_manager = attr_manager
        
        self._is_active = False
        self._is_paused = False
        self._timer: Optional[QTimer] = None
        
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._current_direction = 0
        
        self._max_speed = 280.0
        self._min_speed_ratio = 0.3
        self._deceleration_distance = 150.0
        self._stop_distance = 40.0
        
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
        
        self._target: Optional[QPoint] = None
        self._pause_min = 1.0
        self._pause_max = 4.0
        self._screen_margin = 100
        self._pause_timer: Optional[QTimer] = None
        
        self._wander_dialogues = [
            "出去溜达溜达~",
            "走走走~",
            "散步时间到~",
            "到处看看~",
        ]
        
        self._idle_dialogues = [
            "休息一下~",
            "不走了不走了~",
            "累啦~",
        ]
        
    def set_physics_params(
        self,
        max_speed: float = 280.0,
        min_speed_ratio: float = 0.3,
        deceleration_distance: float = 150.0,
        stop_distance: float = 40.0,
        sin_period: float = 2.19
    ):
        self._max_speed = max_speed
        self._min_speed_ratio = min_speed_ratio
        self._deceleration_distance = deceleration_distance
        self._stop_distance = stop_distance
        self._sin_period = sin_period
        
    def set_walking_motion(self, group_name: str, priority: int = 3):
        self._running_motion_group = group_name
        self._motion_priority = priority
        
    def set_callbacks(
        self,
        on_direction_changed: Optional[Callable[[bool], None]] = None,
        on_running_changed: Optional[Callable[[bool], None]] = None
    ):
        self._on_direction_changed = on_direction_changed
        self._on_running_changed = on_running_changed
        
    def set_pause_duration(self, min_seconds: float = 1.0, max_seconds: float = 4.0):
        self._pause_min = min_seconds
        self._pause_max = max_seconds
        
    def set_screen_margin(self, margin: int = 300):
        self._screen_margin = margin
        
    def start(self):
        if self._is_active:
            return
            
        self._is_active = True
        self._is_paused = False
        self._animation_loop_enabled = True
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._sin_time = 0.0
        self._last_update_time = time.time()
        self._running_motion_group = None
        
        self._target = self._generate_random_target()
        
        if self._timer is None:
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._update)
            
        self._timer.start(self.MIN_UPDATE_INTERVAL)
        
        self.wandering_changed.emit(True)
        
        if hasattr(self.widget, 'talk'):
            dialogue = random.choice(self._wander_dialogues)
            self.widget.talk(dialogue, 2000, force=True)
        
    def stop(self):
        if not self._is_active:
            return
            
        self._is_active = False
        self._is_paused = False
        
        if self._timer:
            self._timer.stop()
            
        if self._pause_timer:
            self._pause_timer.stop()
            
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._sin_time = 0.0
        
        self._is_running = False
        self._stop_running_animation()
        
        self.wandering_changed.emit(False)
        
        if hasattr(self.widget, 'talk'):
            dialogue = random.choice(self._idle_dialogues)
            self.widget.talk(dialogue, 2000, force=True)
        
    def is_active(self) -> bool:
        return self._is_active
        
    def set_attr_manager(self, attr_manager):
        self.attr_manager = attr_manager
        
    def _generate_random_target(self) -> QPoint:
        screen = QApplication.primaryScreen()
        if not screen:
            return QPoint(500, 500)
            
        geo = screen.availableGeometry()
        margin = self._screen_margin
        
        x = random.randint(margin, geo.width() - margin)
        y = random.randint(margin, geo.height() - margin)
        
        return QPoint(x, y)
        
    def _update(self):
        if not self._is_active:
            return
            
        if self._is_paused:
            return
            
        current_time = time.time()
        dt = current_time - self._last_update_time
        self._last_update_time = current_time
        
        widget_pos = self.widget.pos()
        widget_size = self.widget.size()
        center_x = widget_pos.x() + widget_size.width() // 2
        center_y = widget_pos.y() + widget_size.height() // 2
        
        if self._target is None:
            self._target = self._generate_random_target()
            
        dx = self._target.x() - center_x
        dy = self._target.y() - center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < self._stop_distance:
            self._on_target_reached()
            return
            
        self._update_velocity_sin_wave(dx, dy, distance, dt)
        self._set_running_state(True)
        
        self._update_direction(dx)
        
        new_x = widget_pos.x() + self._velocity_x * dt
        new_y = widget_pos.y() + self._velocity_y * dt
        
        new_x, new_y = self._apply_boundary(new_x, new_y, widget_size)
        
        self.widget.move(int(new_x), int(new_y))
        
    def _on_target_reached(self):
        self._is_paused = True
        self._velocity_x = 0.0
        self._velocity_y = 0.0
        self._sin_time = 0.0
        
        self._set_running_state(False)
        
        self.target_reached.emit()
        
        pause_duration = random.uniform(self._pause_min, self._pause_max)
        
        if self._pause_timer is None:
            self._pause_timer = QTimer(self)
            self._pause_timer.setSingleShot(True)
            self._pause_timer.timeout.connect(self._pick_new_target)
            
        self._pause_timer.start(int(pause_duration * 1000))
        
    def _pick_new_target(self):
        if not self._is_active:
            return
            
        self._target = self._generate_random_target()
        self._is_paused = False
        self._last_update_time = time.time()
        self._sin_time = 0.0
        self._set_running_state(True)
        
    def _update_velocity_sin_wave(self, dx: float, dy: float, distance: float, dt: float):
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
        self._sin_time = -self._motion_delay
        
    def _update_direction(self, dx: float):
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
        if not self._animation_loop_enabled:
            self._animation_loop_enabled = True
            return
            
        if not self._running_motion_group:
            motion_groups = self.model.GetMotionGroups() if hasattr(self.model, 'GetMotionGroups') else {}
            for group in motion_groups.keys():
                if "走" in group or "walk" in group.lower():
                    self._running_motion_group = group
                    break
            if not self._running_motion_group:
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
        if self._running_motion_group and self._is_running:
            try:
                self.model.StartRandomMotion(self._running_motion_group, self._motion_priority)
                self.reset_sin_phase()
            except Exception:
                pass
                
    def _check_and_replay_motion(self):
        if not self._is_running:
            if self._motion_check_timer:
                self._motion_check_timer.stop()
            return
            
        if hasattr(self.model, 'IsMotionFinished') and self.model.IsMotionFinished():
            self._play_running_motion()
                
    def _stop_running_animation(self):
        if self._motion_check_timer:
            self._motion_check_timer.stop()
        
        if hasattr(self.model, 'StopAllMotions'):
            try:
                self.model.StopAllMotions()
            except Exception:
                pass
        
    def _apply_boundary(self, x: float, y: float, size) -> Tuple[float, float]:
        screen = QApplication.primaryScreen()
        if not screen:
            return x, y
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
        return self._velocity_x, self._velocity_y
        
    def get_current_direction(self) -> int:
        return self._current_direction
        
    def is_mirrored(self) -> bool:
        return self._is_mirrored
        
    def get_target(self) -> Optional[QPoint]:
        return self._target
