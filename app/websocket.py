#!/usr/bin/env python
import json
import redis
import time
from threading import Thread

r = redis.Redis("localhost")
CHAT_LIMIT = 10

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
                if self.user is None:
                    self.handle_register(message)
                else:
                    if message['type'] == 'chat':
                        self.handle_message(message)
                    elif message['type'] == 'new' and self.chatting is False:
                        self.start_new_chat(message)

    def handle_message(self, message):
        if self.channel is False:
            return

        # Publish message.
        listening = r.publish(self.channel, json.dumps(message))
        if listening != 2:
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

        # Check status of partner.
        status = self.requests_chat(topic, partner)
        if not status:
            self.ws.send(json.dumps({'active':False}))
            return False
        return True
    
    def requests_chat(self, topic, partner):
        partner_status = "request:%s" % partner
        chat_channel = "chat:%s:%s:%s" % (topic, partner, self.user)
        status_size = r.rpush(partner_status, chat_channel)
        if status_size != 1:
            return False
        while not self.chatting:
            return self.handshake(chat_channel)

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
        status_list = "request:%s" % self.user
        r.delete(status_list)
        while not self.chatting:
            request_num = r.llen(status_list)
            if request_num > 0:
                chat_channel = r.lpop(status_list)
                if self.handshake(chat_channel):
                    break

    def handshake(self, chat_channel):
        confirm_list = "confirm:%s" % chat_channel
        confirm_num = r.rpush(confirm_list, chat_channel)
        start = time.time()
        while confirm_num < 2:
            confirm_num = r.llen(confirm_list)
            if (time.time() - start) > 3:   # Don't allow it to loop forever.
                return False
        self.chatting = True
        self.channel = chat_channel
        t = Thread(target=self.get_replies, args=(chat_channel,))
        t.daemon = True
        t.start()
        t = Thread(target=self.timer)
        t.daemon = True
        t.start()
        return True

    def timer(self):
        self.last_update = time.time()
        while self.chatting:
            time.sleep(CHAT_LIMIT+1)
            lag = time.time() - self.last_update 
            if lag > CHAT_LIMIT:
                self.ws.send(json.dumps({'active': False}))
                self.chatting = False

