# How to Use ClaudeGhost

## Important: ClaudeGhost Cannot Run Inside Claude Code

ClaudeGhost **supervises** Claude Code sessions - it cannot run inside an existing Claude Code session.

```
❌ Wrong: Claude Code → ClaudeGhost → Claude Code (nested, won't work)
✅ Correct: You → ClaudeGhost → Claude Code → Your Project
```

---

## Quick Start Guide

### Step 1: Open a Regular Terminal

**NOT inside Cursor/Claude Code!** Open one of these:
- Command Prompt (Win + R, type `cmd`)
- PowerShell
- Windows Terminal

### Step 2: Navigate to Your Project

```bash
cd C:\Users\YourName\YourProject
```

### Step 3: Run ClaudeGhost

**Option A: Interactive Mode (Recommended)**
```bash
python C:\path\to\ClaudeGhost\claudeghost.py
```

Follow the prompts to:
1. Select AFK level (1-5)
2. Set budget limit
3. Choose Telegram notifications
4. Enter your task

**Option B: Quick Mode (One Command)**
```bash
python C:\path\to\ClaudeGhost\claudeghost.py "Your task here" --level 3 --budget 10.00
```

**Option C: Using Batch File**
```bash
C:\path\to\ClaudeGhost\launch_claudeghost.bat "Your task" 3 10.00
```

---

## Installation for Easy Access

### Option 1: Add to PATH (Recommended)

1. Copy the ClaudeGhost directory path:
   ```
   C:\Users\Daniel\CursorRepo\Test\ClaudeGhost
   ```

2. Add to Windows PATH:
   - Press `Win + X` → System
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Under "User variables", select "Path"
   - Click "Edit" → "New"
   - Paste the ClaudeGhost path
   - Click OK

3. Now you can run from anywhere:
   ```bash
   cd C:\YourProject
   launch_claudeghost.bat "Your task" 3 10.00
   ```

### Option 2: Global Python Installation

```bash
cd C:\path\to\ClaudeGhost
pip install -e .
```

Now run from anywhere:
```bash
cd C:\YourProject
claudeghost "Your task" --level 3 --budget 10.00
```

---

## What Happens When You Run ClaudeGhost

1. **ClaudeGhost starts** in your project directory
2. **Spawns Claude Code CLI** with your task
3. **Monitors commands** Claude wants to execute
4. **Auto-approves safe commands** based on your AFK level
5. **Sends Telegram notifications** for risky commands
6. **You approve/block** via Telegram on your phone
7. **Task completes** and you get a summary

---

## Telegram Approval Commands

When you receive a notification on Telegram, reply with:

| Reply | Action |
|-------|--------|
| `A` | Approve the command |
| `B` | Block the command |
| `C <text>` | Send alternative instruction to Claude |
| `D` | Kill the entire process |

---

## Example Workflow

```bash
# 1. Open Command Prompt (NOT in Cursor)
Win + R → cmd

# 2. Go to your project
cd C:\Users\Daniel\Projects\MyWebApp

# 3. Run ClaudeGhost
python C:\Users\Daniel\CursorRepo\Test\ClaudeGhost\claudeghost.py "Add user authentication" --level 3 --budget 10.00

# 4. ClaudeGhost starts Claude Code
# 5. You get Telegram notifications for approvals
# 6. Reply A/B/C/D on your phone
# 7. Task completes!
```

---

## Troubleshooting

### "Cannot run inside Claude Code session"
- Close Cursor/Claude Code
- Open a regular Command Prompt or PowerShell
- Run ClaudeGhost from there

### "claude: command not found"
- Install Claude Code CLI:
  ```bash
  npm install -g @anthropic-ai/claude-code
  claude auth
  ```

### "Telegram connection failed"
- Check your `.env` file has correct token and chat_id
- Run: `python -m src.cli config test`

### "Module not found"
- Install dependencies:
  ```bash
  cd C:\path\to\ClaudeGhost
  pip install -r requirements.txt
  ```

---

## Tips

1. **Start with level 3** - Good balance of autonomy and safety
2. **Set a budget** - Prevents runaway costs
3. **Use Telegram** - Much easier than watching the terminal
4. **Test first** - Try a simple task to get familiar
5. **Keep terminal open** - You can see the live dashboard

---

## Need Help?

- Full manual: [MANUAL.md](../MANUAL.md)
- Telegram setup: [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md)
- Installation: [INSTALL.md](INSTALL.md)
