import random

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout)
from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton, ScrollArea,
                             TitleLabel, BodyLabel, StrongBodyLabel, isDarkTheme)

from .park_constants import (
    PARK_SCENERY, PARK_NPC_DIALOGUES, PARK_RANDOM_EVENTS, PARK_TIPS,
    PARK_WALK_EFFECTS, PARK_WALK_COOLDOWN_SECONDS,
    PARK_WALK_COOLDOWN_MESSAGE, PARK_WALK_MESSAGE,
    PARK_WEATHER_SUNNY, PARK_DEFAULT_WEATHER,
    PARK_EVENT_BASE_PROB, PARK_EVENT_SUNNY_MULTIPLIER,
)
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
)


class SceneryCard(CardWidget):
    scenery_clicked = pyqtSignal(str)

    def __init__(self, scenery: dict, parent=None):
        super().__init__(parent)
        self._scenery = scenery
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()

    def _init_ui(self):
        self.setFixedSize(95, 95)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        emoji = BodyLabel(self._scenery["emoji"])
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(emoji)

        name = BodyLabel(self._scenery["name"])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("font-size: 10px; font-weight: bold; background: transparent;")
        layout.addWidget(name)

        color = self._scenery.get("color", "#8BC34A")
        self.setStyleSheet(f"""
            SceneryCard {{
                border-radius: 10px;
            }}
            SceneryCard:hover {{
                border: 2px solid {color};
                background-color: {color}10;
            }}
        """)

    def mousePressEvent(self, event):
        self.scenery_clicked.emit(self._scenery["key"])
        super().mousePressEvent(event)


class ParkPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, orange_manager=None, attr_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager

        self._walk_cooldown_remaining = 0
        self._walk_cooldown_timer = QTimer(self)
        self._walk_cooldown_timer.setInterval(1000)
        self._walk_cooldown_timer.timeout.connect(self._on_cooldown_tick)

        self._event_timer = QTimer(self)
        self._event_timer.setInterval(15000)
        self._event_timer.timeout.connect(self._trigger_random_event)
        self._event_timer_count = 0

        self._init_ui()

    def open_location(self):
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
        self._build_weather()
        self._build_scenery()
        self._build_walk_section()
        self._build_npc_section()
        self._build_tips_section()
        self._build_hint()

        self._content_layout.addStretch()
        scroll.setWidget(self._content)
        layout.addWidget(scroll)

    def _build_header(self):
        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(30)
        back_btn.clicked.connect(self._on_back)
        header.addWidget(back_btn)

        title = TitleLabel("🌳 小镇公园")
        header.addWidget(title)
        header.addStretch()

        self._orange_label = BodyLabel("🍊 × 0")
        self._orange_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self._orange_label)
        self._content_layout.addLayout(header)

    def _build_ambiance(self):
        card = CardWidget()
        card.setObjectName("parkAmbianceCard")
        card.setStyleSheet("""
            #parkAmbianceCard {
                border-radius: 12px;
                background-color: rgba(139, 195, 74, 0.06);
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(4)

        welcome = StrongBodyLabel("🌳 欢迎来到小镇公园！")
        welcome.setStyleSheet("font-size: 15px;")
        cl.addWidget(welcome)

        desc = BodyLabel(
            "鸟语花香、绿树成荫，这里是小镇居民最爱的休闲场所。\n"
            "Doro可以在这里散步放松、偶遇小咪、触发各种有趣的事情~"
        )
        desc.setStyleSheet("font-size: 11px; color: #888;")
        cl.addWidget(desc)

        self._content_layout.addWidget(card)

    def _build_weather(self):
        self._weather_card = CardWidget()
        self._weather_card.setObjectName("parkWeatherCard")
        self._weather_card.setStyleSheet("""
            #parkWeatherCard {
                border-radius: 10px;
                background-color: rgba(255, 235, 59, 0.08);
                max-height: 40px;
            }
        """)
        wl = QHBoxLayout(self._weather_card)
        wl.setContentsMargins(14, 6, 14, 6)

        weather_label = BodyLabel(f"今日天气：{PARK_DEFAULT_WEATHER}")
        weather_label.setStyleSheet("font-size: 12px; font-weight: bold;")
        wl.addWidget(weather_label)

        wl.addStretch()

        self._weather_bonus_label = BodyLabel("事件概率 ×2")
        self._weather_bonus_label.setStyleSheet("font-size: 11px; color: #FF9800; font-weight: bold;")
        wl.addWidget(self._weather_bonus_label)

        self._content_layout.addWidget(self._weather_card)

    def _build_scenery(self):
        title = StrongBodyLabel("🏞️ 公园景点")
        self._content_layout.addWidget(title)

        scenery_grid = QGridLayout()
        scenery_grid.setSpacing(8)
        self._scenery_cards = {}
        for i, sc in enumerate(PARK_SCENERY):
            card = SceneryCard(sc)
            card.scenery_clicked.connect(self._on_scenery_clicked)
            scenery_grid.addWidget(card, i // 3, i % 3, Qt.AlignCenter)
            self._scenery_cards[sc["key"]] = card
        self._content_layout.addLayout(scenery_grid)

    def _build_walk_section(self):
        title = StrongBodyLabel("🚶 散步")
        self._content_layout.addWidget(title)

        walk_card = CardWidget()
        walk_card.setObjectName("parkWalkCard")
        walk_card.setStyleSheet("""
            #parkWalkCard {
                border-radius: 10px;
                background-color: rgba(139, 195, 74, 0.06);
            }
        """)
        wl = QVBoxLayout(walk_card)
        wl.setContentsMargins(14, 10, 14, 10)
        wl.setSpacing(6)

        desc = BodyLabel("在公园里悠闲地散步，呼吸新鲜空气~ 散步可以提升心情值，但会消耗一点能量。")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 11px; color: #888;")
        wl.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._walk_info = BodyLabel("💖心情+12 ⚡能量-5")
        self._walk_info.setStyleSheet("font-size: 12px; font-weight: bold; color: #4CAF50;")
        btn_row.addWidget(self._walk_info)

        btn_row.addStretch()

        self._walk_btn = PrimaryPushButton("🚶 去散步")
        self._walk_btn.setFixedSize(100, 32)
        self._walk_btn.clicked.connect(self._on_walk)
        btn_row.addWidget(self._walk_btn)

        wl.addLayout(btn_row)
        self._content_layout.addWidget(walk_card)

    def _build_npc_section(self):
        title = StrongBodyLabel("🐱 小咪")
        self._content_layout.addWidget(title)

        npc_card = CardWidget()
        npc_layout = QHBoxLayout(npc_card)
        npc_layout.setContentsMargins(14, 10, 14, 10)
        npc_layout.setSpacing(10)

        avatar = BodyLabel("🐱")
        avatar.setFixedWidth(36)
        avatar.setStyleSheet("font-size: 28px; background: transparent;")
        npc_layout.addWidget(avatar)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        name = StrongBodyLabel("小咪")
        info_layout.addWidget(name)

        role = BodyLabel("公园里的流浪猫，害羞但亲近Doro")
        role.setStyleSheet("font-size: 10px; color: #888;")
        info_layout.addWidget(role)

        self._npc_dialogue = BodyLabel("")
        self._npc_dialogue.setWordWrap(True)
        self._npc_dialogue.setStyleSheet(
            "font-size: 11px; color: #8BC34A; font-style: italic;"
            "padding: 6px 10px; background: rgba(139,195,74,0.06);"
            "border-radius: 8px;"
        )
        info_layout.addWidget(self._npc_dialogue)

        npc_layout.addWidget(info_widget, 1)

        talk_btn = PushButton("💬 互动")
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
        self._refresh_walk_button()

    def _refresh_orange(self):
        if self._orange_manager:
            self._orange_label.setText(f"🍊 × {self._orange_manager.balance}")

    def _refresh_tip(self):
        if PARK_TIPS:
            self._tip_label.setText(random.choice(PARK_TIPS))

    def _refresh_npc_dialogue(self):
        dialogues = PARK_NPC_DIALOGUES.get("mimi_cat", [])
        if dialogues:
            self._npc_dialogue.setText(f'"{random.choice(dialogues)}"')

    def _refresh_walk_button(self):
        if self._walk_cooldown_remaining > 0:
            self._walk_btn.setEnabled(False)
            self._walk_btn.setText(f"⏳ {self._walk_cooldown_remaining}s")
            self._walk_info.setText(f"冷却中... 🕐{self._walk_cooldown_remaining}秒后可散步")
            self._walk_info.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #888;"
            )
        else:
            self._walk_btn.setEnabled(True)
            self._walk_btn.setText("🚶 去散步")
            self._walk_info.setText("💖心情+12  ⚡能量-5")
            self._walk_info.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #4CAF50;"
            )

    def _on_scenery_clicked(self, scenery_key: str):
        sc = next((s for s in PARK_SCENERY if s["key"] == scenery_key), None)
        if not sc:
            return
        msg = f"{sc['emoji']} {sc['name']}：{sc['desc']}"
        self._hint_label.setText(msg)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #33691E; padding: 8px;"
            "background: rgba(139,195,74,0.06); border-radius: 8px;"
        )

    def _on_walk(self):
        if self._walk_cooldown_remaining > 0:
            return
        if not self._attr_manager:
            return

        effects = PARK_WALK_EFFECTS
        attr_map = {
            "mood": ATTR_MOOD,
            "energy": ATTR_ENERGY,
        }
        for k, v in effects.items():
            if k in attr_map:
                self._attr_manager.update_attribute(attr_map[k], v)

        self._walk_cooldown_remaining = PARK_WALK_COOLDOWN_SECONDS
        self._walk_cooldown_timer.start()
        self._refresh_walk_button()

        self._hint_label.setText(PARK_WALK_MESSAGE)
        self._hint_label.setStyleSheet(
            "font-size: 12px; color: #4CAF50; padding: 8px;"
            "background: rgba(76,175,80,0.06); border-radius: 8px;"
        )

    def _on_cooldown_tick(self):
        self._walk_cooldown_remaining -= 1
        if self._walk_cooldown_remaining <= 0:
            self._walk_cooldown_timer.stop()
        self._refresh_walk_button()

    def _trigger_random_event(self):
        self._event_timer_count += 1
        if self._event_timer_count >= 6:
            self._event_timer.stop()

        prob = PARK_EVENT_BASE_PROB * PARK_EVENT_SUNNY_MULTIPLIER
        if random.random() < prob:
            weights = [e["prob"] for e in PARK_RANDOM_EVENTS]
            event = random.choices(PARK_RANDOM_EVENTS, weights=weights, k=1)[0]

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
                        self._orange_manager.add_oranges(v, "公园随机事件")

            self._hint_label.setText(f"🎲 {event['message']}")
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #33691E; padding: 8px;"
                "background: rgba(139,195,74,0.06); border-radius: 8px;"
            )
            self._refresh_orange()

    def _on_talk_npc(self):
        dialogues = PARK_NPC_DIALOGUES.get("mimi_cat", [])
        if dialogues:
            self._hint_label.setText(f'🐱 小咪："{random.choice(dialogues)}"')
            self._hint_label.setStyleSheet(
                "font-size: 12px; color: #33691E; padding: 8px;"
                "background: rgba(139,195,74,0.06); border-radius: 8px;"
            )

    def _on_back(self):
        self._event_timer.stop()
        self._walk_cooldown_timer.stop()
        self._walk_cooldown_remaining = 0
        self.back_requested.emit()

    def refresh_data(self):
        self._refresh_ui()

    def update_theme(self, is_dark: bool = None):
        if is_dark is None:
            is_dark = isDarkTheme()
        self._refresh_orange()
