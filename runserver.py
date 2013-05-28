#!/usr/bin/env python
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from app import my_app
PORT = 8080

if __name__ == '__main__':
    http_server = WSGIServer(('',PORT), my_app, handler_class=WebSocketHandler)
    print "Server is up and running on port %s." % PORT
    http_server.serve_forever()

