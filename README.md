### Docker and The Experiment Factory

![home](scripts/img/expfactory.png)

   >> Don't forget what happened to the researcher who suddenly got everything he wanted.

   >> What happened?

   >> He started using Docker.

## Setup for Local Development
Thanks to @NeuroVault for these steps.

### Installing dependencies
1. Fork the [main repository](https://github.com/expfactory/expfactory-docker)
2. Clone your fork to your computer: `git clone https://github.com/<your_username>/expfactory-docker`

  >> *Warning: if you are using OS X you have to clone the repository to a subfolder in your home folder - `/Users/<your_username/...` - otherwise boot2docker will not be able to mount code directories and will fail silently.*


3. Install docker >= 1.6 (If you are using OS X you'll also need boot2docker)
4. Install docker-compose >= 1.2
5. If you are using OS X and homebrew steps 3 and 4 can be achieved by: `brew update && brew install docker boot2docker docker-compose`
6. Make sure your docker daemon is running (on OS X: `boot2docker init && boot2docker up`)

### Running the server
To run the server in detached mode, do:

      docker-compose up -d

The webpage will be available at 127.0.0.1 (unless you are using boot2docker - then run `boot2docker ip` to figure out which IP address you need to use). You can also run the server in non-detached mode, which shows all the logs in realtime.

      docker-compose up

### Stopping the server
To stop the server:

      docker-compose stop

### Restarting the server
After making changes to the code you need to restart the server (but just the uwsgi component):

      docker-compose restart nginx uwsgi

### Reseting the server
If you would like to reset the server and clean the database:

      docker-compose stop
      docker-compose rm
      docker-compose up

### Running Django shell
If you want to interactively develop, it can be helpful to do so in the Django shell. Thank goodness we can still connect to it in the floaty Docker container with the following!

      docker-compose run --rm uwsgi python manage.py shell

### Connecting to Running container
It can be helpful to debug by connecting to a running container. First you need to find the id of the uwsgi container:

      docker ps

Then you can connect:

      docker exec -i -t [container_id] bash


### Running tests

      docker-compose run --rm uwsgi python manage.py test


### Updating docker image
Any change to the python code needs to update the docker image, which could be adding a new package to requirements.txt. If there is any reason that you would need to modify the Dockerfile or rebuild the image, do:

     docker build -t vanessa/expfactory .



## Getting Started
Before bringing up your container, you must create a file `secrets.py` in the expdj folder with the following:

TURK = {
    'host': 'mechanicalturk.amazonaws.com',
    'sandbox_host':'mechanicalturk.sandbox.amazonaws.com',
    'app_url':'https://www.expfactory.org',
    'debug': 1
}
DOMAIN_NAME = "https://expfactory.org" # MUST BE HTTPS FOR MECHANICAL TURK
AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID_HERE"
AWS_SECRET_ACCESS_KEY_ID="YOUR_SECRET_ACCESS_KEY_HERE"

You should change the keys, the domain name and application URL, and set debug to 0. The Domain Name MUST be HTTPS.

Then you can bring up the container (see steps at beginning of README), essentially:

      docker-compose up -d

You will then need to log into the container to create the superuser. First do docker ps to get the container id of the uwsgi that is running vanessa/expfactory image, and then connect to the running container:

      docker ps
      docker exec -it [container_id] bash

Then you will want to make sure migrations are done, and then you can [interactively generate a superuser](scripts/generate_superuser.py):

      python manage.py makemigrations
      python manage.py syncdb
      python manage.py shell

Then to create your superuser, for example:

      from django.contrib.auth.models import User
      User.objects.create_superuser(username='ADMINUSER', password='ADMINPASS', email='')

and replace `ADMINUSER` and `ADMINPASS` with your chosen username and password, respectively. Finally, you will want to download the most recent battery files:

      python scripts/download_battery.py
      python manage.py collectstatic

The last step is probably not necessary, but it's good to be sure.

## Setup for Production
Log into the production server, and you can run [scripts/prepare_instance.sh](scripts/prepare_instance.sh) to install docker and docker-compose. This script will download the repo and build the image. You can then use the commands specified previously to bring up the image (e.g., `docker-compose up -d`). In the case of using something like AWS, we suggest that before building the image, you create an encrypted (separate) database, and add the credentials to it in your settings.py. There are unfortunately things you will need to do manually to get HTTPS working (see below). You should do the following:

 - set up HTTPS (see instructions below)


### Configuration with Mechanical Turk

Mechnical Turk relies on an AWS Secret Access Key and AWS Access Key. The interface can support multiple battery deployments, each of which might be associated with different credientials, and so this authentication information is not stored with the application, but with a battery object. Thus, you will need to fill in the file called "bogus_secrets.py" and rename it to secrets.py for the variables `SECRET_KEY` and `app_url` and when you are ready for deployment, change the `debug` variable to 0.

### HTTPS
The docker container is set up to have a secure connection with https (port 443). There is no easy, programmatic way to set this up on a server, so you must walk through the steps at [https://gethttpsforfree.com/](https://gethttpsforfree.com/). Note that when you run the python server to verify owning the domain, you may need to stop the local nginx (which is also using port 80):

      sudo service nginx stop

I installed this in [scripts/prepare_instance.sh](scripts/prepare_instance.sh) because it's nice to have a local nginx (outside of the docker container) if you ever want to debug with `python manage.py runserver 0.0.0.0:8000` outside of the container. 

Back to setting up HTTPS - it's basically an exercise in copy pasting, and you should follow the steps to a T to generate the certificates on the server. The docker image will take care of setting up the web server (the nginx.conf file).

### Encrypted database connection
If your provider (eg aws) provides you with a certificate, you can add it to `/etc/ssl/certs` on the server, and this path is already mapped in the docker-compose for the nginx container. You then need to specify to use SSL in the database connection in your `settings.py` or `local_settings.py`:


      DATABASES = {
          'default': {
              'ENGINE': 'django.db.backends.postgresql_psycopg2',
              'NAME': 'dbname',
              'USER': 'dbuser',
              'PASSWORD':'dbpassword',
              'HOST': 'dbhost',
              'PORT': '5432',
              'OPTIONS': {
                      'sslmode': 'require',
                      'sslrootcert':'/etc/ssl/certs/rds-cert.pem'
              },
          }
      }


### Installing expfactory-battery
Finally, you will need to install the battery files into `static` in the expfactory-docker folder (which is mapped to /var/www/static) and you can do this by running the script [scripts/download_battery.py](scripts/download_battery.py) from the base folder:

      cd $HOME/expfactory-docker
      python scripts/download_battery.py


