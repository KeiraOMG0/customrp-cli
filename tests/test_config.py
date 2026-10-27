from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from customrp_cli.config import Config, ConfigError, load_config, parse_config, render_config, toml_value, write_config
from customrp_core import ActivityType, Button, Presence, StatusDisplay, TimestampMode

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib


def parse(text, base_dir=None):
    return parse_config(tomllib.loads(text), base_dir=base_dir)


def problems_of(text):
    with pytest.raises(ConfigError) as e:
        parse(text)
    assert e.value.about_values
    return e.value.problems


FULL = """
[presence]
application_id = "1234"
type = "Listening"
status_display = "details"
name = "Name"
details = "Details"
details_url = "example.com/d"
state = "State"
state_url = "https://example.com/s"
party_size = 2
party_max = 5
timestamps = "custom"
custom_start = 2026-01-01T12:00:00
custom_end = 2026-01-02T12:00:00+02:00
proxy_discord_cdn = false

[presence.large_image]
key = "logo"
text = "Large"
url = "https://example.com/l"

[presence.small_image]
key = "https://example.com/s.png"
text = "Small"

[[presence.buttons]]
label = "One"
url = "https://one.example"

[[presence.buttons]]
label = "Two"
url = "https://two.example"

[connection]
pipe = 3
retry_interval = 2.5
max_retries = 7

[run]
watch_config = false

[logging]
level = "debug"
file = "logs/customrp.log"
"""


def test_empty_file_gives_defaults():
    assert parse("") == Config()


def test_full_file():
    config = parse(FULL, base_dir=Path("/configs"))
    p = config.presence
    assert p.application_id == "1234"
    assert p.type == ActivityType.LISTENING
    assert p.status_display == StatusDisplay.DETAILS
    assert (p.name, p.details, p.details_url, p.state) == ("Name", "Details", "example.com/d", "State")
    assert (p.party_size, p.party_max) == (2, 5)
    assert p.timestamps == TimestampMode.CUSTOM
    assert p.custom_start == datetime(2026, 1, 1, 12)
    assert p.custom_end == datetime(2026, 1, 2, 12, tzinfo=timezone(timedelta(hours=2)))
    assert (p.large_image, p.large_text, p.large_url) == ("logo", "Large", "https://example.com/l")
    assert (p.small_image, p.small_text, p.small_url) == ("https://example.com/s.png", "Small", "")
    assert p.button1 == Button("One", "https://one.example")
    assert p.button2 == Button("Two", "https://two.example")
    assert config.proxy_discord_cdn is False
    assert (config.pipe, config.retry_interval, config.max_retries) == (3, 2.5, 7)
    assert config.watch_config is False
    assert config.log_level == "debug"
    assert config.log_file == Path("/configs/logs/customrp.log")


def test_defaults_for_connection():
    config = parse('[connection]\npipe = "auto"\nmax_retries = -1')
    assert (config.pipe, config.max_retries, config.retry_interval) == (-1, None, 10.0)


def test_template_loads_as_defaults():
    assert parse(render_config(Config())) == Config()


def test_render_roundtrip():
    config = parse(FULL, base_dir=Path("/configs").absolute())
    config.presence.details = 'Quotes " and \\ backslashes, tabs\t, emoji \U0001f600 and DEL \x7f'
    assert parse(render_config(config)) == config


def test_render_roundtrip_single_button():
    config = Config(presence=Presence(button2=Button("Only", "https://x.example")))
    loaded = parse(render_config(config))
    # Empty buttons aren't written, so the second button becomes the first
    assert loaded.presence.button1 == Button("Only", "https://x.example")


def test_unknown_keys_get_suggestions():
    problems = problems_of('[presence]\ndetials = "x"\n[logging]\nlevle = "info"\n[extra]')
    assert "presence.detials: unknown option (did you mean 'details'?)" in problems
    assert "logging.levle: unknown option (did you mean 'level'?)" in problems
    assert any(p.startswith("extra: unknown option") for p in problems)


