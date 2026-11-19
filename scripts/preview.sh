#!/bin/sh
# Serve the site from the repository root. Quit with Ctrl-C.
cd "$(dirname "$0")/.." || exit 1
exec python3 -m http.server 8741 --bind 127.0.0.1
