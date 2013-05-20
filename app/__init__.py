#!/usr/bin/env python
import os
import redis
from flask import Flask
from websocket import handle_websocket

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.debug = True
r = redis.Redis("localhost")

def my_app(environ, start_response):  
    path = environ["PATH_INFO"]  
    if path == "/":  
        return app(environ, start_response)  
    elif path == "/websocket":  
        handle_websocket(environ["wsgi.websocket"])   
    else:  
        return app(environ, start_response)  

import views
