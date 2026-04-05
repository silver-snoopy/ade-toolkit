"""Structured logging setup for ADE."""

from __future__ import annotations

import logging

from ade.config import LoggingConfig


def setup_logging(config: LoggingConfig | None = None) -> logging.Logger:
    """Configure the ade logger from config."""
    logger = logging.getLogger("ade")
    level = getattr(logging, (config.level if config else "info").upper(), logging.INFO)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)

    return logger
