"""
Structured logging with step-level context.

Usage:
    from intellibrowse.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("action executed", extra={"step": 3, "action": "click(5)"})
"""

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger with consistent formatting across the app."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False

    return logger
