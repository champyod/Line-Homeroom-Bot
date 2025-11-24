# LINE Homeroom Bot v1.1.0 - Scheduler Service with TUI

## 🚀 What's New

This release transforms the LINE Homeroom Bot from a simple one-time script into a powerful **background scheduler service** with a beautiful terminal interface!

### ✨ Major Features

#### 📅 Background Scheduler Service
- Runs continuously in the background
- **Precise timing**: Automatically sends messages exactly 21 minutes 17 seconds before events
- Smart scheduling: Checks config every 5 minutes, creates accurate timers for message delivery
- Never miss a reminder again!

#### 🖥️ TUI Mode (Terminal User Interface)
- Interactive display with live updates
- **Real-time countdown timer** that updates every second
- Beautiful progress bar showing time until message send
- Status indicators with emojis (🔍 🎯 ⏰ ✓ 💤 ❌)
- Event information at a glance
- Message statistics counter

![TUI Mode Preview](https://via.placeholder.com/600x400?text=TUI+Mode+Screenshot)

#### 🐛 Developer Mode
- Verbose logging with detailed debug information
- Timing calculations and schedule detection details
- Perfect for troubleshooting and monitoring

#### ⚙️ Better Configuration Management
- `config.json.example` template included
- `config.json` now excluded from git for privacy
- Easy setup: just copy the example and customize

### 🎯 Usage

```bash
# Run scheduler in normal mode
python scheduler_service.py

# Interactive TUI mode with live countdown
python scheduler_service.py --tui
python scheduler_service.py -t

# Verbose developer mode
python scheduler_service.py --dev
python scheduler_service.py -d

# Combine modes
python scheduler_service.py -t -d
```

### 🏗️ Architecture Improvements

- **Single source of truth**: Scheduler calls `main.py` for message sending
- No code duplication
- Easy debugging: test `main.py` independently
- Enhanced error handling with detailed error reporting

### 📊 Technical Details

- **Check interval**: Every 5 minutes for schedule updates
- **Timer precision**: Exact second-level accuracy
- **TUI refresh rate**: 1 second (smooth countdown)
- **Message timing**: Event time - 21 minutes 17 seconds

### 📝 Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed changes.

---

## 🔧 Installation

```bash
git clone https://github.com/champyod/Line-Homeroom-Bot.git
cd Line-Homeroom-Bot
cp config.json.example config.json
# Edit config.json with your schedule
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scheduler_service.py -t
```

## 📚 Documentation

See [README.md](README.md) for complete documentation and usage guide.
