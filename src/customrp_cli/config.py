"""The TOML config file: loading it, checking it, and writing it.

The file has four tables: ``[presence]`` (what to show), ``[connection]``, ``[run]`` and
``[logging]``. docs/configuration.md describes every option.
"""

from __future__ import annotations

import difflib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from customrp_core import ActivityType, Button, Presence, StatusDisplay, TimestampMode, validate
from customrp_core.session import DEFAULT_RETRY_INTERVAL

from . import messages as msg

ACTIVITY_TYPES = {
    "playing": ActivityType.PLAYING,
    "listening": ActivityType.LISTENING,
    "watching": ActivityType.WATCHING,
    "competing": ActivityType.COMPETING,
}
STATUS_DISPLAYS = {
    "name": StatusDisplay.NAME,
    "details": StatusDisplay.DETAILS,
    "state": StatusDisplay.STATE,
}
TIMESTAMP_MODES = {
    "since_last_connection": TimestampMode.SINCE_LAST_CONNECTION,
    "since_startup": TimestampMode.SINCE_STARTUP,
    "since_presence_update": TimestampMode.SINCE_PRESENCE_UPDATE,
    "local_time": TimestampMode.LOCAL_TIME,
    "custom": TimestampMode.CUSTOM,
}
LOG_LEVELS = ("debug", "info", "warning", "error")

DATETIME_EXAMPLE = "2026-01-01T12:00:00"

_SECTIONS = ("presence", "connection", "run", "logging")
_PRESENCE_TEXT = ("application_id", "name", "details", "details_url", "state", "state_url")
_PRESENCE_KEYS = _PRESENCE_TEXT + ("type", "status_display", "party_size", "party_max", "timestamps",
                                   "custom_start", "custom_end", "proxy_discord_cdn", "large_image",
                                   "small_image", "buttons")
_IMAGE_KEYS = ("key", "text", "url")
_BUTTON_KEYS = ("label", "url")


class ConfigError(Exception):
    """The config file can't be used. ``problems`` lists every reason, one line each.

    ``about_values`` is True when the file was read but some values are wrong, and False when
    the file itself is the problem (missing, unreadable, not TOML).
    """

    def __init__(self, problems: list[str], about_values: bool = False):
        super().__init__("\n".join(problems))
        self.problems = problems
        self.about_values = about_values


@dataclass(frozen=True)
class Problem:
    """Something wrong with a config value. Only errors stop the presence from being sent."""

    key: str
    message: str
    is_error: bool = True

    def __str__(self):
        return f"{self.key}: {self.message}"


@dataclass
class Config:
    presence: Presence = field(default_factory=Presence)
    proxy_discord_cdn: bool = True
    pipe: int = -1  # -1 means "auto"
    retry_interval: float = DEFAULT_RETRY_INTERVAL
    max_retries: int | None = None  # None means forever
    watch_config: bool = True
    log_level: str = "info"
    log_file: Path | None = None
    #: Where the config was loaded from, if anywhere
    path: Path | None = None

    def problems(self) -> list[Problem]:
        """Checks the presence the way Discord would; see customrp_core.validate."""
        return [Problem(_issue_key(issue.field), issue.message, issue.is_error)
                for issue in validate(self.presence)]

    def same_runtime_settings(self, other: Config) -> bool:
        """Whether the settings that need a restart to change are the same."""
        keys = ("pipe", "retry_interval", "max_retries", "log_level", "log_file")
        return all(getattr(self, k) == getattr(other, k) for k in keys)


# --- Loading -----------------------------------------------------------------------

def load_config(path: Path) -> Config:
    """Reads and parses a config file. Raises :class:`ConfigError` if it can't be used.

    Validation problems in the presence itself aren't raised; see :meth:`Config.problems`.
    """
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raise ConfigError([msg.CONFIG_MISSING.format(path=path)]) from None
    except OSError as e:
        raise ConfigError([msg.CONFIG_UNREADABLE.format(path=path, reason=e.strerror or e)]) from None

    try:
        text = raw.decode("utf-8-sig")  # Tolerate the BOM some Windows editors add
    except UnicodeDecodeError:
        raise ConfigError([msg.CONFIG_NOT_UTF8.format(path=path)]) from None

    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError([msg.CONFIG_BAD_TOML.format(path=path, reason=e)]) from None

    config = parse_config(document, base_dir=path.parent)
    config.path = path
    return config


