# Troubleshooting

Start with:

```sh
customrp-cli check          # Is the config right?
customrp-cli run -v         # What exactly happens? (stop any background copy first)
```

`-v` logs every connection attempt and every message exchanged with Discord.

## Discord isn't found

```
WARNING Couldn't find a running Discord client; retrying in 10 s
```

- Is the Discord **desktop** app running, as the same user? The browser version can't receive Rich
  Presence from programs.
- Running two Discord clients (for example stable and Canary)? Each takes its own number. Pick one with
  `[connection] pipe = 1`.
- **Linux, Flatpak Discord:** the socket is in `$XDG_RUNTIME_DIR/app/com.discordapp.Discord/`, which is
  searched. If it's still not found, check that Flatpak exposes it there: `ls $XDG_RUNTIME_DIR/app/*/discord-ipc-*`.
- **Linux, Snap Discord:** the socket is looked for in `$XDG_RUNTIME_DIR/snap.discord/`.
- **Linux, started outside your session** (for example over SSH or from cron): `XDG_RUNTIME_DIR` may be
  missing. Set it to `/run/user/$(id -u)`.
- **Linux, customrp-cli itself in a sandbox** (Flatpak, Snap, container): give it access to
  `$XDG_RUNTIME_DIR/discord-ipc-0`.
- **macOS under launchd:** see [running in the background](running-in-the-background.md#macos-launchd-agent).

The paths searched are listed in
[customrp-core's IPC documentation](https://github.com/KeiraOMG0/customrp-core/blob/main/docs/ipc.md).
The Flatpak, Snap and Vesktop locations come from other Rich Presence projects and haven't been
verified with customrp-cli.

## Connected, but nothing shows on your profile

- Discord: **User Settings → Activity Privacy**. Activity sharing must be on.
- You don't see your own buttons; others do.
- Look at `customrp-cli status`. It should say `connected (Presence updated)`.
- Run `customrp-cli preview` to see what's being sent.

## Discord rejects the presence

```
WARNING Discord returned an error (4000): Invalid Client ID; retrying in 10 s
```

`application_id` doesn't match an application. Copy it again from the Developer Portal (General
Information → Application ID), or leave it empty to use CustomRP's default application.

Other errors from Discord usually mean a field it doesn't accept. `customrp-cli check` catches the
common cases; if it doesn't catch yours, please
[open an issue](https://github.com/KeiraOMG0/customrp-cli/issues) with the `run -v` output.

## Images don't show

- Asset names must match exactly. `customrp-cli assets` lists your application's assets.
- Image URLs must point straight at the image file and be publicly reachable.
- Image links on Discord's own CDN go through CustomRP's proxy (see
  [configuration](configuration.md#images)). If you turned that off, they won't show.

## "already running"

```
ERROR customrp-cli is already running (PID 4242). Stop it with: customrp-cli stop
```

Only one instance per user can run. `customrp-cli status` shows where it's from. If it's a systemd
service, stop it with `systemctl --user stop customrp-cli`.

If the process crashed, the lock disappears with it, so there are no stale lock files to clean up.

## The config doesn't reload

- `[run] watch_config` must be `true`, and `run` must not have `--no-watch`.
- A saved file with errors is ignored; the log says why.
- `[connection]` and `[logging]` changes always need a restart.
- Some network filesystems don't update modification times reliably. Use `kill -HUP <pid>` (Linux,
  macOS) or restart.

## Logs

- In a terminal: on screen (stderr).
- systemd: `journalctl --user -u customrp-cli`
- launchd: the `StandardErrorPath` file in the plist
- Anywhere: set `[logging] file`. It's rotated at 1 MB, with three old files kept.

When reporting a bug, include `customrp-cli --version`, your system, how Discord is installed, and the
output of `customrp-cli run -v`. Remove anything private first, like your Discord user name.
