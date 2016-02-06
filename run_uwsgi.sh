#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
git clone https://github.com/expfactory/expfactory-explorer
uwsgi uwsgi.ini
