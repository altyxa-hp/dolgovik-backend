#!/usr/bin/env bash
# Скрипт запуска на Render

set -o errexit  # Остановить при ошибке

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
