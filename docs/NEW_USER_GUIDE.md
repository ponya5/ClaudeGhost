# New User Quick Start

Welcome! This guide will get you running ClaudeGhost in 5 minutes.

## What is ClaudeGhost?

ClaudeGhost supervises the Claude Code CLI, letting it work autonomously while you approve risky commands from your phone via Telegram.

## Installation (5 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost
pip install -r requirements.txt
```

### 2. Setup Telegram Bot (2 minutes)

```bash
python setup_interactive.py
```

The wizard will:
- Guide you to create a bot via @BotFather
- Help you get your chat ID
- Test the connection
- Configure autonomy level

### 3. Run Your First Task

```bash
python -m src.launcher "Create a hello.txt file" --level 3
```

You'll get a Telegram notification when approval is needed!

## What Happens Next?

1. ClaudeGhost starts Claude Code with your task
2. Safe commands (read, write) auto-approve at level 3
3. Risky commands (execute, install) → Telegram notification
4. You reply `A` (approve) or `B` (block) on your phone
5. Task completes, you get a summary

## Autonomy Levels

- Level 1: Asks for everything (paranoid)
- Level 2: Auto-approves reads only
- Level 3: Auto-approves reads + writes (recommended)
- Level 4: Auto-approves reads + writes + execute
- Level 5: Auto-approves everything (god mode)

## Common Commands

```bash
# Interactive mode
python -m src.launcher

# Quick mode with level
python -m src.launcher "your task" --level 3

# Set budget limit
python -m src.launcher "your task" --level 3 --budget 5.00

# Test Telegram connection
python -m src.cli config test

# View configuration
python -m src.cli config show
```

## Need Help?

- Full manual: [MANUAL.md](../MANUAL.md)
- Installation guide: [INSTALL.md](INSTALL.md)
- Telegram setup: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)

## Tips

1. Start with level 3 for normal development
2. Use level 2 for code exploration (read-only)
3. Set a budget to avoid surprises: `--budget 10.00`
4. Reply `C <text>` on Telegram to give alternative instructions
5. Reply `D` to kill the process immediately

That's it! You're ready to use ClaudeGhost.
