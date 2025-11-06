@REM Simple batch wrapper to run the bot directly with Python. Use this path in Task Scheduler's "Program/script" field.
@ECHO OFF
SETLOCAL

REM Resolve script directory
SET SCRIPT_DIR=%~dp0

REM Run python on main.py in the same directory. Assumes `python` is on PATH.
python "%SCRIPT_DIR%main.py" %*

ENDLOCAL
