@echo off
cd /d "%~dp0"
echo AURA is starting at http://127.0.0.1:5000/login
echo Keep this window open while using the project.
".venv\Scripts\python.exe" app.py > server.out.log 2> server.err.log
