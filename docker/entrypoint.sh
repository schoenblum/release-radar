#!/bin/sh
# Prepare the database once, before Uvicorn starts its workers, then hand over to
# the given command. Doing this here means workers never race on migrations or
# on creating the first admin.
set -e
alembic upgrade head
python -m app.bootstrap
exec "$@"
