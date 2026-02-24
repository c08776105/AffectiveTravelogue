#!/usr/bin/env bash

# Run tests for the backend
export UV_CACHE_DIR=./.uv_cache
nohup uv run --env-file ../.env uvicorn main:app --port 8000 &

hurl --test tests.hurl


# cleanup
unset UV_CACHE_DIR
RUNNING_PID=$(pgrep uv)
kill $RUNNING_PID
rm nohup.out
