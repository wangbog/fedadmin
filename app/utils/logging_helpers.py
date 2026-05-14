import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from flask import request


class _LoggerProxy:
    """Lazy logger proxy that retrieves the current app's logger.

    This allows using 'logger.info()' directly without needing to import
    current_app in every module.
    """

    def __getattr__(self, name):
        from flask import current_app

        return getattr(current_app.logger, name)


# Global logger instance that can be used directly
logger = _LoggerProxy()


def setup_logging(app):
    """Configure application logging system.

    Args:
        app: Flask application instance
    """

    # Create log formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler - always output to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    app.logger.addHandler(console_handler)

    # File handler - optional, configured via LOG_FILE environment variable
    log_file = app.config.get("LOG_FILE")
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Use rotating file handler to avoid log files growing too large
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,  # Keep 10 backup files
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(file_handler)

    # Set log level
    log_level_str = app.config.get("LOG_LEVEL", "DEBUG" if app.debug else "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    app.logger.setLevel(log_level)

    # Configure APScheduler logging
    apscheduler_logger = logging.getLogger("apscheduler")
    apscheduler_logger.setLevel(log_level)
    apscheduler_logger.addHandler(console_handler)
    if log_file:
        apscheduler_logger.addHandler(file_handler)

    # Configure SQLAlchemy logging (optional, useful for debugging)
    if app.debug and log_level <= logging.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    app.logger.info(
        f"Logging system initialized - level: {logging.getLevelName(log_level)}, "
        f"debug mode: {app.debug}"
    )


def get_client_ip():
    """
    Get real client IP address, properly handle reverse proxy X-Forwarded-For header.
    Returns first public IP from X-Forwarded-For chain if present, falls back to remote_addr.
    """
    if "X-Forwarded-For" in request.headers:
        # Get first IP from the chain (client real IP)
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr
