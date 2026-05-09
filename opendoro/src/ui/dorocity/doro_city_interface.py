from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QGridLayout, QStackedWidget, QListWidgetItem)
from qfluentwidgets import (CardWidget, PrimaryPushButton, PushButton, ScrollArea,
                             TitleLabel, BodyLabel, StrongBodyLabel, HorizontalSeparator,
                             isDarkTheme, ListWidget)
from qfluentwidgets import FluentIcon as FIF

from .item_constants import ITEM_DEFINITIONS, SHOP_TABS, CATEGORY_ICONS, ITEM_CATEGORIES
from .work_page import WorkPage, WorkCompletionPopup
from .home_page import HomePage
from .cafe_page import CafePage
from .fruit_shop_page import FruitShopPage
from .park_page import ParkPage


RARITY_COLORS = {
    "common": "#888",
    "rare": "#2196F3",
    "legendary": "#FF9800",
}

LOCATIONS = [
    {
        "key": "home",
        "icon": "🏠",
        "name": "Doro的家",
        "desc": "休息、互动、看属性",
        "color": "#FF8C00",
    },
    {
        "key": "fruit_shop",
        "icon": "🍊",
        "name": "欧润吉水果店",
        "desc": "打工赚欧润吉",
        "color": "#FF9800",
        "locked": True,
        "unlock_level": 2,
    },
    {
        "key": "convenience_store",
        "icon": "🏪",
        "name": "便利店",
        "desc": "购买食物和日用品",
        "color": "#4CAF50",
    },
    {
        "key": "park",
        "icon": "🌳",
        "name": "小镇公园",
        "desc": "散步、触发事件",
        "color": "#8BC34A",
    },
    {
        "key": "cafe",
        "icon": "☕",
        "name": "猫咪咖啡馆",
        "desc": "打工、社交",
        "color": "#795548",
        "locked": True,
        "unlock_level": 4,
    },
    {
        "key": "library",
        "icon": "📚",
        "name": "镇图书馆",
        "desc": "学习技能",
        "color": "#607D8B",
        "locked": True,
        "unlock_level": 3,
    },
    {
        "key": "amusement_park",
        "icon": "🎪",
        "name": "游乐场",
        "desc": "游玩、限定玩具",
        "color": "#E91E63",
        "locked": True,
        "unlock_level": 5,
    },
]


class LocationCard(CardWidget):
    location_clicked = pyqtSignal(str)

    def __init__(self, location: dict, parent=None):
        super().__init__(parent)
        self._location = location
        self.setCursor(Qt.PointingHandCursor)
        self._init_ui()
        self._apply_theme(False)

    def _init_ui(self):
        self.setFixedSize(150, 120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = BodyLabel(self._location["icon"])
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        layout.addWidget(icon_label)

        name_label = StrongBodyLabel(self._location["name"])
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        self._bottom_label = BodyLabel()
        self._bottom_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._bottom_label)
        self._refresh_bottom_label()

    def _refresh_bottom_label(self):
        if self._location.get("locked"):
            self._bottom_label.setText(f"🔒 Lv.{self._location['unlock_level']}解锁")
            self._bottom_label.setStyleSheet("font-size: 10px; color: #999;")
        else:
            self._bottom_label.setText(self._location["desc"])
            self._bottom_label.setStyleSheet("font-size: 10px; color: #888;")

    def update_unlock_state(self, doro_level: int):
        if "unlock_level" in self._location:
            was_locked = self._location.get("locked", False)
            self._location["locked"] = doro_level < self._location["unlock_level"]
            if was_locked != self._location["locked"]:
                self._refresh_bottom_label()
                self._apply_theme(self._is_dark)

    def mousePressEvent(self, event):
        if not self._location.get("locked"):
            self.location_clicked.emit(self._location["key"])
        super().mousePressEvent(event)

    def _apply_theme(self, is_dark: bool):
        self._is_dark = is_dark
        locked = self._location.get("locked")
        self.setCursor(Qt.PointingHandCursor if not locked else Qt.ArrowCursor)
        self.setEnabled(not locked)
        if locked:
            self.setStyleSheet("""
                LocationCard {
                    border-radius: 12px;
                    opacity: 0.4;
                }
            """)
        else:
            self.setStyleSheet("""
                LocationCard {
                    border-radius: 12px;
                }
            """)

    def update_theme(self, is_dark: bool):
        self._apply_theme(is_dark)


class ClickableCard(CardWidget):
    item_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.item_clicked.emit()
        super().mousePressEvent(event)


