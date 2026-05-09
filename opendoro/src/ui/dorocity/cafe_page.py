import random

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QGridLayout, QListWidgetItem)
from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton, ScrollArea,
                             TitleLabel, BodyLabel, StrongBodyLabel, ListWidget,
                             isDarkTheme)

from .cafe_constants import (
    CAFE_CATS, CAFE_DRINKS, CAFE_INTERACTIONS,
    CAFE_RANDOM_EVENTS, CAFE_NPC_DIALOGUES, CAFE_TIPS,
)
from .work_constants import WORK_JOBS, WORK_EVENTS
from .work_page import JobCard, WorkCompletionPopup
from .item_constants import ITEM_DEFINITIONS, CATEGORY_ICONS
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
)


class CatCard(CardWidget):
    cat_clicked = pyqtSignal(str)

    def __init__(self, cat: dict, parent=None):
        super().__init__(parent)
        self._cat = cat
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(140, 110)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        emoji = BodyLabel(self._cat["emoji"])
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size: 32px; background: transparent;")
        layout.addWidget(emoji)

        name = StrongBodyLabel(self._cat["name"])
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        personality = BodyLabel(self._cat["personality"])
        personality.setAlignment(Qt.AlignCenter)
        personality.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(personality)

        self.setStyleSheet("""
            CatCard {
                border-radius: 10px;
            }
            CatCard:hover {
                border: 1px solid #795548;
                background-color: rgba(121, 85, 72, 0.05);
            }
        """)

    def mousePressEvent(self, event):
        self.cat_clicked.emit(self._cat["key"])
        super().mousePressEvent(event)


class DrinkCard(CardWidget):
    buy_clicked = pyqtSignal(str)

    def __init__(self, drink: dict, parent=None):
        super().__init__(parent)
        self._drink = drink
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        emoji = BodyLabel(self._drink["emoji"])
        emoji.setFixedWidth(32)
        emoji.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(emoji)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name = StrongBodyLabel(self._drink["name"])
        info_layout.addWidget(name)

        desc = BodyLabel(self._drink["desc"])
        desc.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(desc)

        eff_parts = []
        eff_labels = {"hunger": "饱食", "mood": "心情", "cleanliness": "清洁", "energy": "能量"}
        for k, v in self._drink.get("effects", {}).items():
            if k in eff_labels:
                eff_parts.append(f"{eff_labels[k]}+{v}")
        eff_text = "  ".join(eff_parts)
        eff_label = BodyLabel(eff_text)
        eff_label.setStyleSheet("font-size: 10px; color: #4CAF50;")
        info_layout.addWidget(eff_label)

        layout.addWidget(info_widget, 1)

        price_label = BodyLabel(f"🍊{self._drink['price']}")
        price_label.setStyleSheet("font-weight: bold; color: #FF9800;")
        layout.addWidget(price_label)

        buy_btn = PrimaryPushButton("购买")
        buy_btn.setFixedSize(54, 28)
        buy_btn.clicked.connect(lambda: self.buy_clicked.emit(self._drink["key"]))
        layout.addWidget(buy_btn)

        self.setStyleSheet("""
            DrinkCard {
                border-radius: 8px;
            }
            DrinkCard:hover {
                border: 1px solid rgba(121, 85, 72, 0.3);
            }
        """)


