#!/usr/bin/env python
import hashlib
import redis
from wtforms import Form, TextField, validators, ValidationError

r = redis.Redis("localhost")

class TopicForm(Form):
    new_topic = TextField("New Topic", [validators.Required(
        message=u'No one wants to chat about nothing.')])

    def validate_new_topic(form, field):
        topic = field.data.strip()
	if len(topic) < 6 or len(topic) > 94:
            raise ValidationError("Topic must be between 6 and 94 words.")
        m = hashlib.md5()
        m.update(topic)
        form.topic_hash = m.hexdigest()
        pattern = "topic:%s:*" % form.topic_hash
        repeats = r.keys(pattern)
        if len(repeats) > 0:
            raise ValidationError("Yawn, let's chat about something else.")
        topic = topic.replace("<", "&lt;").replace(">", "&gt;")
	form.new_topic.data = topic

    def add(form, user):
        topic = form.new_topic.data.strip()
	topic_key = "topic:%s:%s" % (form.topic_hash, user)
        r.hset(topic_key, "topic", topic)
        r.hset(topic_key, "hash", form.topic_hash)
        r.hset(topic_key, "author", user)
        r.expire(topic_key, 400)
        return True

