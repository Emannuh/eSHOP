#!/bin/bash
set -e

echo "Waiting for database…"
until python -c "import django; django.setup(); from django.db import connections; connections['default'].ensure_connection()" 2>/dev/null; do
  sleep 1
done

echo "Running migrations…"
python manage.py migrate --noinput

echo "Collecting static files…"
python manage.py collectstatic --noinput

exec "$@"
