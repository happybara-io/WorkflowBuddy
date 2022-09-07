#!/bin/bash


generate_requirements_file() {
    poetry export -o requirements.txt
}

run() {
    # export SLACK_SIGNING_SECRET=***
    # export SLACK_BOT_TOKEN=xoxb-***
    FLASK_APP=app.py FLASK_ENV=development flask run -p 3000
}

## RUN THIS BAD BOY
run