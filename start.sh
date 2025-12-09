#!/bin/sh
set -e

# Run migrations
alembic upgrade head

# Start the server
# exec ensures uvicorn replaces the shell as the main process
exec uvicorn app.main:app --host 0.0.0.0 --port 8000