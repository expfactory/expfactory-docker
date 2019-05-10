#!/bin/bash

# Install experiments and battery if don't exist
if [ ! -d "/code/expdj/experiment_repo" ]; then
    echo "Cloning base experiments, this will take a while."
    mkdir -p /code/expdj/experiment_repo
    git clone https://www.github.com/expfactory/expfactory-experiments /code/expdj/experiment_repo/expfactory-experiments
    git clone https://github.com/expfactory/expfactory-battery /code/expdj/experiment_repo/expfactory-battery
    cp -R /code/expdj/experiment_repo/expfactory-battery/static/* /code/static/
fi

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
