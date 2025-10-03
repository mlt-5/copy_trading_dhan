"""
Logging configuration module.
"""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: Optional log file path
    """
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce verbosity of third-party libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('websocket').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured at {log_level} level")

