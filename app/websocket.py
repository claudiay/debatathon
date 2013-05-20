#!/usr/bin/env python
import json
import redis
import time
from threading import Thread

r = redis.Redis("localhost")
CHAT_LIMIT = 10     #change to 10 seconds later

class handle_websocket(object):

    def __init__(self, ws):
        self.ws = ws
        self.chatting = False
        self.user = None
        self.channel = False
        self.run()

    def run(self):
        while True:
            message = self.ws.receive()
            if message is None:
                break
            else:
                message = json.loads(message)
                print "MESSAGE: ", message
                if self.user is None:
                    self.handle_register(message)
                    print "Registering: ", self.user
                else:
                    if message['type'] == 'chat':
                        print "DOING A CHAT"
                        self.handle_message(message)
                    elif message['type'] == 'new' and self.chatting is False:
                        print "STARTING NEW"
                        self.start_new_chat(message)

    def handle_message(self, message):
        if self.channel is False:
            return

        # Publish message.
        listening = r.publish(self.channel, json.dumps(message))
        print "LISTENING: ", listening
        if listening != 1:      #TODO change to 2
            self.ws.send(json.dumps({'active': False}))
            self.chatting = False
            return

    def handle_register(self, message):
        self.user = message['user']
        t = Thread(target=self.listen_for_requests)
        t.daemon = True
        t.start()

    def start_new_chat(self, message):
        user = message['user']
        topic = message['topic']
        topic_pattern = "topic:%s:*" % topic

        # Find topic key and information.
        topic_keys = r.keys(topic_pattern)
        if len(topic_keys) != 1:    # Doesn't exist or something went wrong.
            self.ws.send(json.dumps({'active': False}))
            return False
        partner = r.hget(topic_keys[0], 'author')
        print "PARTNER IS: ", partner

        # Check status of partner.
        status = self.requests_chat(topic, partner)
        print "STATUS IS: ", status
        if not status:
            self.ws.send(json.dumps({'active':False}))
            return False
        else:
            self.accept_chat(topic)
    
    def requests_chat(self, topic, partner):
        partner_chan = "request:%s" % partner
        partner_requests = r.pubsub()
        partner_requests.subscribe(partner_chan)
        request = {'topic': topic, 'user': self.user, 'status': None}
        r.publish(self.channel, json.dumps(request))
        print "DID THAT SETUP"

        while not self.chatting:
            print "waiting for new"
            return True
            for data_raw in partner_requests.listen():
                print "REQUEST CHAT: ", data_raw
                if data_raw['type'] == "message":
                    reply = json.loads(data_raw['data'])
                    print "REPLY: ", reply
                    if reply['topic'] == topic and reply['user'] == self.user:
                        if reply['status'] == False:
                            self.accept_chat(reply['topic'])
                            return False
                        elif reply['status'] == True:
                            return True
                print "cycle 1 done"
                    
    def accept_chat(self, topic):
        self.channel = "chat:%s" % topic
        self.chatting = True
        t = Thread(target=self.get_replies, args=(topic,))
        t.daemon = True
        t.start()
        t = Thread(target=self.timer)
        t.daemon = True
        t.start()

    def get_replies(self, topic):
        s = r.pubsub()
        s.subscribe(self.channel)
        first_message = {'type':'new', 'topic':topic, 'active': True}
        r.publish(self.channel, json.dumps(first_message))
        for data_raw in s.listen():
            if data_raw['type'] == "message":
                self.ws.send(data_raw['data'])
                self.last_update = time.time()

    def listen_for_requests(self):
        request_chan = "request:%s" % self.user
        chat_requests = r.pubsub()
        chat_requests.subscribe(request_chan)
        while not self.chatting:
            print "listening for next..."
            for data_raw in chat_requests.listen():
                print "LISTENING: ", data_raw
                if data_raw['type'] == "message":
                    request = json.loads(data_raw['data'])
                    print "LISTEN REQUEST: ", request
                    if request['status'] == None:
                        request['status'] = self.chatting
                        reply = json.dumps(request)
                        r.publish(self.channel, reply)
                
                        if self.chatting is False:
                            self.accept_chat(request['topic'])
                            print "Accepted a chat: %s to %s" % (self.user, request['user'])

                print "listen cycle 1, ", self.user

    def timer(self):
        while self.chatting:
            time.sleep(CHAT_LIMIT+1)
            lag = time.time() - self.last_update 
            if lag > CHAT_LIMIT:
                self.ws.send(json.dumps({'active': False}))
                self.chatting = False

