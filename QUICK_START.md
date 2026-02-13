# ClaudeGhost Quick Start

## 3-Step Installation

```bash
# 1. Clone
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost

# 2. Install
pip install -r requirements.txt

# 3. Setup
python setup_interactive.py
```

---

## Usage (From Your Project Directory)

### Interactive Mode
```bash
python C:\path\to\ClaudeGhost\claudeghost.py
```

### Quick Mode
```bash
python C:\path\to\ClaudeGhost\claudeghost.py "Your task here" --level 3 --budget 10.00
```

### Examples
```bash
# Add authentication
python claudeghost.py "Add JWT authentication to the API" --level 3

# Fix a bug
python claudeghost.py "Fix the payment processing bug" --level 4 --budget 5.00

# Code review (read-only)
python claudeghost.py "Review the security of auth.py" --level 2

# Screen-only mode (no Telegram)
python claudeghost.py "Analyze the codebase" --no-telegram
```

---

## AFK Levels

| Level | Name | Auto-Approves |
|-------|------|---------------|
| 1 | Paranoid | Nothing |
| 2 | Auditor | Read-only |
| 3 | Manager | Read + Write ⭐ |
| 4 | Director | Read + Write + Execute |
| 5 | God Mode | Everything |

---

## Telegram Commands

Reply to notifications with:
- `A` = Approve
- `B` = Block
- `C <text>` = Send custom instruction
- `D` = Kill process

---

## Help

```bash
python claudeghost.py --help
```

Full docs: [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)
