# Design

Why customrp-cli is built the way it is.

## What the original does

Before writing anything, CustomRP's source (version 1.19.4.1, C# and Windows Forms) was read to find out
what the app actually does, rather than assuming it's a plain Rich Presence client:

- It talks to the Discord desktop client over Discord's local IPC (a named pipe on Windows), through
  Lachee's DiscordRPC library. It sends a `SET_ACTIVITY` command, keeps the connection open, and retries
  every 10 seconds, up to 30 times, when Discord isn't there.
- Before sending, it validates and cleans up the input: byte and character limits, URL fixing, image URL
  length, proxying Discord-hosted images through `customrp.xyz`, and protecting leading spaces.
- It computes five kinds of timestamps, one of which (local time) needs a refresh at midnight.
- It saves and loads presets as XML (`.crp`).
- It fetches an application's art assets from a public Discord endpoint for its dropdowns.
- The rest is GUI: the window, the tray, dark mode, translations, the update checker, "run on startup", and
  the AppCenter analytics, whose service was shut down in 2025.

All of the first group works without a GUI. The GUI parts have command-line counterparts (a config file,
service managers, `status` and `stop`) or aren't needed. Nothing CustomRP does needs Windows.

## Language: Python

The options considered:

- **C# on cross-platform .NET.** Reusing the original code sounds attractive, but there's little to reuse:
  the logic lives in the Windows Forms event handlers, mixed with UI code. Users would also need the .NET
  runtime, or large self-contained builds.
- **Rust, Go or C.** Single binaries are nice, but performance doesn't matter here (the program sends a
  few hundred bytes now and then), and they're harder to maintain for the people likely to work on this.
- **Python.** The standard library covers everything: Unix sockets, Windows named pipes (through
  `ctypes`), JSON, XML, HTTP, and TOML (since 3.11). It's preinstalled on most Linux systems and on macOS,
  installs with one pipx command, and is the language the maintainer works in.

Python fits the priorities best: cross-platform, simple, maintainable, minimal dependencies. The cost
is needing Python installed; PyInstaller can produce standalone executables later if that matters.

## Library and application

The code is split into two repositories:

- **[customrp-core](https://github.com/KeiraOMG0/customrp-core)** has everything about presences and
  Discord: the model, validation, payload building, the IPC client, the retry loop, presets and assets.
  It has no dependencies and knows nothing about config files or command lines.
- **customrp-cli** (this repository) has the config file, the commands, logging, the single-instance
  lock, and running as a service.

This keeps the CLI small, and lets someone build a different front end (a tray icon, a TUI, a web UI)
on the same core without copying it. Both are published on PyPI, and customrp-cli depends on a
customrp-core version range from there (`>=0.1.2,<0.2`), in both `pyproject.toml` and
`requirements.txt`. Earlier versions installed customrp-core from GitHub, but PyPI doesn't accept
packages that depend on Git URLs.

## Decisions

**TOML for configuration.** It's human-readable, has comments and real date-times (needed for custom
timestamps), and Python reads it without dependencies from 3.11 (`tomli` before that). YAML would need a
dependency and has surprising typing rules; JSON has no comments.

**Strict config checking.** Unknown options are errors, with a suggestion for likely typos. A typo
like `detials` would otherwise be silently ignored.

**Run in the foreground; let the system manage it.** Forking into the background differs on every
platform and duplicates what systemd, launchd and Task Scheduler already do well, such as starting at
login, restarting, and keeping logs. customrp-cli just handles SIGTERM correctly and never prompts.

**One instance per user, using an OS file lock.** Two instances would fight over the presence. A lock held
by the OS (`flock` on Unix, `msvcrt.locking` on Windows) disappears with the process, so a crash never
leaves a stale lock behind.

**Stopping through a file, not a signal.** `customrp-cli stop` creates a request file that the running
instance checks twice a second. Signals would be simpler on Unix, but Windows can't send a graceful
termination signal to another console process. A file works the same everywhere. SIGTERM, SIGINT and
Ctrl+Break are still handled for service managers and terminals.

**Live reload by polling.** The config file's modification time and size are checked twice a second, and
a change is applied once it has been stable for one check, since editors often save in several steps.
Polling a single file costs nothing, and it avoids platform-specific file watching APIs and their
dependencies.

**Retry forever by default.** CustomRP gives up after 30 attempts (5 minutes), which makes sense for a
window someone is looking at. A background service usually starts before Discord, sometimes long before,
so it shouldn't give up.

**English only, but organized for later.** The user-facing text of the CLI is in `messages.py`, so it can
be translated without hunting through the code. There's no translation machinery until someone needs it.

## Security notes

- Nothing listens on the network. The only connections are to Discord's local socket or pipe, plus HTTPS
  to `discord.com` for `customrp-cli assets`.
- No tokens or credentials are used or stored. The application ID is public information.
- Preset files with a `<!DOCTYPE>` are refused, which rules out XML entity tricks in presets from
  untrusted sources.
- Application IDs are checked to be digits before they're put in a URL.
- The state files (lock, PID, status, stop request) live in a per-user folder.
