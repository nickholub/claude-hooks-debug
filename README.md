# Claude Hooks Debug

A debugging tool for Claude Code hooks. Logs all hook events with full JSON payloads for inspection and debugging.

## Features

- Logs all Claude Code hook events to JSON files
- Preserves existing hooks when installing
- Easy install/uninstall scripts
- Daily log rotation

## Supported Hook Events

- `PreToolUse` - Before a tool runs
- `PostToolUse` - After a tool runs
- `Stop` - When Claude stops
- `Notification` - Notification events
- `UserPromptSubmit` - When user submits a prompt

## Installation

```bash
./install.sh
```

This will:
- Backup your existing `~/.claude/settings.json`
- Add debug hooks while preserving your existing hooks
- Configure logging to `/tmp/claude-hooks-debug/`

## Usage

After installation, all hook events will be logged to `/tmp/claude-hooks-debug/hooks-YYYY-MM-DD.json`.

View logs with:

```bash
./view_logs.sh
```

## Uninstallation

```bash
./uninstall.sh
```

This removes only the debug hooks, preserving any other hooks you have configured.

## Log Format

Each log entry contains:

```json
{
  "timestamp": "2025-01-31T12:00:00Z",
  "hook_event": "PreToolUse",
  "project_dir": "/path/to/project",
  "input": { ... }
}
```

## License

MIT
