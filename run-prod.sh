#! /bin/bash

# TODO: try out the gross way of running it https://fly.io/docs/app-guides/multiple-processes/#just-use-bash
# TODO: file is 116MB, don't download every time
/usr/src/app/nocodb &

# TODO: only seeing logs from the nocodb instance 🤔

# ⚠️in memory cache only works if you have 1 process, not multiple
gunicorn app:flask_app --bind 0.0.0.0:4747 --workers=1
