import os
import json
import re
import time
import logging
from datetime import datetime, timedelta, date
import pytz
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import FlexSendMessage
from linebot.exceptions import LineBotApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# File to persist the last day a message was sent (YYYY-MM-DD)
LAST_SEND_FILE = 'last_send.json'

# Time before scheduled event to send message (21 minutes 17 seconds)
ADVANCE_TIME_MINUTES = 21
ADVANCE_TIME_SECONDS = 17

def load_last_send_date():
    """Return the last send date as 'YYYY-MM-DD' string or None if missing/invalid."""
    try:
        if not os.path.exists(LAST_SEND_FILE):
            return None
        with open(LAST_SEND_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('last_send_date')
    except Exception:
        return None


def save_last_send_date(date_str: str):
    """Persist the last send date (expects 'YYYY-MM-DD')."""
    try:
        with open(LAST_SEND_FILE, 'w', encoding='utf-8') as f:
            json.dump({'last_send_date': date_str}, f, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to update last send date: {e}")


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
        logger.error(f"Error loading or parsing config.json: {e}")
        return None


def get_event_for_date(config, target_date):
    """
    Get event information for a specific date.
    Returns: (event_type, event_location, event_detail, event_time, is_special, week_type)
    """
    try:
        CYCLE_START_DATE = datetime.strptime(config["cycle_start_date"], '%Y-%m-%d').date()
        HOLIDAYS = config.get("holidays", [])
        SPECIAL_ASSEMBLY_DAYS = config.get("special_assembly_days", {})
        SPECIAL_HOMEROOM_DAYS = config.get("special_homeroom_days", {})
        ROOM_SCHEDULE = config.get("room_schedule", {})
        DEFAULT_HOMEROOM_TIME = config.get("default_homeroom_time", "08:00")
        DEFAULT_ASSEMBLY_TIME = config.get("default_assembly_time", "07:50")
    except (TypeError, ValueError, KeyError) as e:
        logger.error(f"Error parsing config values: {e}")
        return None

    date_str = target_date.strftime('%Y-%m-%d')
    weekday = target_date.weekday()

    event_type, event_location, event_detail, event_time = None, None, None, None
    is_special = False
    entry_templates = {}
    week_type = None

    # Check holidays
    if date_str in HOLIDAYS:
        return None

    # Check special days
    if date_str in SPECIAL_ASSEMBLY_DAYS:
        event_data = SPECIAL_ASSEMBLY_DAYS[date_str]
        event_type = "assembly"
        is_special = True
        event_location = event_data.get("location", "ไม่ระบุ")
        event_detail = event_data.get("detail")
        event_time = event_data.get("time", DEFAULT_ASSEMBLY_TIME)
        entry_templates = event_data.get("templates", {})
    elif date_str in SPECIAL_HOMEROOM_DAYS:
        event_data = SPECIAL_HOMEROOM_DAYS[date_str]
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
            weeks_passed = (target_date - CYCLE_START_DATE).days // 7
            week_type = "A" if weeks_passed % 2 == 0 else "B"
            event_location = entry[0] if week_type == "A" else entry[1]
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
        return None

    # Calculate week type for homeroom events if not already set
    if event_type == "homeroom" and week_type is None:
        weeks_passed = (target_date - CYCLE_START_DATE).days // 7
        week_type = "A" if weeks_passed % 2 == 0 else "B"

    return {
        'event_type': event_type,
        'event_location': event_location,
        'event_detail': event_detail,
        'event_time': event_time,
        'is_special': is_special,
        'week_type': week_type,
        'entry_templates': entry_templates,
        'date_str': date_str
    }


def send_line_message(config, event_info):
    """Send LINE message for the given event."""
    CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
    GROUP_ID = os.environ.get('GROUP_ID')

    if not CHANNEL_ACCESS_TOKEN or not GROUP_ID:
        logger.error("Required secrets are not set.")
        return False

    MESSAGE_TEMPLATES = config.get("message_templates", {})
    COLORS = config.get("colors", {
        "homeroom": "#007BFF",
        "assembly": "#28A745",
        "special_homeroom": "#FF6B35",
        "special_assembly": "#C1427B"
    })

    def _safe_format(template: str, ctx: dict) -> str:
        if not template:
            return ""
        try:
            return template.format(**ctx)
        except Exception:
            return template

    def lookup_template(source: dict, candidates: list, default: str):
        for k in candidates:
            v = source.get(k)
            if v:
                return v
        return default

    try:
        templates = {**MESSAGE_TEMPLATES, **event_info['entry_templates']}
        template_ctx = {
            "time": event_info['event_time'],
            "location": event_info['event_location'],
            "detail": event_info['event_detail'],
            "week_type": event_info['week_type']
        }

        if event_info['event_type'] == "homeroom":
            header_template = lookup_template(templates, ["header", "homeroom_header"], "HOMEROOM REMINDER (WEEK {week_type})")
            header_text = _safe_format(header_template, {"week_type": event_info['week_type'], "location": event_info['event_location'], "time": event_info['event_time']})
            body_main_template = lookup_template(templates, ["body_main", "homeroom_body_main"], "โฮมรูม {location}")
            body_sub_template = lookup_template(templates, ["body_sub", "homeroom_body_sub"], "วันนี้ เวลา {time} ครับ")
            alt_template = lookup_template(templates, ["alt", "homeroom_alt"], "Week {week_type}: วันนี้ Homeroom {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"week_type": event_info['week_type'], "location": event_info['event_location'], "time": event_info['event_time'], "detail": event_info['event_detail']})
        else:
            header_template = lookup_template(templates, ["header", "assembly_header"], "ASSEMBLY NOTICE")
            header_text = _safe_format(header_template, {"location": event_info['event_location'], "time": event_info['event_time'], "detail": event_info['event_detail']})
            body_main_template = lookup_template(templates, ["body_main", "assembly_body_main"], "เข้าแถวรวมที่ {location}")
            body_sub_template = lookup_template(templates, ["body_sub", "assembly_body_sub"], "วันนี้ เวลา {time} ครับ")
            alt_template = lookup_template(templates, ["alt", "assembly_alt"], "วันนี้เข้าแถวรวมที่ {location} เวลา {time} ครับ")
            alt_text = _safe_format(alt_template, {"location": event_info['event_location'], "time": event_info['event_time'], "detail": event_info['event_detail']})

        body_text_main = _safe_format(body_main_template, template_ctx)
        body_text_sub = _safe_format(body_sub_template, {"time": event_info['event_time'], "location": event_info['event_location'], "detail": event_info['event_detail']})

        # Determine header color
        if event_info['is_special']:
            header_color = COLORS.get(f"special_{event_info['event_type']}", COLORS.get(event_info['event_type'], "#DC3545"))
        else:
            header_color = COLORS.get(event_info['event_type'], "#DC3545")

        body_contents = [
            {"type": "text", "text": body_text_main, "weight": "bold", "size": "xl", "margin": "md", "wrap": True},
            {"type": "text", "text": body_text_sub, "size": "md", "color": "#555555", "margin": "md"}
        ]
        
        if event_info['event_detail']:
            body_contents.append({
                "type": "box",
                "layout": "vertical",
                "margin": "lg",
                "spacing": "sm",
                "contents": [{
                    "type": "box",
                    "layout": "baseline",
                    "spacing": "sm",
                    "contents": [
                        {"type": "text", "text": "รายละเอียด", "color": "#aaaaaa", "size": "sm", "flex": 2},
                        {"type": "text", "text": event_info['event_detail'], "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                    ]
                }]
            })

        line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
        message_contents = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [{"type": "text", "text": header_text, "weight": "bold", "color": "#FFFFFF", "size": "sm"}],
                "backgroundColor": header_color,
                "paddingAll": "md"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": body_contents
            },
            "styles": {"header": {"separator": True}}
        }
        
        flex_message = FlexSendMessage(alt_text=alt_text, contents=message_contents)
        line_bot_api.push_message(GROUP_ID, flex_message)
        
        save_last_send_date(event_info['date_str'])
        event_type_display = f"special {event_info['event_type']}" if event_info['is_special'] else event_info['event_type']
        logger.info(f"{event_info['date_str']}: Message sent for {event_type_display} at {event_info['event_location']} (color: {header_color})")
        return True

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False


def calculate_send_time(event_date, event_time_str):
    """
    Calculate when to send the message (21 minutes 17 seconds before event).
    Returns datetime in Bangkok timezone.
    """
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    
    # Parse event time
    try:
        event_hour, event_minute = map(int, event_time_str.split(':'))
    except:
        logger.error(f"Invalid time format: {event_time_str}")
        return None
    
    # Create datetime for event
    event_datetime = datetime.combine(event_date, datetime.min.time().replace(hour=event_hour, minute=event_minute))
    event_datetime = bangkok_tz.localize(event_datetime)
    
    # Subtract 21 minutes 17 seconds
    send_datetime = event_datetime - timedelta(minutes=ADVANCE_TIME_MINUTES, seconds=ADVANCE_TIME_SECONDS)
    
    return send_datetime


def run_scheduler():
    """Main scheduler loop that runs continuously."""
    logger.info("========================================")
    logger.info("LINE Homeroom Bot Scheduler Service Started")
    logger.info(f"Advance notification time: {ADVANCE_TIME_MINUTES} minutes {ADVANCE_TIME_SECONDS} seconds before event")
    logger.info("========================================")
    
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    last_check_minute = -1
    
    while True:
        try:
            # Get current time in Bangkok
            now = datetime.now(bangkok_tz)
            current_date = now.date()
            current_time_str = now.strftime('%H:%M:%S')
            
            # Only check once per minute (when seconds are near 0)
            current_minute = now.minute
            if current_minute == last_check_minute:
                time.sleep(5)  # Sleep for 5 seconds before checking again
                continue
            
            last_check_minute = current_minute
            
            # Load config
            config = load_config()
            if not config:
                logger.warning("Failed to load config, will retry in 60 seconds")
                time.sleep(60)
                continue
            
            # Get today's event
            event_info = get_event_for_date(config, current_date)
            
            if not event_info:
                # No event today, log once per hour
                if now.minute == 0:
                    logger.info(f"No scheduled event for {current_date.strftime('%Y-%m-%d')} (checked at {current_time_str})")
                time.sleep(30)
                continue
            
            # Calculate when to send message
            send_time = calculate_send_time(current_date, event_info['event_time'])
            
            if not send_time:
                time.sleep(30)
                continue
            
            # Check if it's time to send
            time_diff = (send_time - now).total_seconds()
            
            # If we're within 60 seconds of send time (to account for timing variations)
            if -30 <= time_diff <= 60:
                # Check if already sent today
                last_send_date = load_last_send_date()
                if last_send_date == event_info['date_str']:
                    logger.info(f"Already sent message for today ({event_info['date_str']})")
                    time.sleep(60)
                    continue
                
                logger.info(f"Sending message for {event_info['event_type']} at {event_info['event_location']}")
                logger.info(f"Event time: {event_info['event_time']}, Current time: {current_time_str}")
                
                if send_line_message(config, event_info):
                    logger.info("✓ Message sent successfully!")
                else:
                    logger.error("✗ Failed to send message")
                
                # Sleep for a bit to avoid re-sending
                time.sleep(60)
            else:
                # Log status once per hour
                if now.minute == 0:
                    hours_until = time_diff / 3600
                    if hours_until > 0:
                        logger.info(f"Next message scheduled in {hours_until:.2f} hours (at {send_time.strftime('%H:%M:%S')})")
                    else:
                        logger.info(f"Missed send window by {abs(hours_until):.2f} hours - will try next day")
                
                time.sleep(30)
        
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in scheduler: {e}")
            time.sleep(60)


if __name__ == "__main__":
    run_scheduler()