def parse_config(document: dict, base_dir: Path | None = None) -> Config:
    """Builds a Config from parsed TOML. Raises :class:`ConfigError` listing every problem found."""
    reader = _Reader()
    config = Config()
    reader.check_keys(document, "", _SECTIONS)

    presence = reader.table(document, "", "presence")
    reader.check_keys(presence, "presence", _PRESENCE_KEYS)
    config.presence = _read_presence(reader, presence)
    config.proxy_discord_cdn = reader.boolean(presence, "presence", "proxy_discord_cdn", True)

    connection = reader.table(document, "", "connection")
    reader.check_keys(connection, "connection", ("pipe", "retry_interval", "max_retries"))
    config.pipe = reader.pipe(connection, "connection", "pipe")
    config.retry_interval = reader.number(connection, "connection", "retry_interval", DEFAULT_RETRY_INTERVAL,
                                          minimum=1)
    retries = reader.integer(connection, "connection", "max_retries", -1, minimum=-1)
    config.max_retries = None if retries == -1 else retries

    run = reader.table(document, "", "run")
    reader.check_keys(run, "run", ("watch_config",))
    config.watch_config = reader.boolean(run, "run", "watch_config", True)

    logging_ = reader.table(document, "", "logging")
    reader.check_keys(logging_, "logging", ("level", "file"))
    config.log_level = reader.choice(logging_, "logging", "level", "info", {name: name for name in LOG_LEVELS})
    log_file = reader.string(logging_, "logging", "file")
    if log_file:
        log_path = Path(log_file).expanduser()
        if not log_path.is_absolute() and base_dir is not None:
            log_path = base_dir / log_path
        config.log_file = log_path

    if reader.problems:
        raise ConfigError(reader.problems, about_values=True)
    return config


def _read_presence(reader: _Reader, table: dict) -> Presence:
    p = Presence()
    for name in _PRESENCE_TEXT:
        setattr(p, name, reader.string(table, "presence", name))
    p.type = reader.choice(table, "presence", "type", ActivityType.PLAYING, ACTIVITY_TYPES)
    p.status_display = reader.choice(table, "presence", "status_display", StatusDisplay.NAME, STATUS_DISPLAYS)
    p.party_size = reader.integer(table, "presence", "party_size", 0, minimum=0)
    p.party_max = reader.integer(table, "presence", "party_max", 0, minimum=0)
    p.timestamps = reader.choice(table, "presence", "timestamps", TimestampMode.SINCE_LAST_CONNECTION,
                                 TIMESTAMP_MODES)
    p.custom_start = reader.moment(table, "presence", "custom_start")
    p.custom_end = reader.moment(table, "presence", "custom_end")

    for prefix in ("large", "small"):
        name = prefix + "_image"
        image = reader.table(table, "presence", name)
        reader.check_keys(image, f"presence.{name}", _IMAGE_KEYS)
        setattr(p, name, reader.string(image, f"presence.{name}", "key"))
        setattr(p, prefix + "_text", reader.string(image, f"presence.{name}", "text"))
        setattr(p, prefix + "_url", reader.string(image, f"presence.{name}", "url"))

    buttons = reader.array_of_tables(table, "presence", "buttons")
    if len(buttons) > 2:
        reader.error("presence.buttons", msg.TOO_MANY_BUTTONS.format(count=len(buttons)))
    for n, button in enumerate(buttons[:2], 1):
        prefix = f"presence.buttons[{n}]"
        reader.check_keys(button, prefix, _BUTTON_KEYS)
        setattr(p, f"button{n}", Button(reader.string(button, prefix, "label"), reader.string(button, prefix, "url")))

    return p


