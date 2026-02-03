"""
Tests for Claude Hooks Debug Web Viewer
"""

import json
import pytest
import tempfile
import os
from pathlib import Path

# Import the app and functions to test
from app import (
    app,
    parse_log_file,
    is_valid_log_entry,
    find_all_log_entry_positions,
    get_logs,
    get_available_dates,
    get_unique_values,
)


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_log_file(tmp_path):
    """Create a sample log file for testing."""
    logs = [
        {
            "timestamp": "2026-02-01T10:00:00Z",
            "hook_event": "PreToolUse",
            "project_dir": "/test/project",
            "input": {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "echo hello",
                    "description": "Print hello"
                },
                "session_id": "test-session-1"
            }
        },
        {
            "timestamp": "2026-02-01T10:00:01Z",
            "hook_event": "PostToolUse",
            "project_dir": "/test/project",
            "input": {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "echo hello",
                    "description": "Print hello"
                },
                "tool_response": {
                    "stdout": "hello",
                    "stderr": ""
                },
                "session_id": "test-session-1"
            }
        },
        {
            "timestamp": "2026-02-01T10:00:02Z",
            "hook_event": "Notification",
            "project_dir": "/test/project",
            "input": {
                "message": "Claude is waiting for your input",
                "notification_type": "idle_prompt",
                "session_id": "test-session-1"
            }
        },
        {
            "timestamp": "2026-02-01T10:00:03Z",
            "hook_event": "UserPromptSubmit",
            "project_dir": "/test/project",
            "input": {
                "prompt": "run tests",
                "session_id": "test-session-1"
            }
        },
        {
            "timestamp": "2026-02-01T10:00:04Z",
            "hook_event": "Stop",
            "project_dir": "/test/project",
            "input": {
                "stop_hook_active": True,
                "session_id": "test-session-1"
            }
        }
    ]

    log_file = tmp_path / "hooks-2026-02-01.json"
    with open(log_file, 'w') as f:
        for log in logs:
            f.write(json.dumps(log, indent=2))
            f.write('\n')

    return log_file


@pytest.fixture
def corrupted_log_file(tmp_path):
    """Create a log file with corrupted/interleaved entries."""
    content = '''{
  "timestamp": "2026-02-01T10:00:00Z",
  "hook_event": "PreToolUse",
  "project_dir": "/test/project",
  "input": {
    "tool_name": "Bash",
    "session_id": "test-1"
  }
}
{
  "timestamp": "2026-02-01T10:00:01Z",
  "hook_event": "Notification",
{
  "project_dir": "/test/corrupted",
  "input": {
    "message": "corrupted entry"
  }
}
{
  "timestamp": "2026-02-01T10:00:02Z",
  "hook_event": "PostToolUse",
  "project_dir": "/test/project",
  "input": {
    "tool_name": "Read",
    "session_id": "test-2"
  }
}
'''
    log_file = tmp_path / "hooks-2026-02-01.json"
    log_file.write_text(content)
    return log_file


class TestIsValidLogEntry:
    """Tests for is_valid_log_entry function."""

    def test_valid_entry(self):
        entry = {
            "timestamp": "2026-02-01T10:00:00Z",
            "hook_event": "PreToolUse",
            "input": {"tool_name": "Bash"}
        }
        assert is_valid_log_entry(entry) is True

    def test_missing_timestamp(self):
        entry = {
            "hook_event": "PreToolUse",
            "input": {"tool_name": "Bash"}
        }
        assert is_valid_log_entry(entry) is False

    def test_missing_hook_event(self):
        entry = {
            "timestamp": "2026-02-01T10:00:00Z",
            "input": {"tool_name": "Bash"}
        }
        assert is_valid_log_entry(entry) is False

    def test_missing_input(self):
        entry = {
            "timestamp": "2026-02-01T10:00:00Z",
            "hook_event": "PreToolUse"
        }
        assert is_valid_log_entry(entry) is False

    def test_not_a_dict(self):
        assert is_valid_log_entry("not a dict") is False
        assert is_valid_log_entry(None) is False
        assert is_valid_log_entry([]) is False


class TestFindAllLogEntryPositions:
    """Tests for find_all_log_entry_positions function."""

    def test_finds_pretty_printed_entries(self):
        content = '{\n  "timestamp": "2026-02-01"}\n{\n  "timestamp": "2026-02-02"}'
        positions = find_all_log_entry_positions(content)
        assert len(positions) == 2
        assert 0 in positions

    def test_finds_compact_entries(self):
        content = '{"timestamp": "2026-02-01"}{"timestamp": "2026-02-02"}'
        positions = find_all_log_entry_positions(content)
        assert len(positions) == 2

    def test_empty_content(self):
        positions = find_all_log_entry_positions('')
        assert len(positions) == 0

    def test_no_timestamp_entries(self):
        content = '{"foo": "bar"}{"baz": "qux"}'
        positions = find_all_log_entry_positions(content)
        assert len(positions) == 0


