#! /bin/bash

#########################
# Minimal migration capability
#########################
python minimal_migrate.py

## start up all the app servers
gunicorn app:flask_app --bind 0.0.0.0:4747 --workers=2
