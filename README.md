# LINE Homeroom Bot

A simple, configurable Python bot to send daily homeroom and assembly reminders to a LINE group chat.

## Features

- **Automated Scheduler Service:** Background service that runs continuously and sends messages at the precise time (21 minutes 17 seconds before events).
- **Daily Reminders:** Automatically sends messages each day with homeroom or assembly details.
- **Flexible Scheduling:**
    - Supports A/B week cycles for alternating schedules.
    - Handles regular weekly schedules based on the day of the week.
- **Event Prioritization:** Manages a clear hierarchy for events:
    1.  Holidays (no messages sent)
    2.  Special Assembly Days
    3.  Special Homeroom Days
    4.  Regularly Scheduled Events
- **Highly Customizable:**
    - Configure all schedules, locations, times, and holidays via a single `config.json` file.
    - Customize message content, headers, and alternate texts using message templates.
    - Support for JSON comments in config file.
- **LINE Flex Messages:** Sends nicely formatted, easy-to-read messages using the LINE Flex Message format with color-coded headers.
- **TUI Mode:** Interactive terminal interface with live countdown timer and progress bar.
- **Developer Mode:** Verbose logging for debugging and monitoring.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/champyod/Line-Homeroom-Bot.git
    cd Line-Homeroom-Bot
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Configuration

### 1. `config.json`

Copy `config.json.example` to `config.json` and customize it with your schedule:

```bash
cp config.json.example config.json
```

This file contains all the scheduling and message template configurations.

-   `cycle_start_date`: The start date (YYYY-MM-DD) for the A/B week calculation.
-   `default_homeroom_time` / `default_assembly_time`: Default times for events if not specified elsewhere.
-   `colors`: Custom header colors for different event types (homeroom, assembly, special events).
-   `message_templates`: Global templates for message parts (headers, body, etc.).
-   `holidays`: A list of dates in "YYYY-MM-DD" format when no messages should be sent.
-   `special_assembly_days` / `special_homeroom_days`: Override the regular schedule for specific dates. You can set a custom location, time, detail, and even message templates for each special day.
-   `room_schedule`: Defines the default weekly schedule. Weekdays are numbered "0" (Monday) to "6" (Sunday).
    -   For A/B weeks, provide a list of two locations.
    -   For assemblies, specify `type: "assembly"`.

### 2. Environment Variables

Create a `.env` file in the root directory to store your LINE Bot credentials.

```
CHANNEL_ACCESS_TOKEN="YOUR_CHANNEL_ACCESS_TOKEN"
GROUP_ID="YOUR_TARGET_GROUP_ID"
```

-   **`CHANNEL_ACCESS_TOKEN`**: Your LINE Messaging API channel access token.
-   **`GROUP_ID`**: The ID of the LINE group you want the bot to send messages to.

## Usage

### Manual Execution

Run the bot once to send a message for today's event:

```bash
python main.py
```

### Background Scheduler Service (Recommended)

Run the continuous scheduler service that automatically sends messages 21 minutes 17 seconds before each event:

```bash
# Normal mode
python scheduler_service.py

# With TUI (interactive display with countdown)
python scheduler_service.py --tui
# or
python scheduler_service.py -t

# With verbose logging
python scheduler_service.py --dev
# or
python scheduler_service.py -d

# TUI + Dev mode
python scheduler_service.py -t -d
```

**TUI Mode Features:**
- Real-time countdown timer
- Live progress bar
- Current time display
- Event information
- Next check time
- Message statistics
- Status indicators with emojis

### Windows

Use the provided batch files:

```batch
run_scheduler_service.bat
```

Or run silently in background using VBScript:

```batch
start_scheduler_silent.vbs
```

### Linux/macOS

Run the scheduler as a background service or use systemd/launchd for automatic startup.

## How It Works

The scheduler service:
1. Checks the schedule every 5 minutes
2. Calculates the exact send time (event time - 21 minutes 17 seconds)
3. Creates a precise timer to send the message at that exact moment
4. Sends the message by running `main.py`
5. Prevents duplicate sends using `last_send.json`

All logic for message formatting is in `main.py`, making it easy to test and debug independently.

## Logs

- **Console Output**: Real-time status (normal mode) or TUI display (TUI mode)
- **File Logging**: All events are logged to `scheduler_service.log`
- **Dev Mode**: Detailed debug information including timing calculations

## Version History

### v1.1.0 (2025-11-24)
- Added background scheduler service with precise timing
- Implemented TUI mode with live countdown and progress bar
- Added developer mode with verbose logging
- Refactored to use `main.py` for message sending (single source of truth)
- Added command-line arguments: `--tui/-t`, `--dev/-d`
- Improved error handling and reporting
- Added `config.json.example` template
- Updated `.gitignore` to exclude `config.json`
- Enhanced documentation

### v1.0.0 (2025-11-20)
- Initial release
- Daily homeroom and assembly reminders
- A/B week cycle support
- Special events handling
- Customizable message templates
- Color-coded event headers
- Holiday support
- JSON comments support in config
