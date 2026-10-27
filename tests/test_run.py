"""The run command against a fake Discord, found the same way a real one would be."""

import os
import subprocess
import sys
import threading
import time

import pytest

from customrp_cli import cli, paths
from customrp_cli.instance import Instance
from customrp_core.testing import wait_until


def write_config(path, pipe, details, extra=""):
    path.write_text(f'[presence]\ndetails = "{details}"\n{extra}\n'
                    f'[connection]\npipe = {pipe}\nretry_interval = 1\nmax_retries = 2\n', encoding="utf-8")


def start_in_thread(*argv):
    result = {}
    thread = threading.Thread(target=lambda: result.setdefault("code", cli.main(list(argv))), daemon=True)
    thread.start()
    return thread, result


def test_run_reload_and_stop(fake_discord, config_path):
    write_config(config_path, fake_discord.pipe, "First")
    thread, result = start_in_thread("run")

    assert fake_discord.wait_for_activity()["details"] == "First"
    instance = Instance(paths.state_dir())
    assert wait_until(lambda: instance.read_status().get("state") == "connected")
    assert instance.read_status()["user"] == "tester"
    assert instance.running_pid() == os.getpid()

    # Saving the config file updates the presence without a restart
    time.sleep(0.05)  # Make sure the modification time changes
    write_config(config_path, fake_discord.pipe, "Second")
    assert fake_discord.wait_for_activity(2)["details"] == "Second"

    # A broken edit is ignored; the presence stays as it was
    config_path.write_text('[presence]\ndetails = "x"\n', encoding="utf-8")
    time.sleep(2)
    assert len(fake_discord.activities) == 2

    assert cli.main(["stop"]) == 0
    thread.join(10)
    assert result["code"] == 0
    assert instance.running_pid() is None


def test_second_instance_is_refused(fake_discord, config_path, capsys):
    write_config(config_path, fake_discord.pipe, "Only one")
    thread, result = start_in_thread("run", "--no-watch")
    fake_discord.wait_for_activity()

    assert cli.main(["run"]) == 1
    assert "already running" in capsys.readouterr().err

    assert cli.main(["stop"]) == 0
    thread.join(10)


def test_gives_up_without_discord(config_path, ipc_dir_or_skip):
    write_config(config_path, 7, "Nobody listens")
    started = time.monotonic()
    assert cli.main(["run", "-q"]) == 1
    assert time.monotonic() - started >= 2  # Two retries, one second apart


@pytest.fixture
def ipc_dir_or_skip(monkeypatch, tmp_path):
    if sys.platform == "win32":
        if os.path.exists(r"\\.\pipe\discord-ipc-7"):
            pytest.skip("Something is listening on discord-ipc-7")
    else:
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        for var in ("TMPDIR", "TMP", "TEMP"):
            monkeypatch.setenv(var, str(tmp_path))


def test_end_to_end_subprocess(fake_discord, config_path, tmp_path):
    """Runs the installed command as a separate process, the way a service manager would."""
    write_config(config_path, fake_discord.pipe, "From a subprocess")
    env = dict(os.environ)
    command = [sys.executable, "-m", "customrp_cli"]

    process = subprocess.Popen(command + ["run"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True)
    try:
        assert fake_discord.wait_for_activity(timeout=20)["details"] == "From a subprocess"

        status = subprocess.run(command + ["status"], env=env, capture_output=True, text=True, timeout=30)
        assert status.returncode == 0, status.stdout + status.stderr
        # Not process.pid: on Windows, a venv's python.exe starts the real interpreter as a child
        assert "customrp-cli is running (PID" in status.stdout
        assert "State: connected" in status.stdout

        stop = subprocess.run(command + ["stop"], env=env, capture_output=True, text=True, timeout=30)
        assert stop.returncode == 0, stop.stdout + stop.stderr
        output, _ = process.communicate(timeout=15)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()

    assert process.returncode == 0, output
    assert "Presence updated" in output
    assert "Stopped" in output
