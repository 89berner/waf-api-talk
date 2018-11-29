FROM      debian:stretch
MAINTAINER Juan Berner

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y nano less ca-certificates wget vim curl python-pip procps
RUN pip install --upgrade pip

ADD requirements.txt requirements.txt
RUN pip install --upgrade -r requirements.txt

ADD alerter.py /alerter/alerter.py

CMD python /alerter/alerter.py