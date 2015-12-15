#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
#python manage.py shell < scripts/create_superuser.py
#cp -R assets/ /var/www/
uwsgi uwsgi.ini
