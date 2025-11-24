# Changelog

All notable changes to this project will be documented in this file.

## [v1.1.0] - 2025-11-24

### Added
- **Background Scheduler Service** (`scheduler_service.py`)
  - Continuous monitoring service that runs in the background
  - Precise timing: sends messages exactly 21 minutes 17 seconds before events
  - Automatic schedule refresh every 5 minutes
  - Thread-based timer for accurate message delivery
  
- **TUI Mode** (`--tui` / `-t`)
  - Interactive terminal interface with live updates
  - Real-time countdown timer (updates every second)
  - Progress bar showing time until message send
  - Status indicators with emojis (🔍 🎯 ⏰ ✓ 💤 ❌)
  - Event information display
  - Message statistics counter
  - Clean, centered layout (70 character width)
  
- **Developer Mode** (`--dev` / `-d`)
  - Verbose logging with debug information
  - Detailed timing calculations
  - Config loading status
  - Event detection details
  - Timer scheduling information
  
- **Configuration Management**
  - Added `config.json.example` as a template
  - Added `config.json` to `.gitignore` for privacy
  - Users now copy example to create their own config
  
- **Enhanced Error Handling**
  - Captures and displays errors from `main.py`
  - Shows timeout errors (30s limit)
  - Displays exit codes and stderr output
  - Updates TUI status on errors
  
- **Improved Architecture**
  - Scheduler calls `main.py` via subprocess
  - Single source of truth for message logic
  - Easy debugging: test `main.py` independently
  - No code duplication between scheduler and main

### Changed
- Refactored message sending logic to use `main.py`
- Scheduler now manages timing only, delegates sending to `main.py`
- Updated documentation with new features and usage examples
- Improved logging system with file and console handlers

### Technical Details
- Check interval: Every 5 minutes for schedule updates
- Timer precision: Exact second-level accuracy for message delivery
- TUI refresh rate: 1 second (live countdown)
- Non-TUI refresh rate: 5 seconds
- Message send timing: Event time - 21 minutes 17 seconds

## [v1.0.0] - 2025-11-20

### Added
- Initial release of LINE Homeroom Bot
- Daily homeroom and assembly reminders
- A/B week cycle support for alternating schedules
- Regular weekly schedule based on day of week
- Event prioritization hierarchy:
  1. Holidays (no messages)
  2. Special Assembly Days
  3. Special Homeroom Days
  4. Regularly Scheduled Events
- JSON comments support in `config.json` (single-line `//` and multi-line `/* */`)
- Customizable message templates
- Color-coded event headers:
  - Homeroom: Blue (#007BFF)
  - Assembly: Green (#28A745)
  - Special Homeroom: Orange (#FF6B35)
  - Special Assembly: Magenta (#C1427B)
- LINE Flex Message format for rich, formatted messages
- Daily-send guard using `last_send.json` to prevent duplicates
- Configurable event times and locations
- Support for event details/descriptions
- Template variable substitution (`{time}`, `{location}`, `{detail}`, `{week_type}`)
- Per-event template overrides
- Bangkok timezone support (`Asia/Bangkok`)

### Configuration
- `config.json` with comprehensive settings:
  - `cycle_start_date`: A/B week calculation base
  - `default_homeroom_time`: Default homeroom time
  - `default_assembly_time`: Default assembly time
  - `colors`: Custom header colors for event types
  - `message_templates`: Global message templates
  - `holidays`: List of dates to skip
  - `special_assembly_days`: Special assembly events with custom settings
  - `special_homeroom_days`: Special homeroom events with custom settings
  - `room_schedule`: Weekly schedule (days 0-6)

### Files
- `main.py`: Core bot logic and message sending
- `config.json`: Configuration file (user-specific, not tracked)
- `requirements.txt`: Python dependencies
- `.env`: Environment variables for LINE credentials
- `last_send.json`: Tracks last send date (auto-generated)
- `run_bot.bat`: Windows batch file for running the bot
- `README.md`: Documentation

### Dependencies
- `line-bot-sdk`: LINE Messaging API
- `pytz`: Timezone support
- `python-dotenv`: Environment variable management
