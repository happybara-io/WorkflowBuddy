#!/bin/bash


run() {
    # export SLACK_SIGNING_SECRET=***
    # export SLACK_BOT_TOKEN=xoxb-***
    FLASK_APP=app.py FLASK_DEBUG=true flask run -p 4747
}

run