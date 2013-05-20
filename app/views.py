#!/usr/bin/env python
import redis
import random
import os
from app import app, r
from flask import Flask, request, render_template, redirect, session, url_for
from forms import TopicForm

@app.route("/", methods=['POST', 'GET'])
def home():
    if 'username' in session:
	user = session['username']
	activeuser = "activeuser:%s" % user
	if r.ttl(activeuser) <= 0: # should this user be allowed to exist?
	    session.clear()        # no, delete this session as it's timed out in the db
	    set_user()             # but be nice and grab her a new username
	    return redirect(url_for('home'))
	else:		
	    r.expire(activeuser, 600) # user is just visiting again, give her more time
    else:
	set_user()
	return redirect(url_for('home'))
    if request.method == 'POST':
        if user_topics_full(user):
            return render_template('/index.html', topics=get_topics(), full=True,
                    user=user)
        form = TopicForm(request.form)
        if form.validate():
            form.add(user)
        return render_template('/index.html', topics=get_topics(), form=form,
                user=user)
    if request.method == 'GET' and request.args.get('del_topic', False):
        del_topic(request.args['del_topic'], user)
    form = TopicForm()
    return render_template('/index.html', topics=get_topics(), form=form,
            user=user)

def del_topic(topic_hash, user):
    name = "topic:%s:%s" % (topic_hash, user)
    is_owner = r.exists(name)
    if is_owner:
        r.delete(name)
    return

def user_topics_full(user):
    users_topics = r.keys("topic:*:%s" % user)
    print users_topics
    if len(users_topics) > 10:
        return True
    return False

def get_topics():
    topic_names = r.keys("topic:*")
    topics = []
    for name in topic_names:
        values = r.hgetall(name)
        topics.append(values)
    if len(topics) == 0:
        return False
    return topics

def set_user():
    animals = open('app/animals').read().splitlines()
    modifiers = open('app/modifiers').read().splitlines()
    user = "%s-%s" % (random.choice(modifiers),random.choice(animals))
    while r.keys("activeuser:%s" % (user)): # let's be sure there are no active sessions
	user = "%s-%s" % (random.choice(modifiers),random.choice(animals))
    activeuser = "activeuser:%s" % user     
    r.hset(activeuser, "active", "1")       # redundant
    r.hset(activeuser, "firstview", "1")    # not currently used, for changing welcome message text, etc.
    session['username'] = user
    r.expire(activeuser, 600)               # set user to timeout after 10 mins 
    return



