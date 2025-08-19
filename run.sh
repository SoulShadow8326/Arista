#!/bin/bash

echo "  █████╗  ██████╗  ██╗ ███████╗ ████████╗  █████╗ "
echo " ██╔══██╗ ██╔══██╗ ██║ ██╔════╝ ╚══██╔══╝ ██╔══██╗"
echo " ███████║ ██████╔╝ ██║ ███████╗    ██║    ███████║"
echo " ██╔══██║ ██╔══██╗ ██║ ╚════██║    ██║    ██╔══██║"
echo " ██║  ██║ ██║  ██║ ██║ ███████║    ██║    ██║  ██║"
echo " ╚═╝  ╚═╝ ╚═╝  ╚═╝ ╚═╝ ╚══════╝    ╚═╝    ╚═╝  ╚═╝"

if [ ! -f "arista.db" ]; then
    touch arista.db
fi
cd backend && uvicorn main:app --reload

if [ "$1" = "prod" ]; then
    cd backend
    if command -v gunicorn >/dev/null 2>&1; then
        gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
    else
        uvicorn main:app --host 0.0.0.0 --port 8000
    fi
fi