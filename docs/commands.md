# Commands

```
customrp-cli [-c FILE] [-v] [-q] COMMAND [options]
```

## Options for every command

| Option | |
|---|---|
| `-c FILE`, `--config FILE` | Config file to use. Default: `$CUSTOMRP_CLI_CONFIG`, else the [default location](configuration.md#where-the-file-is). |
| `-v`, `--verbose` | Debug output, including every message exchanged with Discord |
| `-q`, `--quiet` | Errors only |
| `-h`, `--help` | Help for customrp-cli, or for one command (`customrp-cli run -h`) |
| `-V`, `--version` | Version of customrp-cli and customrp-core |

The options can go before or after the command: `customrp-cli -c x.toml run` and
`customrp-cli run -c x.toml` are the same.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Something failed at runtime: gave up reaching Discord, already running, couldn't stop, network or file error |
| 2 | Bad config file or bad command line |
| 3 | `status` only: not running |

## init

```
customrp-cli init [--force]
```

Writes a config file listing every option, set to its default, with comments. It won't overwrite an
existing file without `--force`. Missing folders are created.

## check

```
customrp-cli check
customrp-cli validate
```

Reads the config file and reports every problem: TOML syntax errors, unknown options, wrong types, and
anything Discord would reject. Exits with 2 if there are errors; warnings alone exit with 0.

## preview

```
customrp-cli preview
```

Prints the application ID and the exact `activity` object `run` would send, as JSON, after all the
clean-up (added `https://`, proxied images, computed timestamps). It doesn't contact Discord.

```console
$ customrp-cli preview
{
  "application_id": "896771305108553788",
  "activity": {
    "type": 0,
    "status_display_type": 0,
    "instance": false,
    "details": "Hello",
    "timestamps": {
      "start": 1767268800000
    }
  }
}
```

## run

```
customrp-cli run [--no-watch]
```

Connects to Discord, shows the presence, and keeps it there until stopped. If the config has errors, it
reports them and exits with 2 without connecting.

While running, it:

- waits and retries when Discord isn't running (`[connection] retry_interval`, `max_retries`)
- reconnects when Discord restarts
- reloads the config file when it's saved, unless `--no-watch` or `watch_config = false`
- writes its state to a status file for `customrp-cli status`

It stops on Ctrl+C, `customrp-cli stop`, SIGTERM (what `systemctl stop` and `kill` send), or Ctrl+Break on
Windows. On Linux and macOS, SIGHUP reloads the config. Discord removes the presence as soon as
customrp-cli disconnects.

Only one `run` per user at a time; a second one exits with 1.

## status

```
customrp-cli status
```

```console
$ customrp-cli status
customrp-cli is running (PID 4242)
  State: connected (Presence updated)
  Discord user: you
  Config: /home/you/.config/customrp-cli/config.toml
  Running since: 2026-01-01T12:00:00+01:00
```

States: `connecting`, `connected` (Discord accepted the presence), `waiting` (Discord isn't reachable;
the reason is shown), and `stopped`. Exits with 3 when not running, so scripts can test it.

## stop

```
customrp-cli stop [--timeout SECONDS]
```

Asks the running instance to stop and waits for it (default 10 seconds). Exits with 0 when it has
stopped, or if it wasn't running, and 1 if it didn't stop in time.

It works the same on every system: it leaves a request file that the instance checks twice a second.

## import

```
customrp-cli import PRESET.crp [--force]
```

Puts a CustomRP preset into the config file. If there's no config file yet, it creates one. If there is,
`--force` is needed; the `[presence]` table is replaced, and `[connection]`, `[run]` and `[logging]` are
kept. Comments you added to the old file are lost, since the file is rewritten. Problems in the preset are
reported as warnings and errors afterwards, as `check` would.

## export

```
customrp-cli export PRESET.crp [--force]
```

Saves the configured presence as a CustomRP preset, which the Windows app can load. Won't overwrite
an existing file without `--force`.

## assets

```
customrp-cli assets [--application-id ID]
```

Lists the names of the images uploaded to a Discord application, sorted, along with the Developer Portal
page where they're managed. Uses `application_id` from the config unless `--application-id` is given.
This command needs internet access; it uses Discord's public assets endpoint.

## paths

```
customrp-cli paths
```

Shows the config file in use, the config folder, and the state folder, which holds the lock, PID and
status files. Set `CUSTOMRP_CLI_STATE_DIR` to move the state folder.

## Environment variables

| Variable | Effect |
|---|---|
| `CUSTOMRP_CLI_CONFIG` | Config file, when `-c` isn't given |
| `CUSTOMRP_CLI_STATE_DIR` | Folder for the lock, PID and status files |
| `XDG_CONFIG_HOME`, `XDG_STATE_HOME` | The usual meaning, on Linux |
| `XDG_RUNTIME_DIR`, `TMPDIR` | Where Discord's socket is looked for, on Linux and macOS |
