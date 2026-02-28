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
    ATTR_HUNGER: 80.0,
    ATTR_MOOD: 80.0,
    ATTR_CLEANLINESS: 80.0,
    ATTR_ENERGY: 80.0,
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

# 恢复值
RECOVERY_VALUES = {
    "feed": 20,      # 投喂 - 饱食度
    "play": 25,      # 玩耍 - 心情值
    "clean": 30,     # 清洁 - 清洁度
    "rest": 40,      # 休息 - 能量值
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
