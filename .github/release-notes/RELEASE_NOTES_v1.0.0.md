# LINE Homeroom Bot v1.0.0 - Initial Release

## 🎉 Welcome to LINE Homeroom Bot!

The first release of an automated reminder system for daily homeroom and assembly schedules.

## ✨ Features

### 📨 Automated Reminders
- Sends daily homeroom and assembly notifications to LINE group chat
- Beautiful Flex Message format for easy-to-read messages
- Color-coded headers for different event types

### 🔄 Flexible Scheduling
- **A/B week cycle** support for alternating schedules
- Regular weekly schedules based on day of week
- Custom times for each event

### 🎯 Event Types
- **Homeroom**: Regular classroom check-ins
- **Assembly**: School-wide gatherings
- **Special Events**: Custom events with unique details
- **Holidays**: Automatic skip on holiday dates

### 🎨 Customization
- Fully configurable via `config.json`
- Custom message templates with variable substitution
- Per-event template overrides
- Color-coded event headers:
  - Homeroom: Blue (#007BFF)
  - Assembly: Green (#28A745)
  - Special Homeroom: Orange (#FF6B35)
  - Special Assembly: Magenta (#C1427B)

### 🛡️ Smart Features
- Daily-send guard prevents duplicate messages
- JSON comments support (`//` and `/* */`)
- Event prioritization hierarchy
- Bangkok timezone support

## 📋 Event Priority

1. Holidays (no messages sent)
2. Special Assembly Days
3. Special Homeroom Days  
4. Regularly Scheduled Events

## 🔧 Configuration

All settings in one place - `config.json`:
- `cycle_start_date`: A/B week calculation
- `default_homeroom_time` / `default_assembly_time`
- `colors`: Custom header colors
- `message_templates`: Global templates
- `holidays`: Skip dates
- `special_assembly_days` / `special_homeroom_days`: Special events
- `room_schedule`: Weekly schedule (0=Monday, 6=Sunday)

## 🚀 Quick Start

```bash
git clone https://github.com/champyod/Line-Homeroom-Bot.git
cd Line-Homeroom-Bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Configure .env with LINE credentials
python main.py
```

## 📦 What's Included

- `main.py`: Core bot logic
- `config.json`: Schedule configuration
- `requirements.txt`: Dependencies
- `.env.example`: Environment template
- `run_bot.bat`: Windows launcher
- `README.md`: Full documentation

## 🙏 Credits

Built with:
- [line-bot-sdk](https://github.com/line/line-bot-sdk-python)
- [pytz](https://pypi.org/project/pytz/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

**Note**: This is the base version. For automated scheduling, see v1.1.0 which includes the background scheduler service!
