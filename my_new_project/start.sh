#!/bin/bash
cd /app
export PYTHONPATH=/app:$PYTHONPATH
exec gunicorn my_new_project.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --log-file -

