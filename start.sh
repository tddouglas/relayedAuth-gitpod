#!/usr/bin/env bash
export FLASK_DEBUG=true
python3 -m venv venv
. venv/bin/activate
python3 app/app.py
