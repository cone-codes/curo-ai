#!/usr/bin/env bash
# Start Google Chrome with remote debugging so chrome_crawler.py can attach.
# You must QUIT Chrome completely before running this (or use a separate user-data-dir).

set -euo pipefail

PORT="${CHROME_DEBUG_PORT:-9222}"
CDP_URL="http://127.0.0.1:${PORT}"

echo "Chrome CDP URL: ${CDP_URL}"
echo ""
echo "IMPORTANT:"
echo "  1. Quit all Chrome windows first (Cmd+Q on Mac)."
echo "  2. This script opens Chrome with remote debugging on port ${PORT}."
echo "  3. Sign in to https://www.therealreal.com/ (Google or email)."
echo "  4. In another terminal: PYTHONPATH=. python chrome_crawler.py"
echo ""

if [[ "$(uname -s)" == "Darwin" ]]; then
  CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  USER_DATA="${HOME}/Library/Application Support/Google/Chrome"
  if [[ ! -x "$CHROME" ]]; then
    echo "Google Chrome not found at $CHROME"
    exit 1
  fi
  exec "$CHROME" \
    --remote-debugging-port="${PORT}" \
    --user-data-dir="${USER_DATA}" \
    "https://www.therealreal.com/"
elif [[ "$(uname -s)" == "Linux" ]]; then
  exec google-chrome \
    --remote-debugging-port="${PORT}" \
    "https://www.therealreal.com/" \
    2>/dev/null || chromium-browser --remote-debugging-port="${PORT}" "https://www.therealreal.com/"
else
  echo "Start Chrome manually with: --remote-debugging-port=${PORT}"
  echo "Then open https://www.therealreal.com/"
fi
