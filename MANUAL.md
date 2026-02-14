# ClaudeGhost Manual

A step-by-step guide to using ClaudeGhost with the Claude Code CLI.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Setting Up Telegram](#setting-up-telegram)
4. [Configuration](#configuration)
5. [Your First Run](#your-first-run)
6. [Understanding the Dashboard](#understanding-the-dashboard)
7. [Telegram Commands](#telegram-commands)
8. [AFK Levels Explained](#afk-levels-explained)
9. [Session Loop](#session-loop)
10. [Changelog Tracking](#changelog-tracking)
11. [Updating ClaudeGhost](#updating-claudeghost)
12. [Real-World Examples](#real-world-examples)
13. [Tips & Best Practices](#tips--best-practices)

---

## Prerequisites

### 1. Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
claude auth
claude --version
```

### 2. Python 3.10+

```bash
python --version
```

### 3. Telegram Account

Download Telegram on your phone or use the desktop/web app.

---

## Installation

See [docs/INSTALL.md](docs/INSTALL.md) for complete installation instructions.

Quick setup:

```bash
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
python setup_interactive.py
```

---

## Setting Up Telegram

### Step 1: Create a Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Choose a name and username
4. Copy the bot token

### Step 2: Get Your Chat ID

1. Send any message to your new bot
2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find your `chat.id` in the JSON response

### Step 3: Configure

```bash
python -m src.cli config set bot-token YOUR_BOT_TOKEN
python -m src.cli config set chat-id YOUR_CHAT_ID
python -m src.cli config test
```

Full guide: [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md)

---

## Configuration

### .env File

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLED=true
DEFAULT_AFK_LEVEL=3
MAX_BUDGET_USD=10.00
```

### CLI Commands

```bash
python -m src.cli config show      # View config
python -m src.cli config test      # Test Telegram
python -m src.cli config set <key> <value>
```

---

## Your First Run

```bash
python claudeghost.py "Create a Python script that fetches weather data" --level 3
```

Or launch interactive mode (recommended for first time):

```bash
python claudeghost.py
```

The interactive launcher walks you through 4 steps:
1. Enter your task
2. Select AFK level (with descriptions)
3. Choose communication method (Telegram / Screen)
4. Set budget limit

What happens during a session:
1. ClaudeGhost launches Claude Code with your task (no separate terminal needed)
2. You see real-time progress in the ClaudeGhost dashboard (files read, edited, commands run)
3. Read-only commands auto-approve (level 3)
4. Write commands auto-approve (level 3)
5. Execute commands -> Telegram notification
6. You reply A/B/C/D on Telegram
7. Session ends -> changelog saved -> ask for another session

---

## Understanding the Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ Activity Log                    │ Session Status                │
│                                 │                               │
│ 14:32:01 Spawning: claude "..." │ State: RUNNING                │
│ 14:32:03 Guardian: Read-Only    │ Task: Build REST API...       │
│ 14:32:05 Auto-approved: ls -la  │ AFK Level: 3 (Manager)        │
│ 14:32:07 Auto-approved: mkdir   │ Budget: $0.12 / $10.00        │
│ 14:32:10 Guardian: Execute      │ Notify: Telegram              │
│ 14:32:10 Waiting for Telegram.. │                               │
│                                 ├───────────────────────────────┤
│                                 │ Statistics                    │
│                                 │ Elapsed: 2m 34s               │
│                                 │ Queries: 5                    │
│                                 │ Telegram I/O: 3 / 1           │
└─────────────────────────────────┴───────────────────────────────┘
```

### States

| State | Meaning |
|-------|---------|
| STARTING | Initializing |
| RUNNING | Processing |
| THINKING | Claude generating |
| QUERY | Waiting for decision |
| WAITING | Awaiting Telegram reply |
| BUDGET_PAUSE | Budget exceeded |
| EXITED | Done |

---

## Telegram Commands

When approval is needed, you receive:

```
Approval Needed
Command: npm install express
Risk: 🟠 Execute

Reply:
[A] Approve
[B] Block
[C <text>] Context
[D] Detonate (kill)
```

| Reply | Action |
|-------|--------|
| `A` | Approve and continue |
| `B` | Block and skip |
| `C Use yarn instead` | Send alternative instruction |
| `D` | Kill the process |

---

## AFK Levels Explained

### Level 1: Paranoid
```bash
python -m src.launcher "Review security of auth.py" --level 1
```
Asks for EVERYTHING. Use for security audits.

### Level 2: Auditor
```bash
python -m src.launcher "Analyze the codebase" --level 2
```
Auto-approves reads. Use for code exploration.

### Level 3: Manager (Default)
```bash
python -m src.launcher "Add input validation" --level 3
```
Auto-approves reads + writes. Use for normal development.

### Level 4: Director
```bash
python -m src.launcher "Set up new React project" --level 4
```
Auto-approves reads + writes + execute. Use for scaffolding.

### Level 5: God Mode
```bash
python -m src.launcher "Deploy the application" --level 5
```
Auto-approves everything. Use with active monitoring.

---

## Session Loop

After each task completes, ClaudeGhost asks if you want to start another session. This is ideal for remote work where you want to queue multiple tasks without restarting.

```
Session Complete
  Duration: 5m 12s
  Cost: $0.42 / $10.00

📄 Changelog saved: session_logs/session_20260213_143015_a1b2c3d4.txt

Start another session? [y/N]: y
```

When you say yes, the interactive launcher appears again so you can enter a new task with fresh settings. When you say no, ClaudeGhost exits cleanly.

---

## Changelog Tracking

Every session automatically generates a changelog saved to `session_logs/` inside the ClaudeGhost directory.

Each log file contains:
- Session ID, task, and timestamps
- List of all files modified
- List of all commands executed
- Duration and cost summary

Example log filename: `session_20260213_143015_a1b2c3d4.txt`

At the end of each session, Telegram receives a short summary with the file path. The full changelog is never sent via Telegram to keep messages clean.

```
📝 Session Complete
Files modified: 5
Commands executed: 12

📄 Full changelog: C:\...\session_logs\session_20260213_143015_a1b2c3d4.txt
```

---

## Updating ClaudeGhost

ClaudeGhost checks for updates automatically on startup. If a new version is available, you'll see a notification panel.

To update manually:

```bash
python -m src.updater
```

This will:
1. Check GitHub for the latest release
2. Pull the latest code via `git pull`
3. Update Python dependencies

You can also update manually:

```bash
cd ClaudeGhost
git pull origin main
pip install -r requirements.txt
```

---

## Real-World Examples

### Building a Feature
```bash
python claudeghost.py "Add JWT authentication to the Express app" --level 3
```

### Debugging
```bash
python claudeghost.py "Fix failing tests in tests/unit/" --level 2
```

### Full Autonomy
```bash
python claudeghost.py "Create FastAPI project with Docker" --level 5
```

### Remote Batch Work
```bash
# Start interactive mode, chain multiple sessions
python claudeghost.py
# Task 1: "Add user registration"
# Task 2: "Add email verification"  (after session 1 completes)
# Task 3: "Write unit tests"        (after session 2 completes)
```

### Review What Changed
```bash
# After a session, check the changelog
type session_logs\session_20260213_143015_a1b2c3d4.txt
```

---

## Tips & Best Practices

1. **Start low, go high** - Begin at level 2-3, increase once comfortable
2. **Set budgets** - `MAX_BUDGET_USD=5.00` for experiments, `20.00` for production
3. **Use context injection** - Reply `C Use axios instead of fetch` instead of blocking
4. **Emergency stop** - Reply `D` on Telegram or `Ctrl+C` in terminal
5. **Review changelogs** - Check `session_logs/` after each session to verify changes
6. **Update regularly** - Run `python -m src.updater` to stay current
7. **Use session loop** - Chain related tasks together for efficient remote work

---

## Quick Reference

```
USAGE:
  python claudeghost.py                                # Interactive mode
  python claudeghost.py "<task>" --level 3             # Quick mode
  python claudeghost.py "<task>" --level 3 --budget 5  # With budget
  python claudeghost.py "<task>" --no-telegram         # Screen-only

LEVELS:
  1 = Paranoid   (ask everything)
  2 = Auditor    (auto: read)
  3 = Manager    (auto: read, write)
  4 = Director   (auto: read, write, execute)
  5 = God Mode   (auto: everything)

TELEGRAM REPLIES:
  A = Approve    B = Block
  C <text> = Context    D = Kill

CONFIG:
  python -m src.cli config show
  python -m src.cli config test
  python -m src.cli config set <key> <value>

UPDATE:
  python -m src.updater

CHANGELOGS:
  Saved to session_logs/ after each session
```
