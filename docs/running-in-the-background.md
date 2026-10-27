# Running in the background

`customrp-cli run` is a normal long-running program. It doesn't fork into the background itself; you
start it from a service manager, which takes care of starting it at login, restarting it, and collecting
its log. It stops cleanly on SIGTERM, which every service manager sends.

Discord has to run under the same user, so customrp-cli runs as a **user** service, not a system one.
With `max_retries = -1` (the default), it's fine to start it before Discord; it waits for it.

The examples assume a pipx install. Run `which customrp-cli` (Windows: `where customrp-cli`) to find
your path if you installed it differently.

## Linux: systemd user service

[`contrib/systemd/customrp-cli.service`](../contrib/systemd/customrp-cli.service):

```ini
[Unit]
Description=Custom Discord Rich Presence (customrp-cli)

[Service]
Type=simple
ExecStart=%h/.local/bin/customrp-cli run
Restart=on-failure
RestartSec=30
RestartPreventExitStatus=2

[Install]
WantedBy=default.target
```

```sh
mkdir -p ~/.config/systemd/user
cp contrib/systemd/customrp-cli.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now customrp-cli     # Start now and at every login

systemctl --user status customrp-cli
journalctl --user -u customrp-cli -f           # Follow the log
systemctl --user restart customrp-cli          # After changing [connection] or [logging]
systemctl --user disable --now customrp-cli    # Stop and don't start at login
```

`%h` is your home folder. `RestartPreventExitStatus=2` keeps systemd from restarting it over and over
when the config file has errors; fix the file, then `systemctl --user restart customrp-cli`.

`customrp-cli status` and `customrp-cli stop` work on the service too. But systemd restarts it after a
`stop` only on failure, and `stop` counts as success, so use `systemctl --user stop` to stop it for good.

## Linux: without systemd

Use your desktop's autostart, or start it from a shell profile:

```sh
nohup customrp-cli run -q >/dev/null 2>&1 &
```

Set `[logging] file` to keep a log. A second copy refuses to start, so running this at every login is safe.

XDG desktop autostart (`~/.config/autostart/customrp-cli.desktop`):

```ini
[Desktop Entry]
Type=Application
Name=customrp-cli
Exec=sh -c "$HOME/.local/bin/customrp-cli run -q"
X-GNOME-Autostart-enabled=true
NoDisplay=true
```

## macOS: launchd agent

[`contrib/launchd/io.github.keiraomg0.customrp-cli.plist`](../contrib/launchd/io.github.keiraomg0.customrp-cli.plist).
Replace `YOUR_USER_NAME` in both paths first (launchd doesn't expand `~`), then:

```sh
cp contrib/launchd/io.github.keiraomg0.customrp-cli.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/io.github.keiraomg0.customrp-cli.plist     # Starts now and at login
tail -f ~/Library/Logs/customrp-cli.log
launchctl unload ~/Library/LaunchAgents/io.github.keiraomg0.customrp-cli.plist   # Stop and remove
```

On macOS, Discord's socket is in your per-user temporary folder. customrp-cli asks the system for that
folder when launchd doesn't set `TMPDIR`. If the log still says Discord can't be found, add this to the
plist's main `<dict>`, with the output of `getconf DARWIN_USER_TEMP_DIR`:

```xml
<key>EnvironmentVariables</key>
<dict>
    <key>TMPDIR</key>
    <string>/var/folders/xx/xxxxxxxx/T/</string>
</dict>
```

The macOS setup hasn't been tested yet. Reports are welcome.

## Windows: Task Scheduler

To run without a console window, use `pythonw.exe` from the environment customrp-cli is installed in,
and log to a file, since there's no console to log to:

```toml
[logging]
file = "customrp-cli.log"     # Next to config.toml
```

Find the environment: with pipx, `pipx environment --value PIPX_LOCAL_VENVS` prints the folder that
holds it (`...\venvs\customrp-cli`). With your own virtual environment, it's the `.venv` folder.

Create a task that starts at login (in Command Prompt; adjust the path):

```bat
schtasks /Create /TN "customrp-cli" /SC ONLOGON /RL LIMITED ^
  /TR "\"C:\Users\you\pipx\venvs\customrp-cli\Scripts\pythonw.exe\" -m customrp_cli run"
```

Manage it:

```bat
schtasks /Run /TN "customrp-cli"
customrp-cli status
customrp-cli stop
schtasks /Delete /TN "customrp-cli" /F
```

Or use the Task Scheduler window: **Create Task** → **Triggers**: At log on → **Actions**: Start a program,
with `pythonw.exe` as the program and `-m customrp_cli run` as the arguments.

Running hidden under `pythonw` with a log file has been tested. The `schtasks` setup itself hasn't been
tested yet.

## Checking on it

Whatever starts it, these work from any terminal:

```sh
customrp-cli status    # Running? Connected? As whom?
customrp-cli stop      # Stop it cleanly
```
