#!/usr/bin/env python
import json
import redis
import time
from threading import Thread

r = redis.Redis("localhost")
CHAT_LIMIT = 30     #change to 10 seconds later

class handle_websocket(object):

    def __init__(self, ws):
        self.ws = ws
        self.chatting = False
        self.user = None
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
                    if not self.chatting:    # Marks a new chat.
                        self.start_new_chat(message)         
                        if self.channel is False:
                            break
            
                    # Send out chat message. 
                    listening = r.publish(self.channel, json.dumps(message))
                    print self.channel
                    print "listening: %s" % listening
                    if listening != 1:  # TODO change to 2
                        self.ws.send(json.dumps({'active': False}))
                        self.chatting = False
                        break
            print "Message processed."
    
    def handle_register(self, message):
        self.user = message['user']
        t = Thread(target=self.listen_for_chats)
        t.daemon = True
        t.start()

    def start_new_chat(self, message):
        self.chatting = True
        user = message['user']
        topic = message['topic']
        topic_pattern = "topic:%s:*" % topic

        # Find topic key and information.
        topic_keys = r.keys(topic_pattern)
        if len(topic_keys) != 1:    # Doesn't exist or something went wrong.
            self.ws.send(json.dumps({'active': False}))
        partner = r.hget(topic_keys[0], 'author')
        self.channel = "chat:%s:%s" % (partner, user)
    
        # Check status of partner.
        partner_pattern = "chat:*:%s" % partner
        partner_keys = r.keys(partner_pattern)
        if len(partner_keys) != 0:  # Partner is currently chatting.
            self.ws.send(json.dumps({'active':False}))
            return False
        else:
            # Send partner to the chat.
            print "Grabbing partner into chat."
            r.setex(self.channel, topic, CHAT_LIMIT)

        print topic
        t = Thread(target=self.get_replies, args=(topic,))
        t.daemon = True
        t.start()

    def get_replies(self, topic):
        s = r.pubsub()
        s.subscribe(self.channel)
        for data_raw in s.listen():
            if data_raw['type'] != "message":
                continue
            self.ws.send(data_raw['data'])
            r.setex(self.channel, topic, CHAT_LIMIT)

    def listen_for_chats(self):
        chat_pattern = "chat:%s:*" % self.user
        while True:
            print "Checking for new chats."
            requested_chats = r.keys(chat_pattern)
            if len(requested_chats) > 0:
                topic_hash = r.get(requested_chats[0])
                topic_key = "topic:%s:%s" % (topic_hash, name)
                topic_message = r.hget(topic_key, "topic")
                output_data = {'user': name, 'topic': topic_hash, 'active': True,
                    'new_chat': True, 'output': topic_message}
                print "Output data for chat request: %s" % output_data
                self.ws.send(json.dumps(output_data))
                break
            time.sleep(30)


