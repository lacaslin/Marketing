"""Structured logging with rich terminal output."""

import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logger(name: str = "mcf", level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    rich_handler = RichHandler(console=console, rich_tracebacks=True, show_time=True, markup=True)
    rich_handler.setLevel(logging.DEBUG)
    rich_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(rich_handler)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(file_handler)

    return logger


# Module-level logger
log = setup_logger()
