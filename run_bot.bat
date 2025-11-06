@REM Batch wrapper to call PowerShell launcher. Use this path in Task Scheduler's "Program/script" field.
@ECHO OFF
SETLOCAL

REM Resolve script directory
SET SCRIPT_DIR=%~dp0

REM Call PowerShell script with execution policy bypass to avoid policy issues
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_bot.ps1" %*

ENDLOCAL
