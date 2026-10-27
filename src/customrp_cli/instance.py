"""Keeping to one running instance per user, and letting other commands talk to it.

The running instance holds an exclusive lock on ``customrp-cli.lock`` in the state directory. The
OS releases the lock if the process dies, so a stale file never blocks a new start. Other commands
find the instance through files next to the lock:

* ``customrp-cli.pid``: the running instance's process ID
* ``status.json``: its current connection state, for ``customrp-cli status``
* ``stop-request``: created by ``customrp-cli stop``; the instance exits when it sees it

A stop file works the same on every platform. Signals don't: Windows has no SIGTERM to send
to another console process.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

LOCK_FILE = "customrp-cli.lock"
PID_FILE = "customrp-cli.pid"
STATUS_FILE = "status.json"
STOP_FILE = "stop-request"


def _try_lock(handle) -> bool:
    try:
        if sys.platform == "win32":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(handle):
    try:
        if sys.platform == "win32":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


class Instance:
    """The running instance's files in ``directory``."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._handle = None

    def _file(self, name: str) -> Path:
        return self.directory / name

    # --- Used by the running instance ----------------------------------------------------

    def acquire(self) -> bool:
        """Takes the lock. Returns False if another instance holds it."""
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = open(self._file(LOCK_FILE), "a+b")
        if not _try_lock(handle):
            handle.close()
            return False
        self._handle = handle
        self._file(PID_FILE).write_text(str(os.getpid()), encoding="ascii")
        self.clear_stop_request()
        return True

    def release(self):
        if self._handle is None:
            return
        for name in (PID_FILE, STATUS_FILE, STOP_FILE):
            try:
                self._file(name).unlink()
            except OSError:
                pass
        _unlock(self._handle)
        self._handle.close()
        self._handle = None

    def write_status(self, status: dict):
        tmp = self._file(STATUS_FILE + ".tmp")
        try:
            tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self._file(STATUS_FILE))
        except OSError:
            pass  # Status is informational; never let it stop the presence

    def stop_requested(self) -> bool:
        return self._file(STOP_FILE).exists()

    def clear_stop_request(self):
        try:
            self._file(STOP_FILE).unlink()
        except OSError:
            pass

    # --- Used by other commands ---------------------------------------------------------

    def running_pid(self) -> int | None:
        """The running instance's PID, 0 if it's running but the PID is unknown, or None if it isn't running."""
        lock = self._file(LOCK_FILE)
        if not lock.exists():
            return None
        try:
            handle = open(lock, "a+b")
        except OSError:
            return None
        try:
            if _try_lock(handle):
                _unlock(handle)
                return None
        finally:
            handle.close()

        try:
            return int(self._file(PID_FILE).read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return 0

    def read_status(self) -> dict:
        try:
            return json.loads(self._file(STATUS_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def request_stop(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self._file(STOP_FILE).write_text(str(os.getpid()), encoding="ascii")
