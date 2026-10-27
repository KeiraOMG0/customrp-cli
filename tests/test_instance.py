import os

from customrp_cli.instance import Instance


def test_single_instance(tmp_path):
    first, second = Instance(tmp_path), Instance(tmp_path)
    assert first.running_pid() is None

    assert first.acquire()
    try:
        assert not second.acquire()
        assert second.running_pid() == os.getpid()
    finally:
        first.release()

    assert second.running_pid() is None
    assert second.acquire()
    second.release()


def test_stale_files_dont_count_as_running(tmp_path):
    (tmp_path / "customrp-cli.lock").write_text("")
    (tmp_path / "customrp-cli.pid").write_text("99999")
    assert Instance(tmp_path).running_pid() is None


def test_stop_request(tmp_path):
    running, other = Instance(tmp_path), Instance(tmp_path)
    other.request_stop()
    assert running.acquire()  # Clears a leftover request
    try:
        assert not running.stop_requested()
        other.request_stop()
        assert running.stop_requested()
    finally:
        running.release()
    assert not running.stop_requested()


def test_status(tmp_path):
    instance = Instance(tmp_path)
    assert instance.read_status() == {}
    assert instance.acquire()
    try:
        instance.write_status({"state": "connected", "user": "téster"})
        assert Instance(tmp_path).read_status() == {"state": "connected", "user": "téster"}
    finally:
        instance.release()
    assert instance.read_status() == {}
