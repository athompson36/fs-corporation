#!/bin/sh
set -e

DATA_DIR="${FS_CORP_DATA_DIR:-/data}"
DB_PATH="${FS_CORP_DB:-${DATA_DIR}/company.db}"
mkdir -p "$DATA_DIR"
export FS_CORP_DB="$DB_PATH"

if [ -f /src/alembic.ini ]; then
  cd /src
  alembic upgrade head
fi

if [ -f /src/scripts/bootstrap_dev_company.py ]; then
  python /src/scripts/bootstrap_dev_company.py
fi

exec python -m company.service "$@"
