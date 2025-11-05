import os
import warnings
from datetime import datetime, date
import pytz
from linebot import LineBotApi
from linebot.models import FlexSendMessage
from linebot.exceptions import LineBotApiError, LineBotSdkDeprecatedIn30

# This will hide the specific "Deprecated" warning but still show other important errors
warnings.filterwarnings("ignore", category=LineBotSdkDeprecatedIn30)

# ==============================================================================
# --- CONFIGURATION: EDIT EVERYTHING IN THIS SECTION ---
# ==============================================================================

# Secrets are loaded from GitHub Actions Secrets, no need to edit these lines
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
GROUP_ID = os.environ.get('GROUP_ID')

# --- 1. SET YOUR A/B CYCLE START DATE ---
# !!! IMPORTANT !!!
# Set this to a Monday that you know was the start of a "Week A".
# Format: date(YYYY, M, D)
CYCLE_START_DATE = date(2024, 8, 19) # Example: Monday, August 19th, 2024 is Week A

# --- 2. SET YOUR ROOM SCHEDULE ---
# For each day (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri):
# - If rooms differ: ("Room for Week A", "Room for Week B")
# - If room is the same: "Room Name"
ROOM_SCHEDULE = {
    0: "ห้อง 2302",                     # Monday
    1: ("ห้อง 3503", "ห้อง 3703"),      # Tuesday (A/B)
    2: "ห้อง 3403",                     # Wednesday
    3: "ห้อง 3705",                     # Thursday
    4: "ห้อง 1107"                      # Friday
}

# --- 3. ADD YOUR HOLIDAYS ---
# The bot will NOT send a message on these dates.
# Format: 'YYYY-MM-DD'
HOLIDAYS = [
    '2024-10-14', # Example: Public Holiday
    '2024-12-25', # Example: Christmas
    '2024-12-31',
    '2025-01-01',
    # Add all your school holidays and public holidays here
]
# ==============================================================================
# --- END OF CONFIGURATION --- (No need to edit below this line)
# ==============================================================================

def main():
    if not CHANNEL_ACCESS_TOKEN or not GROUP_ID:
        print("Error: Required secrets (CHANNEL_ACCESS_TOKEN or GROUP_ID) are not set.")
        return

    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now_in_bangkok = datetime.now(bangkok_tz)
    today_str = now_in_bangkok.strftime('%Y-%m-%d')
    weekday = now_in_bangkok.weekday()

    if today_str in HOLIDAYS:
        print(f"Today ({today_str}) is a holiday. No message sent.")
        return

    if weekday not in ROOM_SCHEDULE:
        print(f"Today is a weekend. No message sent.")
        return

    delta = now_in_bangkok.date() - CYCLE_START_DATE
    weeks_passed = delta.days // 7
    current_week_type = "A" if weeks_passed % 2 == 0 else "B"

    todays_schedule_entry = ROOM_SCHEDULE[weekday]
    if isinstance(todays_schedule_entry, tuple):
        todays_room = todays_schedule_entry[0] if current_week_type == "A" else todays_schedule_entry[1]
    else:
        todays_room = todays_schedule_entry

    try:
        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        header_text = f"HOMEROOM REMINDER (WEEK {current_week_type})"
        message_contents = {
          "type": "bubble",
          "header": { "type": "box", "layout": "vertical", "contents": [
              { "type": "text", "text": header_text, "weight": "bold", "color": "#FFFFFF", "size": "sm" }
            ], "backgroundColor": "#007BFF", "paddingAll": "md" },
          "body": { "type": "box", "layout": "vertical", "contents": [
              { "type": "text", "text": todays_room, "weight": "bold", "size": "xl", "margin": "md" },
              { "type": "text", "text": "วันนี้ เวลา 8:00 ครับ", "size": "md", "color": "#555555", "margin": "md" }
            ] },
          "styles": { "header": { "separator": True } }
        }
        alt_text_message = f"Week {current_week_type}: วันนี้ Homeroom {todays_room} เวลา 8:00 ครับ"
        flex_message = FlexSendMessage(alt_text=alt_text_message, contents=message_contents)

        line_bot_api.push_message(GROUP_ID, flex_message)
        print(f"{today_str}: Message sent for Week {current_week_type}. Room: {todays_room}")

    except LineBotApiError as e:
        print(f"Error from LINE API: {e.status_code} {e.error.message}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
