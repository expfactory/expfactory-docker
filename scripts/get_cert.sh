#! /bin/bash
# taken and slightly modified from https://www.metachris.com/2015/12/comparison-of-10-acme-lets-encrypt-clients/

# Create a directory for the keys and cert
DOMAIN=expfactory.org
cd /home/ubuntu/expfactory-docker/compose/nginx/ssl/certs

# backup old key and cert
cp /home/ubuntu/expfactory-docker/compose/nginx/ssl/private/domain.key{,.bak.$(date +%s)}
cp chained.pem{,.bak.$(date +%s)}

# Generate a private key
openssl genrsa 4096 > account.key

# Generate a domain private key (if you haven't already)
openssl genrsa 4096 > /home/ubuntu/expfactory-docker/compose/nginx/ssl/private/domain.key

# Create a CSR for $DOMAIN
# openssl req -new -sha256 -key /home/ubuntu/expfactory-docker/compose/nginx/ssl/private/domain.key -subj "/CN=$DOMAIN" > domain.csr
openssl req -new -sha256 -key /home/ubuntu/expfactory-docker/compose/nginx/ssl/private/domain.key -subj "/" -reqexts SAN -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\nsubjectAltName=DNS:$DOMAIN,DNS:www.$DOMAIN")) > domain.csr

# Create the challenge folder in the webroot
mkdir -p /home/ubuntu/expfactory-docker/compose/nginx/acme-challenge/

# Get a signed certificate with acme-tiny
python /opt/acme-tiny/acme_tiny.py --account-key ./account.key --csr ./domain.csr --acme-dir /home/ubuntu/expfactory-docker/compose/nginx/acme-challenge/ > ./signed.crt

wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > intermediate.pem
cat signed.crt intermediate.pem > chained.pem

# Restart nginx container
cd /home/ubuntu/expfactory-docker
docker-compose restart nginx