def _join(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def _type_name(value) -> str:
    if isinstance(value, bool):
        return msg.TYPE_NAMES[bool]
    if isinstance(value, datetime):
        return "a date and time"
    if isinstance(value, date):
        return "a date"
    if isinstance(value, time):
        return "a time"
    return msg.TYPE_NAMES.get(type(value), type(value).__name__)


class _Reader:
    """Reads typed values out of parsed TOML, collecting problems instead of stopping at the first."""

    def __init__(self):
        self.problems: list[str] = []

    def error(self, key: str, message: str):
        self.problems.append(f"{key}: {message}")

    def check_keys(self, table: dict, prefix: str, allowed):
        for key in table:
            if key not in allowed:
                close = difflib.get_close_matches(key, allowed, n=1)
                hint = msg.DID_YOU_MEAN.format(suggestion=close[0]) if close else ""
                self.error(_join(prefix, key), msg.UNKNOWN_OPTION + hint)

    def _get(self, table: dict, prefix: str, name: str, accept: tuple, expected: str):
        """Returns the value, or None when it's missing or has the wrong type (which is reported)."""
        if name not in table:
            return None
        value = table[name]
        if isinstance(value, accept) and not (isinstance(value, bool) and bool not in accept):
            return value
        self.error(_join(prefix, name), msg.EXPECTED_TYPE.format(expected=expected, actual=_type_name(value)))
        return None

    def table(self, table: dict, prefix: str, name: str) -> dict:
        value = self._get(table, prefix, name, (dict,), msg.TYPE_NAMES[dict])
        return value if value is not None else {}

    def array_of_tables(self, table: dict, prefix: str, name: str) -> list:
        value = self._get(table, prefix, name, (list,), "an array of tables")
        if value is None:
            return []
        if not all(isinstance(item, dict) for item in value):
            self.error(_join(prefix, name), msg.EXPECTED_TYPE.format(expected="an array of tables",
                                                                     actual="an array of other values"))
            return []
        return value

    def string(self, table: dict, prefix: str, name: str, default: str = "") -> str:
        value = self._get(table, prefix, name, (str,), msg.TYPE_NAMES[str])
        return default if value is None else value

    def boolean(self, table: dict, prefix: str, name: str, default: bool) -> bool:
        value = self._get(table, prefix, name, (bool,), msg.TYPE_NAMES[bool])
        return default if value is None else value

    def integer(self, table: dict, prefix: str, name: str, default: int, minimum: int | None = None) -> int:
        value = self._get(table, prefix, name, (int,), msg.TYPE_NAMES[int])
        if value is None:
            return default
        if minimum is not None and value < minimum:
            self.error(_join(prefix, name), msg.AT_LEAST.format(minimum=minimum))
            return default
        return value

    def number(self, table: dict, prefix: str, name: str, default: float, minimum: float) -> float:
        value = self._get(table, prefix, name, (int, float), msg.TYPE_NAMES[float])
        if value is None:
            return default
        if not math.isfinite(value) or value < minimum:
            self.error(_join(prefix, name), msg.AT_LEAST.format(minimum=minimum))
            return default
        return float(value)

    def choice(self, table: dict, prefix: str, name: str, default, choices: dict):
        value = self._get(table, prefix, name, (str,), msg.TYPE_NAMES[str])
        if value is None:
            return default
        normalized = re.sub(r"[\s-]+", "_", value.strip().lower())
        if normalized not in choices:
            self.error(_join(prefix, name), msg.EXPECTED_CHOICE.format(value=value, choices=", ".join(choices)))
            return default
        return choices[normalized]

    def moment(self, table: dict, prefix: str, name: str) -> datetime | None:
        if name not in table:
            return None
        value = table[name]
        key = _join(prefix, name)
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            self.error(key, msg.NEEDS_TIME.format(example=f"{value.isoformat()}T00:00:00"))
            return None
        if isinstance(value, str):
            text = value.strip()
            if text.endswith(("Z", "z")):
                text = text[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                self.error(key, msg.BAD_DATETIME.format(value=value, example=DATETIME_EXAMPLE))
                return None
            if "T" not in text and " " not in text:
                self.error(key, msg.NEEDS_TIME.format(example=f"{text}T00:00:00"))
                return None
            return parsed
        self.error(key, msg.EXPECTED_TYPE.format(expected="a date and time", actual=_type_name(value)))
        return None

    def pipe(self, table: dict, prefix: str, name: str) -> int:
        if name not in table:
            return -1
        value = table[name]
        if isinstance(value, str) and value.strip().lower() == "auto":
            return -1
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 9:
            return value
        self.error(_join(prefix, name), msg.EXPECTED_TYPE.format(expected=msg.PIPE_HINT, actual=repr(value)))
        return -1


_ISSUE_KEYS = {
    "large_image": "presence.large_image.key",
    "large_text": "presence.large_image.text",
    "large_url": "presence.large_image.url",
    "small_image": "presence.small_image.key",
    "small_text": "presence.small_image.text",
    "small_url": "presence.small_image.url",
}


def _issue_key(field_name: str | None) -> str:
    """Translates a customrp_core field name into the matching config key."""
    if field_name is None:
        return "presence"
    if field_name in _ISSUE_KEYS:
        return _ISSUE_KEYS[field_name]
    m = re.fullmatch(r"button(\d)(?:\.(\w+))?", field_name)
    if m:
        return f"presence.buttons[{m[1]}]" + (f".{m[2]}" if m[2] else "")
    return f"presence.{field_name}"


# --- Writing -----------------------------------------------------------------------

def toml_value(value) -> str:
    """Formats a value as TOML. JSON strings are valid TOML basic strings, except for DEL."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return json.dumps(str(value), ensure_ascii=False).replace("\x7f", "\\u007f")


def _name_of(choices: dict, value) -> str:
    return next(name for name, member in choices.items() if member == value)


def render_config(config: Config) -> str:
    """Writes a complete, commented config file. Loading it gives back an equal Config."""
    p = config.presence
    v = toml_value

    def optional_datetime(name, value):
        if value is None:
            return f"# {name} = {DATETIME_EXAMPLE}"
        return f"{name} = {v(value)}"

    buttons = [b for b in p.buttons if b.label or b.url]
    if buttons:
        button_text = "\n\n".join(f"[[presence.buttons]]\nlabel = {v(b.label)}\nurl = {v(b.url)}" for b in buttons)
    else:
        button_text = '# [[presence.buttons]]\n# label = "My website"\n# url = "https://example.com"'

    retry = int(config.retry_interval) if float(config.retry_interval).is_integer() else config.retry_interval

    return f"""\
# customrp-cli configuration
# Every option is described in https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/configuration.md
# While customrp-cli runs, it reloads this file whenever it's saved.

[presence]
# Your Discord application's ID, from https://discord.com/developers/applications
# Leave it empty to use CustomRP's default application.
application_id = {v(p.application_id)}

# playing, listening, watching or competing
type = {v(_name_of(ACTIVITY_TYPES, p.type))}
# What the member list shows next to your name: name (the application's name), details or state
status_display = {v(_name_of(STATUS_DISPLAYS, p.status_display))}

# Sent as the activity's name
name = {v(p.name)}
# The two lines of text, each with an optional link
details = {v(p.details)}
details_url = {v(p.details_url)}
state = {v(p.state)}
state_url = {v(p.state_url)}

# Shown as "(1 of 4)" with the playing type, when both are above 0
party_size = {v(p.party_size)}
party_max = {v(p.party_max)}

# since_last_connection, since_startup, since_presence_update, local_time or custom
timestamps = {v(_name_of(TIMESTAMP_MODES, p.timestamps))}
# For custom: a start, and optionally an end. Times without an offset (like +02:00) are local.
# A start in the future counts down to it.
{optional_datetime("custom_start", p.custom_start)}
{optional_datetime("custom_end", p.custom_end)}

# Send images hosted on Discord's CDN through CustomRP's proxy, since Discord won't show them directly
proxy_discord_cdn = {v(config.proxy_discord_cdn)}

[presence.large_image]
# An asset name from your application, or an image URL
key = {v(p.large_image)}
# Tooltip, and the link opened when the image is clicked
text = {v(p.large_text)}
url = {v(p.large_url)}

[presence.small_image]
key = {v(p.small_image)}
text = {v(p.small_text)}
url = {v(p.small_url)}

# Up to two buttons, each with a label (at most 31 bytes) and a URL
{button_text}

[connection]
# Which Discord to connect to: "auto", or 0 to 9 to pick one when several Discord clients run
pipe = {v("auto") if config.pipe < 0 else v(config.pipe)}
# Seconds between connection attempts while Discord isn't running
retry_interval = {v(retry)}
# How many times to retry before giving up; -1 retries forever
max_retries = {v(-1 if config.max_retries is None else config.max_retries)}

[run]
# Reload this file when it changes
watch_config = {v(config.watch_config)}

[logging]
# debug, info, warning or error
level = {v(config.log_level)}
# Also write the log to this file (relative to this config file's folder). Empty for none.
file = {v(str(config.log_file) if config.log_file else "")}
"""


def write_config(config: Config, path: Path, *, force: bool = False) -> None:
    """Writes a config file, refusing to overwrite unless ``force``. Raises :class:`ConfigError`."""
    if path.exists() and not force:
        raise ConfigError([msg.CONFIG_EXISTS.format(path=path)])
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_config(config), encoding="utf-8")
    except OSError as e:
        raise ConfigError([msg.CANT_WRITE.format(path=path, reason=e.strerror or e)]) from None
