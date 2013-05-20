#!/usr/bin/env python
"""Base redis values for testing."""
import hashlib
import redis

r = redis.Redis("localhost")

# Set up topics
topics = [["Mongoose taste better than guinea pigs.", "raccoon"],
          ["Carrots are not a fruit.", "mongoose"],
          ["WHEEK WHEEK WHEEK", "guineapig"],
          ["Stacking cups is one of life's best skills.", "otter"],
          ["Secret topic: lemon and fish", "raccoon"]
        ]

for topic in topics:
    m = hashlib.md5()
    m.update(topic[0])
    topic_hash = m.hexdigest()
    topic_key = "topic:%s:%s" % (topic_hash, topic[1])
    r.hset(topic_key, "topic", topic[0])
    r.hset(topic_key, "author", topic[1])
    r.hset(topic_key, "hash", topic_hash)
    r.expire(topic_key, 400)

