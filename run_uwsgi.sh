#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
python scripts/download_battery.py
#python manage.py shell < scripts/create_superuser.py
uwsgi uwsgi.ini
