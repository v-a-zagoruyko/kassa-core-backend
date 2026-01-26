#!/bin/sh
set -e

if [ "$(id -u)" -eq 0 ]; then
    mkdir -p /app/media /app/staticfiles
    chown -R app:app /app/media /app/staticfiles || true
    chmod -R u+rwX,g+rwX,o+rX /app/media /app/staticfiles || true
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn kassa_core.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output \
    --user app --group app
