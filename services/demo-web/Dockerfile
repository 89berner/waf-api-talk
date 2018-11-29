#  BASE
FROM ubuntu:16.04
MAINTAINER Juan Berner <89berner@gmail.com>

ENV TERM linux
RUN echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections

# Update before installing any package
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get dist-upgrade -y

RUN apt-get install -y python-pip
RUN apt-get update && apt-get install -y --fix-missing jq vim nano curl telnet less redis-tools

ENV PYTHONPATH /root
WORKDIR /root

# GEO METADATA
ADD GeoLite2-City.mmdb /tmp/

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN mkdir lib/
ADD lib/Event.py lib/Event.py
ADD lib/Waf.py lib/Waf.py
ADD lib/__init__.py lib/__init__.py

ADD templates /root/templates

ADD demo-web.py /root/demo-web.py
RUN chmod +x /root/demo-web.py

CMD /root/demo-web.py
