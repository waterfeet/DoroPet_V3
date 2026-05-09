from PyQt5.QtCore import QObject, pyqtSignal

from src.core.database import PetDatabase
from src.core.logger import logger
from .item_constants import ITEM_DEFINITIONS, ITEM_CATEGORIES, CATEGORY_ICONS


class InventoryManager(QObject):
    inventory_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._db = PetDatabase()

    def get_all_items(self) -> list:
        return self._db.load_inventory()

    def get_items_by_category(self, category: str) -> list:
        return self._db.get_inventory_by_category(category)

    def get_item_count(self, item_key: str = None) -> int:
        return self._db.get_inventory_count(item_key)

    def has_item(self, item_key: str, quantity: int = 1) -> bool:
        return self._db.get_inventory_count(item_key) >= quantity

    def add_item(self, item_key: str, quantity: int = 1):
        info = ITEM_DEFINITIONS.get(item_key)
        if not info:
            logger.warning(f"Unknown item key: {item_key}")
            return
        self._db.add_inventory_item(
            item_key=item_key,
            name=info["name"],
            category=info["category"],
            quantity=quantity,
            rarity=info.get("rarity", "common"),
        )
        logger.info(f"Added {quantity}x {info['name']} to inventory")
        self.inventory_changed.emit()

    def remove_item(self, item_key: str, quantity: int = 1) -> bool:
        result = self._db.remove_inventory_item(item_key, quantity)
        if result:
            info = ITEM_DEFINITIONS.get(item_key, {})
            logger.info(f"Removed {quantity}x {info.get('name', item_key)} from inventory")
            self.inventory_changed.emit()
        return result

    def use_item(self, item_key: str, attr_manager) -> bool:
        info = ITEM_DEFINITIONS.get(item_key)
        if not info:
            return False
        if not self.has_item(item_key):
            return False

        effects = info.get("effects", {})
        attr_map = {
            "hunger": "hunger",
            "mood": "mood",
            "cleanliness": "cleanliness",
            "energy": "energy",
        }
        for effect_key, value in effects.items():
            if effect_key in attr_map and attr_manager:
                attr_manager.update_attribute(effect_key, value)

        self.remove_item(item_key, 1)
        logger.info(f"Used {info['name']}: {effects}")
        return True

    def get_info(self, item_key: str) -> dict:
        return ITEM_DEFINITIONS.get(item_key, {})

    def get_category_name(self, category: str) -> str:
        return ITEM_CATEGORIES.get(category, category)

    def get_category_icon(self, category: str) -> str:
        return CATEGORY_ICONS.get(category, "📦")

    def get_total_items(self) -> int:
        return self._db.get_inventory_count()

    def get_categories_with_items(self) -> list:
        all_items = self._db.load_inventory()
        categories = set()
        for item in all_items:
            categories.add(item["category"])
        return sorted(categories, key=lambda c: list(ITEM_CATEGORIES.keys()).index(c) if c in ITEM_CATEGORIES else 99)
