import os
import warnings
import json
from datetime import datetime, date
import pytz
from linebot import LineBotApi
from linebot.models import FlexSendMessage
from linebot.exceptions import LineBotApiError, LineBotSdkDeprecatedIn_3_0

warnings.filterwarnings("ignore", category=LineBotSdkDeprecatedIn_3_0)

def load_config():
    """Loads the configuration from config.json."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found!")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode config.json. Check for syntax errors.")
        return None

def main():
    CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
    GROUP_ID = os.environ.get('GROUP_ID')

    if not CHANNEL_ACCESS_TOKEN or not GROUP_ID:
        print("Error: Required secrets are not set.")
        return

    config = load_config()
    if not config: return

    try:
        CYCLE_START_DATE = datetime.strptime(config["cycle_start_date"], '%Y-%m-%d').date()
        HOLIDAYS = config.get("holidays", [])
        SPECIAL_ASSEMBLY_DAYS = config.get("special_assembly_days", {})
        ROOM_SCHEDULE = config.get("room_schedule", {})
    except (TypeError, ValueError, KeyError) as e:
        print(f"Error parsing config values: {e}. Check format in config.json.")
        return

    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now_in_bangkok = datetime.now(bangkok_tz)
    today_str = now_in_bangkok.strftime('%Y-%m-%d')
    weekday = now_in_bangkok.weekday()

    event_type, event_location, event_detail, event_time = None, None, None, "8:00"

    if today_str in HOLIDAYS:
        print(f"Today ({today_str}) is a holiday. No message sent.")
        return
    
    # Check for special assembly days first
    if today_str in SPECIAL_ASSEMBLY_DAYS:
        event_data = SPECIAL_ASSEMBLY_DAYS[today_str]
        event_type = "assembly"
        event_location = event_data.get("location", "ไม่ระบุ")
        event_detail = event_data.get("detail") # Will be None if not present
    # Check regular weekly schedule
    elif str(weekday) in ROOM_SCHEDULE:
        entry = ROOM_SCHEDULE[str(weekday)]
        
        if isinstance(entry, dict) and entry.get("type") == "assembly":
            event_type = "assembly"
            event_location = entry.get("location", "ไม่ระบุ")
            event_detail = entry.get("detail")
        else: # It's a homeroom
            event_type = "homeroom"
            weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
            current_week_type = "A" if weeks_passed % 2 == 0 else "B"
            
            if isinstance(entry, list):
                event_location = entry[0] if current_week_type == "A" else entry[1]
            else:
                event_location = entry
    
    if not event_type:
        print(f"No scheduled event for today ({today_str}).")
        return

    # --- Build and Send Message ---
    try:
        header_text, body_text_main, body_text_sub, alt_text = "", event_location, f"วันนี้ เวลา {event_time} ครับ", ""
        
        if event_type == "homeroom":
            weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
            current_week_type = "A" if weeks_passed % 2 == 0 else "B"
            header_text = f"HOMEROOM REMINDER (WEEK {current_week_type})"
            alt_text = f"Week {current_week_type}: วันนี้ Homeroom {event_location} เวลา {event_time} ครับ"
        elif event_type == "assembly":
            header_text = "ASSEMBLY NOTICE"
            body_text_main = f"เข้าแถวรวมที่ {event_location}"
            alt_text = f"แจ้งเตือน: วันนี้เข้าแถวรวมที่ {event_location} เวลา {event_time} ครับ"
            if event_detail:
                alt_text += f" - {event_detail}"

        # Dynamically build the message body
        body_contents = [
            { "type": "text", "text": body_text_main, "weight": "bold", "size": "xl", "margin": "md", "wrap": True },
            { "type": "text", "text": body_text_sub, "size": "md", "color": "#555555", "margin": "md" }
        ]

        # Add the detail text block only if it exists
        if event_detail:
            body_contents.append({
                "type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm",
                "contents": [
                    { "type": "box", "layout": "baseline", "spacing": "sm", "contents": [
                        { "type": "text", "text": "รายละเอียด", "color": "#aaaaaa", "size": "sm", "flex": 2 },
                        { "type": "text", "text": event_detail, "wrap": True, "color": "#666666", "size": "sm", "flex": 5 }
                    ]}
                ]
            })

        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        message_contents = {
          "type": "bubble",
          "header": { "type": "box", "layout": "vertical", "contents": [
              { "type": "text", "text": header_text, "weight": "bold", "color": "#FFFFFF", "size": "sm" }
            ], "backgroundColor": "#DC3545", "paddingAll": "md" },
          "body": { "type": "box", "layout": "vertical", "contents": body_contents },
          "styles": { "header": { "separator": True } }
        }
        flex_message = FlexSendMessage(alt_text=alt_text, contents=message_contents)
        line_bot_api.push_message(GROUP_ID, flex_message)
        print(f"{today_str}: Message sent for {event_type} at {event_location}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()