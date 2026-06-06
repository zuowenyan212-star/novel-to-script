@echo off
pip install -r requirements.txt
uvicorn backend.app:app --reload
pause
