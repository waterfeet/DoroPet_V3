ITEM_CATEGORIES = {
    "food": "🍖 食物",
    "toy": "🎮 玩具",
    "daily": "🧹 日用品",
    "ingredient": "🍳 食材",
    "accessory": "🎀 装饰品",
    "collectible": "💎 收藏品",
}

ITEM_DEFINITIONS = {
    "cat_food": {
        "name": "普通猫粮", "category": "food", "price": 50,
        "effects": {"hunger": 15},
        "description": "基础口粮，填饱肚子", "rarity": "common",
    },
    "orange_jelly": {
        "name": "欧润吉果冻", "category": "food", "price": 50,
        "effects": {"hunger": 20, "mood": 8},
        "description": "Doro最爱的果冻！Q弹可口", "rarity": "common",
    },
    "bento": {
        "name": "三色便当", "category": "food", "price": 100,
        "effects": {"hunger": 35, "mood": 8},
        "description": "营养均衡的精致便当", "rarity": "common",
    },
    "taiyaki": {
        "name": "鲷鱼烧", "category": "food", "price": 100,
        "effects": {"hunger": 25, "mood": 15},
        "description": "热乎乎的鲷鱼形状点心", "rarity": "common",
    },
    "sushi_platter": {
        "name": "豪华寿司拼盘", "category": "food", "price": 250,
        "effects": {"hunger": 50, "mood": 20},
        "description": "新鲜刺身拼盘，附赠小玩具", "rarity": "rare",
    },
    "orange_cake": {
        "name": "欧润吉蛋糕", "category": "food", "price": 300,
        "effects": {"hunger": 45, "mood": 30},
        "description": "满满的欧润吉风味生日蛋糕", "rarity": "rare",
    },
    "yarn_ball": {
        "name": "毛线球", "category": "toy", "price": 50,
        "effects": {"mood": 15},
        "description": "软软的彩色毛线球", "rarity": "common",
    },
    "cat_teaser": {
        "name": "逗猫棒", "category": "toy", "price": 100,
        "effects": {"mood": 22},
        "description": "带铃铛的羽毛逗猫棒", "rarity": "common",
    },
    "puzzle_set": {
        "name": "拼图套装", "category": "toy", "price": 150,
        "effects": {"mood": 30},
        "description": "100片迷你拼图，有概率获得收藏品", "rarity": "common",
    },
    "music_box": {
        "name": "音乐盒", "category": "toy", "price": 300,
        "effects": {"mood": 25, "energy": 10},
        "description": "舒缓的音乐让Doro心情持续变好", "rarity": "rare",
    },
    "orange_plush": {
        "name": "欧润吉玩偶", "category": "toy", "price": 500,
        "effects": {"mood": 40, "energy": 15},
        "description": "软萌的欧润吉形状抱枕", "rarity": "rare",
    },
    "small_towel": {
        "name": "小毛巾", "category": "daily", "price": 50,
        "effects": {"cleanliness": 20},
        "description": "柔软的纯棉小毛巾", "rarity": "common",
    },
    "soap": {
        "name": "香皂", "category": "daily", "price": 100,
        "effects": {"cleanliness": 35, "mood": 5},
        "description": "欧润吉香味的沐浴皂", "rarity": "common",
    },
    "bath_salt": {
        "name": "花瓣浴盐", "category": "daily", "price": 150,
        "effects": {"cleanliness": 50, "mood": 15},
        "description": "让Doro享受SPA级泡澡", "rarity": "rare",
    },
    "flour": {
        "name": "面粉", "category": "ingredient", "price": 50,
        "effects": {}, "description": "烘焙基础食材", "rarity": "common",
    },
    "egg": {
        "name": "鸡蛋", "category": "ingredient", "price": 50,
        "effects": {}, "description": "新鲜农场鸡蛋", "rarity": "common",
    },
    "butter": {
        "name": "黄油", "category": "ingredient", "price": 50,
        "effects": {}, "description": "香浓的动物黄油", "rarity": "common",
    },
    "milk": {
        "name": "牛奶", "category": "ingredient", "price": 50,
        "effects": {}, "description": "新鲜牧场牛奶", "rarity": "common",
    },
    "orange_jam": {
        "name": "欧润吉果酱", "category": "ingredient", "price": 100,
        "effects": {}, "description": "手工熬制的欧润吉果酱", "rarity": "rare",
    },
    "strawberry": {
        "name": "草莓", "category": "ingredient", "price": 50,
        "effects": {}, "description": "鲜红多汁的大草莓", "rarity": "common",
    },
    "chocolate": {
        "name": "巧克力", "category": "ingredient", "price": 100,
        "effects": {}, "description": "醇厚丝滑的黑巧克力", "rarity": "common",
    },
    "flower_clip": {
        "name": "小花发夹", "category": "accessory", "price": 100,
        "effects": {"mood": 8}, "description": "可爱的粉色小花发夹", "rarity": "common",
    },
    "bow_tie": {
        "name": "蝴蝶结领结", "category": "accessory", "price": 200,
        "effects": {"mood": 12}, "description": "精致的蝴蝶结，戴上特别精神", "rarity": "rare",
    },
    "scarf": {
        "name": "小围巾", "category": "accessory", "price": 250,
        "effects": {"mood": 15}, "description": "暖暖的毛线围巾", "rarity": "rare",
    },
    "orange_hat": {
        "name": "欧润吉帽子", "category": "accessory", "price": 400,
        "effects": {"mood": 22}, "description": "Doro专属欧润吉造型帽", "rarity": "rare",
    },
    "golden_orange": {
        "name": "金色欧润吉", "category": "collectible", "price": 0,
        "effects": {}, "description": "传说中的金色欧润吉！闪耀着温暖光芒", "rarity": "legendary",
    },
    "doro_diary": {
        "name": "Doro的日记本", "category": "collectible", "price": 0,
        "effects": {}, "description": "记录着Doro日常的小本子", "rarity": "legendary",
    },
}

SHOP_TABS = [
    ("food", "🍖 食物"),
    ("toy", "🎮 玩具"),
    ("daily", "🧹 日用品"),
    ("ingredient", "🍳 食材"),
    ("accessory", "🎀 装饰"),
]

CATEGORY_ICONS = {
    "food": "🍖",
    "toy": "🎮",
    "daily": "🧹",
    "ingredient": "🍳",
    "accessory": "🎀",
    "collectible": "💎",
}
