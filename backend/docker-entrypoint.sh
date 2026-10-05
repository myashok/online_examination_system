#!/bin/sh
set -eu

echo "Waiting for MySQL at ${OES_DB_HOST}:${OES_DB_PORT}..."
python - <<'PY'
import os
import time

import MySQLdb

host = os.environ.get("OES_DB_HOST", "mysql")
port = int(os.environ.get("OES_DB_PORT", "3306"))
user = os.environ["OES_MIGRATOR_USER"]
password = os.environ["OES_MIGRATOR_PASSWORD"]
database = os.environ.get("OES_DB_NAME", "oes")

last_error = None
for _ in range(60):
    try:
        connection = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=password,
            db=database,
        )
        connection.close()
        raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)

print(last_error)
raise SystemExit(1)
PY

echo "Applying migrations as ${OES_MIGRATOR_USER}..."
OES_DB_USER="${OES_MIGRATOR_USER}" \
OES_DB_PASSWORD="${OES_MIGRATOR_PASSWORD}" \
python manage.py migrate --noinput

echo "Loading demonstration data as ${OES_APP_USER}..."
OES_DB_USER="${OES_APP_USER}" \
OES_DB_PASSWORD="${OES_APP_PASSWORD}" \
python manage.py seed_demo

echo "Starting the API as ${OES_APP_USER}..."
export OES_DB_USER="${OES_APP_USER}"
export OES_DB_PASSWORD="${OES_APP_PASSWORD}"
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60
