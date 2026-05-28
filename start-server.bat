@echo off
echo Starting PromptmaX Django dev server with auto-reload...
cd /d "%~dp0backend"
set DEBUG=True
set PYTHONUNBUFFERED=1
python manage.py runserver 127.0.0.1:8000
pause
