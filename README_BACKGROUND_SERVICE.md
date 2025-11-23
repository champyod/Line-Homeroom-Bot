# LINE Homeroom Bot - Background Scheduler Setup Guide

## Overview
This guide explains how to set up the LINE Homeroom Bot to run automatically in the background on Windows startup. The bot will continuously monitor your schedule and send LINE messages **21 minutes and 17 seconds before** each scheduled event.

## Features
- ✅ Automatically runs on Windows startup
- ✅ Runs completely in background (no visible window)
- ✅ Handles Week A and Week B schedules
- ✅ Sends messages 21 minutes 17 seconds before scheduled time
- ✅ Logs all activity to `scheduler_service.log`
- ✅ Prevents duplicate messages (only sends once per day)

## Files Included

### Main Scheduler Service
- **`scheduler_service.py`** - The main background service that monitors schedules and sends messages

### Launcher Files
- **`run_scheduler_service.bat`** - Batch file to start the service
- **`start_scheduler_silent.vbs`** - VBScript to run the service completely hidden (recommended for startup)

### Configuration
- **`config.json`** - Your schedule configuration (Week A/B, special days, etc.)
- **`.env`** - Your LINE Bot credentials

## Setup Instructions

### Step 1: Verify Python Installation
Make sure Python is installed and accessible from command line:
```cmd
python --version
```

### Step 2: Install Dependencies
If you haven't already, install required packages:
```cmd
pip install -r requirements.txt
```

### Step 3: Configure Your Bot
Ensure your `.env` file contains:
```
CHANNEL_ACCESS_TOKEN=your_channel_access_token_here
GROUP_ID=your_group_id_here
```

### Step 4: Test the Service
Before adding to startup, test that it works:
```cmd
python scheduler_service.py
```

You should see log messages indicating the service is running. Press `Ctrl+C` to stop.

### Step 5: Add to Windows Startup

#### Option A: Using Startup Folder (Recommended)

1. **Press `Win + R`** and type: `shell:startup` then press Enter
   - This opens your Windows Startup folder

2. **Create a shortcut**:
   - Right-click in the Startup folder → New → Shortcut
   - Browse and select: `start_scheduler_silent.vbs`
   - Click Next → Name it "LINE Homeroom Bot" → Finish

3. **Done!** The service will start automatically when Windows starts

#### Option B: Using Task Scheduler (Advanced)

1. **Open Task Scheduler**:
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**:
   - Click "Create Basic Task"
   - Name: `LINE Homeroom Bot Scheduler`
   - Description: `Automatically sends LINE messages before homeroom/assembly`

3. **Trigger**:
   - Select "When I log on"
   - Click Next

4. **Action**:
   - Select "Start a program"
   - Program/script: `wscript.exe`
   - Add arguments: `"C:\full\path\to\start_scheduler_silent.vbs"`
   - (Replace with actual path to your VBS file)
   - Click Next → Finish

5. **Configure Additional Settings**:
   - Right-click the task → Properties
   - Check "Run whether user is logged on or not" (optional)
   - Check "Run with highest privileges" (optional)
   - Click OK

## How It Works

### Timing Logic
- The service checks the schedule every 30-60 seconds
- It calculates when to send messages: **Event Time - 21 minutes 17 seconds**
- Example: If homeroom is at 08:00, message sends at 07:38:43

### Week A/B Detection
- Automatically calculates Week A or Week B based on `cycle_start_date` in config.json
- Handles alternating room schedules (e.g., Monday Week A: Room 3503, Week B: Room 3703)

### Special Days
- Recognizes special assembly days and special homeroom days from config.json
- Applies custom templates and colors for special events

### Daily Message Limit
- Uses `last_send.json` to track when messages were sent
- Ensures only ONE message per day (prevents duplicates)

## Monitoring the Service

### Check if Service is Running
1. **Open Task Manager** (`Ctrl + Shift + Esc`)
2. Go to "Details" tab
3. Look for `pythonw.exe` process

### View Logs
- Check `scheduler_service.log` in the bot directory
- Logs show:
  - When service starts
  - When messages are sent
  - Any errors or warnings
  - Schedule status updates

### Stop the Service
1. Open Task Manager
2. Find `pythonw.exe` process
3. Right-click → End Task

## Troubleshooting

### Service not starting on boot
- Verify Python is in system PATH
- Try using absolute paths in the VBS file
- Check Windows Event Viewer for startup errors

### No messages being sent
- Check `scheduler_service.log` for errors
- Verify `.env` file has correct credentials
- Test manually: `python scheduler_service.py`

### Multiple messages being sent
- Delete `last_send.json` and restart service
- Check if multiple instances are running (Task Manager)

### Wrong timing
- Verify `config.json` has correct event times
- Check system time zone (should be Asia/Bangkok or correct local time)

## Configuration Examples

### Adjusting Advance Time
Edit `scheduler_service.py` if you want different timing:
```python
# Change these values at the top of scheduler_service.py
ADVANCE_TIME_MINUTES = 21  # Change to desired minutes
ADVANCE_TIME_SECONDS = 17  # Change to desired seconds
```

### Week A/B Schedule Example
```json
"room_schedule": {
  "1": [
    "ห้อง 3503",  // Week A
    "ห้อง 3703"   // Week B
  ]
}
```

## Uninstalling

1. Remove shortcut from Startup folder or delete Task Scheduler task
2. Stop any running instances via Task Manager
3. Delete the bot directory if no longer needed

## Support

For issues or questions:
1. Check `scheduler_service.log` for error messages
2. Verify configuration in `config.json`
3. Test with `python scheduler_service.py` to see real-time output

---

**Note**: The service runs continuously and uses minimal resources. It checks schedules periodically and only sends messages at the precise time calculated for each event.
