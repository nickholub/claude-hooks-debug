#!/bin/bash
# Claude Hooks Debug Logger
# Logs all hook events with full JSON payload to a file

LOG_DIR="/tmp/claude-hooks-debug"
LOG_FILE="$LOG_DIR/hooks-$(date +%Y-%m-%d).json"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Read JSON from stdin
INPUT=$(cat)

# Get timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Get hook event name from input or environment
HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // "unknown"')

# Build log entry with metadata
LOG_ENTRY=$(jq -n \
  --arg timestamp "$TIMESTAMP" \
  --arg hook_event "$HOOK_EVENT" \
  --arg project_dir "${CLAUDE_PROJECT_DIR:-}" \
  --argjson input "$INPUT" \
  '{
    timestamp: $timestamp,
    hook_event: $hook_event,
    project_dir: $project_dir,
    input: $input
  }')

# Append to log file
echo "$LOG_ENTRY" >> "$LOG_FILE"

# Also print to stderr for visibility in async hooks
echo "[DEBUG] $HOOK_EVENT logged to $LOG_FILE" >&2

exit 0
