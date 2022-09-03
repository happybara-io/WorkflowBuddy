#!/bin/bash

run() {
    # export SLACK_SIGNING_SECRET=***
    # export SLACK_BOT_TOKEN=xoxb-***
    FLASK_APP=app.py FLASK_ENV=development flask run -p 3000
}

run