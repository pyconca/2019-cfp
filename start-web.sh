#!/bin/sh
flask sync_db && uwsgi --ini /code/uwsgi.ini
