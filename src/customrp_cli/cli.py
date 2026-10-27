"""Command-line parsing and the commands other than ``run``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from customrp_core import AssetsError, PresetError, build_activity, load_preset, save_preset
from customrp_core import __version__ as core_version
from customrp_core.assets import assets_page_url, fetch_assets

from . import __version__, logs, messages as msg, paths, runner
from .config import Config, ConfigError, load_config, write_config
from .instance import Instance

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2  # Also what argparse uses for usage errors
EXIT_NOT_RUNNING = 3  # status only, like LSB init scripts

DESCRIPTION = """\
Show a custom Discord Rich Presence, configured with a TOML file.
An independent command-line alternative to CustomRP for Linux, macOS and Windows."""

EPILOG = """\
Start with "customrp-cli init", edit the config file it creates, then "customrp-cli run".
Documentation: https://github.com/KeiraOMG0/customrp-cli"""


def _out(text: str = ""):
    print(text)


def _err(text: str):
    print(text, file=sys.stderr)


def _common_options(parser: argparse.ArgumentParser, suppress: bool):
    """-c/-v/-q work before and after the command; the copy on subcommands mustn't reset them."""
    default = argparse.SUPPRESS if suppress else None
    parser.add_argument("-c", "--config", type=Path, metavar="FILE", default=default,
                        help=f"config file (default: {paths.default_config_path()}; or set ${paths.CONFIG_ENV})")
    parser.add_argument("-v", "--verbose", action="count", default=argparse.SUPPRESS if suppress else 0,
                        help="show debug output")
    parser.add_argument("-q", "--quiet", action="store_true", default=argparse.SUPPRESS if suppress else False,
                        help="only show errors")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="customrp-cli", description=DESCRIPTION, epilog=EPILOG,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-V", "--version", action="version",
                        version=f"customrp-cli {__version__} (customrp-core {core_version})")
    _common_options(parser, suppress=False)

    common = argparse.ArgumentParser(add_help=False)
    _common_options(common, suppress=True)

    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    def command(name, help_text, **kwargs):
        return commands.add_parser(name, help=help_text, description=help_text, parents=[common], **kwargs)

    p = command("init", "create a config file with every option and its default")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")

    command("check", "check the config file for mistakes", aliases=["validate"])

    command("preview", "print the activity that would be sent to Discord, as JSON")

    p = command("run", "show the presence until stopped (Ctrl+C, SIGTERM or 'customrp-cli stop')")
    p.add_argument("--no-watch", action="store_true", help="don't reload the config file when it changes")

    p = command("stop", "stop the running instance")
    p.add_argument("--timeout", type=float, default=10, metavar="SECONDS",
                   help="how long to wait for it to stop (default: 10)")

    command("status", "say whether an instance is running, and how it's doing")

    p = command("import", "replace the presence in the config file with a CustomRP preset (.crp)")
    p.add_argument("preset", type=Path, help="the .crp file")
    p.add_argument("--force", action="store_true", help="overwrite the existing config file's presence")

    p = command("export", "save the configured presence as a CustomRP preset (.crp)")
    p.add_argument("preset", type=Path, help="the .crp file to write")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")

    p = command("assets", "list the art assets uploaded to the Discord application")
    p.add_argument("--application-id", metavar="ID", help="application to look up (default: from the config file)")

    command("paths", "show where the config and runtime files are")

    return parser


# --- Helpers -------------------------------------------------------------------------

def _config_path(args) -> Path:
    path = args.config or paths.default_config_path()
    return path.expanduser().absolute()


def _load(args) -> Config | None:
    """Loads the config, printing problems. Returns None if it can't be used."""
    try:
        return load_config(_config_path(args))
    except ConfigError as e:
        if e.about_values:
            _err(msg.CONFIG_INVALID)
            for problem in e.problems:
                _err(f"  {problem}")
        else:
            _err(e.problems[0])
        return None


def _print_problems(problems):
    for problem in problems:
        prefix = msg.ERROR_PREFIX if problem.is_error else msg.WARNING_PREFIX
        _err(f"{prefix}: {problem}")


def _instance() -> Instance:
    return Instance(paths.state_dir())


# --- Commands ------------------------------------------------------------------------

def cmd_init(args) -> int:
    path = _config_path(args)
    try:
        write_config(Config(), path, force=args.force)
    except ConfigError as e:
        _err(e.problems[0])
        return EXIT_CONFIG
    _out(msg.CONFIG_WRITTEN.format(path=path))
    return EXIT_OK


def cmd_check(args) -> int:
    config = _load(args)
    if config is None:
        return EXIT_CONFIG
    problems = config.problems()
    _print_problems(problems)
    errors = sum(p.is_error for p in problems)
    if problems:
        _out(msg.CHECK_SUMMARY.format(errors=errors, warnings=len(problems) - errors, path=config.path))
    else:
        _out(msg.CHECK_OK.format(path=config.path))
    return EXIT_CONFIG if errors else EXIT_OK


