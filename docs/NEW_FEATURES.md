# New Features in ClaudeGhost v2.0

## 1. Session Loop - Continue Working Remotely

After each session completes, ClaudeGhost asks if you want to start another session. Perfect for remote work!

### How It Works

```
Session 1 Complete
  ↓
"Start another session?" [y/N]
  ↓
Yes → Interactive launcher → Session 2
  ↓
Session 2 Complete
  ↓
"Start another session?" [y/N]
  ↓
No → Exit
```

### Example

```bash
# Start ClaudeGhost
python claudeghost.py "Add authentication"

# Session runs...
# Session completes

Start another session? [y/N]: y

# Interactive launcher appears
Step 1: Enter Your Task
Task: Fix the payment bug

# Session 2 runs...
# Session 2 completes

Start another session? [y/N]: n
Goodbye!
```

### Benefits

- **Remote Work**: Start multiple tasks without being at your computer
- **Batch Processing**: Queue up multiple tasks in one go
- **Continuous Development**: Keep Claude working while you're away

---

## 2. Changelog Tracking - See What Changed

Every session automatically creates a detailed changelog showing exactly what was done.

### What's Tracked

- **Files Modified**: List of all files that were changed
- **Commands Executed**: Every command that was run
- **Session Details**: Duration, task, timestamps

### Changelog Format

```
======================================================================
ClaudeGhost Session Changelog
======================================================================

Session ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Task: Add JWT authentication to the API
Started: 2026-02-13 14:30:15
Ended: 2026-02-13 14:45:22
Duration: 15m 7s

----------------------------------------------------------------------
Files Modified (5)
----------------------------------------------------------------------
  • src/auth/jwt.py
  • src/middleware/auth_middleware.py
  • src/routes/auth_routes.py
  • tests/test_auth.py
  • requirements.txt

----------------------------------------------------------------------
Commands Executed (12)
----------------------------------------------------------------------
  1. mkdir src/auth
  2. touch src/auth/jwt.py
  3. npm install jsonwebtoken
  4. cat src/middleware/auth_middleware.py
  5. vim src/auth/jwt.py
  ...

======================================================================
End of Changelog
======================================================================
```

### Where Changelogs Are Saved

```
ClaudeGhost/
└── session_logs/
    ├── session_20260213_143015_a1b2c3d4.txt
    ├── session_20260213_150122_b2c3d4e5.txt
    └── session_20260213_162045_c3d4e5f6.txt
```

### Telegram Notification

At the end of each session, you receive:

```
📝 Session Complete
Files modified: 5
Commands executed: 12

📄 Full changelog: C:\...\session_logs\session_20260213_143015_a1b2c3d4.txt
```

The full changelog is saved to a file (not sent via Telegram to avoid long messages).

### Benefits

- **Audit Trail**: Know exactly what Claude did
- **Documentation**: Automatic record of changes
- **Review**: Check what happened while you were away
- **Debugging**: Trace issues back to specific commands

---

## 3. Auto-Update Checker - Stay Current

ClaudeGhost automatically checks for updates when you start it.

### How It Works

When you launch ClaudeGhost, it checks GitHub for the latest version:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Update Available!                                      │
│                                                         │
│  Current version: 2.0.0                                 │
│  Latest version: 2.1.0                                  │
│                                                         │
│  Run: python -m src.updater to update                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Manual Update Check

```bash
python -m src.updater
```

Output:
```
Checking for updates...

Update available: 2.0.0 → 2.1.0

Update now? [Y/n]: y

Updating ClaudeGhost...
✓ Update successful!

Please restart ClaudeGhost.
```

### What Gets Updated

1. **Code**: Pulls latest from GitHub (`git pull origin main`)
2. **Dependencies**: Updates Python packages (`pip install -r requirements.txt`)

### Requirements

- ClaudeGhost must be cloned from GitHub (not downloaded as ZIP)
- Git must be installed
- Internet connection required

### Manual Update (Alternative)

```bash
cd ClaudeGhost
git pull origin main
pip install -r requirements.txt
```

### Benefits

- **Security**: Get security patches quickly
- **Features**: Access new features as they're released
- **Bug Fixes**: Automatic bug fixes
- **Convenience**: One command to update

---

## Usage Examples

### Example 1: Remote Work Session

```bash
# Morning: Start first task
python claudeghost.py "Implement user registration"

# Session completes, you get Telegram notification
# Changelog saved to session_logs/

Start another session? [y/N]: y

# Add another task
Task: Add email verification

# Session completes
# Another changelog saved

Start another session? [y/N]: y

# One more task
Task: Write unit tests for auth

# All done
Start another session? [y/N]: n
Goodbye!

# Check what was done
ls session_logs/
# session_20260213_090000_abc123.txt
# session_20260213_093000_def456.txt
# session_20260213_100000_ghi789.txt
```

### Example 2: Review Changelogs

```bash
# Open the latest changelog
notepad session_logs\session_20260213_100000_ghi789.txt

# Or view all changelogs
dir session_logs
```

### Example 3: Update ClaudeGhost

```bash
# Check for updates
python -m src.updater

# If update available, it will prompt you
Update now? [Y/n]: y

# Restart ClaudeGhost
python claudeghost.py
```

---

## Configuration

### Disable Update Checks

If you don't want automatic update checks, you can modify `src/main.py`:

```python
# Comment out these lines:
# update_available, latest_version = check_for_updates()
# if update_available and latest_version:
#     print_update_notification(latest_version)
```

### Change Changelog Directory

Edit `src/changelog.py`:

```python
def save(self, output_dir: str = "my_custom_logs") -> str:
```

---

## Tips

1. **Review Changelogs**: Check changelogs after each session to verify changes
2. **Keep Logs**: Don't delete session_logs/ - they're your audit trail
3. **Update Regularly**: Run `python -m src.updater` weekly
4. **Session Loop**: Use for batch processing multiple related tasks
5. **Telegram**: Changelogs are linked in Telegram, not sent in full

---

## Troubleshooting

### Changelog Not Saved

- Check that `session_logs/` directory exists
- Verify write permissions
- Check logs for errors

### Update Failed

- Ensure you cloned from GitHub (not downloaded ZIP)
- Check internet connection
- Verify git is installed: `git --version`
- Manual update: `git pull origin main`

### Session Loop Not Working

- Press `Ctrl+C` to exit if stuck
- Check terminal for errors
- Restart ClaudeGhost

---

## See Also

- [HOW_TO_USE.md](HOW_TO_USE.md) - Basic usage guide
- [INTERACTIVE_MODE.md](INTERACTIVE_MODE.md) - Interactive launcher guide
- [MANUAL.md](../MANUAL.md) - Complete manual
