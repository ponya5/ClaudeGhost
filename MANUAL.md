# ClaudeGhost Manual

A step-by-step guide to using ClaudeGhost with the Claude Code CLI.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Setting Up WAHA](#setting-up-waha)
4. [Configuration](#configuration)
5. [Your First Run](#your-first-run)
6. [Understanding the Dashboard](#understanding-the-dashboard)
7. [WhatsApp Commands](#whatsapp-commands)
8. [AFK Levels Explained](#afk-levels-explained)
9. [Real-World Examples](#real-world-examples)
10. [Tips & Best Practices](#tips--best-practices)

---

## Prerequisites

### 1. Claude Code CLI

```bash
# Install the Anthropic Claude CLI
npm install -g @anthropic-ai/claude-code

# Authenticate
claude auth

# Verify
claude --version
```

### 2. Python 3.10+

```bash
python --version  # Should be 3.10 or higher
```

### 3. Docker (for WAHA)

Install from: https://docs.docker.com/get-docker/

---

## Installation

### Option 1: Interactive Setup (Recommended)

```bash
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost
python install.py
```

### Option 2: Manual Setup

```bash
cd ClaudeGhost
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
```

---

## Setting Up WAHA

WAHA provides the WhatsApp API that ClaudeGhost uses for notifications.

### Step 1: Pull Docker Image

```bash
docker pull devlikeapro/waha
```

### Step 2: Initialize WAHA

```bash
docker run --rm -v ".:/app/env" devlikeapro/waha init-waha /app/env
```

This outputs:
```
Credentials generated.
Dashboard: admin / 11111111...
API key: 00000000...
```

**Save the API key!**

### Step 3: Run WAHA

```bash
docker run -it --env-file .env -p 3000:3000 --name waha devlikeapro/waha
```

### Step 4: Link WhatsApp

1. Open http://localhost:3000/dashboard
2. Login with dashboard credentials
3. Start a session named "default"
4. Scan QR code with your WhatsApp app
5. Wait for WORKING status

### Phone Number Format

Your number without `+`, followed by `@c.us`:
- US: `14155551234@c.us`
- UK: `447911123456@c.us`

---

## Configuration

### .env File

```bash
# Copy template
cp .env.example .env
```

Edit `.env`:
```env
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=your-32-char-api-key
WAHA_SESSION=default
TARGET_PHONE=14155551234@c.us
DEFAULT_AFK_LEVEL=3
MAX_BUDGET_USD=10.00
```

### Using the CLI

```bash
# View config
python -m src.cli config show

# Set values
python -m src.cli config set phone 14155551234@c.us
python -m src.cli config set waha-key your-api-key
python -m src.cli config set budget 20.00
python -m src.cli config set level 3

# Test connection
python -m src.cli config test
```

---

## Your First Run

### Basic Syntax

```bash
python -m src.launcher "<task>" --level <1-5>
```

### Example

```bash
python -m src.launcher "Create a Python script that fetches weather data" --level 3
```

What happens:
1. ClaudeGhost spawns Claude CLI with your task
2. Read-only commands auto-approve (level 3)
3. Write commands auto-approve (level 3)
4. Execute commands require WhatsApp approval
5. You get a message, reply A/B/C/D

---

## Understanding the Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│ ClaudeGhost   State: RUNNING  │  Uptime: 2m 34s                │
├─────────────────────────────────┬───────────────────────────────┤
│ Activity Log                    │ Dashboard                     │
│                                 │                               │
│ 14:32:01 Spawning: claude "..." │ Task: Build REST API...       │
│ 14:32:03 Guardian: Read-Only    │ AFK Level: 3 (Manager)        │
│ 14:32:05 Auto-approved: ls -la  │ Budget: $0.12 / $10.00        │
│ 14:32:07 Guardian: Write        │ Approved: 5                   │
│ 14:32:07 Auto-approved: mkdir   │ Blocked: 0                    │
│ 14:32:10 Guardian: Execute      │                               │
│ 14:32:10 Waiting for WhatsApp.. │ Last WAHA: -                  │
├─────────────────────────────────┴───────────────────────────────┤
│ [A]pprove  [B]lock  [C]ontext  [D]etonate  │ Ctrl+C to exit    │
└─────────────────────────────────────────────────────────────────┘
```

### States

| State | Meaning |
|-------|---------|
| STARTING | Initializing |
| RUNNING | Processing |
| THINKING | Claude generating |
| QUERY | Waiting for decision |
| WAITING | Awaiting WhatsApp reply |
| BUDGET_PAUSE | Budget exceeded |
| EXITED | Done |

---

## WhatsApp Commands

When approval needed, you receive:

```
Approval Needed
Command: npm install express
Risk: Execute

Reply:
[A] Approve
[B] Block
[C] Context
[D] Detonate
```

### Replies

| Reply | Action |
|-------|--------|
| `A` | Approve, continue |
| `B` | Block, skip |
| `C Use yarn instead` | Send instruction |
| `D` | Kill process |

---

## AFK Levels Explained

### Level 1: Paranoid
```bash
python -m src.launcher "Review security of auth.py" --level 1
```
- Asks for EVERYTHING
- Use for: Security audits, sensitive work

### Level 2: Auditor
```bash
python -m src.launcher "Analyze the codebase" --level 2
```
- Auto: Read operations
- Use for: Code exploration

### Level 3: Manager (Default)
```bash
python -m src.launcher "Add input validation" --level 3
```
- Auto: Read + Write
- Use for: Normal development

### Level 4: Director
```bash
python -m src.launcher "Set up new React project" --level 4
```
- Auto: Read + Write + Execute
- Use for: Scaffolding, routine tasks

### Level 5: God Mode
```bash
python -m src.launcher "Deploy the application" --level 5
```
- Auto: Everything
- Use for: Full trust, active monitoring

---

## Real-World Examples

### Building a Feature

```bash
python -m src.launcher "Add JWT authentication to the Express app" --level 3
```

Flow:
1. Claude reads code (auto)
2. Creates files (auto)
3. `npm install jsonwebtoken` (WhatsApp)
4. Reply `A`

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

### 1. Start Low, Go High
Begin level 2-3, increase once comfortable.

### 2. Set Budgets
```env
MAX_BUDGET_USD=5.00   # Experimental
MAX_BUDGET_USD=20.00  # Production
```

### 3. Use Context Injection
Instead of blocking:
```
C Use axios instead of fetch
```

### 4. Emergency Stop
- Reply `D` on WhatsApp
- Or `Ctrl+C` in terminal

---

## Quick Reference

```
USAGE:
  python -m src.launcher "<task>" [--level 1-5]

LEVELS:
  1 = Paranoid   (ask everything)
  2 = Auditor    (auto: read)
  3 = Manager    (auto: read, write)
  4 = Director   (auto: read, write, execute)
  5 = God Mode   (auto: everything)

WHATSAPP:
  A = Approve
  B = Block
  C <text> = Context
  D = Kill

CONFIG CLI:
  python -m src.cli config show
  python -m src.cli config set <key> <value>
  python -m src.cli config test
```

---

Happy automating!