def cmd_preview(args) -> int:
    config = _load(args)
    if config is None:
        return EXIT_CONFIG
    problems = config.problems()
    _print_problems(problems)
    if any(p.is_error for p in problems):
        return EXIT_CONFIG

    now = datetime.now().astimezone()
    activity, refresh_in = build_activity(config.presence, connected_at=now, started_at=now,
                                          proxy_discord_cdn=config.proxy_discord_cdn)
    _out(json.dumps({"application_id": config.presence.effective_application_id, "activity": activity},
                    ensure_ascii=False, indent=2))
    return EXIT_OK


def cmd_run(args) -> int:
    config = _load(args)
    if config is None:
        return EXIT_CONFIG

    logs.setup(logs.level_for(config.log_level, args.verbose, args.quiet), config.log_file)
    problems = config.problems()
    for problem in problems:
        (logging.error if problem.is_error else logging.warning)("%s", problem)
    if any(p.is_error for p in problems):
        return EXIT_CONFIG

    return runner.run(config, _instance(), watch=not args.no_watch)


def cmd_stop(args) -> int:
    instance = _instance()
    pid = instance.running_pid()
    if pid is None:
        _out(msg.NOT_RUNNING)
        return EXIT_OK

    instance.request_stop()
    _out(msg.STOP_SENT.format(pid=pid or "unknown"))
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if instance.running_pid() is None:
            _out(msg.STOPPED)
            return EXIT_OK
        time.sleep(0.1)
    _err(msg.STOP_TIMEOUT.format(pid=pid or "unknown", timeout=args.timeout))
    return EXIT_FAILED


def cmd_status(args) -> int:
    instance = _instance()
    pid = instance.running_pid()
    if pid is None:
        _out(msg.NOT_RUNNING)
        return EXIT_NOT_RUNNING

    _out(msg.RUNNING.format(pid=pid or "unknown"))
    status = instance.read_status()
    if status.get("state"):
        detail = f" ({status['message']})" if status.get("message") else ""
        _out(msg.STATUS_STATE.format(state=status["state"], detail=detail))
    if status.get("user"):
        _out(msg.STATUS_USER.format(user=status["user"]))
    if status.get("config"):
        _out(msg.STATUS_CONFIG.format(path=status["config"]))
    if status.get("started"):
        _out(msg.STATUS_SINCE.format(since=status["started"]))
    return EXIT_OK


def cmd_import(args) -> int:
    path = _config_path(args)
    try:
        presence = load_preset(args.preset)
    except PresetError as e:
        _err(str(e))
        return EXIT_FAILED

    config = Config()
    if path.exists():
        if not args.force:
            _err(msg.CONFIG_EXISTS.format(path=path))
            return EXIT_CONFIG
        try:
            config = load_config(path)
            _out(msg.PRESET_KEPT_SETTINGS)
        except ConfigError:
            pass  # Broken anyway; replace it whole

    config.presence = presence
    try:
        write_config(config, path, force=True)
    except ConfigError as e:
        _err(e.problems[0])
        return EXIT_CONFIG

    _print_problems(config.problems())
    _out(msg.PRESET_IMPORTED.format(preset=args.preset, path=path))
    return EXIT_OK


def cmd_export(args) -> int:
    config = _load(args)
    if config is None:
        return EXIT_CONFIG
    if args.preset.exists() and not args.force:
        _err(msg.FILE_EXISTS.format(path=args.preset))
        return EXIT_FAILED
    try:
        save_preset(config.presence, args.preset)
    except PresetError as e:
        _err(str(e))
        return EXIT_FAILED
    _out(msg.PRESET_EXPORTED.format(path=config.path, preset=args.preset))
    return EXIT_OK


def cmd_assets(args) -> int:
    app_id = args.application_id
    if not app_id:
        config = _load(args)
        if config is None:
            return EXIT_CONFIG
        app_id = config.presence.effective_application_id

    try:
        assets = fetch_assets(app_id)
        page = assets_page_url(app_id)
    except AssetsError as e:
        _err(str(e))
        return EXIT_FAILED

    if not assets:
        _out(msg.ASSETS_NONE.format(app_id=app_id))
    else:
        _out(msg.ASSETS_HEADER.format(app_id=app_id))
        for asset in sorted(assets, key=lambda a: a.name.lower()):
            _out(f"  {asset.name}")
    _out(msg.ASSETS_PAGE.format(url=page))
    return EXIT_OK


def cmd_paths(args) -> int:
    state = paths.state_dir()
    _out(f"Config file:      {_config_path(args)}")
    _out(f"Config directory: {paths.config_dir()}")
    _out(f"State directory:  {state}  (lock, PID and status files)")
    return EXIT_OK


COMMANDS = {
    "init": cmd_init,
    "check": cmd_check,
    "validate": cmd_check,
    "preview": cmd_preview,
    "run": cmd_run,
    "stop": cmd_stop,
    "status": cmd_status,
    "import": cmd_import,
    "export": cmd_export,
    "assets": cmd_assets,
    "paths": cmd_paths,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return EXIT_CONFIG

    # Commands other than run log only library warnings (run sets up logging from the config)
    logs.setup(logs.level_for("warning", args.verbose, args.quiet))
    return COMMANDS[args.command](args)
