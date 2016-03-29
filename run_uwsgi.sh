#!/bin/bash
python manage.py makemigrations experiments
python manage.py makemigrations turk
python manage.py makemigrations main
python manage.py migrate auth
python manage.py migrate
python manage.py collectstatic --noinput
mkdir /var/www/.well-known               
mkdir /var/www/.well-known/acme-challenge
git clone https://github.com/expfactory/expfactory-explorer
git clone https://github.com/diafygi/acme-tiny.git /opt/acme-tiny
uwsgi uwsgi.ini
