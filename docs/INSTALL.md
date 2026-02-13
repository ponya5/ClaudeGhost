# ClaudeGhost Installation Guide

## For New Users - Quick Install (5 minutes)

### Prerequisites
- Python 3.10 or higher
- Claude Code CLI installed and authenticated
- Telegram account

### Step 1: Install ClaudeGhost

```bash
# Clone the repository
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost

# Install dependencies
pip install -r requirements.txt
```

> Replace `yourusername` with your actual GitHub username after pushing to GitHub.

### Step 2: Setup Telegram Bot (2 minutes)

Run the interactive setup wizard:
```bash
python setup_interactive.py
```

The wizard will guide you through:
1. Creating a Telegram bot via @BotFather
2. Getting your chat ID
3. Configuring autonomy level and budget
4. Testing the connection

**Or manually:**
1. Open Telegram, search for `@BotFather`
2. Send `/newbot` and follow prompts
3. Copy your bot token
4. Message your bot, then visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. Copy your chat ID from the response
6. Configure:
   ```bash
   cp .env.example .env
   # Edit .env with your token and chat_id
   ```

### Step 3: Test Installation

```bash
python -m src.cli config test
```

You should see:
```
OK Telegram Bot connected
Send test message? [y/N]: y
OK Test message sent
```

### Step 4: Run Your First Task

```bash
python -m src.launcher "Create a hello.txt file" --level 3
```

You'll receive Telegram notifications when approval is needed!

---

## Installation as a Global Command (Optional)

If you want to run `claudeghost` from anywhere:

```bash
# Install in development mode
pip install -e .

# Now you can run from anywhere:
claudeghost "your task" --level 3
```

---

## Installation from PyPI (Future)

Once published to PyPI, users will be able to install with:
```bash
pip install claudeghost
claudeghost --setup
```

**Note:** Not yet published to PyPI. Use git clone method above.

---

## Using with Claude Code

ClaudeGhost is designed to wrap the Claude Code CLI. Make sure you have it installed:

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth

# Verify
claude --version
```

Then run ClaudeGhost to supervise Claude Code sessions:
```bash
python -m src.launcher "your coding task" --level 3
```

---

## Troubleshooting

### "claude: command not found"
Install Claude Code CLI:
```bash
npm install -g @anthropic-ai/claude-code
claude auth
```

### "Telegram Bot connection failed"
1. Verify your bot token is correct
2. Make sure you messaged the bot first
3. Check your chat ID is correct
4. Run: `python -m src.cli config test`

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### Tests failing
```bash
python tests/run_all_tests.py
```

---

## Uninstall

```bash
# If installed with pip install -e .
pip uninstall claudeghost

# Remove the directory
cd ..
rm -rf ClaudeGhost
```

---

## Next Steps

- Read [MANUAL.md](../MANUAL.md) for detailed usage
- See [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) for Telegram setup details
- Check [NEW_USER_GUIDE.md](NEW_USER_GUIDE.md) for quick reference
