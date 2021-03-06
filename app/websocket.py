#!/usr/bin/env python
import json
import redis
import time
from threading import Thread
from users import User, get_topics

r = redis.Redis("localhost")
CHAT_LIMIT = 15

class handle_websocket(object):

    def __init__(self, ws):
        self.ws = ws
        self.chatting = False
        self.running = True
        self.user = None
        self.channel = False
        self.last_topics = {}
        self.pong = time.time()
        self.run()

    def run(self):
        while self.running:
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

    def send(self, message, j=True):
        try:
            if j:
                self.user.keep_alive()
                self.ws.send(json.dumps(message))
            else:
                self.user.keep_alive()
                self.ws.send(message)
        except:
            self.running = False
            self.chatting = False
            return False
        return True

    def end(self):
        self.send({'active': False})
        self.chatting = False
        return False

    def handle_message(self, message):
        if self.channel is False:
            return

        # Publish message.
        message['output'] = message['output'].replace("<", "&lt;").replace(">", "&gt;")
        listening = r.publish(self.channel, json.dumps(message))
        if listening != 2:
            self.end()

    def handle_register(self, message):
        self.user = User(message['user'])
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
            self.send({'active': False})
            return False
        partner = r.hget(topic_keys[0], 'author')

        # Check status of partner.
        status = self.requests_chat(topic, partner)
        if not status:
            self.end()
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
        name = r.keys("topic:%s:*" % topic.split(":")[1])[0]
        topic_name = r.hget(name, "topic")
        first_message = {'type':'new', 'topic':topic, 'topic_name': topic_name,
                        'active': True}
        r.publish(self.channel, json.dumps(first_message))
        for data_raw in s.listen():
            if not self.chatting:
                break
            if data_raw['type'] == "message":
                if not self.send(data_raw['data'], j=False):
                    break
                self.last_update = time.time()

    def update_topics(self):
        topics = get_topics()
        if (topics != self.last_topics) or ((time.time() - self.pong) > 10):
            self.pong = time.time()
            message = {'type':'topics', 'active': True, 'topics': topics}
            self.send(message)
            self.last_topics = topics

    def listen_for_requests(self):
        status_list = "request:%s" % self.user
        r.delete(status_list)
        while not self.chatting and self.running:
            request_num = r.llen(status_list)
            if request_num > 0:
                chat_channel = r.lindex(status_list, 0)
                if self.handshake(chat_channel):
                    break
            self.update_topics()
            self.user.keep_alive()

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
        handle_replies = Thread(target=self.get_replies, args=(chat_channel,))
        handle_replies.daemon = True
        handle_replies.start()
        chat_timer = Thread(target=self.timer)
        chat_timer.daemon = True
        chat_timer.start()
        return True

    def timer(self):
        self.last_update = time.time()
        while self.chatting and self.running:
            time.sleep(1)
            lag = time.time() - self.last_update
            self.user.keep_alive()
            message = {'type':'timer', 'active': True,
                    'time': int(CHAT_LIMIT - lag)}
            self.send(message)
            if lag >= CHAT_LIMIT:
                self.end()

