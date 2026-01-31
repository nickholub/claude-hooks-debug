#!/bin/bash
# Removes debug hooks from Claude global settings

CLAUDE_SETTINGS="$HOME/.claude/settings.json"

echo "Claude Hooks Debug Tool - Uninstaller"
echo "======================================"

if [ ! -f "$CLAUDE_SETTINGS" ]; then
    echo "No settings file found at $CLAUDE_SETTINGS"
    exit 0
fi

# Backup before uninstall
BACKUP_FILE="$HOME/.claude/settings.json.backup.$(date +%Y%m%d_%H%M%S)"
cp "$CLAUDE_SETTINGS" "$BACKUP_FILE"
echo "Backed up existing settings to: $BACKUP_FILE"

# Remove only debug hooks (identified by ClaudeHooksDebug in command path)
# Preserves all other existing hooks
UPDATED=$(cat "$CLAUDE_SETTINGS" | jq '
  .hooks = (
    .hooks | to_entries | map(
      .value = [.value[] | select(
        .hooks | all(
          .command | (. == null or (contains("ClaudeHooksDebug") | not))
        )
      )]
    ) | map(select(.value | length > 0)) | from_entries
  ) |
  if .hooks == {} then del(.hooks) else . end
')

echo "$UPDATED" | jq '.' > "$CLAUDE_SETTINGS"

echo "Removed debug hooks from: $CLAUDE_SETTINGS"
echo ""
echo "Your other hooks have been preserved."
echo "Backup saved at: $BACKUP_FILE"
