# -*- coding: utf-8 -*-
"""
飞行棋插件 - DoroPet
2~4人本地多人飞行棋游戏，支持棋盘绘制、骰子交互、棋子移动
"""

import sys
import os
import math
import random  # 提前导入

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QSizePolicy, QApplication, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QRadialGradient,
    QPainterPath, QLinearGradient, QFontMetrics, QConicalGradient
)
from qfluentwidgets import (
    CardWidget, TitleLabel, SubtitleLabel, BodyLabel,
    StrongBodyLabel, PushButton, PrimaryPushButton, ComboBox,
    isDarkTheme, IconWidget, FluentIcon
)

# 引入游戏逻辑
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from game_ludo import GameLudo, GameState, Player


class DiceWidget(QWidget):
    """骰子绘制组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.value = 0
        self.rolling = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._count = 0

    def setValue(self, value):
        self.value = value
        self.update()

    def startRoll(self, final_value):
        if self.rolling:
            return
        self.rolling = True
        self._final_value = final_value
        self._count = 0
        self._timer.start(60)

    def _animate(self):
        self._count += 1
        self.value = random.randint(1, 6)
        self.update()
        if self._count >= 8:
            self._timer.stop()
            self.value = self._final_value
            self.rolling = False
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        side = min(w, h) - 8
        x, y = (w - side) / 2, (h - side) / 2

        # 骰子背景
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.setBrush(QBrush(QColor(245, 245, 245)))
        painter.drawRoundedRect(int(x), int(y), int(side), int(side), 12, 12)

        if self.value == 0:
            painter.end()
            return

        # 绘制点数
        dot_color = QColor(40, 40, 40)
        painter.setBrush(QBrush(dot_color))
        painter.setPen(QPen(dot_color, 0))

        dot_r = side * 0.08
        c_x, c_y = x + side / 2, y + side / 2
        margin = side * 0.25

        positions = {
            1: [(c_x, c_y)],
            2: [(c_x - margin, c_y - margin), (c_x + margin, c_y + margin)],
            3: [(c_x, c_y), (c_x - margin, c_y - margin), (c_x + margin, c_y + margin)],
            4: [(c_x - margin, c_y - margin), (c_x - margin, c_y + margin),
                (c_x + margin, c_y - margin), (c_x + margin, c_y + margin)],
            5: [(c_x - margin, c_y - margin), (c_x - margin, c_y + margin),
                (c_x, c_y),
                (c_x + margin, c_y - margin), (c_x + margin, c_y + margin)],
            6: [(c_x - margin, c_y - margin), (c_x - margin, c_y),
                (c_x - margin, c_y + margin),
                (c_x + margin, c_y - margin), (c_x + margin, c_y),
                (c_x + margin, c_y + margin)],
        }

        for px, py in positions.get(self.value, []):
            painter.drawEllipse(QPointF(px, py), dot_r, dot_r)

        painter.end()


class BoardWidget(QWidget):
    """棋盘绘制组件"""
    def __init__(self, game, parent=None):
        super().__init__(parent)
        self.game = game
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.clickable_pieces = []
        self.hover_piece = None
        # 保存对Plugin的引用，避免parent().parent()链式访问崩溃
        self._plugin_ref = None

    def setPluginRef(self, plugin):
        """保存插件主窗口引用"""
        self._plugin_ref = plugin

    def setGame(self, game):
        self.game = game
        self.update()

    def paintEvent(self, event):
        if not self.game or self.game.num_players == 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), QColor(45, 45, 48))
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Microsoft YaHei", 18))
            painter.drawText(self.rect(), Qt.AlignCenter, "🎲 飞行棋\n请先开始游戏")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        grid_size = min(w, h) / 15.0
        offset_x = (w - grid_size * 15) / 2
        offset_y = (h - grid_size * 15) / 2

        self.grid_size = grid_size
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.clickable_pieces = []

        self._draw_board_bg(painter, grid_size, offset_x, offset_y)
        self._draw_path(painter, grid_size, offset_x, offset_y)
        self._draw_home_channels(painter, grid_size, offset_x, offset_y)
        self._draw_bases(painter, grid_size, offset_x, offset_y)
        self._draw_center(painter, grid_size, offset_x, offset_y)
        self._draw_pieces(painter, grid_size, offset_x, offset_y)

        painter.end()

    def _draw_board_bg(self, painter, gs, ox, oy):
        painter.fillRect(int(ox), int(oy), int(gs * 15), int(gs * 15), QColor(248, 242, 230))
        painter.setPen(QPen(QColor(180, 160, 130), 3))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(ox), int(oy), int(gs * 15), int(gs * 15))

    def _draw_path(self, painter, gs, ox, oy):
        for idx, (r, c) in enumerate(GameLudo.PATH_COORDS):
            x = ox + c * gs
            y = oy + r * gs
            rect = QRectF(x + 1, y + 1, gs - 2, gs - 2)

            if idx in GameLudo.SAFE_POSITIONS:
                color = self._get_start_color(idx)
                painter.setBrush(QBrush(QColor(color).lighter(150)))
                painter.setPen(QPen(QColor(color), 2))
                painter.drawRoundedRect(rect, 4, 4)
                painter.setPen(QPen(QColor(255, 215, 0), 2))
                painter.setFont(QFont("Segoe UI", int(gs * 0.4)))
                painter.drawText(rect, Qt.AlignCenter, "★")
            else:
                painter.setBrush(QBrush(QColor(255, 248, 240)))
                painter.setPen(QPen(QColor(200, 185, 160), 1))
                painter.drawRoundedRect(rect, 3, 3)

    def _get_start_color(self, path_idx):
        for pid, sidx in GameLudo.START_INDEX.items():
            if sidx == path_idx:
                return GameLudo.PLAYER_CONFIGS[pid]["color_hex"]
        return "#888888"

    def _draw_home_channels(self, painter, gs, ox, oy):
        for pid, coords in GameLudo.HOME_COORDS.items():
            if pid >= self.game.num_players:
                continue
            color = GameLudo.PLAYER_CONFIGS[pid]["color_hex"]
            for i, (r, c) in enumerate(coords):
                x = ox + c * gs
                y = oy + r * gs
                rect = QRectF(x + 2, y + 2, gs - 4, gs - 4)
                alpha = 100 + int(155 * (i + 1) / len(coords))
                base_color = QColor(color)
                base_color.setAlpha(alpha)
                painter.setBrush(QBrush(base_color))
                painter.setPen(QPen(QColor(color), 1))
                painter.drawRoundedRect(rect, 3, 3)
                if i == len(coords) - 1:
                    painter.setPen(QColor(255, 215, 0))
                    painter.setFont(QFont("Segoe UI", int(gs * 0.35)))
                    painter.drawText(rect, Qt.AlignCenter, "🏁")

    def _draw_bases(self, painter, gs, ox, oy):
        base_regions = [
            (0, 0, 6, 6, 1),
            (0, 9, 6, 6, 0),
            (9, 0, 6, 6, 2),
            (9, 9, 6, 6, 3),
        ]
        for r_start, c_start, r_end, c_end, pid in base_regions:
            if pid >= self.game.num_players:
                continue
            color = GameLudo.PLAYER_CONFIGS[pid]["color_hex"]
            x = ox + c_start * gs
            y = oy + r_start * gs
            bw = (c_end - c_start) * gs
            bh = (r_end - r_start) * gs
            painter.setPen(QPen(QColor(color), 2))
            bg_color = QColor(color)
            bg_color.setAlpha(40)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(int(x + 2), int(y + 2), int(bw - 4), int(bh - 4), 8, 8)
            piece_positions = [
                (r_start + 1.5, c_start + 1.5),
                (r_start + 1.5, c_start + 4.5),
                (r_start + 4.5, c_start + 1.5),
                (r_start + 4.5, c_start + 4.5),
            ]
            for pr, pc in piece_positions:
                px = ox + pc * gs
                py = oy + pr * gs
                d = gs * 0.7
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color).darker(130), 1))
                painter.drawEllipse(QRectF(px - d / 2, py - d / 2, d, d))

    def _draw_center(self, painter, gs, ox, oy):
        center_x = ox + 7 * gs
        center_y = oy + 7 * gs
        center_size = gs
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawEllipse(QRectF(center_x - center_size / 2, center_y - center_size / 2,
                                   center_size, center_size))
        painter.setPen(QColor(255, 215, 0))
        painter.setFont(QFont("Segoe UI", int(gs * 0.4), QFont.Bold))
        painter.drawText(QRectF(center_x - center_size / 2, center_y - center_size / 2,
                                center_size, center_size),
                         Qt.AlignCenter, "★")

    def _draw_pieces(self, painter, gs, ox, oy):
        if not self.game:
            return
        for pid in range(min(len(self.game.players), self.game.num_players)):
            player = self.game.players[pid]
            for pi in range(4):
                try:
                    pos = player.pieces[pi]
                except IndexError:
                    continue
                if pos == 58:
                    continue
                try:
                    r, c = self.game.get_piece_grid_pos(pid, pi)
                except Exception:
                    continue
                if r is None or c is None:
                    continue
                cx = ox + c * gs + gs / 2
                cy = oy + r * gs + gs / 2
                radius = gs * 0.35

                is_clickable = False
                if self.game.state == GameState.CHOOSING and pid == self.game.current_player:
                    available = player.get_available_pieces(self.game.dice_value)
                    if pi in available:
                        is_clickable = True

                # 阴影
                shadow = QRadialGradient(cx + 2, cy + 2, radius)
                shadow.setColorAt(0, QColor(0, 0, 0, 80))
                shadow.setColorAt(1, QColor(0, 0, 0, 0))
                painter.setBrush(QBrush(shadow))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cx + 2, cy + 2), radius, radius)

                # 棋子本体
                gradient = QRadialGradient(cx - radius * 0.3, cy - radius * 0.3, radius * 1.2)
                color = QColor(player.color_hex)
                gradient.setColorAt(0, color.lighter(150))
                gradient.setColorAt(0.5, color)
                gradient.setColorAt(1, color.darker(130))
                painter.setBrush(QBrush(gradient))
                if is_clickable:
                    painter.setPen(QPen(QColor(255, 255, 255), 3))
                else:
                    painter.setPen(QPen(color.darker(150), 1))
                painter.drawEllipse(QPointF(cx, cy), radius, radius)

                # 高光
                highlight = QRadialGradient(cx - radius * 0.25, cy - radius * 0.3, radius * 0.4)
                highlight.setColorAt(0, QColor(255, 255, 255, 180))
                highlight.setColorAt(1, QColor(255, 255, 255, 0))
                painter.setBrush(QBrush(highlight))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QPointF(cx - radius * 0.2, cy - radius * 0.2), radius * 0.35, radius * 0.3)

                # 可点击区域
                if is_clickable:
                    click_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
                    self.clickable_pieces.append((pid, pi, click_rect))
                    # 编号标签
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.setFont(QFont("Segoe UI", int(gs * 0.25), QFont.Bold))
                    painter.drawText(QRectF(cx - gs * 0.3, cy + radius + 2, gs * 0.6, gs * 0.3),
                                     Qt.AlignCenter, str(pi + 1))

    def mouseReleaseEvent(self, event):
        """处理鼠标点击选择棋子"""
        if not self.game or self.game.state != GameState.CHOOSING:
            return

        pos = event.pos()
        for pid, pi, rect in self.clickable_pieces:
            if rect.contains(pos):
                # 优先使用保存的plugin引用
                if self._plugin_ref is not None:
                    self._plugin_ref.on_piece_clicked(pi)
                else:
                    # 备选：通过parent链查找
                    try:
                        parent_widget = self.parent()
                        if parent_widget:
                            grandparent = parent_widget.parent()
                            if grandparent and hasattr(grandparent, 'on_piece_clicked'):
                                grandparent.on_piece_clicked(pi)
                    except Exception:
                        pass
                return

    def mouseMoveEvent(self, event):
        pos = event.pos()
        found = any(rect.contains(pos) for _, _, rect in self.clickable_pieces)
        if found != (self.hover_piece is not None):
            self.hover_piece = True if found else None
            self.setCursor(Qt.PointingHandCursor if found else Qt.ArrowCursor)


class PlayerInfoPanel(QFrame):
    """玩家信息面板"""
    def __init__(self, player_id, game, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self.game = game
        self.setFixedHeight(80)
        self.setStyleSheet("""
            PlayerInfoPanel {
                background-color: rgba(40, 40, 45, 0.8);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 100, 0.3);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        self.color_indicator = QFrame()
        self.color_indicator.setFixedSize(20, 20)
        layout.addWidget(self.color_indicator)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        self.name_label = StrongBodyLabel("")
        self.name_label.setTextColor(QColor(220, 220, 220), QColor(220, 220, 220))
        self.status_label = BodyLabel("")
        self.status_label.setTextColor(QColor(160, 160, 160), QColor(160, 160, 160))
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)
        layout.addStretch()

        self.pieces_label = BodyLabel("")
        self.pieces_label.setTextColor(QColor(200, 200, 200), QColor(200, 200, 200))
        layout.addWidget(self.pieces_label)

    def update_info(self):
        if self.player_id >= self.game.num_players:
            self.hide()
            return
        self.show()

        player = self.game.players[self.player_id]
        cfg = GameLudo.PLAYER_CONFIGS[self.player_id]
        self.name_label.setText(f"{cfg['name']} ({cfg['color']})")
        self.color_indicator.setStyleSheet(
            f"background-color: {cfg['color_hex']}; border-radius: 10px; "
            f"border: 2px solid {QColor(cfg['color_hex']).darker(130).name()};"
        )

        pieces_status = ""
        for pi in range(4):
            pos = player.pieces[pi]
            if pos == 58:
                pieces_status += "🏁"
            elif pos == -1:
                pieces_status += "⚪"
            else:
                pieces_status += "●"
        self.pieces_label.setText(pieces_status)
        finished = player.finished_count
        self.status_label.setText(f"已完成: {finished}/4")

        if self.player_id == self.game.current_player and self.game.state != GameState.FINISHED:
            self.setStyleSheet("""
                PlayerInfoPanel {
                    background-color: rgba(60, 60, 80, 0.9);
                    border-radius: 8px;
                    border: 2px solid rgba(100, 180, 255, 0.6);
                }
            """)
        else:
            self.setStyleSheet("""
                PlayerInfoPanel {
                    background-color: rgba(40, 40, 45, 0.8);
                    border-radius: 8px;
                    border: 1px solid rgba(100, 100, 100, 0.3);
                }
            """)


class Plugin(QWidget):
    """飞行棋插件入口"""
    name = "飞行棋"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game = GameLudo()
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._safe_update_ui)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题栏
        header = QHBoxLayout()
        title = TitleLabel("🎲 飞行棋")
        title.setTextColor(QColor(231, 76, 60), QColor(231, 76, 60))
        header.addWidget(title)
        header.addStretch()

        self.player_combo = ComboBox()
        self.player_combo.addItems(["2 人", "3 人", "4 人"])
        self.player_combo.setCurrentIndex(3)
        self.player_combo.setFixedWidth(100)
        header.addWidget(self.player_combo)

        self.start_btn = PrimaryPushButton("开始游戏")
        self.start_btn.setFixedWidth(120)
        self.start_btn.clicked.connect(self.on_start_game)
        header.addWidget(self.start_btn)
        layout.addLayout(header)

        # 主体区域
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)

        # 棋盘
        board_card = CardWidget()
        board_layout = QVBoxLayout(board_card)
        board_layout.setContentsMargins(8, 8, 8, 8)
        self.board_widget = BoardWidget(self.game)
        self.board_widget.setPluginRef(self)  # 保存引用
        board_layout.addWidget(self.board_widget)
        main_layout.addWidget(board_card, 3)

        # 右侧控制区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # 骰子区域
        dice_card = CardWidget()
        dice_layout = QVBoxLayout(dice_card)
        dice_layout.setContentsMargins(16, 16, 16, 16)
        dice_layout.setAlignment(Qt.AlignCenter)

        dice_title = SubtitleLabel("🎲 骰子")
        dice_title.setTextColor(QColor(220, 220, 220), QColor(220, 220, 220))
        dice_title.setAlignment(Qt.AlignCenter)
        dice_layout.addWidget(dice_title)

        self.dice_widget = DiceWidget()
        dice_layout.addWidget(self.dice_widget, 0, Qt.AlignCenter)

        self.roll_btn = PrimaryPushButton("掷骰子")
        self.roll_btn.setFixedHeight(44)
        self.roll_btn.setFixedWidth(120)
        self.roll_btn.clicked.connect(self.on_roll_dice)
        dice_layout.addWidget(self.roll_btn, 0, Qt.AlignCenter)

        right_layout.addWidget(dice_card)

        # 消息区域
        msg_card = CardWidget()
        msg_layout = QVBoxLayout(msg_card)
        msg_layout.setContentsMargins(12, 12, 12, 12)

        msg_title = StrongBodyLabel("游戏消息")
        msg_title.setTextColor(QColor(180, 180, 180), QColor(180, 180, 180))
        msg_layout.addWidget(msg_title)

        self.msg_label = BodyLabel(self.game.message)
        self.msg_label.setWordWrap(True)
        self.msg_label.setTextColor(QColor(200, 200, 200), QColor(200, 200, 200))
        msg_layout.addWidget(self.msg_label)

        right_layout.addWidget(msg_card)

        # 玩家信息
        self.player_panels = []
        player_card = CardWidget()
        player_card_layout = QVBoxLayout(player_card)
        player_card_layout.setContentsMargins(12, 8, 12, 8)
        player_card_layout.setSpacing(6)

        player_title = StrongBodyLabel("👥 玩家状态")
        player_title.setTextColor(QColor(180, 180, 180), QColor(180, 180, 180))
        player_card_layout.addWidget(player_title)

        for i in range(4):
            panel = PlayerInfoPanel(i, self.game)
            self.player_panels.append(panel)
            player_card_layout.addWidget(panel)

        player_card_layout.addStretch()
        right_layout.addWidget(player_card)

        # 提示
        tip_card = CardWidget()
        tip_layout = QVBoxLayout(tip_card)
        tip_layout.setContentsMargins(12, 8, 12, 8)
        tip = BodyLabel("💡 提示：掷骰子后，点击棋盘上高亮的棋子即可移动\n🎯 点击棋子编号或棋子本身即可")
        tip.setWordWrap(True)
        tip.setTextColor(QColor(160, 160, 160), QColor(160, 160, 160))
        tip_layout.addWidget(tip)
        right_layout.addWidget(tip_card)

        right_layout.addStretch()
        main_layout.addWidget(right_panel, 2)

        layout.addLayout(main_layout)

        self.update_ui()

    def on_start_game(self):
        """开始新游戏"""
        try:
            num = self.player_combo.currentIndex() + 2
            self.game.start_game(num)
            self.dice_widget.setValue(0)
            self.roll_btn.setEnabled(True)
            self.roll_btn.setText("🎲 掷骰子")
            self.update_ui()
        except Exception as e:
            self.msg_label.setText(f"⚠️ 开始游戏失败: {str(e)}")

    def on_roll_dice(self):
        """掷骰子"""
        try:
            if self.game.state != GameState.ROLLING:
                return

            player = self.game.players[self.game.current_player]
            all_finished = all(p == 58 for p in player.pieces)
            if all_finished:
                self.game.next_player()
                self.update_ui()
                return

            value = self.game.roll_dice()
            if value is None:
                self.update_ui()
                return

            # 开始骰子动画
            self.dice_widget.startRoll(value)
            self.roll_btn.setEnabled(False)

            # 延迟更新UI
            self._update_timer.start(700)

        except Exception as e:
            self.msg_label.setText(f"⚠️ 掷骰子出错: {str(e)}")
            self.roll_btn.setEnabled(True)

    def _safe_update_ui(self):
        """安全更新UI - 由定时器调用"""
        try:
            self.update_ui()
        except Exception as e:
            self.msg_label.setText(f"⚠️ 界面更新出错: {str(e)}")
            self.roll_btn.setEnabled(True)

    def on_piece_clicked(self, piece_idx):
        """点击棋子后的处理"""
        try:
            if self.game.state != GameState.CHOOSING:
                return

            # 验证棋子索引有效性
            player = self.game.players[self.game.current_player]
            if piece_idx < 0 or piece_idx >= len(player.pieces):
                return

            result = self.game.choose_piece(piece_idx)
            if not result:
                # 选择失败（可能棋子已被移动）
                return

            # 更新骰子显示
            self.dice_widget.setValue(self.game.dice_value)

            # 立即更新一次消息
            self.msg_label.setText(self.game.message)

            # 延迟全面更新UI
            self._update_timer.start(100)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.msg_label.setText(f"⚠️ 操作出错: {str(e)}")
            # 尝试恢复
            self.game.state = GameState.ROLLING
            self.roll_btn.setEnabled(True)

    def update_ui(self):
        """更新整个界面"""
        try:
            self.msg_label.setText(self.game.message)

            if self.game.dice_value > 0:
                self.dice_widget.setValue(self.game.dice_value)

            # 更新骰子按钮
            if self.game.state == GameState.ROLLING and not self.game.winner:
                self.roll_btn.setEnabled(True)
                self.roll_btn.setText("🎲 掷骰子")
            elif self.game.state == GameState.CHOOSING:
                self.roll_btn.setEnabled(False)
                # 显示可选棋子编号提示
                player = self.game.players[self.game.current_player]
                available = player.get_available_pieces(self.game.dice_value)
                nums = ", ".join([str(a + 1) for a in available])
                self.roll_btn.setText(f"👆 选#{nums}")
            elif self.game.state == GameState.FINISHED:
                self.roll_btn.setEnabled(False)
                self.roll_btn.setText("🏆 游戏结束")
            else:
                self.roll_btn.setEnabled(False)
                self.roll_btn.setText("...")

            # 更新玩家面板
            for panel in self.player_panels:
                panel.update_info()

            # 重绘棋盘
            self.board_widget.update()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.msg_label.setText(f"⚠️ 界面更新出错: {str(e)}")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from qfluentwidgets import setTheme, Theme

    app = QApplication(sys.argv)
    setTheme(Theme.DARK)

    window = Plugin()
    window.resize(1000, 720)
    window.setWindowTitle("飞行棋")
    window.show()

    sys.exit(app.exec_())
