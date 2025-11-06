import os
import warnings
import json
from datetime import datetime, date
import pytz
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import FlexSendMessage
from linebot.exceptions import LineBotApiError

load_dotenv()

# ==============================================================================
# --- LOGIC SECTION ---
# ==============================================================================

def load_config():
    """Loads the configuration from config.json."""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading or parsing config.json: {e}")
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
        SPECIAL_HOMEROOM_DAYS = config.get("special_homeroom_days", {})
        ROOM_SCHEDULE = config.get("room_schedule", {})
        # New optional config values
        DEFAULT_EVENT_TIME = config.get("default_event_time", "8:00")
        MESSAGE_TEMPLATES = config.get("message_templates", {})
    except (TypeError, ValueError, KeyError) as e:
        print(f"Error parsing config values: {e}. Check format in config.json.")
        return

    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now_in_bangkok = datetime.now(bangkok_tz)
    today_str = now_in_bangkok.strftime('%Y-%m-%d')
    weekday = now_in_bangkok.weekday()

    event_type, event_location, event_detail, event_time = None, None, None, DEFAULT_EVENT_TIME

    # helper to format templates safely
    def _safe_format(template: str, ctx: dict) -> str:
        if not template:
            return ""
        try:
            return template.format(**ctx)
        except Exception:
            # if formatting fails (missing keys), return template as-is
            return template

    # --- Determine the event based on priority ---
    if today_str in HOLIDAYS: # Priority 1: Holidays
        print(f"Today ({today_str}) is a holiday. No message sent.")
        return
    elif today_str in SPECIAL_ASSEMBLY_DAYS: # Priority 2: Special Assemblies
        event_data = SPECIAL_ASSEMBLY_DAYS[today_str]
        event_type = "assembly"
        # assembly entry can be a string or dict with location/detail/time
        if isinstance(event_data, dict):
            event_location = event_data.get("location", "ไม่ระบุ")
            event_detail = event_data.get("detail")
            event_time = event_data.get("time", event_time)
        else:
            event_location = event_data
    elif today_str in SPECIAL_HOMEROOM_DAYS: # Priority 3: Special Homerooms
        event_type = "homeroom"
        homeroom_entry = SPECIAL_HOMEROOM_DAYS[today_str]
        # homeroom entry can be string or dict {"location":..., "time":...}
        if isinstance(homeroom_entry, dict):
            event_location = homeroom_entry.get("location")
            event_time = homeroom_entry.get("time", event_time)
        else:
            event_location = homeroom_entry
    elif str(weekday) in ROOM_SCHEDULE: # Priority 4: Regular Weekly Schedule
        entry = ROOM_SCHEDULE[str(weekday)]
        if isinstance(entry, dict) and entry.get("type") == "assembly":
            event_type = "assembly"
            event_location = entry.get("location", "ไม่ระบุ")
            event_detail = entry.get("detail")
            event_time = entry.get("time", event_time)
        else:
            event_type = "homeroom"
            # entry may be a string, list (A/B week) or dict with explicit time
            if isinstance(entry, dict):
                # allow {"location":..., "time":...} structure for homeroom
                event_location = entry.get("location")
                event_time = entry.get("time", event_time)
            else:
                event_location = entry
    
    if not event_type:
        print(f"No scheduled event for today ({today_str}).")
        return

    # --- Resolve A/B week for Homeroom events ---
    if event_type == "homeroom" and isinstance(event_location, list):
        weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
        current_week_type = "A" if weeks_passed % 2 == 0 else "B"
        event_location = event_location[0] if current_week_type == "A" else event_location[1]
    
    # --- Build and Send Message ---
    try:
        # Prepare message texts using templates if provided in config
        header_text = ""
        # body_text_main is main headline / room or assembly message
        body_text_main = event_location
        body_text_sub = _safe_format(MESSAGE_TEMPLATES.get("body_sub_template", "วันนี้ เวลา {time} ครับ"), {"time": event_time, "location": event_location, "detail": event_detail})
        alt_text = ""

        if event_type == "homeroom":
            weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
            current_week_type = "A" if weeks_passed % 2 == 0 else "B"
            header_template = MESSAGE_TEMPLATES.get("homeroom_header", "HOMEROOM REMINDER (WEEK {week_type})")
            header_text = _safe_format(header_template, {"week_type": current_week_type, "location": event_location, "time": event_time})
            alt_template = MESSAGE_TEMPLATES.get("homeroom_alt", "Week {week_type}: วันนี้ Homeroom {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"week_type": current_week_type, "location": event_location, "time": event_time, "detail": event_detail})
        elif event_type == "assembly":
            header_template = MESSAGE_TEMPLATES.get("assembly_header", "ASSEMBLY NOTICE")
            header_text = _safe_format(header_template, {"location": event_location, "time": event_time, "detail": event_detail})
            body_text_main = f"เข้าแถวรวมที่ {event_location}"
            alt_template = MESSAGE_TEMPLATES.get("assembly_alt", "แจ้งเตือน: วันนี้เข้าแถวรวมที่ {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"location": event_location, "time": event_time, "detail": event_detail})
            if event_detail:
                # allow templates to include detail; if not, append
                if "{detail}" not in MESSAGE_TEMPLATES.get("assembly_alt", ""):
                    alt_text += f" - {event_detail}"

        body_contents = [
            { "type": "text", "text": body_text_main, "weight": "bold", "size": "xl", "margin": "md", "wrap": True },
            { "type": "text", "text": body_text_sub, "size": "md", "color": "#555555", "margin": "md" }
        ]
        if event_detail:
            body_contents.append({"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "รายละเอียด", "color": "#aaaaaa", "size": "sm", "flex": 2}, {"type": "text", "text": event_detail, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]}]})

        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        message_contents = {"type": "bubble", "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": header_text, "weight": "bold", "color": "#FFFFFF", "size": "sm"}], "backgroundColor": "#DC3545", "paddingAll": "md"}, "body": {"type": "box", "layout": "vertical", "contents": body_contents}, "styles": {"header": {"separator": True}}}
        flex_message = FlexSendMessage(alt_text=alt_text, contents=message_contents)
        line_bot_api.push_message(GROUP_ID, flex_message)
        print(f"{today_str}: Message sent for {event_type} at {event_location}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
