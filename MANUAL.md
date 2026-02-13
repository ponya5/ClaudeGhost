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
9. [Real-World Examples](#real-world-examples)
10. [Tips & Best Practices](#tips--best-practices)

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
python -m src.launcher "Create a Python script that fetches weather data" --level 3
```

What happens:
1. ClaudeGhost spawns Claude CLI with your task
2. Read-only commands auto-approve (level 3)
3. Write commands auto-approve (level 3)
4. Execute commands -> Telegram notification
5. You reply A/B/C/D on Telegram

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

## Real-World Examples

### Building a Feature
```bash
python -m src.launcher "Add JWT authentication to the Express app" --level 3
```

### Debugging
```bash
python -m src.launcher "Fix failing tests in tests/unit/" --level 2
```

### Full Autonomy
```bash
python -m src.launcher "Create FastAPI project with Docker" --level 5
```

---

## Tips & Best Practices

1. **Start low, go high** - Begin at level 2-3, increase once comfortable
2. **Set budgets** - `MAX_BUDGET_USD=5.00` for experiments, `20.00` for production
3. **Use context injection** - Reply `C Use axios instead of fetch` instead of blocking
4. **Emergency stop** - Reply `D` on Telegram or `Ctrl+C` in terminal

---

## Quick Reference

```
USAGE:
  python -m src.launcher "<task>" [--level 1-5] [--budget USD]

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
```
