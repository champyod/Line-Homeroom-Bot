import os
import json
import re
import time
import logging
import sys
import threading
import subprocess
from datetime import datetime, timedelta, date
import pytz
from dotenv import load_dotenv
from week_utils import calculate_effective_weeks
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn
from rich import box
from rich.live import Live

# Initialize Rich Console
console = Console()

# Parse command line arguments
DEV_MODE = any(arg in sys.argv for arg in ['--log=dev', '-log=dev', '-d', '--dev', '--debug'])
TUI_MODE = any(arg in sys.argv for arg in ['--tui', '-t'])

# Configure logging
if not TUI_MODE:
    logging.basicConfig(
        level=logging.DEBUG if DEV_MODE else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scheduler_service.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
else:
    # In TUI mode, log only to file
    logging.basicConfig(
        level=logging.DEBUG if DEV_MODE else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scheduler_service.log')
        ]
    )
    logger = logging.getLogger(__name__)

# TUI state
tui_state = {
    'status': 'Starting...',
    'current_time': '',
    'event_info': '',
    'send_time': '',
    'time_remaining': '',
    'next_check': '',
    'last_action': '',
    'message_count': 0,
    'config': None
}

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
        SKIP_WEEKS = config.get("skip_weeks", [])
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
            weeks_passed = calculate_effective_weeks(CYCLE_START_DATE, target_date, SKIP_WEEKS)
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
        weeks_passed = calculate_effective_weeks(CYCLE_START_DATE, target_date, SKIP_WEEKS)
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


