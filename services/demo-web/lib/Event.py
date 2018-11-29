#COPY OF demo-web/lib/Event.py
from google.cloud import pubsub_v1
import uuid
import json
import logging
import datetime

from hashlib import md5
from base64 import b64decode
from base64 import b64encode
from Crypto import Random
from Crypto.Cipher import AES

TOPIC_NAME = "raw_events"

publisher  = pubsub_v1.PublisherClient()

# This only needs to happen for the demo web
geo_reader = None

### ENCRYPTION ###

# IN PRODUCTION THIS SHOULD BE USING A PUBLIC/PRIVATE KEY
ENCRYPTION_KEY = "myverysecretkey123"

#https://gist.github.com/forkd/168c9d74b988391e702aac5f4aa69e41
BLOCK_SIZE=16
pad   = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * \
                chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

def encrypt_data(data):
    data = pad(data)

    iv     = Random.new().read(AES.block_size)
    cipher = AES.new(md5(ENCRYPTION_KEY.encode('utf8')).hexdigest(), AES.MODE_CBC, iv)
    return b64encode(iv + cipher.encrypt(data))

def decrypt(encrypted_data):
    encrypted_data = b64decode(encrypted_data)

    iv     = encrypted_data[:16]
    cipher = AES.new(md5(ENCRYPTION_KEY.encode('utf8')).hexdigest(), AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data[16:])).decode('utf8')

### UTILS ###

def _get_country_code_from_ip(ip):
    import geoip2.database
    try:
        if (geo_reader is None):
            geo_reader = geoip2.database.Reader('/tmp/GeoLite2-City.mmdb')
        response = geo_reader.city(ip)
        return str(response.country.iso_code)
    except:
        return 'XX'

def _get_request_headers(request):
    headers = {}
    for key in request.headers.keys():
        headers[key] = request.headers.get(key)
    return headers

### EVENT ###

def callback(message_future):
    if message_future.exception():
        logging.error('Publishing message threw an Exception {}.'.format(message_future.exception()))
    else:
        logging.debug("Message created: " + message_future.result())

def create_event(request):
    
    event = {}
    event["UUID"]          = str(uuid.uuid4())
    event["created"]       = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event["created_epoch"] = datetime.datetime.now().strftime("%s")
    event["scheme"]        = request.scheme
    event["full_path"]     = request.full_path
    event["method"]        = request.method
    event["url"]           = request.url
    event["data"]          = encrypt_data(json.dumps(request.form))
    event["headers"]       = _get_request_headers(request)
    if (request.endpoint is not None):
        event["endpoint"] = request.endpoint
    else:
        event["endpoint"] = 'MISSING'

    # extra tags
    event["user-agent"] = request.user_agent.string
    event["ip"]         = request.remote_addr
    event["geo.src"]    = _get_country_code_from_ip(request.remote_addr)

    return event

def send_event(event, project_name):
    for key in event:
        if isinstance(event[key], dict) or isinstance(event[key], list):
            event[key] = json.dumps(event[key])

    json_event = json.dumps(event)

    data = u'{}'.format(json_event)
    data = data.encode('utf-8')
    message_future = publisher.publish(publisher.topic_path(project_name, TOPIC_NAME), data=data)
    message_future.add_done_callback(callback)
    logging.info("Sending event: %s" % json_event)