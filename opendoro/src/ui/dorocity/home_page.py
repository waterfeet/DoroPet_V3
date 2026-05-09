from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout)
from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton, ScrollArea,
                             TitleLabel, BodyLabel, StrongBodyLabel, isDarkTheme)
from .item_constants import ITEM_DEFINITIONS, CATEGORY_ICONS
from src.core.pet_constants import (
    ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY,
    ATTR_NAMES, DORO_LEVEL_TITLES, ORANGE_INTERACTION_COST,
)

HOME_ACTIONS = [
    {"key": "feed", "icon": "🍖", "name": "吃饭", "desc": "饱食度 +30",
     "attr": ATTR_HUNGER, "delta": 30, "item_category": "food"},
    {"key": "play", "icon": "🎮", "name": "玩耍", "desc": "心情值 +30",
     "attr": ATTR_MOOD, "delta": 30, "item_category": "toy"},
    {"key": "clean", "icon": "🧹", "name": "洗澡", "desc": "清洁度 +35",
     "attr": ATTR_CLEANLINESS, "delta": 35, "item_category": "daily"},
    {"key": "rest", "icon": "😴", "name": "休息", "desc": "能量值 +40",
     "attr": ATTR_ENERGY, "delta": 40, "item_category": "daily"},
]


class HomePage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, orange_manager=None, attr_manager=None, inv_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager
        self._inv_manager = inv_manager
        self._active_action = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(30)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        title = TitleLabel("🏠 Doro的家")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        welcome_card = CardWidget()
        wc_layout = QVBoxLayout(welcome_card)
        wc_layout.setContentsMargins(20, 14, 20, 14)
        wc_layout.setSpacing(4)
        self._welcome_title = StrongBodyLabel("欢迎回家，Doro！")
        self._welcome_title.setStyleSheet("font-size: 16px;")
        self._doro_info = BodyLabel("")
        wc_layout.addWidget(self._welcome_title)
        wc_layout.addWidget(self._doro_info)
        layout.addWidget(welcome_card)

        attr_title = StrongBodyLabel("📊 属性状态")
        layout.addWidget(attr_title)

        self._attr_value_labels = {}
        self._attr_bar_labels = {}
        self._attr_status_labels = {}
        attrs_order = [ATTR_HUNGER, ATTR_MOOD, ATTR_CLEANLINESS, ATTR_ENERGY]
        for attr_name in attrs_order:
            card = self._create_attr_row(attr_name)
            layout.addWidget(card)

        action_title = StrongBodyLabel("🏠 在家活动")
        layout.addWidget(action_title)

        action_grid = QGridLayout()
        action_grid.setSpacing(8)
        self._action_buttons = {}
        for i, act in enumerate(HOME_ACTIONS):
            btn = PrimaryPushButton(f"{act['icon']}  {act['name']}")
            btn.setFixedHeight(48)
            btn.clicked.connect(lambda checked, a=act: self._on_action_click(a))
            action_grid.addWidget(btn, i // 2, i % 2)
            self._action_buttons[act["key"]] = btn
        layout.addLayout(action_grid)

        self._action_hint = BodyLabel("")
        self._action_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._action_hint)

        self._item_scroll = ScrollArea()
        self._item_scroll.setMaximumHeight(200)
        self._item_scroll.setWidgetResizable(True)
        self._item_scroll.setViewportMargins(0, 0, 6, 0)
        self._item_scroll.hide()
        self._item_panel = QWidget()
        self._item_panel.setStyleSheet("background: transparent;")
        self._item_layout = QVBoxLayout(self._item_panel)
        self._item_layout.setContentsMargins(0, 0, 8, 0)
        self._item_layout.setSpacing(4)
        self._item_scroll.setWidget(self._item_panel)
        layout.addWidget(self._item_scroll)

        layout.addStretch()
        self.refresh_data()

    def _create_attr_row(self, attr_name: str):
        card = CardWidget()
        card.setMaximumHeight(52)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)

        icons = {
            ATTR_HUNGER: "🍖", ATTR_MOOD: "💖",
            ATTR_CLEANLINESS: "✨", ATTR_ENERGY: "⚡",
        }
        icon = BodyLabel(icons.get(attr_name, "📊"))
        icon.setFixedWidth(24)
        icon.setStyleSheet("font-size: 18px; background: transparent;")
        row.addWidget(icon)

        name = StrongBodyLabel(ATTR_NAMES.get(attr_name, attr_name))
        name.setStyleSheet("font-size: 13px; background: transparent;")
        row.addWidget(name)

        val_label = BodyLabel("50%")
        val_label.setFixedWidth(40)
        val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val_label.setStyleSheet("font-size: 13px; background: transparent;")
        row.addWidget(val_label)
        self._attr_value_labels[attr_name] = val_label

        bar_label = BodyLabel("")
        bar_label.setStyleSheet("font-size: 13px; letter-spacing: 1px; background: transparent;")
        row.addWidget(bar_label, 1)
        self._attr_bar_labels[attr_name] = bar_label

        status_label = BodyLabel("良好")
        status_label.setFixedWidth(32)
        status_label.setAlignment(Qt.AlignCenter)
        self._attr_status_labels[attr_name] = status_label
        row.addWidget(status_label)

        return card

    def _on_action_click(self, action: dict):
        if self._active_action and self._active_action["key"] == action["key"]:
            self._close_item_panel()
            return
        self._active_action = action
        self._show_item_panel(action)

    def _close_item_panel(self):
        self._active_action = None
        self._item_scroll.hide()
        self._action_hint.setText("")
        self._action_hint.setStyleSheet("")

    def _show_item_panel(self, action: dict):
        for i in reversed(range(self._item_layout.count())):
            w = self._item_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        title_row = QWidget()
        title_hl = QHBoxLayout(title_row)
        title_hl.setContentsMargins(0, 4, 0, 2)
        title_hl.setSpacing(8)
        hint = StrongBodyLabel("选择物品或直接使用欧润吉：")
        hint.setStyleSheet("font-size: 12px;")
        title_hl.addWidget(hint)
        cancel_btn = PushButton("✕")
        cancel_btn.setFixedSize(28, 28)
        cancel_btn.setStyleSheet("font-size: 12px; padding: 0px;")
        cancel_btn.clicked.connect(self._close_item_panel)
        title_hl.addStretch()
        title_hl.addWidget(cancel_btn)
        self._item_layout.addWidget(title_row)

        cost = ORANGE_INTERACTION_COST.get(action["key"], 100)
        default_row = QWidget()
        default_hl = QHBoxLayout(default_row)
        default_hl.setContentsMargins(0, 0, 0, 0)
        default_hl.setSpacing(8)

        default_icon = BodyLabel(action["icon"])
        default_icon.setFixedWidth(24)
        default_icon.setStyleSheet("font-size: 18px; background: transparent;")
        default_hl.addWidget(default_icon)

        default_name = BodyLabel(f"{action['name']}基础  {action['desc']}")
        default_hl.addWidget(default_name, 1)

        default_cost = BodyLabel(f"🍊 {cost}")
        default_cost.setStyleSheet("font-weight: bold; color: #FF9800;")
        default_hl.addWidget(default_cost)

        default_btn = PrimaryPushButton("使用")
        default_btn.setFixedSize(50, 28)
        default_btn.clicked.connect(lambda: self._do_default_action(action, cost))
        default_hl.addWidget(default_btn)
        self._item_layout.addWidget(default_row)

        if self._inv_manager:
            cat = action.get("item_category", "")
            items = self._inv_manager.get_items_by_category(cat) if cat else []
            if items:
                sep = BodyLabel("— 使用物品（免费，更有效果）—")
                sep.setAlignment(Qt.AlignCenter)
                sep.setStyleSheet("font-size: 10px; color: #999;")
                self._item_layout.addWidget(sep)

                for row in items:
                    item_key = row["item_key"]
                    info = ITEM_DEFINITIONS.get(item_key, {})
                    qty = row["quantity"]
                    item_row = QWidget()
                    item_hl = QHBoxLayout(item_row)
                    item_hl.setContentsMargins(0, 0, 0, 0)
                    item_hl.setSpacing(8)

                    icon_lbl = BodyLabel(CATEGORY_ICONS.get(cat, "📦"))
                    icon_lbl.setFixedWidth(24)
                    icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
                    item_hl.addWidget(icon_lbl)

                    effects = info.get("effects", {})
                    eff_parts = []
                    eff_labels = {"hunger": "饱食", "mood": "心情", "cleanliness": "清洁", "energy": "能量"}
                    for k, v in effects.items():
                        if k in eff_labels:
                            eff_parts.append(f"{eff_labels[k]}+{v}")
                    eff_str = " ".join(eff_parts) if eff_parts else "无效果"

                    info_widget = QWidget()
                    info_layout = QVBoxLayout(info_widget)
                    info_layout.setContentsMargins(0, 0, 0, 0)
                    info_layout.setSpacing(0)

                    item_name = BodyLabel(f"{info.get('name', item_key)}  ×{qty}")
                    info_layout.addWidget(item_name)

                    item_eff = BodyLabel(eff_str)
                    item_eff.setStyleSheet("font-size: 10px; color: #4CAF50;")
                    info_layout.addWidget(item_eff)
                    item_hl.addWidget(info_widget, 1)

                    rarity = info.get("rarity", "common")
                    rarity_names = {"common": "普通", "rare": "稀有", "legendary": "传说"}
                    rarity_colors = {"common": "#888", "rare": "#2196F3", "legendary": "#FF9800"}
                    rarity_label = BodyLabel(rarity_names.get(rarity, rarity))
                    rarity_label.setAlignment(Qt.AlignCenter)
                    rarity_label.setStyleSheet(
                        f"font-size: 9px; padding: 1px 6px; border-radius: 6px;"
                        f"color: white; background-color: {rarity_colors.get(rarity, '#888')};"
                    )
                    item_hl.addWidget(rarity_label)

                    use_btn = PrimaryPushButton("使用")
                    use_btn.setFixedSize(50, 28)
                    use_btn.clicked.connect(
                        lambda checked, k=item_key: self._use_inventory_item(k, action))
                    item_hl.addWidget(use_btn)
                    self._item_layout.addWidget(item_row)

        self._item_scroll.show()

    def _do_default_action(self, action: dict, cost: int):
        if self._orange_manager:
            if not self._orange_manager.spend_oranges(cost, action["key"]):
                self._action_hint.setText(f"🍊 不够了！({action['name']}需要 {cost} 🍊)")
                self._action_hint.setStyleSheet("font-size: 11px; color: #f44336;")
                self._close_item_panel()
                return
        if self._attr_manager:
            self._attr_manager.update_attribute(action["attr"], action["delta"])
        self._action_hint.setText(
            f"✅ {action['icon']} {action['name']}完成！{action['desc']} (-{cost}🍊)")
        self._action_hint.setStyleSheet("font-size: 11px; color: #4CAF50;")
        self._close_item_panel()
        self._refresh_buttons()
        self.refresh_data()

    def _use_inventory_item(self, item_key: str, action: dict):
        if not self._inv_manager:
            return
        if not self._inv_manager.has_item(item_key):
            self._action_hint.setText("⚠️ 物品数量不足！")
            self._action_hint.setStyleSheet("font-size: 11px; color: #f44336;")
            return
        info = ITEM_DEFINITIONS.get(item_key, {})
        self._inv_manager.use_item(item_key, self._attr_manager)
        eff_parts = []
        eff_labels = {"hunger": "饱食", "mood": "心情", "cleanliness": "清洁", "energy": "能量"}
        for k, v in info.get("effects", {}).items():
            if k in eff_labels:
                eff_parts.append(f"{eff_labels[k]}+{v}")
        eff_str = " ".join(eff_parts) if eff_parts else ""
        self._action_hint.setText(f"✅ 使用了 {info.get('name', item_key)}！{eff_str}")
        self._action_hint.setStyleSheet("font-size: 11px; color: #4CAF50;")
        self._close_item_panel()
        self._refresh_buttons()
        self.refresh_data()

    def _refresh_buttons(self):
        for act in HOME_ACTIONS:
            btn = self._action_buttons.get(act["key"])
            if not btn:
                continue
            cost = ORANGE_INTERACTION_COST.get(act["key"], 100)
            has_items = False
            if self._inv_manager:
                cat = act.get("item_category", "")
                items = self._inv_manager.get_items_by_category(cat) if cat else []
                has_items = len(items) > 0
            can = has_items or (self._orange_manager and self._orange_manager.balance >= cost)
            btn.setEnabled(can)
            if has_items:
                btn.setText(f"{act['icon']}  {act['name']} (有物品)")
            elif self._orange_manager and self._orange_manager.balance >= cost:
                btn.setText(f"{act['icon']}  {act['name']} (-{cost}🍊)")
            else:
                btn.setText(f"{act['icon']}  {act['name']} (🍊不足)")

    def refresh_data(self):
        if self._orange_manager:
            level = self._orange_manager.doro_level
            title_str = DORO_LEVEL_TITLES.get(level, "Doro崽")
            self._doro_info.setText(f"⭐ Lv.{level} {title_str}  |  🍊 × {self._orange_manager.balance}")
        self._refresh_buttons()
        if self._attr_manager:
            attrs = self._attr_manager.get_all_attributes()
            for attr_name, value in attrs.items():
                if attr_name in self._attr_value_labels:
                    self._attr_value_labels[attr_name].setText(f"{value:.0f}%")
                bar_len = 20
                filled = int(value / 100 * bar_len)
                bar = "█" * filled + "░" * (bar_len - filled)
                color = "#4CAF50"
                if value < 20:
                    color = "#f44336"
                elif value < 50:
                    color = "#FF9800"
                if attr_name in self._attr_bar_labels:
                    self._attr_bar_labels[attr_name].setText(bar)
                    self._attr_bar_labels[attr_name].setStyleSheet(
                        f"font-size: 13px; letter-spacing: 1px; color: {color}; background: transparent;")

                status = self._attr_manager.get_status(attr_name)
                status_text = {"critical": "危急", "warning": "警告", "good": "良好"}.get(status, "良好")
                status_color = {
                    "critical": "#f44336", "warning": "#FF9800", "good": "#4CAF50"
                }.get(status, "#4CAF50")
                if attr_name in self._attr_status_labels:
                    lbl = self._attr_status_labels[attr_name]
                    lbl.setText(status_text)
                    lbl.setStyleSheet(f"""
                        font-size: 10px; padding: 2px 8px; border-radius: 8px;
                        color: white; background-color: {status_color};
                    """)
