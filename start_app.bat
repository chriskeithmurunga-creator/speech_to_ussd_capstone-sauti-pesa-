@echo off
REM Double-click this file to start Sema, Tuma and open it in your browser.
REM Must be placed in the ROOT of the project (same folder as main.py).

cd /d "%~dp0"
echo Starting Sema, Tuma...
start "" http://127.0.0.1:8000
python -m app.server
pause
