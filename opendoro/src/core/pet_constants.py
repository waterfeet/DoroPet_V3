# 属性名称
ATTR_HUNGER = "hunger"
ATTR_MOOD = "mood"
ATTR_CLEANLINESS = "cleanliness"
ATTR_ENERGY = "energy"

# 属性中文名
ATTR_NAMES = {
    ATTR_HUNGER: "饱食度",
    ATTR_MOOD: "心情值",
    ATTR_CLEANLINESS: "清洁度",
    ATTR_ENERGY: "能量值",
}

# 默认属性值
DEFAULT_VALUES = {
    ATTR_HUNGER: 50.0,
    ATTR_MOOD: 50.0,
    ATTR_CLEANLINESS: 50.0,
    ATTR_ENERGY: 50.0,
}

# 属性最大值
MAX_VALUES = {
    ATTR_HUNGER: 100.0,
    ATTR_MOOD: 100.0,
    ATTR_CLEANLINESS: 100.0,
    ATTR_ENERGY: 100.0,
}

# 属性最小值
MIN_VALUES = {
    ATTR_HUNGER: 0.0,
    ATTR_MOOD: 0.0,
    ATTR_CLEANLINESS: 0.0,
    ATTR_ENERGY: 0.0,
}

# 每分钟衰减率
DECAY_RATES = {
    ATTR_HUNGER: 1.5,
    ATTR_MOOD: 0.8,
    ATTR_CLEANLINESS: 0.5,
    ATTR_ENERGY: 1.0,
}

# 恢复值（兼容旧版）
RECOVERY_VALUES = {
    "feed": 20,      # 投喂 - 饱食度
    "play": 25,      # 玩耍 - 心情值
    "clean": 30,     # 清洁 - 清洁度
    "rest": 40,      # 休息 - 能量值
}

# 强度倍率
INTENSITY_MULTIPLIERS = {
    "light": 0.5,
    "moderate": 1.0,
    "heavy": 1.5,
}

# 互动效果矩阵（属性变化值）
INTERACTION_EFFECTS = {
    "feed_snack": {"hunger": 10, "mood": 5, "cleanliness": 0, "energy": 0},
    "feed_meal": {"hunger": 20, "mood": 5, "cleanliness": 0, "energy": 0},
    "feed_feast": {"hunger": 35, "mood": 15, "cleanliness": 0, "energy": -5},
    "feed_bad": {"hunger": -20, "mood": -25, "cleanliness": 0, "energy": -10},
    "play_gentle": {"hunger": 0, "mood": 15, "cleanliness": -5, "energy": -5},
    "play_fun": {"hunger": 0, "mood": 25, "cleanliness": -10, "energy": -15},
    "play_exhausting": {"hunger": 0, "mood": 30, "cleanliness": -15, "energy": -30},
    "clean_wipe": {"hunger": 0, "mood": 5, "cleanliness": 15, "energy": 0},
    "clean_wash": {"hunger": 0, "mood": 10, "cleanliness": 35, "energy": -5},
    "rest_nap": {"hunger": -5, "mood": 5, "cleanliness": 0, "energy": 20},
    "rest_sleep": {"hunger": -15, "mood": 10, "cleanliness": 0, "energy": 45},
    "pet_affection": {"hunger": 0, "mood": 10, "cleanliness": 0, "energy": 0},
    "scold": {"hunger": 0, "mood": -25, "cleanliness": 0, "energy": 0},
    "comfort": {"hunger": 0, "mood": 20, "cleanliness": 0, "energy": 5},
}

# 互动中文名
INTERACTION_NAMES = {
    "feed_snack": "投喂零食",
    "feed_meal": "投喂正餐",
    "feed_feast": "投喂大餐",
    "feed_bad": "投喂变质食物",
    "play_gentle": "轻度玩耍",
    "play_fun": "愉快玩耍",
    "play_exhausting": "剧烈玩耍",
    "clean_wipe": "擦拭清洁",
    "clean_wash": "洗澡清洁",
    "rest_nap": "小憩休息",
    "rest_sleep": "沉睡休息",
    "pet_affection": "抚摸互动",
    "scold": "责备",
    "comfort": "安慰",
}

