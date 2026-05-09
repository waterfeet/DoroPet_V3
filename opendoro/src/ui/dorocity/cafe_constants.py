CAFE_CATS = [
    {
        "key": "mimi",
        "name": "小咪",
        "emoji": "🐱",
        "desc": "害羞的白色小猫，喜欢躲在角落观察大家",
        "personality": "害羞",
        "favorite": "cat_food",
    },
    {
        "key": "tora",
        "name": "虎虎",
        "emoji": "🐯",
        "desc": "活泼的橘猫，活力满满，最爱追着逗猫棒跑",
        "personality": "活泼",
        "favorite": "cat_teaser",
    },
    {
        "key": "kuro",
        "name": "小黑",
        "emoji": "🐈‍⬛",
        "desc": "优雅的黑猫，总在窗边晒太阳，举止高贵",
        "personality": "优雅",
        "favorite": "taiyaki",
    },
    {
        "key": "hana",
        "name": "花花",
        "emoji": "😺",
        "desc": "三花猫小公主，咖啡馆的团宠，最喜欢被摸摸头",
        "personality": "粘人",
        "favorite": "orange_jelly",
    },
]

CAFE_DRINKS = [
    {
        "key": "latte",
        "name": "猫咪拿铁",
        "emoji": "☕",
        "price": 30,
        "effects": {"mood": 10, "energy": 5},
        "desc": "温暖的拿铁，奶泡上画着小猫脸",
    },
    {
        "key": "mocha",
        "name": "猫爪摩卡",
        "emoji": "🍫",
        "price": 40,
        "effects": {"mood": 15, "energy": 8},
        "desc": "巧克力摩卡配猫爪棉花糖",
    },
    {
        "key": "orange_latte",
        "name": "欧润吉拿铁",
        "emoji": "🍊",
        "price": 60,
        "effects": {"mood": 20, "energy": 12, "hunger": 5},
        "desc": "咖啡姐姐特调！Doro的最爱，满满欧润吉风味",
    },
    {
        "key": "cat_tea",
        "name": "猫咪奶茶",
        "emoji": "🧋",
        "price": 35,
        "effects": {"mood": 12, "energy": 6},
        "desc": "装在可爱猫爪杯里的香浓奶茶",
    },
    {
        "key": "matcha",
        "name": "抹茶猫咪",
        "emoji": "🍵",
        "price": 45,
        "effects": {"mood": 18, "energy": 10},
        "desc": "日式抹茶拿铁，绿绿的很健康",
    },
]

CAFE_INTERACTIONS = [
    {
        "key": "feed_cats",
        "name": "喂猫咪",
        "icon": "🍖",
        "desc": "用猫粮喂咖啡馆的猫咪们",
        "item_key": "cat_food",
        "effects": {"mood": 10},
        "hint_positive": "猫咪们开心地吃着猫粮，发出满足的咕噜声~",
        "hint_no_item": "没有猫粮了，去便利店买一些吧！",
    },
    {
        "key": "play_with_cats",
        "name": "逗猫咪",
        "icon": "🎣",
        "desc": "用逗猫棒和猫咪们玩耍",
        "item_key": "cat_teaser",
        "effects": {"mood": 15},
        "hint_positive": "猫咪们追着逗猫棒跳来跳去，玩得不亦乐乎！",
        "hint_no_item": "没有逗猫棒了，去便利店买一根吧！",
    },
]

CAFE_RANDOM_EVENTS = [
    {
        "name": "🐱 小咪主动蹭了蹭Doro！",
        "prob": 25,
        "effect": {"mood": 8},
        "message": "小咪今天心情很好，主动过来蹭蹭Doro~",
    },
    {
        "name": "🌟 花花表演了一个后空翻！",
        "prob": 12,
        "effect": {"mood": 12},
        "message": "花花突然翻了个跟头，客人们都鼓掌了！",
    },
    {
        "name": "🍊 在沙发缝里发现了欧润吉！",
        "prob": 15,
        "effect": {"oranges": 30},
        "message": "咦？沙发缝里藏着一颗欧润吉，是哪个猫咪藏的？",
    },
    {
        "name": "☕ 咖啡姐姐送了特调饮品！",
        "prob": 18,
        "effect": {"mood": 10, "energy": 5},
        "message": "咖啡姐姐笑着端来一杯新研发的饮品让Doro尝尝~",
    },
    {
        "name": "😴 虎虎在Doro腿上睡着了...",
        "prob": 20,
        "effect": {"mood": 15, "energy": -3},
        "message": "虎虎玩累了，趴在Doro腿上呼呼大睡，太可爱了不忍心动~",
    },
    {
        "name": "🐈‍⬛ 小黑抓到了一只小飞虫",
        "prob": 10,
        "effect": {"mood": 5},
        "message": "小黑优雅地一跃而起，精准地抓住了骚扰客人的小飞虫！",
    },
]

CAFE_NPC_DIALOGUES = {
    "coffee_sister": [
        "今天Doro想喝点什么呢？欧润吉拿铁刚出炉哦~",
        "你看小咪今天多开心，一定是Doro来了的缘故！",
        "猫咪们都很喜欢Doro呢，要不要和它们玩一会儿？",
        "今天天气真好，咖啡馆的露台特别舒服~",
        "Doro打工辛苦了！来，这杯我请客！",
    ],
}

CAFE_TIPS = [
    "💡 用猫粮可以和猫咪培养感情哦~",
    "💡 打工赚到的欧润吉可以买好喝的咖啡！",
    "💡 猫咪们喜欢被关注，经常来看看它们吧~",
    "💡 欧润吉拿铁是咖啡馆的招牌饮品！",
    "💡 咖啡姐姐最喜欢Doro来帮忙了~",
]
