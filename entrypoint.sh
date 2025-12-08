#!/bin/sh

# Default to 1000 if not set
USER_ID=${HOST_UID:-1000}
GROUP_ID=${HOST_GID:-1000}

echo "Starting with UID: $USER_ID, GID: $GROUP_ID"

# Create group and user matching the host's IDs
groupadd -g "$GROUP_ID" appuser
useradd -u "$USER_ID" -g "$GROUP_ID" -m appuser

# Ensure the workspace (bind mount) is owned by this user
chown -R appuser:appuser /app/workspace

# Drop privileges and execute the command
exec gosu appuser "$@"
