# ClaudeGhost

**Headless Supervisor for the Anthropic Claude CLI** - Run Claude Code autonomously while staying in control via WhatsApp.

ClaudeGhost wraps the `claude` CLI in a supervised shell, automatically approving safe operations based on your configured autonomy level while escalating risky commands to your phone for approval.

---

## Features

- **AFK Autonomy Levels (1-5)**: From paranoid (asks everything) to god mode (full auto)
- **WhatsApp Integration**: Approve/block commands from your phone via WAHA
- **Risk Classification**: Commands categorized as Read-Only, Write, Execute, or Critical
- **Budget Control**: Set spending limits with automatic pause on exceed
- **Live Dashboard**: Rich terminal UI showing real-time status and logs
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Stall Detection**: Alerts you when the CLI hangs

---

## Requirements

- Python 3.10+
- [Anthropic Claude CLI](https://docs.anthropic.com/claude-code/getting-started) installed and authenticated
- [WAHA](https://github.com/devlikeapro/waha) (WhatsApp HTTP API) running locally or remotely
- WhatsApp account linked to WAHA

---

## Installation

### Quick Start

```bash
git clone https://github.com/yourusername/ClaudeGhost.git
cd ClaudeGhost
python install.py
```

### Manual Install

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your settings
```

---

## Configuration

### Environment Variables (.env)

```env
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=your-api-key-from-waha
WAHA_SESSION=default
TARGET_PHONE=14155551234@c.us
DEFAULT_AFK_LEVEL=3
MAX_BUDGET_USD=10.00
```

### Config Management CLI

```bash
# Show current config
python -m src.cli config show

# Set values
python -m src.cli config set phone 14155551234@c.us
python -m src.cli config set waha-key abc123...

# Test WAHA connection
python -m src.cli config test
```

---

## Usage

### Basic Command

```bash
python -m src.launcher "Build a REST API with FastAPI" --level 3
```

### AFK Autonomy Levels

| Level | Name | Read-Only | Write | Execute | Critical |
|-------|------|-----------|-------|---------|----------|
| 1 | Paranoid | Ask | Ask | Ask | Ask |
| 2 | Auditor | Auto | Ask | Ask | Ask |
| 3 | Manager | Auto | Auto | Ask | Ask |
| 4 | Director | Auto | Auto | Auto | Ask |
| 5 | God Mode | Auto | Auto | Auto | Auto |

### WhatsApp Commands

When ClaudeGhost needs approval, reply with:

| Command | Action |
|---------|--------|
| `A` | Approve the pending action |
| `B` | Block/reject the action |
| `C <text>` | Inject custom context/instruction |
| `D` | Kill the entire process immediately |

---

## WAHA Setup

1. Pull WAHA Docker image:
   ```bash
   docker pull devlikeapro/waha
   ```

2. Initialize (generates API key):
   ```bash
   docker run --rm -v ".:/app/env" devlikeapro/waha init-waha /app/env
   ```

3. Run WAHA:
   ```bash
   docker run -it --env-file .env -p 3000:3000 --name waha devlikeapro/waha
   ```

4. Open http://localhost:3000/dashboard and link WhatsApp

See [WAHA Quick Start](https://waha.devlike.pro/docs/overview/quick-start/) for details.

---

## Project Structure

```
ClaudeGhost/
├── src/
│   ├── main.py           # ClaudeGhost orchestrator
│   ├── bridge.py         # PTY wrapper for claude CLI
│   ├── guardian.py       # Risk evaluation & classification
│   ├── waha.py           # WhatsApp HTTP client
│   ├── config.py         # Settings management
│   ├── utils.py          # Logger, dashboard UI
│   ├── launcher.py       # CLI entry point
│   └── cli.py            # Config management CLI
├── .env.example
├── config.yaml
├── requirements.txt
├── install.py
├── README.md
└── MANUAL.md
```

---

## Security

- **Never commit `.env`** - it contains your API keys
- ClaudeGhost runs with your shell permissions
- Critical commands require approval unless Level 5
- Budget limits prevent runaway API costs

---

## License

MIT License
