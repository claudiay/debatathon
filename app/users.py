#!/usr/bin/env python
from app import r

class User(object):

    def __init__(self, user=None):
        self.user = user

    def __str__(self):
        return self.user

    def del_topic(self, topic_hash):
        name = "topic:%s:%s" % (topic_hash, self.user)
        is_owner = r.exists(name)
        if is_owner:
            r.delete(name)
        return

    def topics_full(self):
        users_topics = r.keys("topic:*:%s" % self.user)
        print users_topics
        if len(users_topics) > 10:
            return True
        return False


