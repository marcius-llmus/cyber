#!/bin/sh
set -e

# Default to 1000 if not set
USER_ID=${HOST_UID:-1000}
GROUP_ID=${HOST_GID:-1000}

echo "Starting with UID: $USER_ID, GID: $GROUP_ID"

# Create group and user matching the host's IDs if they don't exist
if ! getent group appuser >/dev/null; then
    groupadd -g "$GROUP_ID" appuser
fi

if ! getent passwd appuser >/dev/null; then
    useradd -u "$USER_ID" -g "$GROUP_ID" -m appuser
fi

chown -R appuser:appuser /app

# Drop privileges and execute the command
exec gosu appuser "$@"