# 旧版操作到新版互动的映射（兼容）
LEGACY_ACTION_MAPPING = {
    ("feed", None): ("feed_meal", "moderate"),
    ("feed", "light"): ("feed_snack", "light"),
    ("feed", "moderate"): ("feed_meal", "moderate"),
    ("feed", "heavy"): ("feed_feast", "heavy"),
    ("play", None): ("play_fun", "moderate"),
    ("play", "light"): ("play_gentle", "light"),
    ("play", "moderate"): ("play_fun", "moderate"),
    ("play", "heavy"): ("play_exhausting", "heavy"),
    ("clean", None): ("clean_wash", "moderate"),
    ("clean", "light"): ("clean_wipe", "light"),
    ("clean", "moderate"): ("clean_wash", "moderate"),
    ("clean", "heavy"): ("clean_wash", "heavy"),
    ("rest", None): ("rest_sleep", "moderate"),
    ("rest", "light"): ("rest_nap", "light"),
    ("rest", "moderate"): ("rest_sleep", "moderate"),
    ("rest", "heavy"): ("rest_sleep", "heavy"),
}

# 状态阈值
STATUS_THRESHOLDS = {
    "critical": 20,
    "warning": 50,
    "good": 50,
}

# 状态颜色
STATUS_COLORS = {
    "critical": "#f44336",  # 红色
    "warning": "#ff9800",   # 橙色
    "good": "#4CAF50",     # 绿色
}

# 联动衰减倍率
LINKAGE_DECAY_MULTIPLIERS = {
    "hunger_to_mood": 2.0,      # 饱食度<20时，心情值衰减×2.0
    "cleanliness_to_mood": 1.5, # 清洁度<30时，心情值衰减×1.5
    "energy_to_all": 1.5,       # 能量值<20时，所有属性衰减×1.5
}

# 联动阈值
LINKAGE_THRESHOLDS = {
    "hunger_critical": 20,
    "cleanliness_warning": 30,
    "energy_critical": 20,
}

# QSettings 配置键名
SETTINGS_KEY_PREFIX = "pet_attribute_"
SETTINGS_LAST_SAVE_TIME = "pet_attributes_last_save_time"

# ============================================================
# 欧润吉（Orange）奖励系统
# ============================================================

# 番茄钟时长对应的欧润吉奖励数量（1🍊基础单位=50）
ORANGE_REWARDS = {
    15: 100,
    25: 150,
    45: 300,
    60: 500,
}

# 连击奖励：连续第N个番茄额外获得
ORANGE_COMBO_BONUS = {3: 50, 5: 100, 8: 150, 12: 250}

# 每日首次完成额外奖励
ORANGE_DAILY_FIRST_BONUS = 100

# 欧润吉交互消耗（鼓励使用物品）
ORANGE_INTERACTION_COST = {
    "feed": 100,
    "play": 100,
    "clean": 100,
    "rest": 100,
}

# 使用欧润吉投喂的属性效果（比免费互动更强）
ORANGE_FEED_EFFECTS = {
    ATTR_HUNGER: 30,
    ATTR_MOOD: 15,
    ATTR_ENERGY: 5,
}

# QSettings 欧润吉存储键
ORANGE_SETTINGS_KEY = "orange_balance"
ORANGE_TODAY_KEY = "orange_today_earned"
ORANGE_TODAY_DATE_KEY = "orange_today_date"
ORANGE_TOTAL_EARNED_KEY = "orange_total_earned"
ORANGE_COMBO_KEY = "orange_current_combo"

# ============================================================
# Doro 等级进化系统
# ============================================================

# 等级所需累计番茄数
DORO_LEVEL_THRESHOLDS = {
    1: 0,
    2: 10,
    3: 30,
    4: 60,
    5: 100,
    6: 150,
    7: 210,
    8: 280,
    9: 360,
    10: 450,
}

# 等级称号
DORO_LEVEL_TITLES = {
    1: "Doro崽",
    2: "Doro崽",
    3: "Doro崽",
    4: "Doro少年",
    5: "Doro少年",
    6: "Doro少年",
    7: "Doro达人",
    8: "Doro达人",
    9: "Doro达人",
    10: "Doro大师",
}

# 等级衰减减免：等级越高，衰减越慢（倍率）
DORO_LEVEL_DECAY_REDUCTION = {
    1: 1.0,
    2: 0.95,
    3: 0.90,
    4: 0.83,
    5: 0.77,
    6: 0.70,
    7: 0.65,
    8: 0.60,
    9: 0.55,
    10: 0.50,
}

# QSettings 等级存储键
DORO_LEVEL_KEY = "doro_level"
DORO_TOTAL_POMODOROS_KEY = "doro_total_pomodoros"
