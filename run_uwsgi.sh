#!/bin/bash
python manage.py syncdb
python manage.py collectstatic --noinput
#python manage.py shell < scripts/create_superuser.py
uwsgi uwsgi.ini
