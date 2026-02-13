# ClaudeGhost

[![Tests](https://github.com/yourusername/ClaudeGhost/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/ClaudeGhost/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Headless Supervisor for the Anthropic Claude CLI** - Run Claude Code autonomously while staying in control via Telegram.

ClaudeGhost wraps the `claude` CLI in a supervised shell, automatically approving safe operations based on your configured autonomy level while escalating risky commands to your phone for approval via **Telegram Bot API**.

---

## Features

- **AFK Autonomy Levels (1-5)**: From paranoid (asks everything) to god mode (full auto)
- **Telegram Bot API**: Approve/block commands from your phone - free, unlimited, instant
- **Risk Classification**: Commands categorized as Read-Only, Write, Execute, or Critical
- **Budget Control**: Set spending limits with automatic pause on exceed
- **Live Dashboard**: Rich terminal UI showing real-time status and logs
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Stall Detection**: Alerts you when the CLI hangs

---

## Requirements

- Python 3.10+
- [Anthropic Claude CLI](https://docs.anthropic.com/claude-code/getting-started) installed
- Telegram account (for notifications)

---

## Installation

See [docs/INSTALL.md](docs/INSTALL.md) for complete installation instructions.

---

## Quick Start (5 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
```

### 2. Setup Telegram Bot

```bash
python setup_interactive.py
```

Or manually:
1. Message **@BotFather** on Telegram -> `/newbot`
2. Copy the bot token
3. Message your bot, get your chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Configure:

```bash
cp .env.example .env
# Edit .env with your token and chat_id
```

Full guide: [`docs/TELEGRAM_SETUP.md`](docs/TELEGRAM_SETUP.md)

### 3. Test Connection

```bash
python -m src.cli config test
```

### 4. Run

```bash
python -m src.launcher "Create a hello world app" --level 3
```

You'll receive Telegram notifications when approval is needed.

---

## AFK Levels

| Level | Name | Auto-Approves |
|-------|------|---------------|
| 1 | Paranoid | Nothing |
| 2 | Auditor | Read-only |
| 3 | Manager | Read + Write |
| 4 | Director | Read + Write + Execute |
| 5 | God Mode | Everything |

---

## Telegram Commands

When approval is needed, reply with:

| Reply | Action |
|-------|--------|
| `A` | Approve |
| `B` | Block |
| `C <text>` | Send alternative instruction |
| `D` | Kill process |

---

## CLI Reference

```bash
# Interactive mode
python -m src.launcher

# Quick mode
python -m src.launcher "task" --level 3 --budget 10.00

# Screen-only (no Telegram)
python -m src.launcher "task" --no-telegram

# Config management
python -m src.cli config show
python -m src.cli config set bot-token YOUR_TOKEN
python -m src.cli config set chat-id YOUR_CHAT_ID
python -m src.cli config test
```

---

## Project Structure

```
ClaudeGhost/
├── src/
│   ├── main.py           # Orchestrator
│   ├── bridge.py          # Claude CLI wrapper (PTY/subprocess)
│   ├── guardian.py         # Risk classification engine
│   ├── telegram_bot.py     # Telegram Bot API client
│   ├── screen_notifier.py  # Terminal-only fallback
│   ├── config.py           # Settings (pydantic)
│   ├── launcher.py         # Interactive launcher
│   ├── cli.py              # CLI utilities
│   └── utils.py            # Logging, stats, TUI dashboard
├── tests/                  # Test suite
├── docs/                   # Documentation
├── .env.example            # Config template
├── requirements.txt
└── setup.py
```

---

## Contributing

Contributions are welcome! See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

## License

MIT
