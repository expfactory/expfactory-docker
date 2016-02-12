#!/bin/bash
python manage.py makemigrations
python manage.py migrate auth
python manage.py migrate
python manage.py collectstatic --noinput
git clone https://github.com/expfactory/expfactory-explorer
uwsgi uwsgi.ini
