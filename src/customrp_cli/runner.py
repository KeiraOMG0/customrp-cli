"""The ``run`` command: show the presence until asked to stop."""

from __future__ import annotations

import logging
import os
import signal
import threading
from datetime import datetime
from pathlib import Path

from customrp_core import PresenceSession, SessionState, display_name

from . import __version__, messages as msg
from .config import Config, ConfigError, load_config
from .instance import Instance

log = logging.getLogger("customrp_cli")

EXIT_OK = 0
EXIT_FAILED = 1

# How often to check for stop requests and config changes, in seconds
TICK = 0.5


class ConfigWatcher:
    """Notices when the config file changes, once it has stopped changing (editors save in steps)."""

    def __init__(self, path: Path):
        self.path = path
        self._loaded = self._signature()
        self._pending = None

    def _signature(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size
        except OSError:
            return None

    def changed(self) -> bool:
        current = self._signature()
        if current == self._loaded or current is None:
            self._pending = None
            return False
        if current != self._pending:
            self._pending = current  # Wait one more tick to see that it has settled
            return False
        self._loaded = current
        self._pending = None
        return True

    def mark_loaded(self):
        self._loaded = self._signature()
        self._pending = None


def _log_problems(problems):
    for problem in problems:
        if problem.is_error:
            log.error("%s", problem)
        else:
            log.warning("%s", problem)


class Runner:
    def __init__(self, config: Config, instance: Instance, *, watch: bool):
        self.config = config
        self.instance = instance
        self.watch = watch and config.watch_config and config.path is not None
        self.stop_event = threading.Event()
        self.reload_event = threading.Event()
        self.started = datetime.now().astimezone()
        self.session = PresenceSession(
            config.presence, pipe=config.pipe, retry_interval=config.retry_interval,
            max_retries=config.max_retries, proxy_discord_cdn=config.proxy_discord_cdn,
            on_state_change=self._state_changed)

    def _state_changed(self, state: SessionState, message: str | None):
        # The library logs connection problems itself; this only records the state for "status"
        user = self.session.user
        self.instance.write_status({
            "pid": os.getpid(),
            "state": state.value,
            "message": message,
            "user": display_name(user) if user else None,
            "config": str(self.config.path) if self.config.path else None,
            "started": self.started.isoformat(timespec="seconds"),
            "updated": datetime.now().astimezone().isoformat(timespec="seconds"),
        })

    def _install_signal_handlers(self):
        previous = {}

        def stop(signum, frame):
            self.stop_event.set()

        def reload(signum, frame):
            self.reload_event.set()

        # SIGINT stays as KeyboardInterrupt. SIGTERM is what service managers send;
        # SIGBREAK is Ctrl+Break on Windows; SIGHUP traditionally means "reload".
        for name, handler in (("SIGTERM", stop), ("SIGBREAK", stop), ("SIGHUP", reload)):
            signum = getattr(signal, name, None)
            if signum is not None:
                try:
                    previous[signum] = signal.signal(signum, handler)
                except (ValueError, OSError):  # Not on the main thread, or not supported
                    pass
        return previous

    def _reload(self, watcher: ConfigWatcher | None):
        path = self.config.path
        if watcher:
            watcher.mark_loaded()
        try:
            new = load_config(path)
        except ConfigError as e:
            log.error(msg.RUN_RELOAD_FAILED.format(path=path))
            for problem in e.problems:
                log.error("  %s", problem)
            return

        problems = new.problems()
        if any(p.is_error for p in problems):
            log.error(msg.RUN_RELOAD_FAILED.format(path=path))
            _log_problems(problems)
            return

        _log_problems(problems)
        if not self.config.same_runtime_settings(new):
            log.warning(msg.RUN_RESTART_NEEDED)
        self.session.proxy_discord_cdn = new.proxy_discord_cdn
        self.watch = self.watch and new.watch_config
        self.config = new
        log.info(msg.RUN_RELOADED.format(path=path))
        self.session.update(new.presence)

    def run(self) -> int:
        previous_handlers = self._install_signal_handlers()
        watcher = ConfigWatcher(self.config.path) if self.watch else None
        self.session.start()
        try:
            while not self.session.wait(TICK):
                if self.stop_event.is_set() or self.instance.stop_requested():
                    break
                if self.reload_event.is_set() or (self.watch and watcher and watcher.changed()):
                    self.reload_event.clear()
                    self._reload(watcher)
        except KeyboardInterrupt:
            pass
        finally:
            self.session.stop()
            self.session.wait(5)
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)

        if self.session.gave_up:
            log.error(msg.RUN_GAVE_UP)
            return EXIT_FAILED
        log.info(msg.RUN_STOPPED)
        return EXIT_OK


def run(config: Config, instance: Instance, *, watch: bool = True) -> int:
    """Runs until stopped. The caller has already set up logging and checked the config for errors."""
    if not instance.acquire():
        log.error(msg.ALREADY_RUNNING.format(pid=instance.running_pid() or "unknown"))
        return EXIT_FAILED
    try:
        log.info(msg.RUN_STARTING.format(version=__version__, path=config.path))
        return Runner(config, instance, watch=watch).run()
    finally:
        instance.release()
