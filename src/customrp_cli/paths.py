"""Where the config file and runtime files live on each platform."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "customrp-cli"
CONFIG_FILE_NAME = "config.toml"

#: Overrides the config file location (the -c option still wins)
CONFIG_ENV = "CUSTOMRP_CLI_CONFIG"
#: Overrides the directory for the lock, PID and status files
STATE_ENV = "CUSTOMRP_CLI_STATE_DIR"


def _env_dir(name: str, fallback: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else fallback


def config_dir() -> Path:
    if sys.platform == "win32":
        return _env_dir("APPDATA", Path.home() / "AppData" / "Roaming") / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return _env_dir("XDG_CONFIG_HOME", Path.home() / ".config") / APP_DIR_NAME


def state_dir() -> Path:
    override = os.environ.get(STATE_ENV)
    if override:
        return Path(override)
    if sys.platform == "win32":
        return _env_dir("LOCALAPPDATA", Path.home() / "AppData" / "Local") / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return _env_dir("XDG_STATE_HOME", Path.home() / ".local" / "state") / APP_DIR_NAME


def default_config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    return Path(override) if override else config_dir() / CONFIG_FILE_NAME
