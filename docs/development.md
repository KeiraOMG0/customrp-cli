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

1. If customrp-core changed, release it first. Then update the version range in `pyproject.toml`
   (PyPI doesn't accept dependencies on Git URLs) and the tag in `requirements.txt`.
2. Update `__version__` in `src/customrp_cli/__init__.py` and `CHANGELOG.md`.
3. Commit and tag: `git tag -a v0.2.0 -m "customrp-cli 0.2.0" && git push origin main v0.2.0`.
4. The workflow builds the package, checks that the tag matches `__version__`, and waits for approval:
   open the run under **Actions**, then **Review deployments** → **pypi** → **Approve and deploy**.

Every push also builds the package and runs `twine check`, so packaging problems show up before a release.

The `pypi` environment (repository **Settings → Environments**) only accepts `v*` tags and needs a
reviewer's approval. The matching trusted publisher on PyPI is set for this repository, workflow
`publish.yml` and environment `pypi`; renaming any of these breaks publishing until PyPI is updated.
