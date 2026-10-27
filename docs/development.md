# Development

## Setup

```sh
git clone https://github.com/KeiraOMG0/customrp-cli.git
cd customrp-cli
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[test]"           # Also installs customrp-core from PyPI
```

To work on customrp-cli and customrp-core together, install a local checkout of the library over the
pinned one:

```sh
pip install -e ../customrp-core
```

## Tests

```sh
pytest
```

They take about 10 seconds and need neither Discord nor a network connection:

| File | Covers |
|---|---|
| `test_config.py` | Parsing, every kind of config error, writing and re-reading config files |
| `test_cli.py` | Each command's output and exit code |
| `test_instance.py` | The single-instance lock, stop requests, the status file |
| `test_run.py` | `run` against customrp-core's `FakeDiscord`, found through normal discovery: live reload, stopping, refusing a second instance, giving up, and a full run in a separate process |
| `test_examples.py` | The example config and service files stay valid |

`FakeDiscord` listens where a real Discord would: a socket in a temporary `XDG_RUNTIME_DIR` on Linux and
macOS, and `\\.\pipe\discord-ipc-9` on Windows, so a real Discord on pipe 0 isn't disturbed. Tests that
need it are skipped if that pipe is taken.

Tests against a real Discord client are in customrp-core (`pytest -m integration` there), since that's
where the Discord communication lives. To try customrp-cli against your own Discord, use `run -v` with a
test config.

CI runs the tests on Ubuntu, Windows and macOS with Python 3.9 and 3.13.

## Layout

```
src/customrp_cli/
  cli.py        Argument parsing, and every command except run
  runner.py     The run command: session, reload, stop, signals
  config.py     The TOML file: reading, checking, writing
  instance.py   Lock, PID, status and stop-request files
  paths.py      Default locations on each platform
  logs.py       Logging to stderr and a rotating file
  messages.py   User-facing text
examples/       A complete example config
contrib/        systemd and launchd files
docs/
tests/
```

## Where changes go

- How presences are validated, built or sent, and Discord communication: **customrp-core**
- Config options, commands, logging, process management: **here**

A new presence option usually needs both: the field in customrp-core, then the config option here
(`config.py`: reading, `render_config`, and the error key mapping), plus documentation in
[configuration.md](configuration.md).

## Releasing

Releases go to [PyPI](https://pypi.org/project/customrp-cli/) through GitHub Actions
(`.github/workflows/publish.yml`), using PyPI's
[trusted publishing](https://docs.pypi.org/trusted-publishers/), so no API token is stored anywhere.

Releases are automatic. To release:

1. If customrp-core changed, release it first, then update its version range in `pyproject.toml`
   and `requirements.txt`.
2. Update `__version__` in `src/customrp_cli/__init__.py`, and rename `## Unreleased` in
   `CHANGELOG.md` to `## <version>`.
3. Commit and push to `main`.

On every push to `main`, the **CI and release** workflow runs the tests on all three systems and builds
the package. If the tests pass and PyPI doesn't have that version yet, it publishes it, tags the commit
`v<version>`, and creates a GitHub release with the changelog section as its notes. Pushes that don't
change the version just run the tests. Don't create `v*` tags by hand; the workflow does that.

Pull requests run the tests and the build, but never publish. If a release fails, open the run under
**Actions** and use **Re-run failed jobs**, or start it again from **Actions → CI and release → Run
workflow** on `main`.

The `pypi` environment (repository **Settings → Environments**) only accepts the `main` branch. To
require approval before each release, add yourself as a required reviewer there.

The matching trusted publisher on PyPI is set for this repository, workflow `publish.yml` and
environment `pypi`; renaming any of these breaks publishing until PyPI is updated.
