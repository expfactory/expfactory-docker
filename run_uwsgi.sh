#!/bin/bash
python manage.py makemigrations experiments
python manage.py makemigrations turk
python manage.py makemigrations main
python manage.py migrate auth
python manage.py migrate
python manage.py collectstatic --noinput
git clone https://github.com/expfactory/expfactory-explorer
uwsgi uwsgi.ini
