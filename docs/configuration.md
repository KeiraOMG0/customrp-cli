# Configuration

customrp-cli reads one [TOML](https://toml.io) file. `customrp-cli init` writes one with every option,
set to its default, with comments. [`examples/config.toml`](../examples/config.toml) is a filled-in
example.

Every option can be left out; the defaults are listed below. Unknown options are errors, with a
suggestion when it looks like a typo, so mistakes don't go unnoticed.

## Where the file is

| System | Default |
|---|---|
| Linux and other Unix | `$XDG_CONFIG_HOME/customrp-cli/config.toml`, usually `~/.config/customrp-cli/config.toml` |
| macOS | `~/Library/Application Support/customrp-cli/config.toml` |
| Windows | `%APPDATA%\customrp-cli\config.toml` |

`-c FILE` on the command line wins over the `CUSTOMRP_CLI_CONFIG` environment variable, which wins over
the default. `customrp-cli paths` shows which file is used.

The file must be UTF-8. A byte order mark, which some Windows editors add, is fine.

## Reloading

While `customrp-cli run` is running, saving the file updates the presence within about a second, without
reconnecting. Exceptions:

- If the new file has errors, they're logged and the presence stays as it was. Fix the file and save again.
- Changing `application_id` reconnects, since Discord ties the application to the connection.
- `[connection]` and `[logging]` changes need a restart (`customrp-cli stop`, then `run` again).

Reloading can be turned off with `[run] watch_config = false` or `run --no-watch`. On Linux and macOS,
`kill -HUP <pid>` reloads the file either way.

## `[presence]`

What to show. These are CustomRP's fields; its limits apply, and they're checked before anything is sent.
"Bytes" means the text's UTF-8 size, which is how Discord counts: `é` takes 2 bytes and most emoji take 4.

| Option | Type | Default | Description |
|---|---|---|---|
| `application_id` | string | `""` | Your Discord application's ID (up to 19 digits). Its name is what appears after "Playing". Empty uses CustomRP's default application. |
| `type` | string | `"playing"` | `playing`, `listening`, `watching` or `competing` |
| `status_display` | string | `"name"` | What the member list shows next to your name: `name` (the application's name), `details` or `state` |
| `name` | string | `""` | Sent as the activity's name, up to 256 characters |
| `details` | string | `""` | First line, up to 128 bytes |
| `details_url` | string | `""` | Makes the first line a link |
| `state` | string | `""` | Second line, up to 128 bytes |
| `state_url` | string | `""` | Makes the second line a link |
| `party_size` | integer | `0` | Shown as "(1 of 4)" after the state; only with `playing`, and only when both numbers are above 0 |
| `party_max` | integer | `0` | Raised to `party_size` if it's smaller |
| `timestamps` | string | `"since_last_connection"` | See [Timestamps](#timestamps) |
| `custom_start` | date-time | not set | For `timestamps = "custom"` |
| `custom_end` | date-time | not set | For `timestamps = "custom"` |
| `proxy_discord_cdn` | boolean | `true` | See [Images](#images) |

Text fields can't be exactly one character long, because Discord rejects that. To start a line with
blank space, use a no-break space (`"\u00a0"` in TOML); normal leading spaces are removed by Discord.

URLs without `http://` or `https://` get `https://` added. Hosts with non-ASCII letters and spaces in
paths are encoded for you.

### Timestamps

| Value | Shows |
|---|---|
| `since_last_connection` | Time since customrp-cli last connected to Discord |
| `since_startup` | Time since `customrp-cli run` started |
| `since_presence_update` | Time since the presence was last sent (it's resent when you save the config) |
| `local_time` | Your current local time, as "elapsed" time since midnight. It's refreshed just after midnight. |
| `custom` | Time since `custom_start`, or a countdown to it if it's in the future. With `custom_end` too, Discord shows the span between them. |

The `competing` type never shows a timer.

Write dates and times as TOML date-times. Without an offset they're local time:

```toml
custom_start = 2026-07-01T18:00:00          # local time
custom_end = 2026-07-01T20:00:00+02:00      # with an offset
# custom_start = "2026-07-01 18:00"         # a string works too
```

A date alone (`2026-07-01`) is an error, since it's unclear what time was meant.

### Images

```toml
[presence.large_image]
key = "logo"                 # An asset name, or an image URL
text = "Hover text"          # Up to 128 bytes
url = "https://example.com"  # Opened when the image is clicked

[presence.small_image]       # Same options; shown in the corner of the large image
key = "https://example.com/badge.png"
text = "Small hover text"
```

`key` is either the name of an image uploaded to your application (Developer Portal → Rich Presence →
Art Assets; `customrp-cli assets` lists them), or a direct link to an image. Image links must stay within
256 characters after Discord rewrites them, which works out to links of up to about 200 characters.
`customrp-cli check` tells you if one is too long.

Discord won't show images hosted on its own CDN (`cdn.discordapp.com`, `media.discordapp.net`). Like
CustomRP, customrp-cli sends those links through CustomRP's image proxy at `customrp.xyz/proxy`, which is
run by CustomRP's developer. Set `proxy_discord_cdn = false` to send them unchanged.

`text` and `url` only appear when `key` is set.

### Buttons

Up to two buttons, each a `[[presence.buttons]]` table:

```toml
[[presence.buttons]]
label = "My website"         # Up to 31 bytes
url = "https://example.com"  # Up to 512 characters

[[presence.buttons]]
label = "My code"
url = "https://github.com/you"
```

A button with only a label or only a URL isn't shown (`check` warns about it). In error messages, buttons
are numbered from 1: `presence.buttons[1].label` is the first button's label.

Discord doesn't show your own buttons to you, only to others.

## `[connection]`

| Option | Type | Default | Description |
|---|---|---|---|
| `pipe` | `"auto"` or 0-9 | `"auto"` | Which Discord to connect to. Each running Discord client takes the next free number, starting at 0. `"auto"` uses the first one found. |
| `retry_interval` | number | `10` | Seconds to wait before trying again when Discord isn't running or the connection drops. At least 1. |
| `max_retries` | integer | `-1` | How many attempts before giving up. `-1` keeps trying forever, which suits a background service. CustomRP gives up after 30. |

## `[run]`

| Option | Type | Default | Description |
|---|---|---|---|
| `watch_config` | boolean | `true` | Reload the config file when it changes |

## `[logging]`

| Option | Type | Default | Description |
|---|---|---|---|
| `level` | string | `"info"` | `debug`, `info`, `warning` or `error`. `-v` and `-q` override it. |
| `file` | string | `""` | Also write the log to this file. Relative paths are relative to the config file's folder; `~` works. It's rotated at 1 MB, and three old files are kept. |

The log always goes to stderr as well, except when started with `pythonw` on Windows, which has none.

## Checking

```console
$ customrp-cli check
error: presence.details: must be at least 2 characters long (Discord rejects single characters)
warning: presence.buttons[1]: has no url, so it won't be shown
1 error(s), 1 warning(s) in /home/you/.config/customrp-cli/config.toml
```

Errors stop `run` from starting, or a reload from applying. Warnings are only reported.

## A complete example

```toml
[presence]
application_id = "123456789012345678"
type = "watching"
status_display = "details"
details = "The Lord of the Rings"
details_url = "https://www.themoviedb.org/movie/120"
state = "Extended edition"
timestamps = "custom"
custom_start = 2026-03-14T20:00:00
custom_end = 2026-03-15T00:01:00

[presence.large_image]
key = "film"
text = "Movie night"

[presence.small_image]
key = "popcorn"
text = "Snacks: ready"

[[presence.buttons]]
label = "Join the watch party"
url = "https://example.com/party"

[connection]
retry_interval = 15

[logging]
file = "customrp-cli.log"
```
