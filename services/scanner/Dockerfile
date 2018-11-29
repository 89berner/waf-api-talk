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
RUN apt-get update && apt-get install -y --fix-missing vim nano curl telnet less htop

# INSTALL SCANNERS
RUN apt-get update && apt-get install -y skipfish nikto sqlmap

CMD nikto -update

ENV PYTHONPATH /root
WORKDIR /root

ADD requirements.txt requirements.txt
RUN pip install -r requirements.txt

ADD scanner.py /root/scanner.py
RUN chmod +x /root/scanner.py

CMD /root/scanner.py