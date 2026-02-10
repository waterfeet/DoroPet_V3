import logging
import os
import sys
from datetime import datetime

# Global logger instance
logger = logging.getLogger("DoroPet")

def setup_logger():
    """
    Setup the global logger configuration.
    - Creates 'log' directory if not exists.
    - Sets up file handler with timestamped filename.
    - Sets up stream handler for console output.
    """
    global logger
    
    # prevent adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    
    # 1. Create log directory
    log_dir = os.path.join(os.getcwd(), "log")
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
