# Migrating from CustomRP

## Bringing your presence over

In CustomRP: **File → Save Preset**, which saves a `.crp` file. Then:

```sh
customrp-cli import "My preset.crp"            # Creates the config if there's none
customrp-cli import "My preset.crp" --force    # Replaces the presence in an existing config
customrp-cli check
```

Going back works too: `customrp-cli export "My preset.crp"` writes a preset the Windows app can load.

Quit CustomRP before starting customrp-cli, or both will try to set your presence.

## Where each CustomRP field went

| CustomRP | Config option |
|---|---|
| ID | `presence.application_id` |
| Type | `presence.type` |
| Show in member list | `presence.status_display` |
| Name | `presence.name` |
| Details, and its URL | `presence.details`, `presence.details_url` |
| State, and its URL | `presence.state`, `presence.state_url` |
| Party | `presence.party_size`, `presence.party_max` |
| Timestamps | `presence.timestamps` (`since_last_connection`, `since_startup`, `since_presence_update`, `local_time`, `custom`) |
| Custom timestamp start and end | `presence.custom_start`, `presence.custom_end` (no end = the end checkbox unticked) |
| Large image key, text, URL | `[presence.large_image]` `key`, `text`, `url` |
| Small image key, text, URL | `[presence.small_image]` `key`, `text`, `url` |
| Button 1 and 2 | `[[presence.buttons]]` tables with `label` and `url` |
| Pipe selector (Ctrl+Shift+Connect) | `connection.pipe` |
| Autoconnect | Always on: `run` connects right away |
| Run on startup | A service; see [running in the background](running-in-the-background.md) |
| Start minimized, dark mode, language | Not applicable |
| Check for updates | Not included; update with pipx or pip |

## Behaviour that matches

Validation and clean-up follow CustomRP 1.19.4.1: the same length limits, URL fixing, image proxying for
Discord-hosted images, leading no-break spaces, party rules and timestamp modes. The details are in
customrp-core's [compatibility notes](https://github.com/KeiraOMG0/customrp-core/blob/main/docs/compatibility.md).

## Behaviour that differs

| CustomRP | customrp-cli | Why |
|---|---|---|
| Gives up after 30 connection attempts | Retries forever by default | Suits a background service; set `max_retries = 30` to match |
| One-character fields are only highlighted red | They're errors | Discord rejects them anyway |
| Text boxes stop you at the length limit | Over-long values are errors | There's no text box to stop you |
| Party values for non-Playing types, and timestamps for Competing, are still sent if set earlier | They're left out | Matches what CustomRP's interface shows |
| Custom timestamp without a date uses "now" | `custom_start` is required for `custom` | A config file has no date picker default |
| Settings in a .NET settings file | A TOML file | Readable, editable, works everywhere |
