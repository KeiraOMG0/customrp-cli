# customrp-cli documentation

customrp-cli shows a custom Discord Rich Presence, configured with a TOML file. It's an independent
command-line alternative to [CustomRP](https://www.customrp.xyz) for Linux, macOS and Windows.

| Page | For |
|---|---|
| [Installation](installation.md) | Installing, updating and removing it on each system |
| [Configuration](configuration.md) | Every option in the config file |
| [Commands](commands.md) | Every command, its options and exit codes |
| [Running in the background](running-in-the-background.md) | systemd, launchd, Task Scheduler, and without a service manager |
| [Troubleshooting](troubleshooting.md) | When the presence doesn't show up |
| [Migrating from CustomRP](migrating-from-customrp.md) | Moving presets over, and what's different |
| [Design](design.md) | Why it's built the way it is: language, structure, decisions |
| [Development](development.md) | Tests, project layout, releasing |

The engine underneath is [customrp-core](https://github.com/KeiraOMG0/customrp-core), which has its own
[documentation](https://github.com/KeiraOMG0/customrp-core/tree/main/docs) on how presences are validated
and sent.
