"""Logging setup: to stderr, and optionally to a rotating file."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
DEBUG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotate the log file at 1 MB and keep 3 old ones, so it can't fill a disk
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def level_for(config_level: str, verbose: int, quiet: bool) -> int:
    """-v and -q on the command line override the config file's level."""
    if quiet:
        return logging.ERROR
    if verbose:
        return logging.DEBUG
    return getattr(logging, config_level.upper(), logging.INFO)


def setup(level: int, log_file: Path | None = None) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.setLevel(level)

    formatter = logging.Formatter(DEBUG_FORMAT if level <= logging.DEBUG else FORMAT, DATE_FORMAT)

    # pythonw (used to run in the background on Windows) has no stderr
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=MAX_BYTES,
                                                            backupCount=BACKUP_COUNT, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
