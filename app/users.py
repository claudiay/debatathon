#!/usr/bin/env python
import redis
r = redis.Redis("localhost")


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
        if len(users_topics) > 9:
            return True
        return False

    def not_active(self):
        key = "activeuser:%s" % self.user
        return r.ttl(key) <= 0

    def keep_alive(self, time=15):
        key = "activeuser:%s" % self.user
        r.expire(key, time)
	return


def get_topics():
    topic_names = r.keys("topic:*")
    active_users = r.keys("activeuser:*")
    
    avaliable_users = []
    for user in active_users:
        user_values = r.hgetall(user)
        username = user_values.get('name', False)
        if username and r.llen("request:%s" % username) == 0:
            avaliable_users.append(username)

    topics = []
    for topic in topic_names:
        values = r.hgetall(topic)
        if values.get('author') in avaliable_users:
            topics.append(values)
    if len(topics) == 0:
        return False
    return topics


