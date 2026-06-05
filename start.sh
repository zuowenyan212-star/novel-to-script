#!/usr/bin/env bash
set -e
pip install -r requirements.txt
uvicorn backend.app:app --reload
