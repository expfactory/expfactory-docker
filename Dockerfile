FROM python:3.7-stretch
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev \
    libgeos-dev \
    openssl \
    wget

RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt && \
    git clone -b update/python3 https://www.github.com/vsoch/expfactory-python && \
    cd expfactory-python && \
    python setup.py install && \
    pip uninstall -y cython

RUN apt-get remove -y gfortran && \
    apt-get autoremove -y && \
    apt-get clean && \
     rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD . /code/

CMD /code/run_uwsgi.sh

EXPOSE 3031
