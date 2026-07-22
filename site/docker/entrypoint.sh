#!/bin/sh
set -e
# Site white-label: nginx (:80) + BFF FastAPI (:8090 localhost)
uvicorn main:app --host 127.0.0.1 --port 8090 --app-dir /app/bff &
exec nginx -g 'daemon off;'
