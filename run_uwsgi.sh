#!/bin/bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python scripts/create_superuser.py
uwsgi uwsgi.ini
