import sys
import random
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGridLayout, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QKeyEvent
from qfluentwidgets import PrimaryPushButton, StrongBodyLabel

class Game2048(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 500)
        self.setFocusPolicy(Qt.StrongFocus)  # Enable focus for keyboard events
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        self.score_label = StrongBodyLabel("Score: 0", self)
        self.score_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(self.score_label)
        header_layout.addStretch()
        
        self.restart_btn = PrimaryPushButton("Restart", self)
        self.restart_btn.clicked.connect(self.start_game)
        self.restart_btn.setFocusPolicy(Qt.NoFocus) # Prevent button from stealing focus
        header_layout.addWidget(self.restart_btn)
        
        self.layout.addLayout(header_layout)

        # Game Board
        self.board_container = QFrame(self)
        self.board_container.setStyleSheet("background-color: #bbada0; border-radius: 6px;")
        self.board_layout = QGridLayout(self.board_container)
        self.board_layout.setContentsMargins(10, 10, 10, 10)
        self.board_layout.setSpacing(10)
        
        self.tiles = {}  # (r, c) -> QLabel
        self.grid = [[0]*4 for _ in range(4)]
        
        # Initialize grid UI
        for r in range(4):
            for c in range(4):
                label = QLabel("", self.board_container)
                label.setFixedSize(70, 70)
                label.setAlignment(Qt.AlignCenter)
                label.setFont(QFont("Arial", 22, QFont.Bold))
                label.setStyleSheet("background-color: #cdc1b4; border-radius: 3px;")
                self.board_layout.addWidget(label, r, c)
                self.tiles[(r, c)] = label
        
        self.layout.addWidget(self.board_container)
        
        # Instructions
        self.layout.addWidget(QLabel("Use Arrow Keys or WASD to move", self))
        
        self.start_game()

    def start_game(self):
        self.grid = [[0]*4 for _ in range(4)]
        self.score = 0
        self.add_random_tile()
        self.add_random_tile()
        self.update_ui()
        self.setFocus()

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def add_random_tile(self):
        empty_cells = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if not empty_cells:
            return
        r, c = random.choice(empty_cells)
        self.grid[r][c] = 4 if random.random() > 0.9 else 2

    def update_ui(self):
        self.score_label.setText(f"Score: {self.score}")
        for r in range(4):
            for c in range(4):
                val = self.grid[r][c]
                label = self.tiles[(r, c)]
                if val == 0:
                    label.setText("")
                    label.setStyleSheet("background-color: #cdc1b4; border-radius: 3px;")
                else:
                    label.setText(str(val))
                    bg_color = self.get_color(val)
                    text_color = "#776e65" if val <= 4 else "#f9f6f2"
                    label.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border-radius: 3px;")

    def get_color(self, value):
        colors = {
            2: "#eee4da", 4: "#ede0c8", 8: "#f2b179", 16: "#f59563",
            32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72", 256: "#edcc61",
            512: "#edc850", 1024: "#edc53f", 2048: "#edc22e"
        }
        return colors.get(value, "#3c3a32")

    def keyPressEvent(self, event):
        key = event.key()
        moved = False
        if key in (Qt.Key_Left, Qt.Key_A):
            moved = self.move_left()
        elif key in (Qt.Key_Right, Qt.Key_D):
            moved = self.move_right()
        elif key in (Qt.Key_Up, Qt.Key_W):
            moved = self.move_up()
        elif key in (Qt.Key_Down, Qt.Key_S):
            moved = self.move_down()
            
        if moved:
            self.add_random_tile()
            self.update_ui()
            if self.is_game_over():
                QMessageBox.information(self, "Game Over", f"Final Score: {self.score}")
                self.start_game()

    def compress(self, row):
        new_row = [i for i in row if i != 0]
        new_row += [0] * (4 - len(new_row))
        return new_row

    def merge(self, row):
        for i in range(3):
            if row[i] != 0 and row[i] == row[i+1]:
                row[i] *= 2
                self.score += row[i]
                row[i+1] = 0
        return row

    def move_left(self):
        new_grid = []
        moved = False
        for row in self.grid:
            compressed = self.compress(row)
            merged = self.merge(compressed)
            final = self.compress(merged)
            new_grid.append(final)
            if final != row:
                moved = True
        self.grid = new_grid
        return moved

    def move_right(self):
        new_grid = []
        moved = False
        for row in self.grid:
            reversed_row = row[::-1]
            compressed = self.compress(reversed_row)
            merged = self.merge(compressed)
            final = self.compress(merged)
            final_row = final[::-1]
            new_grid.append(final_row)
            if final_row != row:
                moved = True
        self.grid = new_grid
        return moved

    def move_up(self):
        transposed = [list(row) for row in zip(*self.grid)]
        self.grid = transposed
        moved = self.move_left()
        self.grid = [list(row) for row in zip(*self.grid)]
        return moved

    def move_down(self):
        transposed = [list(row) for row in zip(*self.grid)]
        self.grid = transposed
        moved = self.move_right()
        self.grid = [list(row) for row in zip(*self.grid)]
        return moved

    def is_game_over(self):
        if any(0 in row for row in self.grid):
            return False
        for r in range(4):
            for c in range(4):
                val = self.grid[r][c]
                if c < 3 and val == self.grid[r][c+1]:
                    return False
                if r < 3 and val == self.grid[r+1][c]:
                    return False
        return True

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = Game2048()
    w.show()
    sys.exit(app.exec_())
