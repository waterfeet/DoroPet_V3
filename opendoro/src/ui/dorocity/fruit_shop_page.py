import random

from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QSettings
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout)
from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton, ScrollArea,
                             TitleLabel, BodyLabel, StrongBodyLabel, isDarkTheme)
from datetime import date

from .fruit_shop_constants import (
    FRUIT_SHOP_DISPLAY, FRUIT_SHOP_NPC_DIALOGUES,
    FRUIT_SHOP_RANDOM_EVENTS, FRUIT_SHOP_TIPS,
    FRUIT_SHOP_FREE_ORANGE_MESSAGE, FRUIT_SHOP_FREE_ORANGE_UNAVAILABLE,
)
from .work_constants import WORK_JOBS, WORK_EVENTS
from .work_page import JobCard, WorkCompletionPopup
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
)


class FruitCard(CardWidget):
    fruit_clicked = pyqtSignal(str)

    def __init__(self, fruit: dict, parent=None):
        super().__init__(parent)
        self._fruit = fruit
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(95, 95)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        emoji = BodyLabel(self._fruit["emoji"])
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(emoji)

        name = BodyLabel(self._fruit["name"])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-size: 11px; font-weight: bold; background: transparent;")
        layout.addWidget(name)

        color = self._fruit.get("color", "#FF9800")
        self.setStyleSheet(f"""
            FruitCard {{
                border-radius: 10px;
            }}
            FruitCard:hover {{
                border: 2px solid {color};
                background-color: {color}10;
            }}
        """)

    def mousePressEvent(self, event):
        self.fruit_clicked.emit(self._fruit["key"])
        super().mousePressEvent(event)


