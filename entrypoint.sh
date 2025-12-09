#!/bin/sh
set -e

# Default to 1000 if not set
USER_ID=${HOST_UID:-1000}
GROUP_ID=${HOST_GID:-1000}

# Check current container user
CURRENT_UID=$(id -u)
echo "Entrypoint: Target UID $USER_ID, Current UID $CURRENT_UID"

# Podman keep-id mode: Container starts as the mapped user.
if [ "$CURRENT_UID" -eq "$USER_ID" ]; then
    echo "Running as target UID."
    exec "$@"
fi

# Docker mode: Container starts as root.
if [ "$CURRENT_UID" -eq 0 ]; then
    echo "Running as root. Setting up user $USER_ID."
    if ! getent passwd "$USER_ID" >/dev/null; then
        groupadd -g "$GROUP_ID" appuser || true
        useradd -u "$USER_ID" -g "$GROUP_ID" -m appuser
    fi
    APP_USER=$(getent passwd "$USER_ID" | cut -d: -f1)
    chown -R "$APP_USER":"$APP_USER" /app/workspace
    exec gosu "$APP_USER" "$@"
else
    echo "ERROR: Container UID ($CURRENT_UID) does not match Host UID ($USER_ID). Aborting."
    exit 1
fi
