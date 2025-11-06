import os
import warnings
import json
import re
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
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove single-line comments (// comment)
            content = re.sub(r'//.*', '', content)
            # Remove multi-line comments (/* comment */)
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)
            return json.loads(content)
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
        DEFAULT_HOMEROOM_TIME = config.get("default_homeroom_time", "8:00")
        DEFAULT_ASSEMBLY_TIME = config.get("default_assembly_time", "8:00")
        MESSAGE_TEMPLATES = config.get("message_templates", {})
        COLORS = config.get("colors", {
            "homeroom": "#007BFF",
            "assembly": "#28A745",
            "special_homeroom": "#FF6B35", 
            "special_assembly": "#C1427B"
        })
    except (TypeError, ValueError, KeyError) as e:
        print(f"Error parsing config values: {e}. Check format in config.json.")
        return

    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now_in_bangkok = datetime.now(bangkok_tz)
    today_str = now_in_bangkok.strftime('%Y-%m-%d')
    weekday = now_in_bangkok.weekday()

    event_type, event_location, event_detail, event_time = None, None, None, None

    def _safe_format(template: str, ctx: dict) -> str:
        if not template:
            return ""
        try:
            return template.format(**ctx)
        except Exception:
            return template

    # --- Determine Event ---
    is_special = False
    if today_str in HOLIDAYS:
        print(f"Today ({today_str}) is a holiday. No message sent.")
        return
    elif today_str in SPECIAL_ASSEMBLY_DAYS:
        event_data = SPECIAL_ASSEMBLY_DAYS[today_str]
        event_type = "assembly"
        is_special = True
        event_location = event_data.get("location", "ไม่ระบุ")
        event_detail = event_data.get("detail")
        event_time = event_data.get("time", DEFAULT_ASSEMBLY_TIME)
        entry_templates = event_data.get("templates", {})
    elif today_str in SPECIAL_HOMEROOM_DAYS:
        event_data = SPECIAL_HOMEROOM_DAYS[today_str]
        event_type = "homeroom"
        is_special = True
        event_location = event_data.get("location", "ไม่ระบุ")
        event_detail = event_data.get("detail")
        event_time = event_data.get("time", DEFAULT_HOMEROOM_TIME)
        entry_templates = event_data.get("templates", {})
    elif str(weekday) in ROOM_SCHEDULE:
        entry = ROOM_SCHEDULE[str(weekday)]
        
        if isinstance(entry, dict):
            event_type = entry.get("type", "homeroom")
            event_location = entry.get("location")
            event_detail = entry.get("detail")
            event_time = entry.get("time", DEFAULT_HOMEROOM_TIME if event_type == "homeroom" else DEFAULT_ASSEMBLY_TIME)
            entry_templates = entry.get("templates", {})
        elif isinstance(entry, list):
            event_type = "homeroom"
            weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
            current_week_type = "A" if weeks_passed % 2 == 0 else "B"
            event_location = entry[0] if current_week_type == "A" else entry[1]
            event_detail = None
            event_time = DEFAULT_HOMEROOM_TIME
            entry_templates = {}
        else:
            event_type = "homeroom"
            event_location = entry
            event_detail = None
            event_time = DEFAULT_HOMEROOM_TIME
            entry_templates = {}
    
    if not event_type:
        print(f"No scheduled event for today ({today_str}).")
        return

    current_week_type = None
    if event_type == "homeroom":
        weeks_passed = (now_in_bangkok.date() - CYCLE_START_DATE).days // 7
        current_week_type = "A" if weeks_passed % 2 == 0 else "B"
    
    # --- Build and Send Message ---
    try:
        entry_templates_local = entry_templates if 'entry_templates' in locals() and entry_templates else {}
        templates = {**MESSAGE_TEMPLATES, **entry_templates_local}

        header_text = ""
        template_ctx = {"time": event_time, "location": event_location, "detail": event_detail, "week_type": current_week_type}

        def lookup_template(source: dict, candidates: list, default: str):
            for k in candidates:
                v = source.get(k)
                if v:
                    return v
            return default

        if event_type == "homeroom":
            header_template = lookup_template(templates, ["header", "homeroom_header"], "HOMEROOM REMINDER (WEEK {week_type})")
            header_text = _safe_format(header_template, {"week_type": current_week_type, "location": event_location, "time": event_time})
            body_main_template = lookup_template(templates, ["body_main", "homeroom_body_main"], "โฮมรูม {location}")
            body_sub_template = lookup_template(templates, ["body_sub", "homeroom_body_sub"], "วันนี้ เวลา {time} ครับ")
            alt_template = lookup_template(templates, ["alt", "homeroom_alt"], "Week {week_type}: วันนี้ Homeroom {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"week_type": current_week_type, "location": event_location, "time": event_time, "detail": event_detail})
        else:
            header_template = lookup_template(templates, ["header", "assembly_header"], "ASSEMBLY NOTICE")
            header_text = _safe_format(header_template, {"location": event_location, "time": event_time, "detail": event_detail})
            body_main_template = lookup_template(templates, ["body_main", "assembly_body_main"], "เข้าแถวรวมที่ {location}")
            body_sub_template = lookup_template(templates, ["body_sub", "assembly_body_sub"], "วันนี้ เวลา {time} ครับ")
            alt_template = lookup_template(templates, ["alt", "assembly_alt"], "วันนี้เข้าแถวรวมที่ {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"location": event_location, "time": event_time, "detail": event_detail})

        body_text_main = _safe_format(body_main_template, template_ctx)
        body_text_sub = _safe_format(body_sub_template, {"time": event_time, "location": event_location, "detail": event_detail})

        # --- Determine Header Color ---
        if is_special:
            header_color = COLORS.get(f"special_{event_type}", COLORS.get(event_type, "#DC3545"))
        else:
            header_color = COLORS.get(event_type, "#DC3545")

        body_contents = [
            { "type": "text", "text": body_text_main, "weight": "bold", "size": "xl", "margin": "md", "wrap": True },
            { "type": "text", "text": body_text_sub, "size": "md", "color": "#555555", "margin": "md" }
        ]
        if event_detail:
            body_contents.append({"type": "box", "layout": "vertical", "margin": "lg", "spacing": "sm", "contents": [{"type": "box", "layout": "baseline", "spacing": "sm", "contents": [{"type": "text", "text": "รายละเอียด", "color": "#aaaaaa", "size": "sm", "flex": 2}, {"type": "text", "text": event_detail, "wrap": True, "color": "#666666", "size": "sm", "flex": 5}]}]})

        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        message_contents = {"type": "bubble", "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": header_text, "weight": "bold", "color": "#FFFFFF", "size": "sm"}], "backgroundColor": header_color, "paddingAll": "md"}, "body": {"type": "box", "layout": "vertical", "contents": body_contents}, "styles": {"header": {"separator": True}}}
        flex_message = FlexSendMessage(alt_text=alt_text, contents=message_contents)
        line_bot_api.push_message(GROUP_ID, flex_message)
        event_type_display = f"special {event_type}" if is_special else event_type
        print(f"{today_str}: Message sent for {event_type_display} at {event_location} (color: {header_color})")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