class FruitShopPage(QWidget):
    back_requested = pyqtSignal()
    work_completed = pyqtSignal(int, str)

    def __init__(self, orange_manager=None, attr_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager

        self._selected_job = None
        self._working = False
        self._work_remaining = 0
        self._work_total = 0

        self._work_timer = QTimer(self)
        self._work_timer.setInterval(1000)
        self._work_timer.timeout.connect(self._on_work_tick)

        self._event_timer = QTimer(self)
        self._event_timer.setInterval(15000)
        self._event_timer.timeout.connect(self._trigger_random_event)
        self._event_timer_count = 0

        self._init_ui()

    def open_location(self):
        self._selected_job = None
        self._working = False
        self._work_timer.stop()
        self._event_timer_count = 0
        self._event_timer.start()
        self._refresh_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 12, 16, 12)
        self._content_layout.setSpacing(10)

        self._build_header()
        self._build_ambiance()
        self._build_fruit_display()
        self._build_free_orange()
        self._build_work_section()
        self._build_npc_section()
        self._build_tips_section()
        self._build_hint()

        self._content_layout.addStretch()
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

        self._work_popup = WorkCompletionPopup(self)

    def _build_header(self):
        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(30)
        back_btn.clicked.connect(self._on_back)
        header.addWidget(back_btn)

        title = TitleLabel("🍊 欧润吉水果店")
        header.addWidget(title)
        header.addStretch()

        self._orange_label = BodyLabel("🍊 × 0")
        self._orange_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self._orange_label)
        self._content_layout.addLayout(header)

    def _build_ambiance(self):
        card = CardWidget()
        card.setObjectName("fruitShopAmbianceCard")
        card.setStyleSheet("""
            #fruitShopAmbianceCard {
                border-radius: 12px;
                background-color: rgba(255, 140, 0, 0.06);
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(4)

        welcome = StrongBodyLabel("🍊 欢迎来到欧润吉水果店！")
        welcome.setStyleSheet("font-size: 15px;")
        cl.addWidget(welcome)

        desc = BodyLabel(
            "空气中弥漫着甜甜的果香，橙子爷爷正笑眯眯地整理货架。\n"
            "这里是小镇最新鲜的水果店，也是Doro打工赚欧润吉的好地方~"
        )
        desc.setStyleSheet("font-size: 11px; color: #888;")
        cl.addWidget(desc)

        self._content_layout.addWidget(card)

    def _build_fruit_display(self):
        title = StrongBodyLabel("🍎 今日新鲜水果")
        self._content_layout.addWidget(title)

        fruit_grid = QGridLayout()
        fruit_grid.setSpacing(8)
        self._fruit_cards = {}
        for i, fruit in enumerate(FRUIT_SHOP_DISPLAY):
            card = FruitCard(fruit)
            card.fruit_clicked.connect(self._on_fruit_clicked)
            fruit_grid.addWidget(card, i // 3, i % 3, Qt.AlignCenter)
            self._fruit_cards[fruit["key"]] = card
        self._content_layout.addLayout(fruit_grid)

    def _build_free_orange(self):
        self._free_orange_card = CardWidget()
        self._free_orange_card.setObjectName("freeOrangeCard")
        self._free_orange_card.setStyleSheet("""
            #freeOrangeCard {
                border-radius: 10px;
                background-color: rgba(255, 152, 0, 0.06);
            }
        """)
        free_layout = QHBoxLayout(self._free_orange_card)
        free_layout.setContentsMargins(14, 10, 14, 10)
        free_layout.setSpacing(10)

        icon = BodyLabel("🎁")
        icon.setFixedWidth(32)
        icon.setStyleSheet("font-size: 24px; background: transparent;")
        free_layout.addWidget(icon)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        title = StrongBodyLabel("每日免费欧润吉")
        info_layout.addWidget(title)

        self._free_orange_desc = BodyLabel("饱食度低于30时可以领取（每日1次）")
        self._free_orange_desc.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(self._free_orange_desc)

        free_layout.addWidget(info_widget, 1)

        self._free_orange_btn = PrimaryPushButton("🍊 领取")
        self._free_orange_btn.setFixedSize(70, 30)
        self._free_orange_btn.clicked.connect(self._on_claim_free_orange)
        free_layout.addWidget(self._free_orange_btn)

        self._content_layout.addWidget(self._free_orange_card)

    def _build_work_section(self):
        self._work_section_title = StrongBodyLabel("💼 水果店打工")
        self._content_layout.addWidget(self._work_section_title)

        self._work_select_label = StrongBodyLabel("选择工作：")
        self._content_layout.addWidget(self._work_select_label)

        self._jobs_container = QWidget()
        self._jobs_layout = QVBoxLayout(self._jobs_container)
        self._jobs_layout.setContentsMargins(0, 0, 0, 0)
        self._jobs_layout.setSpacing(6)
        self._content_layout.addWidget(self._jobs_container)

        self._start_work_btn = PrimaryPushButton("▶ 开始打工")
        self._start_work_btn.setFixedHeight(36)
        self._start_work_btn.clicked.connect(self._start_work)
        self._start_work_btn.setEnabled(False)
        self._content_layout.addWidget(self._start_work_btn)

        self._work_status_area = QWidget()
        self._work_status_area.hide()
        self._work_status_layout = QVBoxLayout(self._work_status_area)
        self._work_status_layout.setContentsMargins(0, 0, 0, 0)
        self._work_status_layout.setSpacing(6)
        self._content_layout.addWidget(self._work_status_area)

    def _build_npc_section(self):
        title = StrongBodyLabel("👴 橙子爷爷")
        self._content_layout.addWidget(title)

        npc_card = CardWidget()
        npc_layout = QHBoxLayout(npc_card)
        npc_layout.setContentsMargins(14, 10, 14, 10)
        npc_layout.setSpacing(10)

        avatar = BodyLabel("👴")
        avatar.setFixedWidth(36)
        avatar.setStyleSheet("font-size: 28px; background: transparent;")
        npc_layout.addWidget(avatar)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name = StrongBodyLabel("橙子爷爷")
        info_layout.addWidget(name)

        role = BodyLabel("慈祥的水果店老板，最爱讲故事，特别喜欢Doro")
        role.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(role)

        self._npc_dialogue = BodyLabel("")
        self._npc_dialogue.setWordWrap(True)
        self._npc_dialogue.setStyleSheet(
            "font-size: 11px; color: #E65100; font-style: italic;"
            "padding: 6px 10px; background: rgba(255,140,0,0.06);"
            "border-radius: 8px;"
        )
        info_layout.addWidget(self._npc_dialogue)

        npc_layout.addWidget(info_widget, 1)

        talk_btn = PushButton("💬 聊天")
        talk_btn.setFixedSize(60, 28)
        talk_btn.clicked.connect(self._on_talk_npc)
        npc_layout.addWidget(talk_btn)

        self._content_layout.addWidget(npc_card)

    def _build_tips_section(self):
        self._tip_label = BodyLabel("")
        self._tip_label.setAlignment(Qt.AlignCenter)
        self._tip_label.setWordWrap(True)
        self._tip_label.setStyleSheet(
            "font-size: 10px; color: #888; padding: 6px 10px;"
            "background: rgba(0,0,0,0.02); border-radius: 8px;"
        )
        self._content_layout.addWidget(self._tip_label)

    def _build_hint(self):
        self._hint_label = BodyLabel("")
        self._hint_label.setAlignment(Qt.AlignCenter)
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet("font-size: 12px; padding: 8px;")
        self._content_layout.addWidget(self._hint_label)

    def _refresh_ui(self):
        self._refresh_orange()
        self._refresh_tip()
        self._refresh_npc_dialogue()
        self._refresh_free_orange()
        self._refresh_work_section()

    def _refresh_orange(self):
        if self._orange_manager:
            self._orange_label.setText(f"🍊 × {self._orange_manager.balance}")

    def _refresh_tip(self):
        if FRUIT_SHOP_TIPS:
            self._tip_label.setText(random.choice(FRUIT_SHOP_TIPS))

    def _refresh_npc_dialogue(self):
        dialogues = FRUIT_SHOP_NPC_DIALOGUES.get("grandpa_orange", [])
        if dialogues:
            self._npc_dialogue.setText(f'"{random.choice(dialogues)}"')

    def _refresh_free_orange(self):
        if not self._attr_manager or not self._orange_manager:
            self._free_orange_btn.setEnabled(False)
            return

        hunger_value = self._attr_manager.get_attribute(ATTR_HUNGER)
        settings = QSettings("DoroPet", "Settings")
        last_claim_date = settings.value("fruit_shop_free_orange_date", "")
        today_str = date.today().isoformat()
        already_claimed = (last_claim_date == today_str)

        if already_claimed:
            self._free_orange_btn.setEnabled(False)
            self._free_orange_btn.setText("✅ 已领")
            self._free_orange_desc.setText("今天已经领过了，明天再来吧~")
        elif hunger_value >= 30:
            self._free_orange_btn.setEnabled(False)
            self._free_orange_btn.setText("🔒 不饿")
            self._free_orange_desc.setText(
                f"当前饱食度 {hunger_value:.0f}%，需要低于30%才能领取"
            )
        else:
            self._free_orange_btn.setEnabled(True)
            self._free_orange_btn.setText("🍊 领取")
            self._free_orange_desc.setText(
                f"当前饱食度 {hunger_value:.0f}%，可以领取免费欧润吉！"
            )

    def _on_claim_free_orange(self):
        if not self._attr_manager or not self._orange_manager:
            return

        settings = QSettings("DoroPet", "Settings")
        today_str = date.today().isoformat()
        settings.setValue("fruit_shop_free_orange_date", today_str)

        self._attr_manager.update_attribute(ATTR_HUNGER, 50)
        self._hint_label.setText(FRUIT_SHOP_FREE_ORANGE_MESSAGE)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #4CAF50; padding: 8px;"
            "background: rgba(76,175,80,0.06); border-radius: 8px;"
        )
        self._refresh_free_orange()
        self._refresh_orange()

    def _refresh_work_section(self):
        for i in reversed(range(self._jobs_layout.count())):
            w = self._jobs_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        data = WORK_JOBS.get("fruit_shop", WORK_JOBS["fruit_shop"])
        doro_level = self._orange_manager.doro_level if self._orange_manager else 1

        if self._working:
            self._work_select_label.hide()
            self._jobs_container.hide()
            self._start_work_btn.hide()
            self._work_status_area.show()

            for i in reversed(range(self._work_status_layout.count())):
                w = self._work_status_layout.itemAt(i).widget()
                if w:
                    w.deleteLater()

            job = self._selected_job or {}
            status_text = BodyLabel(f"🔨 {job.get('name', '')} 进行中...")
            status_text.setStyleSheet("font-size: 14px; font-weight: bold;")
            self._work_status_layout.addWidget(status_text)

            mins = self._work_remaining // 60
            secs = self._work_remaining % 60
            self._work_time_label = BodyLabel(f"⏱ 剩余 {mins}:{secs:02d}")
            self._work_time_label.setStyleSheet(
                "font-size: 22px; color: #FF8C00; font-weight: bold;"
            )
            self._work_status_layout.addWidget(self._work_time_label)

            self._work_progress_label = BodyLabel("")
            self._work_progress_label.setStyleSheet("font-size: 11px; color: #888;")
            self._work_status_layout.addWidget(self._work_progress_label)

            cancel_btn = PushButton("❌ 取消打工")
            cancel_btn.setFixedHeight(28)
            cancel_btn.clicked.connect(self._cancel_work)
            self._work_status_layout.addWidget(cancel_btn)
        else:
            self._work_select_label.show()
            self._jobs_container.show()
            self._start_work_btn.show()
            self._work_status_area.hide()

            self._job_cards = []
            for job in data["jobs"]:
                job["accent"] = data.get("accent", "#FF8C00")
                locked = doro_level < job["unlock_level"]
                card = JobCard(job)
                card.job_selected.connect(self._on_job_selected)
                if locked:
                    card.set_locked(True, job["unlock_level"])
                self._job_cards.append(card)
                self._jobs_layout.addWidget(card)

            self._start_work_btn.setEnabled(self._selected_job is not None)

    def _on_fruit_clicked(self, fruit_key: str):
        fruit = next((f for f in FRUIT_SHOP_DISPLAY if f["key"] == fruit_key), None)
        if not fruit:
            return
        msg = f"{fruit['emoji']} {fruit['name']}：{fruit['desc']}"
        self._hint_label.setText(msg)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #E65100; padding: 8px;"
            "background: rgba(255,140,0,0.06); border-radius: 8px;"
        )

    def _on_job_selected(self, job_key: str):
        data = WORK_JOBS.get("fruit_shop", WORK_JOBS["fruit_shop"])
        for card in self._job_cards:
            card.set_selected(card._job["key"] == job_key)
        for job in data["jobs"]:
            if job["key"] == job_key:
                self._selected_job = job
                self._start_work_btn.setEnabled(True)
                self._start_work_btn.setText(f"▶ 开始打工 — {job['name']}")
                break

    def _start_work(self):
        if not self._selected_job or self._working:
            return
        self._working = True
        self._work_total = self._selected_job["duration_minutes"] * 60
        self._work_remaining = self._work_total
        self._work_timer.start()
        self._refresh_work_section()
        self._hint_label.setText(f"🔨 {self._selected_job['name']} 开始！Doro加油~")
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #FF8C00; padding: 8px;"
            "background: rgba(255,140,0,0.06); border-radius: 8px;"
        )

    def _cancel_work(self):
        self._working = False
        self._work_timer.stop()
        self._selected_job = None
        self._refresh_work_section()
        self._hint_label.setText("❌ 打工已取消")
        self._hint_label.setStyleSheet("font-size: 12px; color: #888; padding: 8px;")

    def _on_work_tick(self):
        self._work_remaining -= 1
        if self._work_remaining > 0:
            mins = self._work_remaining // 60
            secs = self._work_remaining % 60
            if hasattr(self, '_work_time_label'):
                self._work_time_label.setText(f"⏱ 剩余 {mins}:{secs:02d}")
            progress_pct = int((1 - self._work_remaining / self._work_total) * 100)
            if hasattr(self, '_work_progress_label'):
                bar = "█" * (progress_pct // 5) + "░" * (20 - progress_pct // 5)
                self._work_progress_label.setText(f"[{bar}] {progress_pct}%")
        else:
            self._work_timer.stop()
            self._working = False
            self._complete_work()

    def _complete_work(self):
        if not self._selected_job:
            return

        job = self._selected_job
        base_earnings = job["earnings"]

        event_triggered = None
        if random.random() < 0.25:
            weights = [e["prob"] for e in WORK_EVENTS]
            event_triggered = random.choices(WORK_EVENTS, weights=weights, k=1)[0]

        final_earnings = base_earnings
        if event_triggered:
            eff = event_triggered["effect"]
            if "earnings_multiplier" in eff:
                final_earnings = int(final_earnings * eff["earnings_multiplier"])
            if "earnings_bonus" in eff:
                final_earnings += eff["earnings_bonus"]

        if self._orange_manager:
            self._orange_manager.add_oranges(final_earnings, f"水果店打工-{job['name']}")

        if self._attr_manager and "effects" in job:
            attr_map_effects = {
                "hunger": ATTR_HUNGER,
                "mood": ATTR_MOOD,
                "cleanliness": ATTR_CLEANLINESS,
                "energy": ATTR_ENERGY,
            }
            for attr_key, delta in job["effects"].items():
                if attr_key in attr_map_effects:
                    self._attr_manager.update_attribute(attr_map_effects[attr_key], delta)

        if event_triggered:
            eff = event_triggered["effect"]
            attr_map_effects = {
                "hunger": ATTR_HUNGER,
                "mood": ATTR_MOOD,
                "cleanliness": ATTR_CLEANLINESS,
                "energy": ATTR_ENERGY,
            }
            for attr_key in ["mood", "cleanliness"]:
                if attr_key in eff and self._attr_manager:
                    self._attr_manager.update_attribute(attr_map_effects[attr_key], eff[attr_key])

        msg = f"🍊 打工完成！获得 🍊 × {final_earnings}"
        if event_triggered:
            msg += f"\n{event_triggered['name']}"

        self._selected_job = None
        self._refresh_work_section()
        self._refresh_orange()

        if self._work_popup:
            self._work_popup.show_message(msg)
        self.work_completed.emit(final_earnings, msg)

    def _trigger_random_event(self):
        self._event_timer_count += 1
        if self._event_timer_count >= 4:
            self._event_timer.stop()

        if random.random() < 0.30:
            weights = [e["prob"] for e in FRUIT_SHOP_RANDOM_EVENTS]
            event = random.choices(FRUIT_SHOP_RANDOM_EVENTS, weights=weights, k=1)[0]

            if self._attr_manager:
                effect = event["effect"]
                attr_map = {
                    "hunger": ATTR_HUNGER,
                    "mood": ATTR_MOOD,
                    "cleanliness": ATTR_CLEANLINESS,
                    "energy": ATTR_ENERGY,
                }
                for k, v in effect.items():
                    if k in attr_map:
                        self._attr_manager.update_attribute(attr_map[k], v)
                    elif k == "oranges" and self._orange_manager:
                        self._orange_manager.add_oranges(v, "水果店随机事件")

            self._hint_label.setText(f"🎲 {event['message']}")
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #E65100; padding: 8px;"
                "background: rgba(255,140,0,0.06); border-radius: 8px;"
            )
            self._refresh_orange()

    def _on_talk_npc(self):
        dialogues = FRUIT_SHOP_NPC_DIALOGUES.get("grandpa_orange", [])
        if dialogues:
            self._hint_label.setText(f'👴 橙子爷爷："{random.choice(dialogues)}"')
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #E65100; padding: 8px;"
                "background: rgba(255,140,0,0.06); border-radius: 8px;"
            )

    def _on_back(self):
        if self._working:
            return
        self._event_timer.stop()
        self._work_timer.stop()
        self._selected_job = None
        self.back_requested.emit()

    def refresh_data(self):
        self._refresh_ui()

    def update_theme(self, is_dark: bool = None):
        if is_dark is None:
            is_dark = isDarkTheme()
        self._refresh_orange()
