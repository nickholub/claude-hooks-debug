#!/bin/bash
# Installs debug hooks into Claude global settings

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
BACKUP_FILE="$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"

echo "Claude Hooks Debug Tool - Installer"
echo "===================================="

# Ensure .claude directory exists
mkdir -p "$HOME/.claude"

# Backup existing settings
if [ -f "$CLAUDE_SETTINGS" ]; then
    cp "$CLAUDE_SETTINGS" "$BACKUP_FILE"
    echo "Backed up existing settings to: $BACKUP_FILE"
fi

# Read existing settings or create empty object
if [ -f "$CLAUDE_SETTINGS" ]; then
    EXISTING=$(cat "$CLAUDE_SETTINGS")
else
    EXISTING='{}'
fi

# Read our hook settings
NEW_HOOKS=$(cat "$SCRIPT_DIR/settings.json" | jq '.hooks')

# First, remove any existing debug hooks to prevent duplicates
CLEANED=$(echo "$EXISTING" | jq '
  if .hooks then
    .hooks = (
      .hooks | to_entries | map(
        .value = [.value[] | select(
          .hooks | all(
            .command | (. == null or (contains("ClaudeHooksDebug") | not))
          )
        )]
      ) | from_entries
    )
  else
    .
  end
')

# Merge hooks into existing settings (append to existing hook arrays)
# This preserves any existing hooks while adding the debug hooks
MERGED=$(echo "$CLEANED" | jq --argjson new_hooks "$NEW_HOOKS" '
  .hooks = (
    (.hooks // {}) as $existing |
    $new_hooks | to_entries | reduce .[] as $entry (
      $existing;
      .[$entry.key] = ((.[$entry.key] // []) + $entry.value)
    )
  )
')

# Write merged settings
echo "$MERGED" | jq '.' > "$CLAUDE_SETTINGS"

echo "Installed debug hooks to: $CLAUDE_SETTINGS"
echo ""
echo "Hooks configured:"
echo "  - PreToolUse"
echo "  - PostToolUse"
echo "  - Stop"
echo "  - Notification"
echo "  - UserPromptSubmit"
echo ""
echo "Logs will be written to: /tmp/claude-hooks-debug/hooks-YYYY-MM-DD.json"
echo ""
echo "View logs with: $SCRIPT_DIR/view_logs.sh"
echo "Uninstall with: $SCRIPT_DIR/uninstall.sh"
