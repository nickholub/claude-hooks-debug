#!/bin/bash
# Start the Claude Hooks Debug web viewer
# Usage: ./start_web.sh [port]
# Default port: 5050

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/web"

PORT="${1:-5050}"

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Flask not found. Installing..."
    pip3 install flask
fi

echo "Starting Claude Hooks Debug Web Viewer..."
echo "Open http://localhost:$PORT in your browser"
echo "Press Ctrl+C to stop"
echo ""

python3 app.py --port "$PORT"