class ItemSlot(ClickableCard):
    def __init__(self, item_key: str, quantity: int = 1, parent=None):
        super().__init__(parent)
        self._item_key = item_key
        self._quantity = quantity
        self.setFixedSize(90, 100)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        info = ITEM_DEFINITIONS.get(self._item_key, {})
        category = info.get("category", "food")
        icon = CATEGORY_ICONS.get(category, "📦")

        icon_label = BodyLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(icon_label)

        name_label = BodyLabel(info.get("name", self._item_key))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-size: 10px; font-weight: bold; background: transparent;")
        layout.addWidget(name_label)

        if self._quantity > 1:
            qty_label = BodyLabel(f"×{self._quantity}")
            qty_label.setAlignment(Qt.AlignCenter)
            qty_label.setStyleSheet("font-size: 10px; color: #FF9800; background: transparent;")
            layout.addWidget(qty_label)

        self.setStyleSheet("""
            ClickableCard {
                border-radius: 8px;
            }
        """)

    @property
    def item_key(self):
        return self._item_key


class ShopPage(QWidget):
    item_purchased = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, orange_manager=None, inventory_manager=None, parent=None):
        super().__init__(parent)
        self._orange_manager = orange_manager
        self._inv_manager = inventory_manager
        self._current_tab = "food"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        header.addStretch()
        layout.addLayout(header)

        title = TitleLabel("🏪 便利店")
        layout.addWidget(title)

        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(4)

        self._tab_buttons = {}
        for tab_key, tab_name in SHOP_TABS:
            btn = PushButton(tab_name)
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=tab_key: self._switch_tab(k))
            tab_layout.addWidget(btn)
            self._tab_buttons[tab_key] = btn
        tab_layout.addStretch()
        layout.addWidget(tab_widget)

        self._item_list = ListWidget()
        self._item_list.setSpacing(1)
        layout.addWidget(self._item_list)

        self._switch_tab("food")

    def _switch_tab(self, tab_key: str):
        self._current_tab = tab_key
        for key, btn in self._tab_buttons.items():
            btn.setEnabled(key != tab_key)
        self._load_items()

    def _load_items(self):
        self._item_list.clear()

        items = [
            (k, v) for k, v in ITEM_DEFINITIONS.items()
            if v.get("category") == self._current_tab and v.get("price", 0) > 0
        ]

        for item_key, info in items:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 8, 14, 8)
            row_layout.setSpacing(10)

            icon = BodyLabel(CATEGORY_ICONS.get(info["category"], "📦"))
            icon.setFixedWidth(28)
            icon.setStyleSheet("font-size: 20px; background: transparent;")
            row_layout.addWidget(icon)

            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(1)

            name_label = BodyLabel(info["name"])
            desc_label = BodyLabel(info.get("description", ""))
            desc_label.setStyleSheet("font-size: 10px;")

            info_layout.addWidget(name_label)
            info_layout.addWidget(desc_label)
            row_layout.addWidget(info_widget, 1)

            price_label = BodyLabel(f"🍊 {info['price']}")
            price_label.setStyleSheet("font-weight: bold;")
            row_layout.addWidget(price_label)

            buy_btn = PrimaryPushButton("购买")
            buy_btn.setFixedSize(54, 28)
            buy_btn.clicked.connect(lambda checked, k=item_key: self._buy_item(k))
            row_layout.addWidget(buy_btn)

            list_item = QListWidgetItem()
            list_item.setSizeHint(row.sizeHint())
            self._item_list.addItem(list_item)
            self._item_list.setItemWidget(list_item, row)

    def _buy_item(self, item_key: str):
        info = ITEM_DEFINITIONS.get(item_key, {})
        price = info.get("price", 0)
        if not self._orange_manager or self._orange_manager.balance < price:
            return
        if not self._inv_manager:
            return

        self._orange_manager.spend_oranges(price, f"购买{info.get('name', item_key)}")
        self._inv_manager.add_item(item_key)
        self.item_purchased.emit(item_key)

    def refresh_data(self):
        self._load_items()


