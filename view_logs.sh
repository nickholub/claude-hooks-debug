#!/bin/bash
# View Claude hooks debug logs

LOG_DIR="/tmp/claude-hooks-debug"
TODAY_LOG="$LOG_DIR/hooks-$(date +%Y-%m-%d).json"

usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -f, --follow     Follow log file (like tail -f)"
    echo "  -a, --all        Show all log files"
    echo "  -p, --pretty     Pretty print JSON"
    echo "  -e, --events     Show only event names"
    echo "  -h, --help       Show this help"
    echo ""
    echo "Log directory: $LOG_DIR"
}

if [ ! -d "$LOG_DIR" ]; then
    echo "No logs found. Log directory does not exist: $LOG_DIR"
    echo "Start a Claude session with hooks enabled to generate logs."
    exit 0
fi

case "${1:-}" in
    -f|--follow)
        echo "Following: $TODAY_LOG"
        echo "Press Ctrl+C to stop"
        echo "---"
        tail -f "$TODAY_LOG" 2>/dev/null | jq '.'
        ;;
    -a|--all)
        echo "All log files:"
        ls -la "$LOG_DIR"
        ;;
    -p|--pretty)
        if [ -f "$TODAY_LOG" ]; then
            cat "$TODAY_LOG" | jq '.'
        else
            echo "No logs for today"
        fi
        ;;
    -e|--events)
        if [ -f "$TODAY_LOG" ]; then
            cat "$TODAY_LOG" | jq -r '[.timestamp, .hook_event] | @tsv'
        else
            echo "No logs for today"
        fi
        ;;
    -h|--help)
        usage
        ;;
    "")
        if [ -f "$TODAY_LOG" ]; then
            echo "Today's log: $TODAY_LOG"
            echo "---"
            cat "$TODAY_LOG" | jq '.'
        else
            echo "No logs for today at: $TODAY_LOG"
            echo ""
            echo "Available logs:"
            ls "$LOG_DIR" 2>/dev/null || echo "  (none)"
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac
