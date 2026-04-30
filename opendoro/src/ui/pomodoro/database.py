import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple
from src.core.database import BaseDatabase
from src.core.logger import logger


class PomodoroDatabase(BaseDatabase):
    def __init__(self):
        super().__init__("pomodoro.db")

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS pomodoro_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            pomodoro_count INTEGER NOT NULL DEFAULT 0,
            total_focus_seconds INTEGER NOT NULL DEFAULT 0,
            chat_count INTEGER NOT NULL DEFAULT 0,
            interaction_count INTEGER NOT NULL DEFAULT 0
        )''')
        self.conn.commit()

    def migrate(self):
        pass

    def add_record(self, record_date: str, start_time: str, duration: int, completed: bool = True):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO pomodoro_records (date, start_time, duration, completed) VALUES (?, ?, ?, ?)",
            (record_date, start_time, duration, 1 if completed else 0)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_today_stats(self) -> dict:
        today_str = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT pomodoro_count, total_focus_seconds, chat_count, interaction_count FROM daily_stats WHERE date = ?",
            (today_str,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "pomodoro_count": row["pomodoro_count"],
                "total_focus_seconds": row["total_focus_seconds"],
                "chat_count": row["chat_count"],
                "interaction_count": row["interaction_count"],
            }
        return {"pomodoro_count": 0, "total_focus_seconds": 0, "chat_count": 0, "interaction_count": 0}

    def update_today_stats(self, pomodoro_count: int = None, focus_seconds: int = None,
                           chat_count: int = None, interaction_count: int = None):
        today_str = date.today().isoformat()
        cursor = self.conn.cursor()

        cursor.execute("SELECT id FROM daily_stats WHERE date = ?", (today_str,))
        existing = cursor.fetchone()

        if existing:
            updates = []
            params = []
            if pomodoro_count is not None:
                updates.append("pomodoro_count = ?")
                params.append(pomodoro_count)
            if focus_seconds is not None:
                updates.append("total_focus_seconds = ?")
                params.append(focus_seconds)
            if chat_count is not None:
                updates.append("chat_count = ?")
                params.append(chat_count)
            if interaction_count is not None:
                updates.append("interaction_count = ?")
                params.append(interaction_count)
            if updates:
                params.append(today_str)
                cursor.execute(f"UPDATE daily_stats SET {', '.join(updates)} WHERE date = ?", params)
        else:
            cursor.execute(
                "INSERT INTO daily_stats (date, pomodoro_count, total_focus_seconds, chat_count, interaction_count) VALUES (?, ?, ?, ?, ?)",
                (today_str, pomodoro_count or 0, focus_seconds or 0, chat_count or 0, interaction_count or 0)
            )
        self.conn.commit()

    def add_completed_pomodoro(self, duration: int):
        now = datetime.now()
        self.add_record(now.date().isoformat(), now.strftime("%H:%M:%S"), duration, True)

        today_str = now.date().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT pomodoro_count, total_focus_seconds FROM daily_stats WHERE date = ?", (today_str,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE daily_stats SET pomodoro_count = ?, total_focus_seconds = ? WHERE date = ?",
                (row["pomodoro_count"] + 1, row["total_focus_seconds"] + duration, today_str)
            )
        else:
            cursor.execute(
                "INSERT INTO daily_stats (date, pomodoro_count, total_focus_seconds, chat_count, interaction_count) VALUES (?, ?, ?, ?, ?)",
                (today_str, 1, duration, 0, 0)
            )
        self.conn.commit()

    def add_interrupted_pomodoro(self, duration: int):
        now = datetime.now()
        self.add_record(now.date().isoformat(), now.strftime("%H:%M:%S"), duration, False)

    def get_total_pomodoros(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM pomodoro_records WHERE completed = 1")
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def get_total_focus_seconds(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(total_focus_seconds), 0) as total FROM daily_stats")
        row = cursor.fetchone()
        return row["total"] if row else 0

    def get_best_streak(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT date FROM daily_stats WHERE pomodoro_count > 0 ORDER BY date ASC")
        dates = [row["date"] for row in cursor.fetchall()]
        if not dates:
            return 0
        best = 1
        current = 1
        for i in range(1, len(dates)):
            prev_date = datetime.strptime(dates[i - 1], "%Y-%m-%d").date()
            curr_date = datetime.strptime(dates[i], "%Y-%m-%d").date()
            if (curr_date - prev_date).days == 1:
                current += 1
            else:
                best = max(best, current)
                current = 1
        best = max(best, current)
        return best

    def get_week_stats(self) -> List[Tuple[str, int]]:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT date, pomodoro_count FROM daily_stats WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (monday.isoformat(), today.isoformat())
        )
        rows = cursor.fetchall()
        result = []
        for i in range(7):
            d = monday + timedelta(days=i)
            d_str = d.isoformat()
            count = 0
            for row in rows:
                if row["date"] == d_str:
                    count = row["pomodoro_count"]
                    break
            result.append((d_str, count))
        return result

    def get_week_total_focus_seconds(self) -> int:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(total_focus_seconds), 0) as total FROM daily_stats WHERE date >= ? AND date <= ?",
            (monday.isoformat(), today.isoformat())
        )
        row = cursor.fetchone()
        return row["total"] if row else 0
