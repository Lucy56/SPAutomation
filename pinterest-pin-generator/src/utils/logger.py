"""Logging configuration"""
import logging
import colorlog
from src.config.settings import LOG_LEVEL

def setup_logger(name: str) -> logging.Logger:
    """Create a configured logger with color output"""

    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    logger = colorlog.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    return logger