def send_message_via_main():
    """Send LINE message by running main.py."""
    try:
        # Run main.py to send the message
        result = subprocess.run(
            [sys.executable, 'main.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Log main.py output
            if result.stdout:
                output = result.stdout.strip()
                if DEV_MODE:
                    log_message('debug', f"main.py output: {output}")
                else:
                    log_message('info', output)
            return True
        else:
            logger.error(f"main.py failed with exit code {result.returncode}")
            if result.stdout:
                logger.error(f"main.py stdout: {result.stdout.strip()}")
            if result.stderr:
                logger.error(f"main.py stderr: {result.stderr.strip()}")
            
            # Update TUI to show error
            if TUI_MODE:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                if error_msg:
                    tui_state['last_action'] = f"Error: {error_msg[:50]}"
                    tui_state['status'] = '❌ Send failed'
            
            return False
    
    except subprocess.TimeoutExpired:
        logger.error("main.py execution timed out (30s)")
        if TUI_MODE:
            tui_state['last_action'] = "Error: main.py timed out (30s)"
            tui_state['status'] = '❌ Timeout'
        return False
    except Exception as e:
        logger.error(f"Error running main.py: {e}")
        if TUI_MODE:
            tui_state['last_action'] = f"Error: {str(e)[:50]}"
            tui_state['status'] = '❌ Exception'
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


def format_time_remaining(seconds):
    """Format seconds into human-readable time (hours, mins, secs)."""
    if seconds < 0:
        return f"-{format_time_remaining(-seconds)}"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min{'s' if minutes != 1 else ''}")
    if secs > 0 or not parts:
        parts.append(f"{secs} sec{'s' if secs != 1 else ''}")
    
    return " ".join(parts)


def clear_screen():
    """Clear the terminal screen."""
    console.clear()


def draw_tui():
    """Draw the TUI interface."""
    clear_screen()
    
    if DEV_MODE:
        draw_debug_tui()
    else:
        draw_simple_tui()


def draw_simple_tui():
    """Draw the standard user information TUI using Rich."""
    # Create layout elements
    status_text = Text()
    status_text.append("Status: ", style="bold cyan")
    status_text.append(f"{tui_state['status']}\n", style="white")
    status_text.append("Current Time: ", style="bold cyan")
    status_text.append(f"{tui_state['current_time']}\n", style="white")
    
    if tui_state['event_info']:
        status_text.append("\nToday's Event:\n", style="bold yellow")
        status_text.append(f"  {tui_state['event_info']}\n", style="white")
    
    if tui_state['send_time']:
        status_text.append(f"\nScheduled Send Time: {tui_state['send_time']}\n", style="bold green")
    
    # Next check & stats
    stats_text = Text()
    if tui_state['next_check']:
        stats_text.append(f"Next Check: {tui_state['next_check']}   ", style="dim")
    stats_text.append(f"Sent Today: {tui_state['message_count']}\n", style="dim")
    
    if tui_state['last_action']:
        stats_text.append(f"Last Action: {tui_state['last_action']}", style="italic dim")

    # Progress Bar if active
    progress_renderable = Text("")
    if tui_state['time_remaining'] and tui_state['send_time']:
        # Parse time for progress
        remaining_str = tui_state['time_remaining']
        total_secs = 0
        try:
            if 'hour' in remaining_str:
                hours = int(remaining_str.split('hour')[0].split()[-1])
                total_secs += hours * 3600
            if 'min' in remaining_str:
                mins = int(remaining_str.split('min')[0].split()[-1])
                total_secs += mins * 60
            if 'sec' in remaining_str:
                secs = int(remaining_str.split('sec')[0].split()[-1])
                total_secs += secs
            
            # Create a progress bar
            # Assume max 24h for visualization context
            max_seconds = 24 * 3600 
            completed = max(0, max_seconds - total_secs)
            
            # We can use a rich.progress.BarColumn directly? 
            # Or just a textual representation for simplicity in a static panel update.
            # Let's use string manipulation for now to keep it steady, or a mini table.
            pct = max(0, min(100, (1 - (total_secs / max_seconds)) * 100))
            color = "green" if pct > 90 else "yellow" if pct > 50 else "red"
            progress_renderable = Text(f"\nTime Remaining: {remaining_str}\n", style=f"bold {color}")
            
        except:
            pass

    # Combine into a Panel
    content = Layout()
    content.split_column(
        Layout(status_text),
        Layout(progress_renderable, size=3 if str(progress_renderable) else 0),
        Layout(stats_text)
    )

    panel = Panel(
        content,
        title="[bold blue]LINE Homeroom Bot Scheduler[/]",
        subtitle="[dim]Press Ctrl+C to stop[/]",
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)


def get_debug_renderable():
    """Generate the detailed debug TUI layout as a renderable."""
    config = tui_state.get('config')
    
    # 1. Environment Info
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(bangkok_tz)
    today = now.date()
    
    env_table = Table(show_header=False, box=None, padding=0)
    env_table.add_column("Key", style="bold cyan")
    env_table.add_column("Value", style="white")
    
    env_table.add_row("Current Time", f"{now.strftime('%Y-%m-%d %H:%M:%S')} (Week {now.isocalendar()[1]})")
    env_table.add_row("Group ID", f"{os.environ.get('GROUP_ID', 'Not Set')[:5]}***")
    
    if config:
        cycle_start = datetime.strptime(config["cycle_start_date"], '%Y-%m-%d').date()
        skip_weeks = config.get("skip_weeks", [])
        env_table.add_row("Cycle Start", str(cycle_start))
        env_table.add_row("Skip Weeks", f"{len(skip_weeks)} periods defined")
    else:
        env_table.add_row("Config", "[red]Not Loading[/]")

    env_panel = Panel(env_table, title="Environment", border_style="cyan")

    # 2. Calculation Logic
    if config:
        cycle_start = datetime.strptime(config["cycle_start_date"], '%Y-%m-%d').date()
        skip_weeks = config.get("skip_weeks", [])
        
        total_school_days_passed = 0
        skipped_school_days_passed = 0
        skipped_dates = set()
        if skip_weeks:
            for raw_period in skip_weeks:
                try:
                    s_start = datetime.strptime(raw_period["start"], "%Y-%m-%d").date()
                    s_end = datetime.strptime(raw_period["end"], "%Y-%m-%d").date()
                    curr = s_start
                    while curr <= s_end:
                        skipped_dates.add(curr)
                        curr += timedelta(days=1)
                except: pass
                
        curr = cycle_start
        while curr < today:
            if curr.weekday() < 5: 
                total_school_days_passed += 1
                if curr in skipped_dates:
                    skipped_school_days_passed += 1
            curr += timedelta(days=1)
                
        effective_days = total_school_days_passed - skipped_school_days_passed
        weeks_passed = max(0, effective_days) // 5
        week_type = "A" if weeks_passed % 2 == 0 else "B"
        
        calc_table = Table(show_header=False, box=None, padding=0)
        calc_table.add_column("Key", style="bold magenta")
        calc_table.add_column("Value")
        
        calc_table.add_row("Total Schedule Days", f"{ (today - cycle_start).days } (Calendar)")
        calc_table.add_row("Total School Days", f"{ total_school_days_passed } (Mon-Fri)")
        calc_table.add_row("Skipped School Days", f"{ skipped_school_days_passed }")
        calc_table.add_row("Effective Days", f"{ effective_days }")
        calc_table.add_row("Weeks Passed", f"{ weeks_passed } (Floor({effective_days}/5))")
        calc_table.add_row("Week Type", f"[bold yellow]{week_type}[/]")
        
        calc_panel = Panel(calc_table, title="Week Rotation (Base-5)", border_style="magenta")
    else:
        calc_panel = Panel("Waiting for config...", title="Week Rotation", border_style="red")

    # 3. Weekly Schedule Table
    sched_table = Table(title=f"Weekly Schedule: {today.strftime('%Y')}-W{now.isocalendar()[1]}", box=box.ROUNDED, expand=True)
    sched_table.add_column("Date", style="cyan", no_wrap=True)
    sched_table.add_column("Day", style="blue")
    sched_table.add_column("WkType", justify="center")
    sched_table.add_column("Event", style="green")
    sched_table.add_column("Location")
    sched_table.add_column("Time")
    sched_table.add_column("Send At", style="magenta")

    if config:
        days_since_sunday = (today.weekday() + 1) % 7
        start_sunday = today - timedelta(days=days_since_sunday)
        
        for i in range(7):
            target_date = start_sunday + timedelta(days=i)
            is_today = (target_date == today)
            
            info = get_event_for_date(config, target_date)
            
            date_str = target_date.strftime('%m-%d')
            day_name = target_date.strftime('%A')
            
            row_style = "bold white" if is_today else "dim" if target_date < today else None
            
            if info:
                evt_type = info['event_type']
                wk_type = info.get('week_type') or "-"
                loc = info['event_location'] or "-"
                evt_time = info['event_time']
                
                send_dt = calculate_send_time(target_date, evt_time)
                send_time_str = send_dt.strftime('%H:%M:%S') if send_dt else "-"
                
                sched_table.add_row(
                    date_str, day_name, str(wk_type), evt_type, loc, evt_time, send_time_str,
                    style=row_style
                )
            else:
                sched_table.add_row(
                    date_str, day_name, "-", "No Event", "-", "-", "-",
                    style=row_style
                )

    # 4. Message Preview Panel (for today's event)
    msg_preview_content = Text("No event today", style="dim")
    if config and tui_state.get('event_info'):
        event_info = get_event_for_date(config, today)
        if event_info:
            msg_preview_content = Text()
            msg_preview_content.append("┌─ Flex Message ─┐\n", style="bold green")
            msg_preview_content.append(f"│ Type: {event_info['event_type'].upper()}\n", style="cyan")
            msg_preview_content.append(f"│ Loc : {event_info['event_location']}\n", style="white")
            msg_preview_content.append(f"│ Time: {event_info['event_time']}\n", style="white")
            if event_info.get('event_detail'):
                msg_preview_content.append(f"│ Info: {event_info['event_detail'][:30]}\n", style="dim")
            msg_preview_content.append("└────────────────┘\n", style="bold green")
            
            # Alt text
            wk = event_info.get('week_type') or ''
            loc = event_info['event_location']
            tm = event_info['event_time']
            if event_info['event_type'] == 'homeroom':
                alt = f"Week {wk}: วันนี้ Homeroom {loc} เวลา {tm}"
            else:
                alt = f"วันนี้เข้าแถวรวมที่ {loc} เวลา {tm}"
            msg_preview_content.append("\n[Alt Text]\n", style="bold yellow")
            msg_preview_content.append(alt, style="italic")
    
    msg_panel = Panel(msg_preview_content, title="Message Preview", border_style="green")

    # 5. Footer Status with Next Check
    last_send = load_last_send_date() or "None"
    next_chk = tui_state.get('next_check') or '-'
    status_msg = f"Status: {tui_state['status']}  |  Last Sent: {last_send}  |  Next Check: {next_chk}  |  Msgs: {tui_state['message_count']}"
    if tui_state['last_action']:
        status_msg += f"\nLast Action: {tui_state['last_action']}"
    
    footer_panel = Panel(status_msg, style="dim white")

    # Layout Assembly
    layout = Layout()
    layout.split_column(
        Layout(name="top", size=10),
        Layout(name="middle", ratio=1),
        Layout(name="bottom", size=4)
    )
    layout["top"].split_row(
        Layout(env_panel),
        Layout(calc_panel)
    )
    layout["middle"].split_row(
        Layout(sched_table, ratio=3),
        Layout(msg_panel, ratio=1)
    )
    layout["bottom"].update(footer_panel)
    
    return Panel(layout, title="[bold]LINE Homeroom Bot - Debug Mode[/]", border_style="green")


def draw_debug_tui():
    """Draw the debug TUI (wrapper for compatibility)."""
    console.clear()
    console.print(get_debug_renderable())


def log_message(level, message):
    """Log message - either to logger or TUI."""
    if TUI_MODE:
        # Update TUI state based on message content
        if "Current time:" in message:
            tui_state['current_time'] = message.split("Current time: ")[1] if "Current time: " in message else ""
        elif "Event:" in message:
            tui_state['event_info'] = message.split("Event: ")[1] if "Event: " in message else ""
        elif "Send time:" in message:
            tui_state['send_time'] = message.split("Send time: ")[1] if "Send time: " in message else ""
        elif "Time until send:" in message:
            tui_state['time_remaining'] = message.split("Time until send: ")[1] if "Time until send: " in message else ""
        elif "Next check at" in message:
            tui_state['next_check'] = message.split("Next check at ")[1] if "Next check at " in message else ""
        elif "Scheduled message" in message:
            tui_state['status'] = '⏰ Waiting for send time'
            tui_state['last_action'] = message
        elif "Message sent successfully" in message:
            tui_state['status'] = '✓ Message Sent'
            tui_state['message_count'] += 1
            tui_state['last_action'] = message
        elif "No scheduled event" in message:
            tui_state['status'] = '💤 No event today'
            tui_state['event_info'] = ''
            tui_state['send_time'] = ''
            tui_state['time_remaining'] = ''
        
        # Always log to file
        if level == 'debug' and DEV_MODE:
            logger.debug(message)
        elif level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
    else:
        # Normal logging
        if level == 'debug' and DEV_MODE:
            logger.debug(message)
        elif level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)


# Global variable to store the scheduled timer
scheduled_timer = None
scheduled_timer_lock = threading.Lock()


def send_scheduled_message(config, event_info):
    """Called by the timer to send the message at the exact time."""
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(bangkok_tz)
    
    # Check if already sent today
    last_send_date = load_last_send_date()
    if last_send_date == event_info['date_str']:
        log_message('info', f"Already sent message for today ({event_info['date_str']})")
        return
    
    log_message('info', f"⏰ Triggered: Sending message for {event_info['event_type']} at {event_info['event_location']}")
    log_message('info', f"Event time: {event_info['event_time']}, Current time: {now.strftime('%H:%M:%S')}")
    
    if send_message_via_main():
        log_message('info', "✓ Message sent successfully!")
        if TUI_MODE:
            draw_tui()
    else:
        log_message('error', "✗ Failed to send message")


def schedule_message(config, event_info, send_time):
    """Schedule a timer to send the message at the exact time."""
    global scheduled_timer
    
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(bangkok_tz)
    
    delay_seconds = (send_time - now).total_seconds()
    
    if delay_seconds < 0:
        if DEV_MODE:
            log_message('debug', f"Send time has passed ({format_time_remaining(delay_seconds)} ago)")
        return False
    
    with scheduled_timer_lock:
        # Cancel existing timer if any
        if scheduled_timer is not None:
            scheduled_timer.cancel()
            if DEV_MODE:
                log_message('debug', "Cancelled previous scheduled timer")
        
        # Create new timer
        scheduled_timer = threading.Timer(
            delay_seconds,
            send_scheduled_message,
            args=(config, event_info)
        )
        scheduled_timer.daemon = True
        scheduled_timer.start()
    
    log_message('info', f"📅 Scheduled message for {send_time.strftime('%H:%M:%S')} ({format_time_remaining(delay_seconds)} from now)")
    
    return True


def get_tui_renderable():
    """Get the appropriate renderable based on mode."""
    if DEV_MODE:
        return get_debug_renderable()
    else:
        return get_simple_renderable()


def get_simple_renderable():
    """Generate the simple TUI as a renderable."""
    status_text = Text()
    status_text.append("Status: ", style="bold cyan")
    status_text.append(f"{tui_state['status']}\n", style="white")
    status_text.append("Current Time: ", style="bold cyan")
    status_text.append(f"{tui_state['current_time']}\n", style="white")
    
    if tui_state['event_info']:
        status_text.append("\nToday's Event:\n", style="bold yellow")
        status_text.append(f"  {tui_state['event_info']}\n", style="white")
    
    if tui_state['send_time']:
        status_text.append(f"\nScheduled Send Time: {tui_state['send_time']}\n", style="bold green")
    
    if tui_state['time_remaining']:
        status_text.append(f"Time Remaining: {tui_state['time_remaining']}\n", style="bold magenta")
    
    stats_text = Text()
    if tui_state['next_check']:
        stats_text.append(f"Next Check: {tui_state['next_check']}   ", style="dim")
    stats_text.append(f"Sent Today: {tui_state['message_count']}\n", style="dim")
    
    if tui_state['last_action']:
        stats_text.append(f"Last Action: {tui_state['last_action']}", style="italic dim")

    content = Layout()
    content.split_column(
        Layout(status_text, ratio=2),
        Layout(stats_text, ratio=1)
    )

    return Panel(
        content,
        title="[bold blue]LINE Homeroom Bot Scheduler[/]",
        subtitle="[dim]Press Ctrl+C to stop[/]",
        border_style="blue",
        padding=(1, 2)
    )


def run_scheduler():
    """Main scheduler loop that runs continuously."""
    tui_state['status'] = 'Initializing...'
    
    bangkok_tz = pytz.timezone("Asia/Bangkok")
    last_check_time = None
    cached_send_time = None
    cached_event_info = None
    
    if not TUI_MODE:
        # Non-TUI mode: just log and loop
        log_message('info', "========================================")
        log_message('info', "LINE Homeroom Bot Scheduler Service Started")
        log_message('info', f"Advance notification time: {ADVANCE_TIME_MINUTES} minutes {ADVANCE_TIME_SECONDS} seconds before event")
        if DEV_MODE:
            log_message('info', "Development Mode: Verbose logging enabled")
        log_message('info', "Checking schedule every 5 minutes")
        log_message('info', "========================================")
        
        # Run non-TUI loop
        while True:
            try:
                now = datetime.now(bangkok_tz)
                current_date = now.date()
                current_time_str = now.strftime('%H:%M:%S')
                
                do_full_check = (last_check_time is None or 
                               (now - last_check_time).total_seconds() >= 300)
                
                if do_full_check:
                    last_check_time = now
                    if DEV_MODE:
                        log_message('debug', f"Current time: {current_time_str}")
                    
                    config = load_config()
                    if not config:
                        log_message('warning', "Failed to load config, will retry in 5 minutes")
                        time.sleep(5)
                        continue
                    
                    tui_state['config'] = config
                    event_info = get_event_for_date(config, current_date)
                    
                    if not event_info:
                        log_message('info', f"No scheduled event for {current_date.strftime('%Y-%m-%d')}")
                        time.sleep(5)
                        continue
                    
                    send_time = calculate_send_time(current_date, event_info['event_time'])
                    if not send_time:
                        log_message('warning', "Failed to calculate send time")
                        time.sleep(5)
                        continue
                    
                    cached_send_time = send_time
                    cached_event_info = event_info
                    
                    last_send_date = load_last_send_date()
                    if last_send_date == event_info['date_str']:
                        log_message('info', f"Already sent message for today")
                        cached_send_time = None
                        cached_event_info = None
                        time.sleep(5)
                        continue
                    
                    schedule_message(config, event_info, send_time)
                
                time.sleep(5)
            
            except KeyboardInterrupt:
                log_message('info', "Scheduler stopped by user")
                with scheduled_timer_lock:
                    if scheduled_timer is not None:
                        scheduled_timer.cancel()
                break
            except Exception as e:
                log_message('error', f"Unexpected error in scheduler: {e}")
                time.sleep(300)
        return
    
    # TUI MODE: Use Live with alternate screen buffer
    try:
        with Live(get_tui_renderable(), refresh_per_second=1, screen=True, console=console) as live:
            while True:
                try:
                    now = datetime.now(bangkok_tz)
                    current_date = now.date()
                    current_time_str = now.strftime('%H:%M:%S')
                    tui_state['current_time'] = current_time_str
                    
                    do_full_check = (last_check_time is None or 
                                   (now - last_check_time).total_seconds() >= 300)
                    
                    if do_full_check:
                        last_check_time = now
                        tui_state['status'] = '🔍 Checking schedule...'
                        live.update(get_tui_renderable())
                        
                        if DEV_MODE:
                            log_message('debug', f"Current time: {current_time_str}")
                        
                        config = load_config()
                        if not config:
                            log_message('warning', "Failed to load config, will retry in 5 minutes")
                            tui_state['status'] = '⚠️ Config load failed'
                            live.update(get_tui_renderable())
                            time.sleep(5)
                            continue
                        
                        tui_state['config'] = config
                        event_info = get_event_for_date(config, current_date)
                        
                        if not event_info:
                            log_message('info', f"No scheduled event for {current_date.strftime('%Y-%m-%d')}")
                            tui_state['status'] = '💤 No event today'
                            tui_state['event_info'] = ''
                            tui_state['send_time'] = ''
                            tui_state['time_remaining'] = ''
                            cached_send_time = None
                            cached_event_info = None
                            
                            next_check = now + timedelta(minutes=5)
                            tui_state['next_check'] = next_check.strftime('%H:%M:%S')
                            
                            live.update(get_tui_renderable())
                            time.sleep(1)
                            continue
                        
                        send_time = calculate_send_time(current_date, event_info['event_time'])
                        
                        if not send_time:
                            log_message('warning', "Failed to calculate send time")
                            tui_state['status'] = '⚠️ Send time calculation failed'
                            live.update(get_tui_renderable())
                            time.sleep(5)
                            continue
                        
                        cached_send_time = send_time
                        cached_event_info = event_info
                        
                        time_diff = (send_time - now).total_seconds()
                        
                        if DEV_MODE:
                            log_message('debug', f"Event: {event_info['event_type']} at {event_info['event_location']}")
                            log_message('debug', f"Send time: {send_time.strftime('%H:%M:%S')}")
                        
                        tui_state['event_info'] = f"{event_info['event_type'].title()} at {event_info['event_location']} ({event_info['event_time']})"
                        tui_state['send_time'] = send_time.strftime('%H:%M:%S')
                        tui_state['time_remaining'] = format_time_remaining(time_diff)
                        
                        last_send_date = load_last_send_date()
                        if last_send_date == event_info['date_str']:
                            log_message('info', f"Already sent message for today")
                            tui_state['status'] = '✓ Already sent today'
                            cached_send_time = None
                            cached_event_info = None
                            
                            next_check = now + timedelta(minutes=5)
                            tui_state['next_check'] = next_check.strftime('%H:%M:%S')
                            
                            live.update(get_tui_renderable())
                            time.sleep(1)
                            continue
                        
                        schedule_message(config, event_info, send_time)
                        tui_state['status'] = '⏰ Waiting for send time'
                        
                        next_check = now + timedelta(minutes=5)
                        tui_state['next_check'] = next_check.strftime('%H:%M:%S')
                    
                    else:
                        # Just update time remaining
                        if cached_send_time and cached_event_info:
                            time_diff = (cached_send_time - now).total_seconds()
                            tui_state['time_remaining'] = format_time_remaining(time_diff)
                            
                            if last_check_time:
                                next_check = last_check_time + timedelta(minutes=5)
                                tui_state['next_check'] = next_check.strftime('%H:%M:%S')
                    
                    live.update(get_tui_renderable())
                    time.sleep(1)
                
                except KeyboardInterrupt:
                    log_message('info', "Scheduler stopped by user")
                    with scheduled_timer_lock:
                        if scheduled_timer is not None:
                            scheduled_timer.cancel()
                    break
                except Exception as e:
                    log_message('error', f"Unexpected error in scheduler: {e}")
                    tui_state['status'] = f'❌ Error: {str(e)[:30]}'
                    live.update(get_tui_renderable())
                    time.sleep(5)
    
    except KeyboardInterrupt:
        # Clean exit from Live context
        pass


if __name__ == "__main__":
    run_scheduler()
