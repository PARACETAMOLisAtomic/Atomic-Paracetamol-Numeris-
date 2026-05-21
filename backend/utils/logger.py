import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Any, Dict
import json


class JSONFormatter(logging.Formatter):
    """Formatter that outputs JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        if hasattr(record, "extra"):
            log_record["extra"] = record.extra
        return json.dumps(log_record)


def get_logger(name: str) -> logging.Logger:
    """
    Create a get_logger(name: str) function that returns a Python logger
    - JSON-formatted output with fields: timestamp, level, module, message, extra data
    - Log rotation: RotatingFileHandler, max 100MB per file, keep 7 backups
    - Logs go to: backend/logs/{name}.log AND stdout
    - Log levels: DEBUG in development, INFO in production (read from .env APP_ENV)

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger

    # Determine log level from environment
    app_env = os.getenv("APP_ENV", "development")
    log_level = logging.DEBUG if app_env == "development" else logging.INFO
    logger.setLevel(log_level)

    # Create JSON formatter
    json_formatter = JSONFormatter()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation
    log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7
    )
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    return logger


def performance_log(func_name: str, duration_ms: float, extra: Dict[str, Any] = None) -> None:
    """
    Include a performance_log(func_name, duration_ms, extra) helper for timing

    Args:
        func_name: Name of the function being timed
        duration_ms: Duration in milliseconds
        extra: Additional data to include in the log
    """
    logger = get_logger("performance")
    extra_data = extra or {}
    extra_data.update({
        "function": func_name,
        "duration_ms": duration_ms
    })
    # Create a LogRecord with extra data
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        "",  # message
        (),  # args
        None,  # exc_info
        extra=extra_data,
        func=func_name
    )
    logger.handle(record)