# Scheduling Line-Homeroom-Bot on Windows

This repository includes two helper files to run the bot from Windows Task Scheduler:

- `run_bot.ps1` — PowerShell script that:
  - changes to the script directory,
  - loads environment variables from `.env`,
  - optionally activates `venv\Scripts\Activate.ps1` if it exists,
  - runs `python main.py`.
- `run_bot.bat` — small batch wrapper that calls `run_bot.ps1` (use this as the Task Scheduler action for best compatibility).

Basic steps (Task Scheduler GUI):

1. Open Task Scheduler.
2. Create a Basic Task or Create Task (recommended to use Create Task to set advanced options).
3. On the Action tab choose "Start a program".
   - Program/script: C:\Windows\System32\cmd.exe
   - Add arguments: /c ""C:\path\to\repo\run_bot.bat""
   - Start in (optional): C:\path\to\repo
4. On the Triggers tab set schedule (Daily/Weekly/At log on). Example: daily at 07:40.
5. On the General tab, choose "Run whether user is logged in or not" and supply credentials if needed. Optionally check "Run with highest privileges".

Schtasks command example:

```powershell
schtasks /Create /SC DAILY /TN "LineHomeroomBot" /TR "C:\path\to\run_bot.bat" /ST 07:40 /RL HIGHEST /F
```

Notes and tips
- Protect the `.env` file — it contains your `CHANNEL_ACCESS_TOKEN` and `GROUP_ID`.
- If you use a virtual environment, create it in the repo as `venv` so the PowerShell script will auto-activate it before running.
- To test without scheduling, run `run_bot.bat` (double-click or via a terminal) and inspect output.
- If the Task Scheduler can't access network resources while running under a system account, run the task under an account with network access or credentials enabled.

If you want, I can also generate a ready-to-import XML Task Scheduler export or a small `install_task.ps1` that creates the task using `schtasks` with parameters. Which would you prefer?
