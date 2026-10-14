#!/bin/sh
# Prepare the data folder, then run the server as an unprivileged user.
set -e

DATA_DIR="${VARIANCE_STUDIO_DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    # Mounted volumes are often owned by root; make the folder writable
    # for the app user. Only the top folder is changed, not its contents.
    chown app:app "$DATA_DIR" 2>/dev/null || true
    exec gosu app "$@"
fi

exec "$@"