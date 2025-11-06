# LINE Homeroom Bot

A simple, configurable Python bot to send daily homeroom and assembly reminders to a LINE group chat.

## Features

- **Daily Reminders:** Automatically sends a message each morning with the day's homeroom or assembly details.
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
- **LINE Flex Messages:** Sends nicely formatted, easy-to-read messages using the LINE Flex Message format.

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

This file contains all the scheduling and message template configurations.

-   `cycle_start_date`: The start date (YYYY-MM-DD) for the A/B week calculation.
-   `default_homeroom_time` / `default_assembly_time`: Default times for events if not specified elsewhere.
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

Run the bot manually:

```bash
python main.py
```

The script will check the current date, determine the appropriate event, and send a message if one is scheduled.

### Scheduling (Automation)

To run the bot automatically every day, you can set up a cron job (on Linux/macOS) or a Task Scheduler job (on Windows).

**Cron Job (Linux/macOS)**

This example runs the script at 7:00 AM every day.

```bash
0 7 * * * /path/to/your/project/venv/bin/python /path/to/your/project/main.py
```

**Windows Task Scheduler**

The `run_bot.bat` script is provided for convenience.

1.  Open **Task Scheduler**.
2.  Click **Create Basic Task...**
3.  Set the **Trigger** to run daily at your desired time (e.g., 7:00 AM).
4.  For the **Action**, select **Start a program**.
5.  In the "Program/script" field, browse to and select the `run_bot.bat` file in your project directory.
6.  Complete the wizard. The task will now run automatically.
