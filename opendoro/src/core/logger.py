import logging
import os
import sys
from datetime import datetime

def get_user_data_dir():
    """
    Get user data directory for DoroPet.
    On Windows, this is %LOCALAPPDATA%\\DoroPet
    """
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        return os.path.join(local_app_data, 'DoroPet')
    return os.getcwd()

# Global logger instance
logger = logging.getLogger("DoroPet")

def setup_logger():
    """
    Setup the global logger configuration.
    - Creates 'log' directory in user data folder if not exists.
    - Sets up file handler with timestamped filename.
    - Sets up stream handler for console output.
    """
    global logger
    
    # prevent adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    
    # 1. Create log directory in user data folder
    log_dir = os.path.join(get_user_data_dir(), "log")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # 2. Generate filename based on time
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"log_{timestamp}.txt")
    
    # 3. Define Formatter
    # Format: [Time] [Module] [Type] Message
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 4. File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 5. Stream Handler (Console)
    # This is important so that LogInterface can capture it via sys.stdout/stderr redirection
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    logger.info(f"Logger initialized. Saving logs to: {log_file}")
    
    return logger

_LEVEL_NAMES = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL"
}

def set_log_level(level):
    """
    Dynamically set the logger level.
    :param level: logging level (e.g., logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
    """
    global logger
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
    level_name = _LEVEL_NAMES.get(level, str(level))
    logger.info(f"Log level changed to: {level_name}")

def get_log_level():
    """
    Get the current logger level.
    :return: current logging level
    """
    global logger
    return logger.level

def get_log_level_name():
    """
    Get the current logger level name.
    :return: current logging level name (e.g., 'DEBUG', 'INFO')
    """
    global logger
    return _LEVEL_NAMES.get(logger.level, str(logger.level))