class CafePage(QWidget):
    back_requested = pyqtSignal()
    work_completed = pyqtSignal(int, str)

    def __init__(self, orange_manager=None, attr_manager=None, inv_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager
        self._inv_manager = inv_manager

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
        self._build_cats_section()
        self._build_interaction_section()
        self._build_drinks_section()
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

        title = TitleLabel("☕ 猫咪咖啡馆")
        header.addWidget(title)
        header.addStretch()

        self._orange_label = BodyLabel("🍊 × 0")
        self._orange_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self._orange_label)
        self._content_layout.addLayout(header)

    def _build_ambiance(self):
        card = CardWidget()
        card.setObjectName("cafeAmbianceCard")
        card.setStyleSheet("""
            #cafeAmbianceCard {
                border-radius: 12px;
                background-color: rgba(121, 85, 72, 0.08);
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(4)

        welcome = StrongBodyLabel("☕ 欢迎来到猫咪咖啡馆！")
        welcome.setStyleSheet("font-size: 15px;")
        cl.addWidget(welcome)

        desc = BodyLabel(
            "温暖的灯光、舒缓的爵士乐、慵懒的猫咪们...\n"
            "这里是Doro最喜欢的放松角落，也是打工赚欧润吉的好地方~"
        )
        desc.setStyleSheet("font-size: 11px; color: #888;")
        cl.addWidget(desc)

        self._content_layout.addWidget(card)

    def _build_cats_section(self):
        title = StrongBodyLabel("🐱 今日在店的猫咪")
        self._content_layout.addWidget(title)

        cats_grid = QGridLayout()
        cats_grid.setSpacing(8)
        self._cat_cards = {}
        for i, cat in enumerate(CAFE_CATS):
            card = CatCard(cat)
            card.cat_clicked.connect(self._on_cat_clicked)
            cats_grid.addWidget(card, i // 2, i % 2, Qt.AlignCenter)
            self._cat_cards[cat["key"]] = card
        self._content_layout.addLayout(cats_grid)

    def _build_interaction_section(self):
        title = StrongBodyLabel("🐾 与猫咪互动")
        self._content_layout.addWidget(title)

        interact_widget = QWidget()
        interact_layout = QHBoxLayout(interact_widget)
        interact_layout.setContentsMargins(0, 0, 0, 0)
        interact_layout.setSpacing(8)

        self._interact_buttons = {}
        for act in CAFE_INTERACTIONS:
            btn = PrimaryPushButton(f"{act['icon']} {act['name']}")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda checked, a=act: self._on_interact(a))
            interact_layout.addWidget(btn)
            self._interact_buttons[act["key"]] = btn

        self._content_layout.addWidget(interact_widget)

    def _build_drinks_section(self):
        title = StrongBodyLabel("☕ 饮品菜单")
        self._content_layout.addWidget(title)

        for drink in CAFE_DRINKS:
            card = DrinkCard(drink)
            card.buy_clicked.connect(self._on_buy_drink)
            self._content_layout.addWidget(card)

    def _build_work_section(self):
        self._work_section_title = StrongBodyLabel("💼 咖啡馆打工")
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
        title = StrongBodyLabel("👩‍💼 咖啡姐姐")
        self._content_layout.addWidget(title)

        npc_card = CardWidget()
        npc_layout = QHBoxLayout(npc_card)
        npc_layout.setContentsMargins(14, 10, 14, 10)
        npc_layout.setSpacing(10)

        avatar = BodyLabel("👩‍💼")
        avatar.setFixedWidth(36)
        avatar.setStyleSheet("font-size: 28px; background: transparent;")
        npc_layout.addWidget(avatar)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name = StrongBodyLabel("咖啡姐姐")
        info_layout.addWidget(name)

        role = BodyLabel("温柔的咖啡馆老板，特别喜欢Doro")
        role.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(role)

        self._npc_dialogue = BodyLabel("")
        self._npc_dialogue.setWordWrap(True)
        self._npc_dialogue.setStyleSheet(
            "font-size: 11px; color: #795548; font-style: italic;"
            "padding: 6px 10px; background: rgba(121,85,72,0.06);"
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
        self._refresh_interact_buttons()
        self._refresh_work_section()

    def _refresh_orange(self):
        if self._orange_manager:
            self._orange_label.setText(f"🍊 × {self._orange_manager.balance}")

    def _refresh_tip(self):
        if CAFE_TIPS:
            self._tip_label.setText(random.choice(CAFE_TIPS))

    def _refresh_npc_dialogue(self):
        dialogues = CAFE_NPC_DIALOGUES.get("coffee_sister", [])
        if dialogues:
            self._npc_dialogue.setText(f'"{random.choice(dialogues)}"')

    def _refresh_interact_buttons(self):
        for act in CAFE_INTERACTIONS:
            btn = self._interact_buttons.get(act["key"])
            if not btn:
                continue
            has_item = False
            if self._inv_manager:
                has_item = self._inv_manager.has_item(act["item_key"])
            if has_item:
                btn.setEnabled(True)
                btn.setText(f"{act['icon']} {act['name']} (有物品)")
            else:
                btn.setEnabled(False)
                btn.setText(f"{act['icon']} {act['name']} (缺物品)")

    def _refresh_work_section(self):
        for i in reversed(range(self._jobs_layout.count())):
            w = self._jobs_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        data = WORK_JOBS.get("cafe", WORK_JOBS["fruit_shop"])
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
                "font-size: 22px; color: #795548; font-weight: bold;"
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
                job["accent"] = data.get("accent", "#795548")
                locked = doro_level < job["unlock_level"]
                card = JobCard(job)
                card.job_selected.connect(self._on_job_selected)
                if locked:
                    card.set_locked(True, job["unlock_level"])
                self._job_cards.append(card)
                self._jobs_layout.addWidget(card)

            self._start_work_btn.setEnabled(self._selected_job is not None)

    def _on_cat_clicked(self, cat_key: str):
        cat = next((c for c in CAFE_CATS if c["key"] == cat_key), None)
        if not cat:
            return
        msg = f"{cat['emoji']} {cat['name']}：{cat['desc']}"
        self._hint_label.setText(msg)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #795548; padding: 8px;"
            "background: rgba(121,85,72,0.06); border-radius: 8px;"
        )

    def _on_interact(self, action: dict):
        if not self._inv_manager:
            self._hint_label.setText("⚠️ 物品系统未初始化")
            self._hint_label.setStyleSheet("font-size: 12px; color: #f44336; padding: 8px;")
            return

        item_key = action["item_key"]
        if not self._inv_manager.has_item(item_key):
            self._hint_label.setText(f"⚠️ {action['hint_no_item']}")
            self._hint_label.setStyleSheet("font-size: 12px; color: #f44336; padding: 8px;")
            return

        self._inv_manager.use_item(item_key, self._attr_manager)

        effect_parts = []
        eff_labels = {"hunger": "饱食", "mood": "心情", "cleanliness": "清洁", "energy": "能量"}
        for k, v in action.get("effects", {}).items():
            if k in eff_labels:
                effect_parts.append(f"{eff_labels[k]}+{v}")

        info = ITEM_DEFINITIONS.get(item_key, {})
        msg = f"✅ {info.get('name', '猫粮')}使用成功！{action['hint_positive']} ({' '.join(effect_parts)})"
        self._hint_label.setText(msg)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #4CAF50; padding: 8px;"
            "background: rgba(76,175,80,0.06); border-radius: 8px;"
        )

        self._refresh_interact_buttons()
        self._refresh_orange()

    def _on_buy_drink(self, drink_key: str):
        drink = next((d for d in CAFE_DRINKS if d["key"] == drink_key), None)
        if not drink:
            return

        if not self._orange_manager:
            return

        price = drink["price"]
        if self._orange_manager.balance < price:
            self._hint_label.setText(f"⚠️ 欧润吉不够！{drink['name']}需要 🍊{price}")
            self._hint_label.setStyleSheet("font-size: 12px; color: #f44336; padding: 8px;")
            return

        self._orange_manager.spend_oranges(price, f"购买{drink['name']}")

        if self._attr_manager:
            effects = drink.get("effects", {})
            attr_map = {
                "hunger": ATTR_HUNGER,
                "mood": ATTR_MOOD,
                "cleanliness": ATTR_CLEANLINESS,
                "energy": ATTR_ENERGY,
            }
            for k, v in effects.items():
                if k in attr_map:
                    self._attr_manager.update_attribute(attr_map[k], v)

        eff_parts = []
        eff_labels = {"hunger": "饱食", "mood": "心情", "cleanliness": "清洁", "energy": "能量"}
        for k, v in drink.get("effects", {}).items():
            if k in eff_labels:
                eff_parts.append(f"{eff_labels[k]}+{v}")

        msg = f"☕ 购买了 {drink['emoji']} {drink['name']}！({' '.join(eff_parts)})"
        self._hint_label.setText(msg)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #4CAF50; padding: 8px;"
            "background: rgba(76,175,80,0.06); border-radius: 8px;"
        )

        self._refresh_orange()

    def _on_job_selected(self, job_key: str):
        data = WORK_JOBS.get("cafe", WORK_JOBS["fruit_shop"])
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
            "font-size: 12px; color: #795548; padding: 8px;"
            "background: rgba(121,85,72,0.06); border-radius: 8px;"
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
            self._orange_manager.add_oranges(final_earnings, f"咖啡馆打工-{job['name']}")

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

        msg = f"☕ 打工完成！获得 🍊 × {final_earnings}"
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
            weights = [e["prob"] for e in CAFE_RANDOM_EVENTS]
            event = random.choices(CAFE_RANDOM_EVENTS, weights=weights, k=1)[0]

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
                        self._orange_manager.add_oranges(v, "咖啡馆随机事件")

            self._hint_label.setText(f"🎲 {event['message']}")
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #795548; padding: 8px;"
                "background: rgba(121,85,72,0.06); border-radius: 8px;"
            )
            self._refresh_orange()

    def _on_talk_npc(self):
        dialogues = CAFE_NPC_DIALOGUES.get("coffee_sister", [])
        if dialogues:
            self._hint_label.setText(f'👩‍💼 咖啡姐姐："{random.choice(dialogues)}"')
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #795548; padding: 8px;"
                "background: rgba(121,85,72,0.06); border-radius: 8px;"
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
