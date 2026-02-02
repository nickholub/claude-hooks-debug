#!/usr/bin/env python3
"""
Claude Hooks Debug - Web Log Viewer
A simple web app to view and filter Claude Code hook logs.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

LOG_DIR = "/tmp/claude-hooks-debug"

# Track file positions for SSE
file_positions = {}


def is_valid_log_entry(obj):
    """Check if an object is a valid log entry with required fields."""
    if not isinstance(obj, dict):
        return False
    required_fields = ['timestamp', 'hook_event', 'input']
    return all(field in obj for field in required_fields)


def find_all_log_entry_positions(content):
    """Find all positions that look like log entry starts."""
    positions = []
    patterns = ['{\n  "timestamp"', '{"timestamp"']

    for pattern in patterns:
        pos = 0
        while True:
            pos = content.find(pattern, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += 1

    return sorted(set(positions))


def parse_log_file(filepath):
    """Parse a log file containing concatenated JSON objects."""
    logs = []
    with open(filepath, 'r') as f:
        content = f.read()

    decoder = json.JSONDecoder()

    # Find all potential log entry start positions
    positions = find_all_log_entry_positions(content)

    for pos in positions:
        try:
            obj, _ = decoder.raw_decode(content, pos)
            if is_valid_log_entry(obj):
                logs.append(obj)
        except json.JSONDecodeError:
            # Skip malformed entries
            continue

    return logs


def get_available_dates():
    """Get list of available log dates."""
    dates = []
    log_path = Path(LOG_DIR)
    if log_path.exists():
        for f in sorted(log_path.glob("hooks-*.json"), reverse=True):
            # Extract date from filename
            match = re.search(r'hooks-(\d{4}-\d{2}-\d{2})\.json', f.name)
            if match:
                dates.append(match.group(1))
    return dates


def get_logs(date=None, hook_event=None, tool_name=None, search=None, limit=100):
    """Get logs with optional filters."""
    all_logs = []
    log_path = Path(LOG_DIR)

    if not log_path.exists():
        return []

    # Determine which files to read
    if date:
        files = [log_path / f"hooks-{date}.json"]
    else:
        files = sorted(log_path.glob("hooks-*.json"), reverse=True)

    for filepath in files:
        if filepath.exists():
            logs = parse_log_file(filepath)
            all_logs.extend(logs)

    # Sort by timestamp descending (newest first)
    all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Apply filters
    filtered = []
    for log in all_logs:
        # Filter by hook event
        if hook_event and log.get('hook_event') != hook_event:
            continue

        # Filter by tool name
        if tool_name:
            input_data = log.get('input', {})
            if input_data.get('tool_name') != tool_name:
                continue

        # Filter by search term
        if search:
            log_str = json.dumps(log).lower()
            if search.lower() not in log_str:
                continue

        filtered.append(log)

        if len(filtered) >= limit:
            break

    return filtered


def get_unique_values(logs, field_path):
    """Extract unique values from logs for a given field path."""
    values = set()
    for log in logs:
        value = log
        for key in field_path.split('.'):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break
        if value:
            values.add(value)
    return sorted(values)


@app.route('/')
def index():
    """Main page with log viewer."""
    dates = get_available_dates()

    # Get filter parameters
    date = request.args.get('date', dates[0] if dates else None)
    hook_event = request.args.get('hook_event', '')
    tool_name = request.args.get('tool_name', '')
    search = request.args.get('search', '')
    limit = int(request.args.get('limit', 100))

    # Get logs
    logs = get_logs(
        date=date if date else None,
        hook_event=hook_event if hook_event else None,
        tool_name=tool_name if tool_name else None,
        search=search if search else None,
        limit=limit
    )

    # Get all logs for extracting filter options
    all_logs = get_logs(date=date, limit=1000)
    hook_events = get_unique_values(all_logs, 'hook_event')
    tool_names = get_unique_values(all_logs, 'input.tool_name')

    return render_template('index.html',
                         logs=logs,
                         dates=dates,
                         current_date=date,
                         hook_events=hook_events,
                         current_hook_event=hook_event,
                         tool_names=tool_names,
                         current_tool_name=tool_name,
                         search=search,
                         limit=limit,
                         total_count=len(logs))


@app.route('/api/logs')
def api_logs():
    """API endpoint for logs."""
    date = request.args.get('date')
    hook_event = request.args.get('hook_event')
    tool_name = request.args.get('tool_name')
    search = request.args.get('search')
    limit = int(request.args.get('limit', 100))

    logs = get_logs(
        date=date if date else None,
        hook_event=hook_event if hook_event else None,
        tool_name=tool_name if tool_name else None,
        search=search if search else None,
        limit=limit
    )

    return jsonify(logs)


@app.route('/api/log/<int:index>')
def api_log_detail(index):
    """Get a specific log entry."""
    date = request.args.get('date')
    logs = get_logs(date=date, limit=1000)
    if 0 <= index < len(logs):
        return jsonify(logs[index])
    return jsonify({'error': 'Log not found'}), 404


def parse_new_entries(content, start_pos=0):
    """Parse JSON objects from content starting at position."""
    logs = []
    decoder = json.JSONDecoder()
    pos = start_pos

    while pos < len(content):
        # Skip whitespace
        while pos < len(content) and content[pos].isspace():
            pos += 1
        if pos >= len(content):
            break

        try:
            obj, end_pos = decoder.raw_decode(content, pos)
            logs.append((obj, pos + end_pos))
            pos += end_pos
        except json.JSONDecodeError:
            break

    return logs


def generate_sse_events(date):
    """Generator for SSE events watching log file changes."""
    log_path = Path(LOG_DIR)
    today = date or datetime.now().strftime('%Y-%m-%d')
    filepath = log_path / f"hooks-{today}.json"

    # Start from end of file
    last_size = 0
    last_position = 0

    if filepath.exists():
        last_size = filepath.stat().st_size
        # Parse existing content to find end position
        with open(filepath, 'r') as f:
            content = f.read()
        entries = parse_new_entries(content)
        if entries:
            last_position = entries[-1][1]

    # Send initial connection message
    yield f"data: {json.dumps({'type': 'connected', 'watching': str(filepath)})}\n\n"

    while True:
        try:
            # Check if file exists and has grown
            if filepath.exists():
                current_size = filepath.stat().st_size

                if current_size > last_size:
                    with open(filepath, 'r') as f:
                        content = f.read()

                    # Parse new entries from last known position
                    new_entries = parse_new_entries(content, last_position)

                    for entry, end_pos in new_entries:
                        yield f"data: {json.dumps({'type': 'log', 'data': entry})}\n\n"
                        last_position = end_pos

                    last_size = current_size

            # Also check if date changed (new day = new file)
            new_today = datetime.now().strftime('%Y-%m-%d')
            if new_today != today:
                today = new_today
                filepath = log_path / f"hooks-{today}.json"
                last_size = 0
                last_position = 0
                yield f"data: {json.dumps({'type': 'newday', 'date': today})}\n\n"

            time.sleep(0.5)  # Check every 500ms

        except GeneratorExit:
            break
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            time.sleep(1)


@app.route('/api/stream')
def stream():
    """SSE endpoint for real-time log updates."""
    date = request.args.get('date')
    return Response(
        generate_sse_events(date),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Claude Hooks Debug Web Viewer')
    parser.add_argument('--port', type=int, default=5050, help='Port to run on (default: 5050)')
    args = parser.parse_args()

    print("Starting Claude Hooks Debug Web Viewer...")
    print(f"Log directory: {LOG_DIR}")
    print(f"Open http://localhost:{args.port} in your browser")
    app.run(debug=True, host='0.0.0.0', port=args.port)
