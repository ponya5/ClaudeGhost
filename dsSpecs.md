# 👻 Product Requirements Document (PRD): ClaudeGhost

**Version:** 1.0  
**Date:** 2026-02-12  
**Target System:** Python 3.10+ (Dockerized or Local Venv)  
**Integration Target:** Anthropic claude CLI

## 1. Executive Summary

ClaudeGhost (CG) is a "Headless Supervisor" wrapper for the Anthropic claude CLI. It allows developers to execute autonomous coding tasks while away from the keyboard (AFK) by bridging the CLI's decision requests to a WhatsApp interface.

Unlike a standard script, CG wraps the claude process in a pseudo-terminal (PTY), interprets its TUI (Text User Interface) state in real-time, and governs execution based on a user-defined Autonomy Matrix.

## 2. Core User Flow

1. **Initiation:** User opens their terminal (in VS Code, Cursor, or Kiro) and runs:
   ```bash
   python main.py "Refactor the auth_service.py to use JWT" --level 3
   ```

2. **Execution:** CG spawns the claude CLI in a hidden process.

3. **Interception:**
   - If claude wants to run `ls -la`, CG auto-approves (Level 3 allows read-only).
   - If claude wants to run `rm -rf ./db`, CG detects a high-risk action.

4. **Notification:** CG pauses claude and sends a WhatsApp message via WAHA:
   ```
   🤖 Approval Needed
   Command: rm -rf ./db
   Risk: 🔴 Critical
   Reply: A (Approve), B (Block), C (Context)
   ```

5. **Resolution:** User replies "A" from their phone. CG injects "y" into the hidden claude process.

6. **Completion:** Task finishes. CG sends a summary report to WhatsApp.

## 3. Functional Requirements

### 3.1 The "Ghost Bridge" (Terminal Wrapper)

**Requirement:** Must wrap the claude binary using a PTY (Pseudo-Terminal) to preserve TUI features (colors, spinners) while allowing programmatic I/O.

- **Library:** pexpect (Linux/macOS/WSL) or weexpect (Windows native). Strong recommendation: Run in WSL or Docker to use standard pexpect.
- **ANSI Stripping:** The bridge must implement a regex-based AnsiCleaner to strip color codes (e.g., `\x1b[32m`) from stdout before text analysis.
- **State Detection:**
  - IDLE: Detects `> ` (Ready for input).
  - QUERY: Detects `Do you want to run this command?` or `(y/n)`.
  - THINKING: Detects active spinner or lack of prompt (silence).

### 3.2 The "Guardian" (Autonomy Engine)

The system must enforce the following AFK Levels:

| Level | Name      | Read-Only (ls, cat) | Write (edit, mv) | Execute (npm, python) | High Risk (rm, git push) |
|-------|-----------|---------------------|------------------|-----------------------|--------------------------|
| 1     | Paranoid  | ✋ Ask               | ✋ Ask            | ✋ Ask                 | ✋ Ask                    |
| 2     | Auditor   | ✅ Auto             | ✋ Ask            | ✋ Ask                 | ✋ Ask                    |
| 3     | Manager   | ✅ Auto             | ✅ Auto          | ✋ Ask                 | ✋ Ask                    |
| 4     | Director  | ✅ Auto             | ✅ Auto          | ✅ Auto               | ✋ Ask                    |
| 5     | God Mode  | ✅ Auto             | ✅ Auto          | ✅ Auto               | ✅ Auto (Notify Only)    |

### 3.3 The "Medium" (WhatsApp Interface)

- **Integration:** Connect to a local WAHA (WhatsApp HTTP API) instance.
- **Endpoint:** POST `http://localhost:3000/api/sendText`
- **Polling Loop:** Since no public webhook is available, CG must poll `GET http://localhost:3000/api/messages` every 3 seconds while in a "Wait State."
- **Message Menu:**
  - [A] Approve: Injects `y` + Enter.
  - [B] Block: Injects `n` + Enter.
  - [C] Context: User replies with text (e.g., "Don't delete that, use archive instead"). CG injects this text into the CLI.
  - [D] Detonate: Kills the process immediately.

## 4. Technical Specifications

### 4.1 System Architecture

```
graph TD
User((User on WhatsApp)) <-->|HTTP/Polling| WAHA[WAHA Local Server]
WAHA <-->|JSON| CG[ClaudeGhost Core]
subgraph "ClaudeGhost Internals"
    CG -->|Spawns| PTY[PTY Wrapper]
    PTY -->|Stdin/Stdout| CLI[Claude Code CLI]
    CG -->|Enforces| Policy[Autonomy Matrix]
end
CLI -->|File Ops| FileSystem
```

### 4.2 Configuration (config.py)

Must support .env loading:

```ini
WAHA_API_URL=http://localhost:3000
TARGET_PHONE=1234567890@c.us
DEFAULT_AFK_LEVEL=3
MAX_BUDGET_USD=5.00
```

### 4.3 Directory Structure

```
/claude_ghost
├── /src
│   ├── bridge.py       # Pexpect logic & ANSI cleaning
│   ├── guardian.py     # Autonomy logic & decision tree
│   ├── waha.py         # WhatsApp API client & Polling
│   ├── utils.py        # Logging & Rich UI helpers
│   └── main.py         # Entry point
├── .env.example
├── requirements.txt    # pexpect, requests, rich, pydantic
└── Dockerfile          # Optional: For consistent PTY environment
```

## 5. Development Guidelines (Prompt for AI)

### Critical Implementation Details

1. **Regex Resilience:** The claude CLI is chatty. You must match partial prompts.
   - Target: `(?i)do you want to (run|create|edit)`

2. **Budget Watchdog:** Parse the stdout for `Cost: $0.15`. Maintain a running total. If `current_cost > max_budget`, trigger a critical pause regardless of AFK Level.

3. **Keep-Alive:** The claude CLI might hang. Implement a 60-second "heartbeat" check. If no output is received for 60s during a "thinking" phase, send a "Stalled?" warning to WhatsApp.

### "Vibe" & Code Style

- **Language:** Python 3.11+
- **Type Hinting:** Strict (from typing import Optional, List).
- **Logging:** Use rich.console to create a beautiful split-screen TUI.
  - Left Panel: Live generic logs.
  - Right Panel: Ghost Status (Current Task, Budget, Last WAHA Msg).

## 6. Deployment Context (Cursor / Kiro)

**Note to Developer:**

Even though the user executes this inside Cursor or Kiro, ClaudeGhost replaces the direct invocation of claude.

- **Incorrect:** Running `claude` in Cursor terminal.
- **Correct:** Opening Cursor terminal and running `python -m src.main "Build a reacting landing page" --level 3`.

ClaudeGhost becomes the "operator" of the terminal session. Cursor/Kiro simply acts as the window hosting the Python process.
