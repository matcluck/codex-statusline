# Codex Statusline

Native Codex CLI footer and terminal title presets, plus an optional installer that preserves unrelated config settings.

## Recommended layout

```toml
[tui]
status_line = ["model-with-reasoning", "fast-mode", "current-dir", "git-branch", "context-used", "used-tokens", "five-hour-limit", "weekly-limit"]
terminal_title = ["spinner", "project", "git-branch", "status", "thread", "task-progress"]
notifications = true
notification_condition = "unfocused"
notification_method = "auto"
```

The footer shows model/reasoning, Fast mode, directory, Git branch, context used, token usage, and available rate limits. The title shows activity and task progress across terminal tabs. Notifications help when the terminal is unfocused; delivery depends on your terminal's support. Some fields only appear when applicable or available.

Uses `context-used`; the previous `context-usage` identifier is not present in the installed Codex 0.159.0 binary.

## Installation

### Manual (Codex CLI only)

Copy the keys from [recommended-config.toml](recommended-config.toml) into the existing `[tui]` section in `~/.codex/config.toml`, or create that section if absent. Preserve any unrelated keys and avoid duplicate `[tui]` headers. Bash and Python are not required for manual setup.

### Installer (Python 3.11+)

From this repository:

```sh
python3 install.py --dry-run
python3 install.py
```

The installer validates TOML, merges only preset keys, checks that unrelated settings remain unchanged, backs up the original config, and replaces the file atomically. Repeated installation of the same preset does nothing. No third-party packages required.

The backup and its `.json` metadata live beside the config with owner-only permissions. Keep both for undo. The installer prints the exact undo command:

```sh
python3 install.py --undo /path/to/config.toml.statusline-UNIQUE.bak
```

Undo refuses if the config changed after installation or the backup changed. This protects later edits; in that case compare the backup and current config and restore the desired keys manually. Undo removes a config created by the installer if no config previously existed.

Use `--config /path/to/config.toml` to target another config. Include the same target when undoing. Nonstandard layouts such as an inline `tui = {...}` table are refused without changing the config.

## Presets

| Preset | Footer | Use |
| --- | --- | --- |
| Recommended | Model/reasoning, Fast mode, directory, branch, context used, used tokens, limits | Everyday work |
| Compact | Model/reasoning, Fast mode, branch, context used, limits | Narrow terminals |
| Detailed | Recommended plus total input/output tokens | Inspecting token usage |

All presets include the same title and notification settings. Compact and detailed files are in [presets](presets).

```sh
python3 install.py --preset compact
python3 install.py --preset detailed
```

## Customize interactively

- `/statusline`: toggle and reorder footer fields; save to config.
- `/title`: toggle and reorder terminal title fields; save to config.
- `/status`: inspect current session settings and token usage.

Use the pickers to check fields supported by your installed Codex version. For file-based changes, start a new Codex session to check the result.

## Validation

Local compatibility check: Codex CLI **0.159.0**, October 5, 2026. Field identifiers were checked against the installed binary; visual rendering and notification delivery depend on the terminal and were not tested automatically.

```sh
python3 -m unittest discover -s tests -v
```

Tests cover preservation of unrelated/nested settings, multiline values, invalid input, dry runs, repeat installs, backup permissions, undo, and refusal to overwrite later edits.

References: [OpenAI configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference), [OpenAI CLI commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli).

## License

MIT
