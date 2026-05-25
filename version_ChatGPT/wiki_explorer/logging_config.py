"""Logging configuration helpers for Wiki-Explorer."""

from __future__ import annotations

import logging
import sys

LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> None:
    """Configure application logging.

    In normal mode logs are suppressed, so they do not interfere with the
    user-facing rich output. In verbose mode informational diagnostics are
    printed to stderr using the standard logging module.
    """
    if verbose:
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
            stream=sys.stderr,
            force=True,
        )
        return

    logging.basicConfig(
        level=logging.CRITICAL + 1,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stderr,
        force=True,
    )
