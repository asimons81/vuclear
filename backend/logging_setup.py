"""
Logging configuration for Vuclear backend.
Called once at module load by backend.main before any loggers are used.
"""
import logging
import logging.handlers
import sys


def configure_logging() -> None:
    """Set up root logger: stderr stream + optional rotating file under data/logs/."""
    # Import here to avoid a circular import (config imports nothing from backend)
    from backend.config import settings

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if called more than once (e.g. during tests)
    if root.handlers:
        return

    # Console handler → stderr so it doesn't mix with any stdout output
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Rotating file handler — written after ensure_dirs() creates the directory,
    # but we guard with a try/except so a missing directory never crashes startup.
    try:
        log_path = settings.app_log
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        # Can't write log file — continue with console only
        logging.getLogger(__name__).warning(
            "Could not open log file %s; logging to stderr only", settings.app_log
        )
