# -*- coding: utf-8 -*-
"""
飞行棋 (Ludo) 游戏核心逻辑
支持 2~4 名玩家本地轮流游玩
"""

import random
from enum import Enum


class GameState(Enum):
    """游戏状态"""
    WAITING = 0        # 等待开始
    ROLLING = 1        # 等待掷骰子
    CHOOSING = 2       # 选择棋子移动
    FINISHED = 3       # 游戏结束


class Player:
    """玩家类"""
    def __init__(self, player_id, name, color, color_hex):
        self.id = player_id
        self.name = name
        self.color = color
        self.color_hex = color_hex
        self.pieces = [-1] * 4         # -1=基地, 0~51=路径, 52~57=终点通道, 58=终点
        self.finished_count = 0
        self.is_human = True

    def reset(self):
        self.pieces = [-1] * 4
        self.finished_count = 0

    def has_piece_in_base(self):
        return -1 in self.pieces

    def has_piece_on_board(self):
        return any(0 <= p <= 57 for p in self.pieces)

    def get_available_pieces(self, dice_value):
        """获取可以移动的棋子索引列表"""
        available = []
        for i, pos in enumerate(self.pieces):
            if pos == -1:
                if dice_value == 6:
                    available.append(i)
            elif pos < 58:
                new_pos = pos + dice_value
                if new_pos <= 58:
                    available.append(i)
        return available


