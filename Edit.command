#!/bin/bash
# Edit the lab website in your browser, on THIS Mac.
# Double-click this file in Finder. It starts the private preview (if it is
# not already running) and opens it in edit mode: click any paragraph,
# heading, caption or publication entry and type; press Save to write the
# change into the real HTML file in this folder. "Lab name..." updates
# js/site-config.js. "Exit editing" returns to the plain preview.
# Backups of each file you save are kept in
#   ~/Library/Application Support/Lab website preview/backups/
# To stop the preview: close this Terminal window, or press Control-C.

cd "$(dirname "$0")" || exit 1
PORT=8741
URL="http://127.0.0.1:$PORT/#edit"

if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "The preview is already running. Opening the editor at $URL"
  open "$URL"
  exit 0
fi

( sleep 1; open "$URL" ) &
exec python3 scripts/preview_server.py --port "$PORT"
