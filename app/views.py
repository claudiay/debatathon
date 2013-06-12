#!/usr/bin/env python
import random
import os
from app import app, r
from flask import Flask, request, render_template, redirect, session, url_for
from forms import TopicForm
from users import User, get_topics

@app.route("/", methods=['POST', 'GET'])
def home():
    
    # Session keeping.
    if 'username' in session:
	user = User(session['username'])
	if user.not_active():
	    session.clear()
	    set_user()
	    return redirect(url_for('retry'))
	else:
            user.keep_alive(time=600)
    else:
	set_user()
	return redirect(url_for('retry'))

    return chat(user)

@app.route("/retry", methods=['GET'])
def retry():
    if 'username' not in session:
        return redirect(url_for('help'))
    else:
        return redirect(url_for('home'))

def chat(user):
    # Creating new topics.
    if request.method == 'POST':
        if user.topics_full():
            return render_template('/index.html', topics=get_topics(), full=True,
                    user=user.user)
        form = TopicForm(request.form)
        if form.validate():
            form.add(user.user)
        return render_template('/index.html', topics=get_topics(), form=form,
                user=user.user)
    
    # Deleting topics.
    if request.method == 'GET' and request.args.get('del_topic', False):
        user.del_topic(request.args['del_topic'])
    form = TopicForm()
    return render_template('/index.html', topics=get_topics(), form=form,
            user=user.user)

@app.route("/help", methods=['GET'])
def help():
    return render_template('/help.html')


def set_user():
    animals = open('app/animals').read().splitlines()
    modifiers = open('app/modifiers').read().splitlines()
    user = "%s-%s" % (random.choice(modifiers),random.choice(animals))
    while r.keys("activeuser:%s" % (user)): # let's be sure there are no active sessions
	user = "%s-%s" % (random.choice(modifiers),random.choice(animals))
    activeuser = "activeuser:%s" % user     
    r.hset(activeuser, "name", user)
    r.hset(activeuser, "firstview", "1")    # not currently used, for changing welcome message text, etc.
    session['username'] = user
    r.expire(activeuser, 600)               # set user to timeout after 10 mins 
    return


