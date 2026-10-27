import shutil
import sys
import tempfile

import pytest

from customrp_core.testing import FakeDiscord, ipc_address


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Keeps every test away from the real config and state directories."""
    monkeypatch.setenv("CUSTOMRP_CLI_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setenv("CUSTOMRP_CLI_STATE_DIR", str(tmp_path / "state"))
    return tmp_path


@pytest.fixture
def config_path(isolated):
    return isolated / "config.toml"


@pytest.fixture
def fake_discord(monkeypatch):
    """A fake Discord where discovery finds it: pipe 9 on Windows (so a real Discord on pipe 0 is
    left alone), or a socket in a temporary XDG_RUNTIME_DIR elsewhere. ``.pipe`` says which."""
    directory = None
    if sys.platform == "win32":
        pipe, address = 9, ipc_address(9)
    else:
        # Unix socket paths are limited to about 100 characters, so not under pytest's tmp_path
        directory = tempfile.mkdtemp(prefix="crp-", dir="/tmp")
        pipe, address = 0, ipc_address(0, directory)
        monkeypatch.setenv("XDG_RUNTIME_DIR", directory)

    server = FakeDiscord(address)
    try:
        server.start()
    except OSError as e:
        pytest.skip(f"Can't listen on {address}: {e}")
    server.pipe = pipe
    yield server
    server.stop()
    if directory:
        shutil.rmtree(directory, ignore_errors=True)
