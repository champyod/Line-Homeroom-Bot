@ECHO OFF
REM Background Scheduler Service for LINE Homeroom Bot
REM This script runs the scheduler service that continuously monitors
REM the schedule and sends messages 21 minutes 17 seconds before events

SETLOCAL

REM Get script directory
SET SCRIPT_DIR=%~dp0

REM Change to script directory
CD /D "%SCRIPT_DIR%"

REM Run the scheduler service with pythonw (no console window) or python
REM Using pythonw to run silently in background
START "LINE Homeroom Bot Scheduler" /MIN pythonw "%SCRIPT_DIR%scheduler_service.py"

ENDLOCAL