class TestParseLogFile:
    """Tests for parse_log_file function."""

    def test_parses_valid_log_file(self, sample_log_file):
        logs = parse_log_file(sample_log_file)
        assert len(logs) == 5
        assert logs[0]['hook_event'] == 'PreToolUse'
        assert logs[1]['hook_event'] == 'PostToolUse'
        assert logs[2]['hook_event'] == 'Notification'
        assert logs[3]['hook_event'] == 'UserPromptSubmit'
        assert logs[4]['hook_event'] == 'Stop'

    def test_handles_corrupted_file(self, corrupted_log_file):
        logs = parse_log_file(corrupted_log_file)
        # Should skip the corrupted entry and parse valid ones
        assert len(logs) >= 2
        # Verify parsed entries are valid
        for log in logs:
            assert is_valid_log_entry(log)

    def test_extracts_correct_fields(self, sample_log_file):
        logs = parse_log_file(sample_log_file)

        # Check PreToolUse entry
        pre_tool = logs[0]
        assert pre_tool['timestamp'] == '2026-02-01T10:00:00Z'
        assert pre_tool['input']['tool_name'] == 'Bash'
        assert pre_tool['input']['tool_input']['command'] == 'echo hello'

        # Check Notification entry
        notification = logs[2]
        assert notification['input']['message'] == 'Claude is waiting for your input'
        assert notification['input']['notification_type'] == 'idle_prompt'


class TestGetUniqueValues:
    """Tests for get_unique_values function."""

    def test_extracts_simple_field(self):
        logs = [
            {'hook_event': 'PreToolUse'},
            {'hook_event': 'PostToolUse'},
            {'hook_event': 'PreToolUse'},
        ]
        values = get_unique_values(logs, 'hook_event')
        assert sorted(values) == ['PostToolUse', 'PreToolUse']

    def test_extracts_nested_field(self):
        logs = [
            {'input': {'tool_name': 'Bash'}},
            {'input': {'tool_name': 'Read'}},
            {'input': {'tool_name': 'Bash'}},
        ]
        values = get_unique_values(logs, 'input.tool_name')
        assert sorted(values) == ['Bash', 'Read']

    def test_handles_missing_fields(self):
        logs = [
            {'input': {'tool_name': 'Bash'}},
            {'input': {}},
            {'other': 'field'},
        ]
        values = get_unique_values(logs, 'input.tool_name')
        assert values == ['Bash']


class TestFlaskRoutes:
    """Tests for Flask API routes."""

    def test_index_returns_html(self, client, sample_log_file, monkeypatch):
        # Monkeypatch LOG_DIR to use our test file
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/')
        assert response.status_code == 200
        assert b'Claude Hooks Debug' in response.data

    def test_api_logs_returns_json(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/logs')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_api_logs_respects_limit(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/logs?limit=2')
        data = json.loads(response.data)
        assert len(data) <= 2

    def test_api_logs_filters_by_hook_event(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/logs?hook_event=PreToolUse')
        data = json.loads(response.data)

        for log in data:
            assert log['hook_event'] == 'PreToolUse'

    def test_api_logs_filters_by_tool_name(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/logs?tool_name=Bash')
        data = json.loads(response.data)

        for log in data:
            assert log['input'].get('tool_name') == 'Bash'

    def test_api_logs_search(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/logs?search=hello')
        data = json.loads(response.data)

        # Should find entries containing "hello"
        assert len(data) > 0
        for log in data:
            assert 'hello' in json.dumps(log).lower()

    def test_api_stream_returns_event_stream(self, client, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        response = client.get('/api/stream')
        assert response.status_code == 200
        assert 'text/event-stream' in response.content_type


class TestGetLogs:
    """Tests for get_logs function."""

    def test_returns_logs_sorted_by_timestamp(self, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        logs = get_logs(date='2026-02-01')

        # Verify descending order (newest first)
        timestamps = [log['timestamp'] for log in logs]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_respects_limit(self, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        logs = get_logs(date='2026-02-01', limit=2)
        assert len(logs) <= 2

    def test_filters_by_hook_event(self, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        logs = get_logs(date='2026-02-01', hook_event='Notification')

        assert len(logs) == 1
        assert logs[0]['hook_event'] == 'Notification'

    def test_filters_by_search(self, sample_log_file, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(sample_log_file.parent))

        logs = get_logs(date='2026-02-01', search='waiting')

        assert len(logs) == 1
        assert 'waiting' in logs[0]['input']['message']


class TestGetAvailableDates:
    """Tests for get_available_dates function."""

    def test_returns_dates_from_filenames(self, tmp_path, monkeypatch):
        # Create test log files
        (tmp_path / 'hooks-2026-02-01.json').write_text('{}')
        (tmp_path / 'hooks-2026-02-02.json').write_text('{}')
        (tmp_path / 'hooks-2026-01-31.json').write_text('{}')

        monkeypatch.setattr('app.LOG_DIR', str(tmp_path))

        dates = get_available_dates()

        assert '2026-02-01' in dates
        assert '2026-02-02' in dates
        assert '2026-01-31' in dates

    def test_returns_empty_for_no_logs(self, tmp_path, monkeypatch):
        monkeypatch.setattr('app.LOG_DIR', str(tmp_path))

        dates = get_available_dates()
        assert dates == []

    def test_ignores_non_log_files(self, tmp_path, monkeypatch):
        (tmp_path / 'hooks-2026-02-01.json').write_text('{}')
        (tmp_path / 'other-file.json').write_text('{}')
        (tmp_path / 'hooks-invalid.json').write_text('{}')

        monkeypatch.setattr('app.LOG_DIR', str(tmp_path))

        dates = get_available_dates()

        assert dates == ['2026-02-01']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
