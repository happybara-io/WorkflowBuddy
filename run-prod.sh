#! /bin/bash

# ⚠️in memory cache only works if you have 1 process, not multiple
gunicorn app:flask_app --bind 0.0.0.0:4747 --workers=1