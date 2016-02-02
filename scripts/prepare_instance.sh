sudo apt-get update > /dev/null
sudo apt-get install -y --force-yes git 
sudo apt-get install -y --force-yes build-essential
sudo apt-get install -y --force-yes nginx
sudo apt-get install -y --force-yes python-dev

# Add docker key server
sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

# Install Docker!
echo -n "deb https://apt.dockerproject.org/repo ubuntu-trusty main" > docker.list
sudo mv docker.list /etc/apt/sources.list.d
sudo apt-get update
sudo apt-get purge lxc-docker
sudo apt-cache policy docker-engine
sudo apt-get install -y --force-yes docker-engine
sudo service docker start
sudo gpasswd -a ubuntu docker
sudo service docker restart

curl -L https://github.com/docker/compose/releases/download/1.5.2/docker-compose-`uname -s`-`uname -m` > docker-compose
sudo mv docker-compose /usr/local/bin
chmod +x /usr/local/bin/docker-compose

# Note that you will need to log in and out for changes to take effect

if [ ! -d $HOME/expfactory-docker ]
then
  git clone https://github.com/expfactory/expfactory-docker
  cd $HOME/expfactory-docker
  docker build -t vanessa/expfactory .
  docker-compose -d up
fi
