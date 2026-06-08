import logging
import sys
import os
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init(autoreset=True)

class ColorFormatter(logging.Formatter):
    """Custom Formatter to add colors to console logs based on levels."""
    LEVEL_COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, "")
        original_levelname = record.levelname
        
        # Colorize the level name
        record.levelname = f"{color}{original_levelname}{Style.RESET_ALL}"
        formatted = super().format(record)
        
        # Restore original level name for subsequent handlers
        record.levelname = original_levelname
        return formatted

def setup_logging(log_file="trading_bot.log", level=logging.INFO):
    """Set up loggers for the application, writing to console and a file."""
    # Ensure the directory of log_file exists if a path is passed
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger("trading_bot")
    root_logger.setLevel(logging.DEBUG)  # Log everything at debug level to handlers
    
    # Avoid duplicate handlers if setup is called multiple times
    if root_logger.handlers:
        return root_logger

    # 1. Console Handler (user-friendly)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s", 
        datefmt="%H:%M:%S"
    )
    console_formatter = ColorFormatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 2. File Handler (detailed structured logs)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Always log verbose debugging info to file
    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | [%(filename)s:%(lineno)d] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # Disable propagation to avoid duplicates if logging is imported elsewhere
    root_logger.propagate = False

    return root_logger

# Helper to retrieve the logger
def get_logger():
    return logging.getLogger("trading_bot")
