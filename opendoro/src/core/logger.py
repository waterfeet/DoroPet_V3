import logging
import os
import sys
from datetime import datetime

LOG_COLORS = {
    logging.DEBUG:    "\033[36m",
    logging.INFO:     "\033[32m",
    logging.WARNING:  "\033[33m",
    logging.ERROR:    "\033[31m",
    logging.CRITICAL: "\033[35m",
}
LOG_RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

_LEVEL_ICONS = {
    logging.DEBUG:    "🐛",
    logging.INFO:     "ℹ️",
    logging.WARNING:  "⚠️",
    logging.ERROR:    "❌",
    logging.CRITICAL: "🔥",
}

_LEVEL_NAMES = {
    logging.DEBUG:    "DEBUG",
    logging.INFO:     "INFO",
    logging.WARNING:  "WARNING",
    logging.ERROR:    "ERROR",
    logging.CRITICAL: "CRITICAL",
}

def get_user_data_dir():
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()


class ColoredConsoleFormatter(logging.Formatter):
    def format(self, record):
        level_color = LOG_COLORS.get(record.levelno, "")
        icon = _LEVEL_ICONS.get(record.levelno, "")
        level_name = _LEVEL_NAMES.get(record.levelno, record.levelname)
        time_str = self.formatTime(record, self.datefmt)
        module_name = record.name.replace("DoroPet.", "")
        if module_name == "DoroPet":
            module_name = "Core"

        formatted = (
            f"{DIM}{time_str}{LOG_RESET} "
            f"{level_color}{BOLD}{icon} {level_name:<7}{LOG_RESET} "
            f"[{module_name}] "
            f"{record.getMessage()}"
        )
        if record.exc_info and record.exc_info[0]:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


class FileFormatter(logging.Formatter):
    def format(self, record):
        icon = _LEVEL_ICONS.get(record.levelno, "")
        level_name = _LEVEL_NAMES.get(record.levelno, record.levelname)
        time_str = self.formatTime(record, self.datefmt)
        module_name = record.name.replace("DoroPet.", "")
        if module_name == "DoroPet":
            module_name = "Core"

        formatted = (
            f"[{time_str}] "
            f"[{level_name}] "
            f"[{module_name}] "
            f"{record.getMessage()}"
        )
        if record.exc_info and record.exc_info[0]:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


class LevelIconInjector(logging.Handler):
    def emit(self, record):
        record.level_icon = _LEVEL_ICONS.get(record.levelno, "")
        record.level_color_name = _LEVEL_NAMES.get(record.levelno, "INFO").lower()


class DoroLogger(logging.Logger):
    def __init__(self, name="DoroPet", level=logging.NOTSET):
        super().__init__(name, level)

    def debug(self, msg, *args, **kwargs):
        super().debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        super().info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        super().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        super().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        super().critical(msg, *args, **kwargs)


logging.setLoggerClass(DoroLogger)
logger = logging.getLogger("DoroPet")


def _cleanup_old_logs(log_dir, keep_count=10):
    try:
        log_files = [f for f in os.listdir(log_dir) if f.startswith("log_") and f.endswith(".txt")]
        log_files.sort(reverse=True)
        for old_file in log_files[keep_count:]:
            os.remove(os.path.join(log_dir, old_file))
    except Exception:
        pass


def setup_logger():
    global logger

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    log_dir = os.path.join(get_user_data_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    _cleanup_old_logs(log_dir, keep_count=10)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"log_{timestamp}.txt")

    datefmt = '%H:%M:%S'

    file_formatter = FileFormatter(datefmt=datefmt)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    console_formatter = ColoredConsoleFormatter(datefmt=datefmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(console_formatter)
    logger.addHandler(stream_handler)

    logger.addHandler(LevelIconInjector())

    logger.info(f"日志系统已初始化 | 文件: {log_file}")

    return logger


def set_log_level(level):
    global logger
    logger.setLevel(level)
    for handler in logger.handlers:
        if not isinstance(handler, LevelIconInjector):
            handler.setLevel(level)
    level_name = _LEVEL_NAMES.get(level, str(level))
    logger.info(f"日志级别已切换: {level_name}")


def get_log_level():
    global logger
    return logger.level


def get_log_level_name():
    global logger
    return _LEVEL_NAMES.get(logger.level, str(logger.level))


def get_level_icon(levelno):
    return _LEVEL_ICONS.get(levelno, "")


def get_module_logger(module_name):
    return logging.getLogger(f"DoroPet.{module_name}")
