# Installation

## Requirements

| | |
|---|---|
| Python | 3.9 or newer. Python 3.9 and 3.10 also need `tomli`, which is installed automatically. |
| Git | pip uses it to download customrp-core from GitHub |
| Discord | The desktop app, running on the same computer and user account. Flatpak, Snap and Vesktop should work too (see [troubleshooting](troubleshooting.md#discord-isnt-found)). |

customrp-cli isn't on PyPI. It installs from GitHub, and it fetches customrp-core from GitHub too. That's
what `requirements.txt` and the dependency in `pyproject.toml` point at, pinned to a release tag.

## With pipx (recommended)

[pipx](https://pipx.pypa.io) installs command-line tools into their own environments and puts them on
your `PATH`. If you already have it, skip to [installing customrp-cli](#installing-customrp-cli).

### Installing pipx

pipx needs **Python 3.11 or newer**. On Python 3.9 or 3.10, use the
[virtual environment](#with-a-virtual-environment-and-requirementstxt) method instead.

**macOS** ([Homebrew](https://brew.sh)):

```sh
brew install pipx
pipx ensurepath
```

**Ubuntu 23.04 or newer, Debian 12 or newer:**

```sh
sudo apt update
sudo apt install pipx
pipx ensurepath
```

**Fedora:**

```sh
sudo dnf install pipx
pipx ensurepath
```

**Arch:**

```sh
sudo pacman -S python-pipx
pipx ensurepath
```

**Other Linux distributions:**

```sh
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

If that fails with `externally-managed-environment`, your distribution wants you to use its own package
(look for one named `pipx` or `python3-pipx`). If there isn't one, put pipx in a virtual environment of
its own:

```sh
python3 -m venv ~/.local/share/pipx-venv
~/.local/share/pipx-venv/bin/pip install pipx
ln -s ~/.local/share/pipx-venv/bin/pipx ~/.local/bin/pipx
pipx ensurepath
```

**Windows**, with pip (use `python3` instead of `py` if Python came from the Microsoft Store):

```powershell
py -m pip install --user pipx
py -m pipx ensurepath
```

If pip warns that `pipx.exe` isn't on your `PATH`, go to the folder named in the warning and run
`.\pipx.exe ensurepath` there instead.

**Windows**, with [Scoop](https://scoop.sh):

```powershell
scoop install pipx
pipx ensurepath
```

Then **close the terminal and open a new one**, so the `PATH` change from `ensurepath` takes effect, and
check that it works:

```sh
pipx --version
```

These steps follow pipx's own [installation guide](https://pipx.pypa.io/stable/how-to/install-pipx.html),
which has more options and troubleshooting.

### Installing customrp-cli

```sh
pipx install git+https://github.com/KeiraOMG0/customrp-cli.git
customrp-cli --version
```

To install a specific release, add `@v0.1.0` to the URL.

## With a virtual environment and requirements.txt

```sh
git clone https://github.com/KeiraOMG0/customrp-cli.git
cd customrp-cli
python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt    # customrp-core from GitHub, and tomli on old Pythons
pip install .
customrp-cli --version
```

The command is only on your `PATH` while the environment is active. Without activating it, run
`.venv/bin/customrp-cli` (Windows: `.venv\Scripts\customrp-cli.exe`), or `python -m customrp_cli` with
the environment's Python.

On Debian and Ubuntu, `python3 -m venv` needs the `python3-venv` package.

## Windows notes

- Use `py` instead of `python3` if `python3` isn't found.
- `customrp-cli run` opens a console window. To run it hidden, use `pythonw.exe` from the same environment;
  see [running in the background](running-in-the-background.md#windows-task-scheduler).
- PowerShell may block `Activate.ps1`. Either run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or skip activation and call
  `.venv\Scripts\customrp-cli.exe` directly.
- If you also use CustomRP, quit it before running customrp-cli. Both would try to set your presence.

## Updating

```sh
pipx upgrade customrp-cli                           # pipx
pip install --upgrade -r requirements.txt . # venv, after git pull
```

Your config file isn't touched by updates.

## Uninstalling

```sh
customrp-cli stop
pipx uninstall customrp-cli          # or delete the virtual environment
```

Then delete the config folder (`customrp-cli paths` shows it) if you don't want to keep your settings.
If you set up a background service, remove that too (see
[running in the background](running-in-the-background.md)).

## Standalone executables

There aren't any yet. Since customrp-cli is pure Python, [PyInstaller](https://pyinstaller.org) can
build one if you need it:

```sh
pip install pyinstaller
pyinstaller --onefile --name customrp-cli src/customrp_cli/__main__.py
```

This isn't tested or supported yet.
