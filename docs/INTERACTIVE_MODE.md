# Interactive Mode Guide

When you run ClaudeGhost without arguments, it launches in interactive mode with step-by-step prompts.

## How to Launch Interactive Mode

```bash
python claudeghost.py
```

Or from anywhere if added to PATH:
```bash
python C:\path\to\ClaudeGhost\claudeghost.py
```

---

## Interactive Prompts

### Step 1: Enter Your Task

```
Step 1: Enter Your Task

Examples:
  - Refactor auth_service.py to use JWT
  - Add unit tests for UserController
  - Fix the bug in payment processing

Task: _
```

**What to enter:** Describe what you want Claude to do in your project.

**Examples:**
- "Add JWT authentication to the API"
- "Fix the payment processing bug in checkout.py"
- "Create a REST API for user management"
- "Refactor the database queries to use async"

---

### Step 2: Select AFK Autonomy Level

```
Step 2: Select AFK Autonomy Level

┏━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Level  ┃ Name       ┃ Description                                         ┃
┡━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1      │ Paranoid   │ Ask for everything (max safety)                     │
│ 2      │ Auditor    │ Auto-approve: read-only commands                    │
│ 3      │ Manager    │ Auto-approve: read + write (recommended)            │
│ 4      │ Director   │ Auto-approve: read + write + execute                │
│ 5      │ God Mode   │ Auto-approve: everything (full autonomy)            │
└────────┴────────────┴─────────────────────────────────────────────────────┘

Select level [1/2/3/4/5] (3): _
```

**What each level means:**

| Level | Name | Auto-Approves | When to Use |
|-------|------|---------------|-------------|
| 1 | Paranoid | Nothing | Security audits, sensitive code |
| 2 | Auditor | Read-only (ls, cat, grep) | Code exploration, analysis |
| 3 | Manager | Read + Write (mkdir, touch, edit files) | Normal development (recommended) |
| 4 | Director | Read + Write + Execute (npm install, pip) | Project setup, scaffolding |
| 5 | God Mode | Everything (including rm, deploy) | Full trust, active monitoring |

**Recommendation:** Start with level 3 for most tasks.

---

### Step 3: Communication Method

```
Step 3: Communication Method

  [1] Telegram - Get approval requests on your phone
  [2] Screen Only - Show prompts in terminal

Select mode [1/2/telegram/screen] (1): _
```

**Options:**

1. **Telegram** (Recommended)
   - Get notifications on your phone
   - Approve/block from anywhere
   - Don't need to watch the terminal
   - Requires Telegram bot setup

2. **Screen Only**
   - Prompts appear in terminal
   - Must watch the terminal window
   - No Telegram setup needed
   - Good for testing

**Recommendation:** Use Telegram for real work, Screen Only for testing.

---

### Step 4: Set Budget Limit (Quota)

```
Step 4: Set Budget Limit (Quota)

┏━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Preset     ┃ Amount   ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━┩
│ Tiny       │ $1.00    │
│ Small      │ $5.00    │
│ Medium     │ $10.00   │
│ Large      │ $20.00   │
│ Unlimited  │ No limit │
│ custom     │ Enter amount │
└────────────┴──────────┘

Select preset or 'custom' [tiny/small/medium/large/unlimited/custom] (medium): _
```

**What this does:** Pauses ClaudeGhost when spending reaches this limit.

**Presets:**
- **Tiny ($1)** - Quick tasks, testing
- **Small ($5)** - Single feature, bug fix
- **Medium ($10)** - Normal development session (recommended)
- **Large ($20)** - Complex refactoring, multiple features
- **Unlimited** - No limit (use with caution)
- **Custom** - Enter your own amount

**Recommendation:** Start with $5-10 for most tasks.

---

### Step 5: Confirmation

```
Session Configuration Summary

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                ┃                                                     ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Task:          │ Add JWT authentication to the API                   │
│ AFK Level:     │ 3 (Manager)                                         │
│ Budget:        │ $10.00                                              │
│ Notifications: │ Telegram                                            │
│ Working Dir:   │ C:\Users\Daniel\Projects\MyApp                      │
└────────────────┴─────────────────────────────────────────────────────┘

Execute task? [Y/n]: _
```

**Review your settings** and confirm:
- Press `Y` or `Enter` to start
- Press `N` to cancel

---

## Complete Example Session

```bash
# 1. Launch
C:\Users\Daniel\Projects\MyApp> python C:\path\to\ClaudeGhost\claudeghost.py

# 2. Enter task
Task: Add user authentication with JWT

# 3. Select level
Select level [1/2/3/4/5] (3): 3

# 4. Select communication
Select mode [1/2/telegram/screen] (1): 1

# 5. Select budget
Select preset or 'custom' (medium): medium

# 6. Confirm
Execute task? [Y/n]: y

# 7. ClaudeGhost starts!
# You'll see the live dashboard and get Telegram notifications
```

---

## Tips

1. **Task Description**
   - Be specific: "Add JWT auth" not just "auth"
   - Include file names if relevant: "Fix bug in payment.py"
   - Mention the goal: "Refactor to improve performance"

2. **AFK Level**
   - Start conservative (level 2-3)
   - Increase as you get comfortable
   - Use level 1 for sensitive operations

3. **Communication**
   - Telegram is much more convenient
   - Screen-only is good for quick tests
   - You can change this in .env later

4. **Budget**
   - Set realistic limits
   - You can always increase mid-session
   - Better to start low and adjust

---

## Quick Mode Alternative

If you already know your settings, skip interactive mode:

```bash
python claudeghost.py "Your task" --level 3 --budget 10.00
```

See [HOW_TO_USE.md](HOW_TO_USE.md) for more details.
