#!/bin/bash
# Private preview of the lab website on THIS Mac.
# Double-click this file in Finder. It serves this folder at
# http://127.0.0.1:8741/ (an address only this computer can open) and opens
# it in your default browser. Nothing is published.
# To stop the preview: close this Terminal window, or press Control-C.
# To edit pages in the browser, use Edit.command instead.

cd "$(dirname "$0")" || exit 1
PORT=8741
URL="http://127.0.0.1:$PORT/"

if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "The preview is already running. Opening $URL"
  echo "(To restart it, close its Terminal window first, then double-click again.)"
  open "$URL"
  exit 0
fi

( sleep 1; open "$URL" ) &
exec python3 scripts/preview_server.py --port "$PORT"