class GameLudo:
    """飞行棋游戏主逻辑"""

    # 15x15 网格中，路径52格的中心坐标 (row, col)
    PATH_COORDS = [
        (6, 13), (6, 12), (6, 11), (6, 10), (6, 9),
        (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        (0, 7), (0, 6),
        (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (5, 5),
        (6, 4), (6, 3), (6, 2), (6, 1), (6, 0),
        (7, 0), (8, 0),
        (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6),
        (9, 6), (10, 6), (11, 6), (12, 6), (13, 6), (14, 6),
        (14, 7), (14, 8),
        (13, 8), (12, 8), (11, 8), (10, 8), (9, 8), (8, 9),
        (8, 10), (8, 11), (8, 12), (8, 13), (8, 14),
        (7, 14),
    ]

    # 各玩家起点在路径上的索引
    START_INDEX = {
        0: 0,   # 红色 (右上)
        1: 13,  # 蓝色 (左上)
        2: 26,  # 绿色 (左下)
        3: 39,  # 黄色 (右下)
    }

    # 各玩家终点通道坐标 (从外到内6格)
    HOME_COORDS = {
        0: [(7, 13), (7, 12), (7, 11), (7, 10), (7, 9), (7, 8)],
        1: [(1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7)],
        2: [(7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6)],
        3: [(13, 7), (12, 7), (11, 7), (10, 7), (9, 7), (8, 7)],
    }

    # 玩家基地中4个棋子的位置
    BASE_COORDS = {
        0: [(1, 10), (1, 13), (4, 10), (4, 13)],
        1: [(1, 1), (1, 4), (4, 1), (4, 4)],
        2: [(10, 1), (10, 4), (13, 1), (13, 4)],
        3: [(10, 10), (10, 13), (13, 10), (13, 13)],
    }

    # 安全格（各玩家起点）
    SAFE_POSITIONS = {0, 13, 26, 39}

    PLAYER_CONFIGS = [
        {"name": "玩家1", "color": "红", "color_hex": "#E74C3C"},
        {"name": "玩家2", "color": "蓝", "color_hex": "#3498DB"},
        {"name": "玩家3", "color": "绿", "color_hex": "#2ECC71"},
        {"name": "玩家4", "color": "黄", "color_hex": "#F1C40F"},
    ]

    def __init__(self):
        self.players = []
        self.num_players = 0
        self.current_player = 0
        self.dice_value = 0
        self.state = GameState.WAITING
        self.winner = None
        self.roll_count = 0
        self.last_dice_value = 0
        self.message = "点击「开始游戏」创建新对局"
        self.path_grid = {}

    def start_game(self, num_players):
        if num_players < 2 or num_players > 4:
            return False
        self.num_players = num_players
        self.players = []
        for i in range(num_players):
            cfg = self.PLAYER_CONFIGS[i]
            self.players.append(Player(i, cfg["name"], cfg["color"], cfg["color_hex"]))
        self.current_player = 0
        self.dice_value = 0
        self.state = GameState.ROLLING
        self.winner = None
        self.roll_count = 0
        self.last_dice_value = 0
        self.path_grid = {}
        self.message = f"{self.players[0].name} 请掷骰子 🎲"
        return True

    def roll_dice(self):
        """掷骰子 - 只能从ROLLING状态调用"""
        if self.state != GameState.ROLLING:
            return None

        player = self.players[self.current_player]

        # 检查是否所有棋子都已到达终点
        all_finished = all(p == 58 for p in player.pieces)
        if all_finished:
            self.next_player()
            return None

        value = random.randint(1, 6)
        self.dice_value = value
        self.last_dice_value = value

        available = player.get_available_pieces(value)

        if not available:
            # 没有棋子可移动
            msg = f"🎲 掷出 {value}，没有棋子可以移动"
            if value == 6:
                # 掷出6但基地没棋子或路径棋子不能走6步到终点
                self.next_player()
            else:
                self.next_player()
            self.message = msg
            return value

        if len(available) == 1:
            # 只有一个棋子可移动，自动移动
            self.move_piece(self.current_player, available[0], value)
            return value

        # 多个棋子可移动，让玩家选择
        self.state = GameState.CHOOSING
        self.message = f"🎲 掷出 {value}，请选择一个棋子移动"
        return value

    def move_piece(self, player_id, piece_idx, steps):
        """移动指定棋子（内部方法，不检查状态）"""
        try:
            player = self.players[player_id]
            old_pos = player.pieces[piece_idx]

            if old_pos == -1:
                # === 从基地出来 ===
                start_idx = self.START_INDEX[player_id]
                start_coord = self.PATH_COORDS[start_idx]

                # 检查起点是否被其他玩家棋子占用
                start_occupied = False
                msg_eat = ""
                if start_coord in self.path_grid:
                    victim_id, victim_piece = self.path_grid[start_coord]
                    if victim_id != player_id:
                        # 吃掉对方
                        self.players[victim_id].pieces[victim_piece] = -1
                        del self.path_grid[start_coord]
                        msg_eat = f" 吃掉了{self.players[victim_id].name}的棋子！"
                    else:
                        # 自己的棋子已在起点，叠在一起
                        start_occupied = True

                player.pieces[piece_idx] = 0
                if not start_occupied:
                    self.path_grid[start_coord] = (player_id, piece_idx)
                self.message = f"{player.name} 出动了一个棋子！{msg_eat}"

                # 处理后续（再掷/换人）
                self._after_move(steps)
                return

            # === 在路径或终点通道上移动 ===
            new_pos = old_pos + steps

            if new_pos > 58:
                # 超出终点，不能移动
                self.message = f"步数超出终点，不能移动"
                self._after_move(steps)
                return

            # 计算旧位置坐标
            old_coord = self._pos_to_coord(player_id, old_pos)

            if new_pos == 58:
                # === 到达终点 ===
                player.pieces[piece_idx] = 58
                player.finished_count += 1
                self.message = f"{player.name} 的棋子到达终点 🎉！"

                # 清除旧位置占用
                if old_coord and old_coord in self.path_grid and self.path_grid.get(old_coord) == (player_id, piece_idx):
                    del self.path_grid[old_coord]

                # 检查是否获胜
                if player.finished_count >= 4:
                    self.state = GameState.FINISHED
                    self.winner = player_id
                    self.message = f"🏆 {player.name} 获得胜利！🏆"
                    return

                # 到达终点后继续处理（再掷/换人）
                self._after_move(steps)
                return

            # === 在路径或终点通道上普通移动 ===
            new_coord = self._pos_to_coord(player_id, new_pos)

            # 检查目标位置
            can_land = True
            if new_coord in self.path_grid:
                victim_id, victim_piece = self.path_grid[new_coord]
                if victim_id != player_id:
                    # 检查是否是安全格
                    is_safe = False
                    if new_pos < 52:
                        g_idx = (self.START_INDEX[player_id] + new_pos) % 52
                        is_safe = g_idx in self.SAFE_POSITIONS
                    if not is_safe and new_pos < 52:
                        # 吃掉对方
                        self.players[victim_id].pieces[victim_piece] = -1
                        del self.path_grid[new_coord]
                        self.message = f"{player.name} 💥 吃掉了{self.players[victim_id].name}的棋子！"
                    elif is_safe:
                        self.message = f"对方在安全格上，不能吃掉"
                        can_land = False

            if can_land:
                # 检查目标位置是否已有自己的棋子
                target_has_self = False
                if new_coord in self.path_grid:
                    t_id, _ = self.path_grid[new_coord]
                    if t_id == player_id:
                        target_has_self = True

                # 清除旧位置占用
                if old_coord and old_coord in self.path_grid and self.path_grid.get(old_coord) == (player_id, piece_idx):
                    del self.path_grid[old_coord]

                player.pieces[piece_idx] = new_pos
                if not target_has_self:
                    self.path_grid[new_coord] = (player_id, piece_idx)
                if not (self.message and "吃掉" in self.message and "不能" not in self.message):
                    self.message = f"{player.name} 棋子移动了 {steps} 步"

            # 处理后续
            self._after_move(steps)

        except Exception as e:
            import traceback
            self.message = f"⚠️ 游戏内部错误: {str(e)}"
            # 打印详细堆栈（在控制台可见）
            traceback.print_exc()
            # 尝试恢复状态
            self.state = GameState.ROLLING

    def _pos_to_coord(self, player_id, pos):
        """将棋子步数转换为网格坐标"""
        if pos is None or pos == -1:
            return None
        try:
            if pos < 52:
                g_idx = (self.START_INDEX[player_id] + pos) % 52
                if 0 <= g_idx < len(self.PATH_COORDS):
                    return self.PATH_COORDS[g_idx]
                return None
            elif pos < 58:
                home_idx = pos - 52
                if 0 <= home_idx < len(self.HOME_COORDS[player_id]):
                    return self.HOME_COORDS[player_id][home_idx]
                return None
        except Exception:
            return None
        return None

    def _after_move(self, steps):
        """移动后的后续处理"""
        if self.state == GameState.FINISHED:
            return

        if steps == 6:
            self.roll_count += 1
            if self.roll_count >= 3:
                self.message += " 连续三次掷出6，换人！"
                self.next_player()
            else:
                self.state = GameState.ROLLING
                self.message += " 再掷一次！"
        else:
            self.next_player()

    def choose_piece(self, piece_idx):
        """玩家选择棋子"""
        if self.state != GameState.CHOOSING:
            return False

        player = self.players[self.current_player]
        available = player.get_available_pieces(self.dice_value)

        if piece_idx not in available:
            return False

        self.move_piece(self.current_player, piece_idx, self.dice_value)
        return True

    def next_player(self):
        """切换到下一个玩家"""
        self.roll_count = 0
        if self.state == GameState.FINISHED:
            return
        next_p = (self.current_player + 1) % self.num_players
        self.current_player = next_p
        self.state = GameState.ROLLING
        self.message = f"{self.players[next_p].name} 请掷骰子 🎲"

    def get_piece_grid_pos(self, player_id, piece_idx):
        """获取棋子在网格上的坐标"""
        try:
            player = self.players[player_id]
            pos = player.pieces[piece_idx]

            if pos == -1:
                return self.BASE_COORDS[player_id][piece_idx]
            elif pos == 58:
                return self.HOME_COORDS[player_id][-1]
            elif pos < 52:
                global_idx = (self.START_INDEX[player_id] + pos) % 52
                return self.PATH_COORDS[global_idx]
            else:
                home_idx = min(pos - 52, 5)
                return self.HOME_COORDS[player_id][home_idx]
        except Exception:
            # 出错时返回基地位置
            return self.BASE_COORDS[player_id][piece_idx]

    def get_piece_state_text(self, player_id, piece_idx):
        pos = self.players[player_id].pieces[piece_idx]
        if pos == -1:
            return "基地"
        elif pos == 58:
            return "终点🏁"
        elif pos < 52:
            return f"路径{pos}"
        else:
            return f"通道{pos-52}"
