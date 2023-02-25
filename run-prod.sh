#! /bin/bash

gunicorn app:flask_app --bind 0.0.0.0:4747 --workers=2
