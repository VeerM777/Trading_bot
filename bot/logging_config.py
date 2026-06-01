import os
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE_PATH = os.path.join(BASE_DIR, "trading_bot.log")

def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Sets up structured logging.
    - Console logs are clean using Rich.
    - File logs are detailed and written to trading_bot.log.
    """
    log_level = logging.DEBUG if debug else logging.INFO

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        level=log_level
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
    ))
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    logger.debug(f"Logging initialized. Log file path: {LOG_FILE_PATH}")
    return logger

logger = setup_logging()
