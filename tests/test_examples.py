"""The shipped example and service files must stay valid."""

import plistlib
from pathlib import Path

from customrp_cli.config import load_config

ROOT = Path(__file__).resolve().parent.parent


def test_example_config_has_no_problems():
    config = load_config(ROOT / "examples" / "config.toml")
    assert config.problems() == []
    assert config.presence.button2.label == "My website"


def test_launchd_plist_parses():
    with open(ROOT / "contrib" / "launchd" / "io.github.keiraomg0.customrp-cli.plist", "rb") as f:
        plist = plistlib.load(f)
    assert plist["ProgramArguments"][-1] == "run"


def test_systemd_unit_runs_the_cli():
    unit = (ROOT / "contrib" / "systemd" / "customrp-cli.service").read_text(encoding="utf-8")
    assert "ExecStart=%h/.local/bin/customrp-cli run" in unit
    assert "RestartPreventExitStatus=2" in unit
