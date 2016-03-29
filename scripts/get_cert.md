Here is the script that will be run as a cron job:
 
[get_cert.sh](get_cert.sh)

The variable DOMAIN should be updated with the main domain for the server.

Next we needed to change where the script is saving the certificates. It looks like from the expfactory docker container that the certificates are being pulled from /etc/ssl/certs on the host, from docker-compose.yml:

    - /etc/ssl/certs:/etc/ssl/certs:ro
    - /etc/ssl/private:/etc/ssl/private:ro


The key and certificate output by the script are currently called domain.key (in the private folder) and chained.pem (in the certs folder).

The script needed to restart the nginx container. Since it's run as root, the environmental variable $HOME will not work, /home/ubuntu is hardcoded.
  
There is one main change that needed to be made to the nginx.conf, we needed an alias to serve the challenge files that letsencrypt will look for to verify domain ownership.

        location /.well-known/acme-challenge/ {
            alias /var/www/.well-known/acme-challenge/;
        }

These appear before the directive that redirects all requests to port 443. Full conf [here](../nginx.conf):
 
The "well-known" directory does not exist by default so it needed to be created for the nginx container in docker-compose.yml as a volume. We also needed the host server to be able to write to it. So a mounted volume like this was added:

      /var/www/.well-known/acme-challenge/:/var/www/.well-known/acme-challenge/:ro

Of course /var/www/.well-known/acme-challenge/ will need to exist on the host as well.

Requirements for all this to work. On the host we will need to have acme tiny installed. The current get_cert.sh script expects it to live in /opt/acme-tiny/. The following would install it to that directory:

      git clone https://github.com/diafygi/acme-tiny.git /opt/acme-tiny

This was added to the script [run_uwsgi.sh](run_uwsgi.sh)

The get_cert.sh script also needs the following to be installed on the host:
  
      python
      openssl
      wget

On to getting get_cert.sh to run as a cron job. If you run the following as root you can edit root's crontab file:

      crontab -e

From there you can insert the following line to get the script to run every month on the 4th at 1am, change 04 to whatever day you want it to run:

      00 01 04 * * /bin/bash /<Full path to where you put script>/get_cert.sh

The current configuration is at 4pm:

      00 23 04 * * /bin/bash /<Full path to where you put script>/get_cert.sh


If you can't run crontab -e then the cron file lives here:

      /var/spool/cron/crontabs/root 

I think the cron service may need to be restarted if this is updated:

      service cron restart

Right now the cron job needs to be run as root because it generates files in /etc/ssl/certs and /var/www/.well-known/acme-challenge. If these were moved to be in the project directory on the host it could be run as the normal unprivileged user on the server.

For security people recommend that you create a new user on the server and set that user to only have access to the get_cert.sh script, and the couple of directories needed to put files in, that way it only has access to the ssl keys and nothing else on the server. I don't think it would be able to restart nginx then though. The wildcard for security is https://github.com/diafygi/acme-tiny. The python file is quite small and I've read through it and it is innocous.

Ok checklist to make sure I have everything. Heres what needs to be run to run the script by itself:

- get get_cert.sh
- update get_cert.sh output key and certificate to match filenames listed in nginx.conf
- update get_cert.sh output locations to match where the certs are currently stored
- update get_cert.sh to change directories to where docker application lives and restart nginx once certs are generated
- Update nginx.conf to serve files from .well-known/acme-challenge on port 80.
- Make sure .well-known/acme-challenge directory exists on host and container, and that the two directories are linked as docker volumes.
- install acme-tiny to /opt/
- install get_cert.sh dependencies python, openssl, wget if not already present.
- And then adding it to cron on the host is the last step to making it automagic. 

You will want to run the script by itself before adding to cron to make sure it works before relying on cron to do it. LetsEncrypt rate limits the number of times you can get certs every day to a pretty low number, so if something goes wrong be careful not to try/run it too much or the servers IP could get blocked.
