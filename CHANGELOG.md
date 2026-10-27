# Changelog

## 0.1.1

- Published on PyPI: `pipx install customrp-cli`
- Depends on customrp-core from PyPI (`>=0.1.2,<0.2`); `requirements.txt` still installs it from GitHub
- Step-by-step pipx installation instructions
- README links are absolute, so they work on PyPI too

## 0.1.0

First release.

- Config file in TOML covering everything CustomRP 1.19.4.1 can show, with strict checking
- Commands: `init`, `check`, `preview`, `run`, `status`, `stop`, `import`, `export`, `assets`, `paths`
- `run` waits for Discord, reconnects, and reloads the config file when it's saved
- One instance per user; `stop` and `status` work on Linux, macOS and Windows
- systemd and launchd files in `contrib/`
- Built on customrp-core 0.1.1
