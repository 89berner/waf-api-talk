#!/usr/bin/python

from flask import Flask, render_template, url_for, request, redirect, send_from_directory, session, make_response
from functools import wraps
from flask import g

import os
import time
import logging
import json
import argparse
import traceback
import datetime
from datetime import date, timedelta

import lib.Event as Event
import lib.Waf   as Waf

parser = argparse.ArgumentParser(description='Port to use')
parser.add_argument('--port', type=int, default=80, help='an integer for the accumulator')
args = parser.parse_args()

frontend = Flask(__name__)

PROJECT_NAME = os.environ['PROJECT_NAME']

@frontend.before_request
def before_request():
    g.event = Event.create_event(request)
    if ('login_id' in request.args):
        g.event['login_id'] = request.args['login_id']
    
    block_message = Waf.perform_waf_check(g.event, 'REQUEST', request.form)
    if (block_message is not None):
        logging.debug("Request was blocked: %s" % block_message)
        return render_template('blocked.html')

@frontend.after_request
def after_request(response):

    blocked = False
    if ('waf_action' not in g.event and 'skip_waf' not in g.event):
        content = response.get_data()
        logging.info("Will try to go through WAF with content: %s" % content)
        block_message = Waf.perform_waf_check(g.event, 'RESPONSE', request.form, Event.encrypt_data(content))
        if (block_message is not None):
            g.event['request_response'] = content
            logging.debug("Response was blocked: %s" % block_message)
            blocked = True
        
        logging.debug("Response is: " + response.get_data())

    Event.send_event(g.event, PROJECT_NAME)

    if (blocked is True):
        response = make_response(render_template('blocked.html'))

    return response

@frontend.route('/', methods=['GET', 'POST'])
def home():
    logging.debug("Got a request!")
    return render_template('login.html')

@frontend.route('/ping', methods=['GET', 'POST'])
def ping():
    #return render_template('login.html')
    return "pong"

@frontend.route('/good_endpoint', methods=['GET', 'POST'])
def good_endpoint():
    return "good_data"

@frontend.route('/vulnerable_content', methods=['GET', 'POST'])
def vulnerable_content():
    return "Exception details: com.mysql.jdbc.MysqlDataTruncation"

@frontend.route('/img/<path:path>')
def send_js(path):
    g.event['skip_waf'] = 1
    return send_from_directory(os.path.join(frontend.root_path, 'templates/img'), path)

# This should not be stored in the code
frontend.secret_key = 'QIYQVCRN3U9Q25F5AFHKE5LIADF(@DANIEE123'

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    frontend.run(host="0.0.0.0", port=args.port)