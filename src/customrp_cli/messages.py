"""User-facing text, kept in one place so it's easy to review (and to translate, should that ever happen).

Messages from customrp-core (validation, presets, connection errors) are passed through as they are.
"""

# --- Config file -----------------------------------------------------------------

CONFIG_MISSING = "No config file at {path}. Create one with: customrp-cli init"
CONFIG_UNREADABLE = "Can't read {path}: {reason}"
CONFIG_NOT_UTF8 = "{path} isn't a UTF-8 text file"
CONFIG_BAD_TOML = "{path} isn't valid TOML: {reason}"
CONFIG_EXISTS = "{path} already exists. Use --force to overwrite it."
CONFIG_WRITTEN = "Wrote {path}"
CONFIG_INVALID = "The config file has errors:"

UNKNOWN_OPTION = "unknown option"
DID_YOU_MEAN = " (did you mean '{suggestion}'?)"
EXPECTED_TYPE = "expected {expected}, got {actual}"
EXPECTED_CHOICE = "{value!r} isn't one of: {choices}"
AT_LEAST = "must be at least {minimum}"
TOO_MANY_BUTTONS = "Discord shows at most 2 buttons; {count} are set"
NEEDS_TIME = "needs a time as well as a date, like {example}"
BAD_DATETIME = "{value!r} isn't a date and time, like {example}"
PIPE_HINT = '"auto" or a number from 0 to 9'

TYPE_NAMES = {
    str: "a string", bool: "true or false", int: "a whole number", float: "a number", dict: "a table",
    list: "an array",
}

# --- Commands --------------------------------------------------------------------

CHECK_OK = "No problems found in {path}"
CHECK_SUMMARY = "{errors} error(s), {warnings} warning(s) in {path}"
ERROR_PREFIX = "error"
WARNING_PREFIX = "warning"

ALREADY_RUNNING = "customrp-cli is already running (PID {pid}). Stop it with: customrp-cli stop"
NOT_RUNNING = "customrp-cli isn't running"
RUNNING = "customrp-cli is running (PID {pid})"
STATUS_STATE = "  State: {state}{detail}"
STATUS_USER = "  Discord user: {user}"
STATUS_CONFIG = "  Config: {path}"
STATUS_SINCE = "  Running since: {since}"
STOP_SENT = "Asked customrp-cli (PID {pid}) to stop"
STOPPED = "Stopped"
STOP_TIMEOUT = "customrp-cli (PID {pid}) didn't stop within {timeout} seconds"

PRESET_IMPORTED = "Imported {preset} into {path}"
PRESET_EXPORTED = "Exported the presence from {path} to {preset}"
PRESET_KEPT_SETTINGS = "Kept the [connection], [run] and [logging] settings from the existing file"
FILE_EXISTS = "{path} already exists. Use --force to overwrite it."
CANT_WRITE = "Can't write {path}: {reason}"

ASSETS_NONE = "Application {app_id} has no art assets"
ASSETS_HEADER = "Art assets of application {app_id}:"
ASSETS_PAGE = "Manage them at {url}"

# --- Running ---------------------------------------------------------------------

RUN_STARTING = "Starting customrp-cli {version} with {path}"
RUN_STOPPED = "Stopped"
RUN_GAVE_UP = "Gave up connecting to Discord. Is the Discord desktop app running?"
RUN_RELOADED = "Reloaded {path}"
RUN_RELOAD_FAILED = "Not reloading {path}, it has errors:"
RUN_RESTART_NEEDED = "Changes to [connection] and [logging] take effect after a restart"
