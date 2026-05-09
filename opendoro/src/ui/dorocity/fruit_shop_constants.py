FRUIT_SHOP_DISPLAY = [
    {
        "key": "orange",
        "name": "欧润吉",
        "emoji": "🍊",
        "desc": "Doro最爱的水果！新鲜采摘的欧润吉，满满维C",
        "color": "#FF9800",
    },
    {
        "key": "apple",
        "name": "苹果",
        "emoji": "🍎",
        "desc": "红彤彤的脆苹果，每天一个不用看医生",
        "color": "#F44336",
    },
    {
        "key": "grape",
        "name": "葡萄",
        "emoji": "🍇",
        "desc": "紫莹莹的无籽葡萄，清甜多汁",
        "color": "#9C27B0",
    },
    {
        "key": "watermelon",
        "name": "西瓜",
        "emoji": "🍉",
        "desc": "夏天必备！冰镇西瓜切开的一瞬间最幸福",
        "color": "#4CAF50",
    },
    {
        "key": "strawberry_basket",
        "name": "草莓",
        "emoji": "🍓",
        "desc": "精选大颗草莓，红艳香甜，一口一个",
        "color": "#E91E63",
    },
    {
        "key": "peach",
        "name": "桃子",
        "emoji": "🍑",
        "desc": "水蜜桃甜甜软软，咬一口汁水四溅",
        "color": "#FFAB91",
    },
]

FRUIT_SHOP_NPC_DIALOGUES = {
    "grandpa_orange": [
        "欢迎Doro来啦！今天新到了一批特别甜的欧润吉，要不要尝尝？",
        "Doro真是个好孩子，每次都来帮忙~",
        "爷爷年轻的时候啊，也是一口气能吃十个欧润吉！",
        "水果店虽然不大，但有Doro在就特别热闹~",
        "来，帮爷爷把这个欧润吉摆到最显眼的位置上去！",
        "你知道为什么欧润吉这么甜吗？因为是用爱心浇灌的呀~",
        "Doro今天看起来特别精神！是不是又去咖啡馆喝了欧润吉拿铁？",
        "爷爷这有个藏了很久的欧润吉，特别甜，给Doro偷偷留着呢~",
    ],
}

FRUIT_SHOP_RANDOM_EVENTS = [
    {
        "name": "🍊 橙子爷爷偷偷塞了个欧润吉！",
        "prob": 20,
        "effect": {"oranges": 20, "mood": 8},
        "message": "橙子爷爷笑眯眯地从柜台下拿出一个又大又圆的欧润吉塞给Doro~",
    },
    {
        "name": "🐦 一只小鸟飞来啄了一个葡萄",
        "prob": 15,
        "effect": {"mood": 5},
        "message": "一只圆滚滚的小鸟落在水果摊上，啄了一颗葡萄飞走了，橙子爷爷笑着说没关系~",
    },
    {
        "name": "👧 路过的小朋友看中了草莓",
        "prob": 18,
        "effect": {"mood": 6},
        "message": "一个小朋友拉着妈妈的手指着草莓说'好漂亮！'，Doro帮忙挑了一盒最红的~",
    },
    {
        "name": "🌈 阳光透过水果架形成了一道小彩虹",
        "prob": 12,
        "effect": {"mood": 10},
        "message": "午后的阳光洒在水果上，晶莹剔透的水果折射出漂亮的彩虹光影！",
    },
    {
        "name": "📦 送货车来了一批新水果",
        "prob": 15,
        "effect": {"mood": 5, "oranges": 15},
        "message": "送货大叔卸下好几箱新鲜水果，橙子爷爷高兴地给了Doro一点零花钱~",
    },
    {
        "name": "🍯 隔壁蜂蜜店送来了试吃品",
        "prob": 10,
        "effect": {"mood": 8, "hunger": 5},
        "message": "隔壁蜂蜜店的阿姨送来一小罐蜂蜜，Doro蘸着水果吃，甜到心里去了~",
    },
]

FRUIT_SHOP_TIPS = [
    "💡 每天可以免费领一个欧润吉哦（饱食度<30时）~",
    "💡 欧润吉品鉴师是最赚钱的水果店工作！",
    "💡 橙子爷爷最喜欢别人陪他聊天了~",
    "💡 打工之余看看水果，心情会变好哦！",
    "💡 水果店解锁等级：Lv.2",
]

FRUIT_SHOP_FREE_ORANGE_COST = 50
FRUIT_SHOP_FREE_ORANGE_MESSAGE = "🍊 橙子爷爷送了一个欧润吉给Doro！饱食度恢复了~"
FRUIT_SHOP_FREE_ORANGE_UNAVAILABLE = "橙子爷爷说：Doro还不饿呢，等饿了再来拿欧润吉吧~"