class InventoryPage(QWidget):
    item_used = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self, inventory_manager=None, attr_manager=None, parent=None):
        super().__init__(parent)
        self._inv_manager = inventory_manager
        self._attr_manager = attr_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        back_btn = PushButton("◀ 回都市")
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)
        header.addStretch()

        self._total_label = BodyLabel("共 0 件物品")
        header.addWidget(self._total_label)
        layout.addLayout(header)

        title = TitleLabel("🎒 物品栏")
        layout.addWidget(title)

        self._items_scroll = ScrollArea()
        self._items_scroll.setWidgetResizable(True)
        self._items_container = QWidget()
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(8)
        self._items_layout.addStretch()
        self._items_scroll.setWidget(self._items_container)
        layout.addWidget(self._items_scroll)

        self._empty_label = BodyLabel("物品栏空空如也~ 去便利店买点东西吧！")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #888; padding: 40px;")
        layout.addWidget(self._empty_label)

    def refresh_data(self):
        for i in reversed(range(self._items_layout.count())):
            w = self._items_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        if not self._inv_manager:
            self._empty_label.setVisible(True)
            self._total_label.setText("共 0 件物品")
            return

        items = self._inv_manager.get_all_items()
        if not items:
            self._empty_label.setVisible(True)
            self._total_label.setText("共 0 件物品")
            return

        self._empty_label.setVisible(False)
        total_qty = sum(row["quantity"] for row in items)
        self._total_label.setText(f"共 {total_qty} 件物品")

        categories = {}
        for row in items:
            cat = row["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(row)

        for cat, cat_items in categories.items():
            cat_name = ITEM_CATEGORIES.get(cat, cat)
            cat_icon = CATEGORY_ICONS.get(cat, "📦")
            cat_label = StrongBodyLabel(f"{cat_icon} {cat_name}")
            self._items_layout.insertWidget(self._items_layout.count() - 1, cat_label)

            grid = QWidget()
            grid_layout = QGridLayout(grid)
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(6)

            for i, row in enumerate(cat_items):
                slot = ItemSlot(row["item_key"], row["quantity"])
                slot.item_clicked.connect(lambda k=row["item_key"]: self._on_item_click(k))
                grid_layout.addWidget(slot, i // 5, i % 5)

            self._items_layout.insertWidget(self._items_layout.count() - 1, grid)

    def _on_item_click(self, item_key: str):
        if not self._inv_manager or not self._attr_manager:
            return
        info = ITEM_DEFINITIONS.get(item_key, {})
        if not info.get("effects"):
            return
        self._inv_manager.use_item(item_key, self._attr_manager)
        self.item_used.emit(item_key)
        self.refresh_data()


class DoroCityInterface(QWidget):
    inventory_updated = pyqtSignal()

    PAGE_MAP = 0
    PAGE_HOME = 1
    PAGE_INVENTORY = 2
    PAGE_SHOP = 3
    PAGE_WORK = 4
    PAGE_CAFE = 5
    PAGE_FRUIT_SHOP = 6
    PAGE_PARK = 7

    def __init__(self, orange_manager=None, attr_manager=None, parent=None):
        super().__init__(parent)
        self.setObjectName("DoroCityInterface")
        self._orange_manager = orange_manager
        self._attr_manager = attr_manager
        self._inv_manager = None
        self._inventory_page = None
        self._shop_page = None
        self._work_page = None
        self._work_popup = None
        self._home_page = None
        self._cafe_page = None
        self._fruit_shop_page = None
        self._park_page = None

        self._init_ui()

    def set_inventory_manager(self, inv_manager):
        self._inv_manager = inv_manager
        if self._orange_manager:
            self._orange_manager.orange_changed.connect(self._on_orange_changed)
        if self._inventory_page is None:
            self._inventory_page = InventoryPage(inv_manager, self._attr_manager)
            self._inventory_page.back_requested.connect(self._go_to_map)
            self._stack.addWidget(self._inventory_page)
        else:
            self._inventory_page._inv_manager = inv_manager

        if self._shop_page is None:
            self._shop_page = ShopPage(self._orange_manager, inv_manager)
            self._shop_page.back_requested.connect(self._go_to_map)
            self._stack.addWidget(self._shop_page)
        else:
            self._shop_page._inv_manager = inv_manager

        if self._inv_manager:
            self._inv_manager.inventory_changed.connect(self._on_inventory_changed)

        if self._home_page:
            self._home_page._inv_manager = inv_manager

        if self._work_page is None:
            self._work_page = WorkPage(self._orange_manager, self._attr_manager)
            self._work_page.back_requested.connect(self._go_to_map)
            self._work_page.work_completed.connect(self._on_work_completed)
            self._stack.addWidget(self._work_page)
            self._work_popup = WorkCompletionPopup(self._work_page)

        if self._cafe_page is None:
            self._cafe_page = CafePage(self._orange_manager, self._attr_manager, inv_manager)
            self._cafe_page.back_requested.connect(self._go_to_map)
            self._cafe_page.work_completed.connect(self._on_work_completed)
            self._stack.addWidget(self._cafe_page)

        if self._fruit_shop_page is None:
            self._fruit_shop_page = FruitShopPage(self._orange_manager, self._attr_manager)
            self._fruit_shop_page.back_requested.connect(self._go_to_map)
            self._fruit_shop_page.work_completed.connect(self._on_work_completed)
            self._stack.addWidget(self._fruit_shop_page)

        if self._park_page is None:
            self._park_page = ParkPage(self._orange_manager, self._attr_manager)
            self._park_page.back_requested.connect(self._go_to_map)
            self._stack.addWidget(self._park_page)

    def set_attr_manager(self, attr_manager):
        self._attr_manager = attr_manager
        if self._inventory_page:
            self._inventory_page._attr_manager = attr_manager
        if self._work_page:
            self._work_page._attr_manager = attr_manager
        if self._home_page:
            self._home_page._attr_manager = attr_manager
        if self._cafe_page:
            self._cafe_page._attr_manager = attr_manager
        if self._fruit_shop_page:
            self._fruit_shop_page._attr_manager = attr_manager
        if self._park_page:
            self._park_page._attr_manager = attr_manager

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        title = TitleLabel("🏙️ Doro都市")
        header.addWidget(title)
        header.addStretch()

        self._orange_label = BodyLabel("🍊 × 0")
        self._orange_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(self._orange_label)
        main_layout.addLayout(header)

        test_bar = QWidget()
        test_layout = QHBoxLayout(test_bar)
        test_layout.setContentsMargins(0, 0, 0, 0)
        test_layout.setSpacing(4)

        test_label = BodyLabel("🧪 测试：")
        test_label.setStyleSheet("font-size: 11px; color: #888;")
        test_layout.addWidget(test_label)

        for lv in [1, 3, 5, 10]:
            btn = PushButton(f"Lv.{lv}")
            btn.setFixedHeight(22)
            btn.setMinimumWidth(40)
            btn.setStyleSheet("font-size: 10px; padding: 0 6px;")
            btn.clicked.connect(lambda checked, l=lv: self._test_set_level(l))
            test_layout.addWidget(btn)

        for amount in [500, 1000, 5000]:
            btn = PushButton(f"+{amount}🍊")
            btn.setFixedHeight(22)
            btn.setMinimumWidth(55)
            btn.setStyleSheet("font-size: 10px; padding: 0 6px;")
            btn.clicked.connect(lambda checked, a=amount: self._test_add_oranges(a))
            test_layout.addWidget(btn)

        clear_btn = PushButton("×0🍊")
        clear_btn.setFixedHeight(22)
        clear_btn.setMinimumWidth(40)
        clear_btn.setStyleSheet("font-size: 10px; padding: 0 6px; color: #E53935;")
        clear_btn.clicked.connect(self._test_clear_oranges)
        test_layout.addWidget(clear_btn)

        test_layout.addStretch()
        main_layout.addWidget(test_bar)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; }")
        self._map_page = self._create_map_page()
        self._stack.addWidget(self._map_page)
        self._home_page = HomePage(self._orange_manager, self._attr_manager, None)
        self._home_page.back_requested.connect(self._go_to_map)
        self._stack.addWidget(self._home_page)
        main_layout.addWidget(self._stack)
        self._refresh_orange()
        self._refresh_location_locks()

    def _create_map_page(self):
        page = QWidget()
        page.setObjectName("doroCityMapPage")
        page.setStyleSheet("#doroCityMapPage { background: transparent; }")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        status_card = CardWidget()
        status_card.setMaximumHeight(50)
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(14, 8, 14, 8)
        status_layout.setSpacing(10)

        self._status_hint = BodyLabel("点击地点前往探索！")
        status_layout.addWidget(self._status_hint)
        status_layout.addStretch()

        self._inventory_btn = PushButton("🎒 物品栏")
        self._inventory_btn.setFixedHeight(28)
        self._inventory_btn.clicked.connect(self._on_inventory_btn)
        status_layout.addWidget(self._inventory_btn)

        self._shop_btn = PrimaryPushButton("🏪 便利店")
        self._shop_btn.setFixedHeight(28)
        self._shop_btn.clicked.connect(self._on_shop_btn)
        status_layout.addWidget(self._shop_btn)

        layout.addWidget(status_card)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        map_card_container = QWidget()
        map_card_container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(map_card_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        map_card = CardWidget()
        map_card.setObjectName("doroCityMapCard")
        map_layout = QGridLayout(map_card)
        map_layout.setContentsMargins(16, 16, 16, 16)
        map_layout.setSpacing(10)

        self._location_cards = {}
        for i, loc in enumerate(LOCATIONS):
            card = LocationCard(loc)
            card.location_clicked.connect(self._on_location_click)
            map_layout.addWidget(card, i // 3, i % 3, Qt.AlignCenter)
            self._location_cards[loc["key"]] = card

        container_layout.addWidget(map_card)
        scroll.setWidget(map_card_container)
        layout.addWidget(scroll)
        return page

    def _go_to_map(self):
        self._stack.setCurrentIndex(self.PAGE_MAP)

    def _test_set_level(self, level: int):
        if self._orange_manager:
            self._orange_manager.set_level_for_test(level)

    def _test_add_oranges(self, amount: int):
        if self._orange_manager:
            self._orange_manager.set_oranges_for_test(
                self._orange_manager.balance + amount
            )

    def _test_clear_oranges(self):
        if self._orange_manager:
            self._orange_manager.set_oranges_for_test(0)

    def _on_inventory_btn(self):
        if self._inventory_page:
            self._inventory_page.refresh_data()
        self._stack.setCurrentIndex(self.PAGE_INVENTORY)

    def _on_shop_btn(self):
        if self._shop_page:
            self._shop_page.refresh_data()
        self._stack.setCurrentIndex(self.PAGE_SHOP)

    def _on_location_click(self, location_key: str):
        try:
            if location_key == "convenience_store":
                if self._shop_page:
                    self._shop_page.refresh_data()
                self._stack.setCurrentIndex(self.PAGE_SHOP)
            elif location_key == "home":
                if self._home_page:
                    self._home_page.refresh_data()
                self._stack.setCurrentIndex(self.PAGE_HOME)
            elif location_key == "park":
                if self._park_page:
                    self._park_page.open_location()
                self._stack.setCurrentIndex(self.PAGE_PARK)
            elif location_key == "fruit_shop":
                if self._fruit_shop_page:
                    self._fruit_shop_page.open_location()
                self._stack.setCurrentIndex(self.PAGE_FRUIT_SHOP)
            elif location_key == "cafe":
                if self._cafe_page:
                    self._cafe_page.open_location()
                self._stack.setCurrentIndex(self.PAGE_CAFE)
            elif location_key == "library":
                self._status_hint.setText("📚 镇图书馆 (学习功能即将上线)")
            elif location_key == "amusement_park":
                self._status_hint.setText("🎪 游乐场 (游玩功能即将上线)")
        except Exception:
            pass

    def _on_orange_changed(self, balance: int, today: int):
        self._refresh_orange()

    def _on_work_completed(self, earnings: int, message: str):
        if self._work_popup:
            self._work_popup.show_message(message)
        self._refresh_orange()

    def _on_inventory_changed(self):
        if self._inventory_page:
            self._inventory_page.refresh_data()
        self.inventory_updated.emit()

    def _refresh_orange(self):
        if self._orange_manager:
            self._orange_label.setText(f"🍊 × {self._orange_manager.balance}")

    def update_theme(self, is_dark: bool = None):
        if is_dark is None:
            is_dark = isDarkTheme()
        for card in self._location_cards.values():
            card.update_theme(is_dark)
        if self._cafe_page:
            self._cafe_page.update_theme(is_dark)
        if self._fruit_shop_page:
            self._fruit_shop_page.update_theme(is_dark)
        if self._park_page:
            self._park_page.update_theme(is_dark)
        self._refresh_orange()

    def refresh_data(self):
        self._refresh_orange()
        self._refresh_location_locks()
        if self._shop_page:
            self._shop_page.refresh_data()
        if self._work_page:
            self._work_page.refresh_data()
        if self._home_page:
            self._home_page.refresh_data()
        if self._cafe_page:
            self._cafe_page.refresh_data()
        if self._fruit_shop_page:
            self._fruit_shop_page.refresh_data()
        if self._park_page:
            self._park_page.refresh_data()

    def _refresh_location_locks(self):
        doro_level = self._orange_manager.doro_level if self._orange_manager else 1
        for card in self._location_cards.values():
            card.update_unlock_state(doro_level)
