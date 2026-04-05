from __future__ import annotations

import logging

from ade.config import LoggingConfig
from ade.logging_setup import setup_logging


def test_setup_logging_default_level() -> None:
    log = setup_logging()
    assert log.level == logging.INFO


def test_setup_logging_from_config() -> None:
    config = LoggingConfig(level="debug")
    log = setup_logging(config=config)
    assert log.level == logging.DEBUG


def test_setup_logging_returns_ade_logger() -> None:
    log = setup_logging()
    assert log.name == "ade"
