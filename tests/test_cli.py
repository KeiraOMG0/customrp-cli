import json

import pytest

from customrp_cli import __version__, cli
from customrp_cli.config import load_config
from customrp_core import AssetsError, Button, Presence, save_preset
from customrp_core.assets import Asset


def run(*argv):
    return cli.main(list(argv))


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        run("--version")
    assert e.value.code == 0
    assert f"customrp-cli {__version__}" in capsys.readouterr().out


def test_no_command_shows_help(capsys):
    assert run() == cli.EXIT_CONFIG
    assert "usage: customrp-cli" in capsys.readouterr().out


def test_unknown_command():
    with pytest.raises(SystemExit) as e:
        run("dance")
    assert e.value.code == 2


def test_init(config_path, capsys):
    assert run("init") == 0
    assert config_path.exists()
    assert str(config_path) in capsys.readouterr().out

    assert run("init") == cli.EXIT_CONFIG
    assert "already exists" in capsys.readouterr().err
    assert run("init", "--force") == 0


def test_config_option_before_and_after_command(tmp_path):
    first, second = tmp_path / "a.toml", tmp_path / "b.toml"
    assert run("-c", str(first), "init") == 0
    assert run("init", "--config", str(second)) == 0
    assert first.exists() and second.exists()


def test_check(config_path, capsys):
    assert run("check") == cli.EXIT_CONFIG
    assert "customrp-cli init" in capsys.readouterr().err

    config_path.write_text('[presence]\ndetails = "Hello"\n')
    assert run("check") == 0
    assert "No problems found" in capsys.readouterr().out

    config_path.write_text('[presence]\ndetails = "H"\nparty_size = 3\n')
    assert run("validate") == cli.EXIT_CONFIG
    captured = capsys.readouterr()
    assert "error: presence.details: must be at least 2 characters long" in captured.err
    assert "warning: presence.party_max: is smaller than party_size" in captured.err
    assert "1 error(s), 1 warning(s)" in captured.out


def test_check_reports_every_bad_value(config_path, capsys):
    config_path.write_text('[presence]\ndetails = 1\ntype = "dancing"\n')
    assert run("check") == cli.EXIT_CONFIG
    err = capsys.readouterr().err
    assert "The config file has errors:" in err
    assert "  presence.details: expected a string" in err
    assert "  presence.type: 'dancing' isn't one of" in err


def test_preview(config_path, capsys):
    config_path.write_text('[presence]\napplication_id = "42"\ndetails = "Hello"\n'
                           '[presence.large_image]\nkey = "https://cdn.discordapp.com/a.png"\n')
    assert run("preview") == 0
    data = json.loads(capsys.readouterr().out)
    assert data["application_id"] == "42"
    assert data["activity"]["details"] == "Hello"
    assert data["activity"]["assets"]["large_image"] == "https://customrp.xyz/proxy/a.png"


def test_preview_refuses_errors(config_path, capsys):
    config_path.write_text('[presence]\ndetails = "x"\n')
    assert run("preview") == cli.EXIT_CONFIG
    assert capsys.readouterr().out == ""


def test_import_and_export(config_path, tmp_path, capsys):
    preset = tmp_path / "in.crp"
    save_preset(Presence(details="From preset", button1=Button("Go", "https://go.example")), preset)

    assert run("import", str(preset)) == 0
    assert load_config(config_path).presence.details == "From preset"

    # Importing over an existing file needs --force, and keeps the non-presence settings
    text = config_path.read_text().replace("max_retries = -1", "max_retries = 5")
    config_path.write_text(text)
    assert run("import", str(preset)) == cli.EXIT_CONFIG
    assert run("import", str(preset), "--force") == 0
    assert load_config(config_path).max_retries == 5
    assert "Kept the [connection]" in capsys.readouterr().out

    out = tmp_path / "out.crp"
    assert run("export", str(out)) == 0
    assert run("export", str(out)) == cli.EXIT_FAILED
    assert run("export", str(out), "--force") == 0

    from customrp_core import load_preset
    assert load_preset(out).button1 == Button("Go", "https://go.example")


def test_import_bad_preset(tmp_path, capsys):
    bad = tmp_path / "bad.crp"
    bad.write_text("<NotAPreset/>")
    assert run("import", str(bad)) == cli.EXIT_FAILED
    assert "Not a preset file" in capsys.readouterr().err


def test_assets(config_path, monkeypatch, capsys):
    looked_up = []

    def fake_fetch(app_id):
        looked_up.append(app_id)
        return [Asset("1", "zeta", 1), Asset("2", "Alpha", 2)]

    monkeypatch.setattr(cli, "fetch_assets", fake_fetch)
    config_path.write_text('[presence]\napplication_id = "777"\n')
    assert run("assets") == 0
    out = capsys.readouterr().out
    assert out.index("Alpha") < out.index("zeta")
    assert "developers/applications/777/rich-presence/assets" in out

    assert run("assets", "--application-id", "888") == 0
    assert looked_up == ["777", "888"]


def test_assets_failure(monkeypatch, capsys):
    def failing(app_id):
        raise AssetsError("Couldn't reach Discord: offline")

    monkeypatch.setattr(cli, "fetch_assets", failing)
    assert run("assets", "--application-id", "1") == cli.EXIT_FAILED
    assert "Couldn't reach Discord" in capsys.readouterr().err


def test_status_and_stop_when_not_running(capsys):
    assert run("status") == cli.EXIT_NOT_RUNNING
    assert run("stop") == 0
    assert capsys.readouterr().out.count("isn't running") == 2


def test_paths(isolated, capsys):
    assert run("paths") == 0
    out = capsys.readouterr().out
    assert str(isolated / "config.toml") in out
    assert str(isolated / "state") in out


def test_run_refuses_invalid_config(config_path, capsys):
    config_path.write_text('[presence]\ndetails = "x"\n')
    assert run("run") == cli.EXIT_CONFIG
