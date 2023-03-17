#!/bin/bash


run() {
    # export SLACK_SIGNING_SECRET=***
    # export SLACK_BOT_TOKEN=xoxb-***
    export WB_DATA_DIR="./workflow-buddy-local/db/"
    export ENV=DEV
    export FLASK_APP=app.py
    export FLASK_DEBUG=true
    #########################
    # Minimal migration capability
    #########################
    python minimal_migrate.py

    flask run -p 4747
}

run