def test_wrong_types_are_all_reported():
    problems = problems_of('[presence]\ndetails = 5\nparty_size = "two"\nproxy_discord_cdn = "yes"\n'
                           'large_image = "logo"\n[connection]\nretry_interval = true')
    assert problems == [
        "presence.details: expected a string, got a whole number",
        "presence.party_size: expected a whole number, got a string",
        "presence.large_image: expected a table, got a string",
        "presence.proxy_discord_cdn: expected true or false, got a string",
        "connection.retry_interval: expected a number, got true or false",
    ]


def test_choices():
    assert parse('[presence]\ntype = " Competing "\ntimestamps = "local-time"').presence.timestamps == \
        TimestampMode.LOCAL_TIME
    problems = problems_of('[presence]\ntype = "streaming"')
    assert problems == ["presence.type: 'streaming' isn't one of: playing, listening, watching, competing"]


def test_ranges():
    problems = problems_of("[presence]\nparty_size = -1\n[connection]\npipe = 10\nretry_interval = 0.5\n"
                           "max_retries = -2")
    assert problems == [
        "presence.party_size: must be at least 0",
        'connection.pipe: expected "auto" or a number from 0 to 9, got 10',
        "connection.retry_interval: must be at least 1",
        "connection.max_retries: must be at least -1",
    ]


def test_datetimes():
    p = parse('[presence]\ncustom_start = "2026-03-04T05:06:07Z"\ncustom_end = "2026-03-04 08:00"').presence
    assert p.custom_start == datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
    assert p.custom_end == datetime(2026, 3, 4, 8, 0)

    problems = problems_of('[presence]\ncustom_start = 2026-03-04\ncustom_end = "soon"')
    assert problems == [
        "presence.custom_start: needs a time as well as a date, like 2026-03-04T00:00:00",
        "presence.custom_end: 'soon' isn't a date and time, like 2026-01-01T12:00:00",
    ]


def test_buttons():
    text = '[presence]\nbuttons = [{label = "a1", url = "x.com"}, {label = "b2", url = "y.com"}, {label = "c3"}]'
    assert problems_of(text) == ["presence.buttons: Discord shows at most 2 buttons; 3 are set"]
    assert problems_of('[presence]\nbuttons = ["a"]') == [
        "presence.buttons: expected an array of tables, got an array of other values"]
    assert problems_of('[[presence.buttons]]\nlable = "ab"\nurl = "x"') == [
        "presence.buttons[1].lable: unknown option (did you mean 'label'?)"]


def test_problems_use_config_keys():
    config = parse('[presence]\ndetails = "x"\ntimestamps = "custom"\n[presence.large_image]\ntext = "tooltip"\n'
                   '[[presence.buttons]]\nlabel = "l"\nurl = "not a url"')
    found = {(p.key, p.is_error) for p in config.problems()}
    assert found == {
        ("presence.details", True),
        ("presence.custom_start", True),
        ("presence.large_image.key", False),
        ("presence.buttons[1].label", True),
        ("presence.buttons[1].url", True),
    }


def test_load_errors(tmp_path):
    with pytest.raises(ConfigError, match="customrp-cli init") as e:
        load_config(tmp_path / "missing.toml")
    assert not e.value.about_values

    bad = tmp_path / "bad.toml"
    bad.write_text("[presence\n")
    with pytest.raises(ConfigError, match="isn't valid TOML"):
        load_config(bad)

    binary = tmp_path / "binary.toml"
    binary.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ConfigError, match="UTF-8"):
        load_config(binary)


def test_load_tolerates_bom(tmp_path):
    path = tmp_path / "c.toml"
    path.write_bytes(b'\xef\xbb\xbf[presence]\ndetails = "Hi"\n')
    config = load_config(path)
    assert config.presence.details == "Hi"
    assert config.path == path


def test_write_config(tmp_path):
    path = tmp_path / "sub" / "config.toml"
    write_config(Config(), path)
    assert load_config(path).presence == Presence()
    with pytest.raises(ConfigError, match="already exists"):
        write_config(Config(), path)
    write_config(Config(presence=Presence(details="New")), path, force=True)
    assert load_config(path).presence.details == "New"


def test_toml_value():
    assert toml_value(True) == "true"
    assert toml_value(3) == "3"
    assert toml_value(2.5) == "2.5"
    assert toml_value("a\nb") == '"a\\nb"'
    assert toml_value(datetime(2026, 1, 1, 12)) == "2026-01-01T12:00:00"
