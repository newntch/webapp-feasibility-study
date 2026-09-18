#!/bin/sh
set -eu

/app/.venv/bin/python manage.py migrate --noinput
/app/.venv/bin/python manage.py ensure_demo_user

exec "$@"
