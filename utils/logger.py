import logging
import os
from datetime import datetime
from config import LOGS_DIR


def setup_logger(test_name, youtube_url):
    """Setup and return a logger for the test run"""
    # Create a unique log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_url = (
        youtube_url.replace(":", "_")
        .replace("/", "_")
        .replace("?", "_")
        .replace("=", "_")
    )
    log_filename = f"{test_name}_{safe_url}_{timestamp}.log"
    log_path = os.path.join(LOGS_DIR, log_filename)

    # Configure logger
    logger = logging.getLogger(f"{test_name}_{timestamp}")
    logger.setLevel(logging.INFO)

    # Create file handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger, log_path
