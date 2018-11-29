#!/bin/bash

echo "Starting logstash.."

exec /opt/logstash/bin/logstash -f /opt/conf/logstash.conf
