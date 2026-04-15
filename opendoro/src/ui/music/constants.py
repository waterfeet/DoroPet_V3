from enum import Enum


class PlayMode(Enum):
    SEQUENCE = "sequence"
    LIST_LOOP = "list_loop"
    SINGLE_LOOP = "single_loop"
    SHUFFLE = "shuffle"


class VinylConstants:
    WIDGET_SIZE = 420
    RECORD_RADIUS = 130
    LABEL_RADIUS = 65
    CENTER_HOLE_OUTER = 12
    CENTER_HOLE_INNER = 6
    ROTATION_SPEED = 2.0
    ROTATION_INTERVAL = 25
    NEEDLE_ANGLE_PLAYING = 25
    NEEDLE_ANGLE_STOPPED = -30
    NEEDLE_ANGLE_PAUSED = -20


class PlayerConstants:
    BOTTOM_PLAYER_HEIGHT = 70
    PROGRESS_BAR_HEIGHT = 24
    BOTTOM_PLAYER_MARGIN = 24
    MAX_RETRY_COUNT = 3
    RETRY_DELAY_MS = 1000


class PlaylistConstants:
    DOCK_WIDTH = 350
    DOCK_ANIMATION_DURATION = 300


class ColorConstants:
    DEFAULT_BACKGROUND = "rgba(42, 42, 42, 1)"
    DARK_BG_START = "rgb(60, 60, 80)"
    DARK_BG_END = "rgb(30, 30, 50)"


PLAY_MODE_CONFIG = {
    PlayMode.SEQUENCE: ("right_arrow", "顺序播放"),
    PlayMode.LIST_LOOP: ("sync", "列表循环"),
    PlayMode.SINGLE_LOOP: ("update", "单曲循环"),
    PlayMode.SHUFFLE: ("tiles", "随机播放"),
}

MUSIC_PLATFORMS = [
    ('netease', '奈缇斯', 'NeteaseMusicClient'),
    ('qq', '咕嘎', 'QQMusicClient'),
    ('kugou', '酷汪', 'KugouMusicClient'),
    ('kuwo', '酷me', 'KuwoMusicClient'),
    ('migu', '咪咕', 'MiguMusicClient'),
]

PLATFORM_MAP = {
    "全部平台": "NeteaseMusicClient,QQMusicClient,KuwoMusicClient,KugouMusicClient,MiguMusicClient",
    "🎵 奈缇斯": "NeteaseMusicClient",
    "🎶 咕嘎": "QQMusicClient",
    "🎧 酷汪": "KugouMusicClient",
    "📻 酷me": "KuwoMusicClient",
    "🎤 咪咕": "MiguMusicClient",
    "📺 B站音乐": "BilibiliMusicClient",
}
