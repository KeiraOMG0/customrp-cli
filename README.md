# customrp-cli

Show a custom Discord Rich Presence ("Playing ...", with your own text, images, buttons and timer) from
the command line, configured with a TOML file. It runs natively on **Linux**, **macOS** and **Windows**.

customrp-cli is a command-line alternative to [CustomRP](https://www.customrp.xyz), the Windows app by
maximmax42. It does what CustomRP does, minus the window. It's built on
[customrp-core](https://github.com/KeiraOMG0/customrp-core), a library that does the heavy lifting.

> **Independent project.** customrp-cli isn't made or maintained by CustomRP's developer, and isn't an
> official replacement. Please report problems [here](https://github.com/KeiraOMG0/customrp-cli/issues),
> not on the CustomRP repository.

```console
$ customrp-cli init
Wrote /home/you/.config/customrp-cli/config.toml
$ nano ~/.config/customrp-cli/config.toml
$ customrp-cli run
2026-01-01 12:00:00 INFO    Starting customrp-cli 0.1.0 with /home/you/.config/customrp-cli/config.toml
2026-01-01 12:00:00 INFO    Connecting to Discord with application ID 896771305108553788
2026-01-01 12:00:00 INFO    Connected to /run/user/1000/discord-ipc-0
2026-01-01 12:00:00 INFO    Connected to Discord as you
2026-01-01 12:00:00 INFO    Presence updated
```

## Why

CustomRP is a Windows Forms application, so it only runs on Windows. Linux users have had to rely on Wine
or RPC bridges. The GUI is convenient, but the useful part, telling Discord what to show, doesn't need a
window. customrp-cli does that part natively, from a config file. That also makes it work on headless
setups, under a service manager, and in dotfiles.

## Features

- Everything CustomRP can show: activity type (Playing, Listening, Watching, Competing), name, details
  and state lines with optional links, party size, large and small images (asset names or URLs) with
  tooltips and links, two buttons, and which field appears in the member list
- All five CustomRP timestamp modes: since last connection, since startup, since last update, local
  time, and custom start/end (including countdowns)
- Live reload: save the config file and the presence updates within a second, without reconnecting
- Checks your config the way Discord will (length limits in bytes, one-character fields, broken URLs,
  image URLs that are too long) and names the exact option at fault
- Waits for Discord: if Discord isn't running yet, it retries every 10 seconds, and reconnects if
  Discord restarts
- Imports and exports CustomRP's `.crp` presets, so you can move presets between this and the Windows app
- Lists the art assets uploaded to your Discord application
- One instance per user, with `status` and `stop` commands that work on every platform
- Runs as a systemd user service, a launchd agent, or a Windows scheduled task; ready-made files are in
  [`contrib/`](https://github.com/KeiraOMG0/customrp-cli/tree/main/contrib)
- No GUI, no Wine, and nothing beyond Python (plus `tomli` on Python 3.9 and 3.10)

## How it differs from CustomRP

| CustomRP (Windows app) | customrp-cli |
|---|---|
| Window with text boxes and dropdowns | A TOML config file ([reference](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/configuration.md)) |
| Click "Update presence" | Save the file; it reloads automatically |
| Minimizes to the tray | Runs in a terminal or as a background service |
| "Run on startup" checkbox | systemd, launchd or Task Scheduler ([guide](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/running-in-the-background.md)) |
| Gives up after 30 attempts to reach Discord | Retries forever by default (`max_retries`) |
| Translated into many languages | English only for now |
| Built-in update checker | Update with `pipx upgrade customrp-cli` |

More in [docs/migrating-from-customrp.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/migrating-from-customrp.md).

## Supported systems

| System | Status |
|---|---|
| Linux | Tests run in CI on Ubuntu, and were run on Ubuntu 24.04 (WSL), against a fake Discord over a real Unix socket, including running as a separate process. **Not yet tested against the real Discord client on Linux.** |
| Windows 10/11 | Tests run in CI and on Windows 11 against a fake Discord over a named pipe, including background mode with `pythonw`. The underlying library has completed a handshake with the real Discord client. |
| macOS | Tests run in CI on macOS against a fake Discord over a real Unix socket, including running as a separate process. **Not yet tested against the real Discord client on macOS**, and the launchd setup is untested. |

You need:

- Python 3.9 or newer
- The Discord **desktop** app (or a client that provides Discord's IPC socket, like Vesktop) running on
  the same computer, as the same user. The browser version can't show Rich Presence from other programs.

## Installation

The easiest way is [pipx](https://pipx.pypa.io), which puts customrp-cli in its own environment and
on your `PATH`:

```sh
pipx install customrp-cli
```

Don't have pipx? It needs Python 3.11 or newer. The short version:

| System | Command |
|---|---|
| macOS | `brew install pipx` |
| Ubuntu, Debian | `sudo apt install pipx` |
| Fedora | `sudo dnf install pipx` |
| Arch | `sudo pacman -S python-pipx` |
| Windows | `py -m pip install --user pipx` |

Then run `pipx ensurepath` (on Windows: `py -m pipx ensurepath`) and open a new terminal. Step-by-step
instructions for every system are in [docs/installation.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/installation.md#installing-pipx).

Or with a virtual environment and `requirements.txt`:

```sh
git clone https://github.com/KeiraOMG0/customrp-cli.git
cd customrp-cli
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # Installs customrp-core from GitHub
pip install .
```

Plain `pip install customrp-cli` inside a virtual environment works too.

Details, including Windows notes and uninstalling, are in [docs/installation.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/installation.md).

## Quick start

```sh
customrp-cli init       # Writes a config file with every option, then prints its path
# Edit the file: set details, state, images, buttons...
customrp-cli check      # Points out mistakes
customrp-cli preview    # Shows exactly what will be sent to Discord
customrp-cli run        # Shows the presence until you press Ctrl+C
```

To use your own application name and images, create an application in the
[Discord Developer Portal](https://discord.com/developers/applications) and put its ID in
`application_id`. CustomRP's [setup guide](https://docs.customrp.xyz/setting-up) walks through it.

## Configuration

A minimal config:

```toml
[presence]
application_id = "123456789012345678"
details = "Exploring the Linux desktop"
state = "Day 3"
timestamps = "since_startup"

[presence.large_image]
key = "penguin"               # An asset name from your application, or an image URL
text = "Tux says hi"

[[presence.buttons]]
label = "My website"
url = "https://example.com"
```

Every option is optional. [`examples/config.toml`](https://github.com/KeiraOMG0/customrp-cli/blob/main/examples/config.toml) is a complete, commented
example, and [docs/configuration.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/configuration.md) explains each option.

The config file is at:

| System | Default path |
|---|---|
| Linux | `~/.config/customrp-cli/config.toml` (or `$XDG_CONFIG_HOME/customrp-cli/`) |
| macOS | `~/Library/Application Support/customrp-cli/config.toml` |
| Windows | `%APPDATA%\customrp-cli\config.toml` |

Use another file with `-c path/to/file.toml`, or set `CUSTOMRP_CLI_CONFIG`.

## Commands

| Command | Does |
|---|---|
| `customrp-cli init [--force]` | Create a config file listing every option |
| `customrp-cli check` | Check the config for mistakes (alias: `validate`) |
| `customrp-cli preview` | Print the activity that would be sent, as JSON |
| `customrp-cli run [--no-watch]` | Show the presence until stopped |
| `customrp-cli status` | Show whether it's running, its connection state and Discord user |
| `customrp-cli stop` | Stop the running instance |
| `customrp-cli import FILE.crp [--force]` | Replace the presence in the config with a CustomRP preset |
| `customrp-cli export FILE.crp [--force]` | Save the configured presence as a CustomRP preset |
| `customrp-cli assets [--application-id ID]` | List the images uploaded to your Discord application |
| `customrp-cli paths` | Show where the config and runtime files are |

Options for every command: `-c/--config FILE`, `-v/--verbose` (debug output), `-q/--quiet` (errors
only), `-h/--help`, plus `-V/--version`. Exit codes and more examples are in
[docs/commands.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/commands.md).

customrp-cli never asks questions or waits for input, so it's safe to use from scripts, cron and service
managers.

## Running in the background

```sh
# Linux (systemd), after installing with pipx:
mkdir -p ~/.config/systemd/user
curl -o ~/.config/systemd/user/customrp-cli.service \
  https://raw.githubusercontent.com/KeiraOMG0/customrp-cli/main/contrib/systemd/customrp-cli.service
systemctl --user daemon-reload
systemctl --user enable --now customrp-cli
journalctl --user -u customrp-cli -f     # Watch the log
```

macOS (launchd) and Windows (Task Scheduler) are covered in
[docs/running-in-the-background.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/running-in-the-background.md).

## Logging and troubleshooting

`run` logs to the terminal (stderr). Add `-v` to see every message exchanged with Discord, or set
`[logging] file` to also log to a file (rotated at 1 MB).

| Problem | Try |
|---|---|
| `Couldn't find a running Discord client` | Start the Discord desktop app. With Flatpak or Snap, see [troubleshooting](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/troubleshooting.md#discord-isnt-found). |
| `Discord returned an error (4000): Invalid Client ID` | `application_id` is wrong |
| Runs fine but nothing shows on your profile | In Discord: User Settings → Activity Privacy → turn on sharing your activity |
| `already running` | `customrp-cli status`, then `customrp-cli stop` |

More in [docs/troubleshooting.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/troubleshooting.md).

## Known limitations

- English only.
- Only the presence settings are shared with CustomRP, through `.crp` presets; CustomRP's own settings
  file isn't read.
- One instance per user. Showing two presences at once isn't supported.
- Discord's socket locations for Flatpak, Snap and Vesktop come from other Rich Presence projects and
  haven't been verified here.
- Changes to `[connection]` and `[logging]` need a restart; `[presence]` changes apply live.

## Documentation

[docs/](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/index.md): [installation](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/installation.md) · [configuration](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/configuration.md) ·
[commands](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/commands.md) · [background](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/running-in-the-background.md) ·
[troubleshooting](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/troubleshooting.md) · [migrating from CustomRP](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/migrating-from-customrp.md) ·
[design](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/design.md) · [development](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/development.md)

## Running the tests

```sh
pip install -e ".[test]"
pytest
```

The tests don't need Discord; they use a fake Discord server from customrp-core. See
[docs/development.md](https://github.com/KeiraOMG0/customrp-cli/blob/main/docs/development.md).

## Contributing

Issues and pull requests are welcome. Please:

- open an issue first for anything big
- add tests for behaviour changes (`pytest` must pass)
- keep it small: no new dependencies or abstractions without a concrete need
- put changes to how presences work in [customrp-core](https://github.com/KeiraOMG0/customrp-core),
  and changes to the command line, config and running in this repository

## Credits

- [CustomRP](https://github.com/maximmax42/Discord-CustomRP) by maximmax42 (MIT). The features, rules and
  preset format come from it, and its developer was open to an independent alternative.
- CustomRP's default Discord application and its image proxy (`customrp.xyz/proxy`, used for Discord-hosted
  images) belong to CustomRP's developer.

## License

MIT. See [LICENSE](https://github.com/KeiraOMG0/customrp-cli/blob/main/LICENSE).
