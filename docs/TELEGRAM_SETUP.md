# Telegram Bot Setup Guide

## Why Telegram?

- **5-minute setup** - just talk to @BotFather
- **Free & unlimited** - no message limits
- **Official API** - no third-party dependencies
- **Instant delivery** - real-time notifications
- **Cross-platform** - works on phone, desktop, web

---

## Step 1: Create Your Bot (2 minutes)

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a display name (e.g., `ClaudeGhost Bot`)
4. Choose a username (e.g., `my_claudeghost_bot`)
5. BotFather replies with your **bot token**:
   ```
   Use this token to access the HTTP API:
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
6. **Copy the token** - you'll need it for `.env`

---

## Step 2: Get Your Chat ID (2 minutes)

1. Open your new bot in Telegram and send it any message (e.g., "hello")
2. Open this URL in your browser (replace `<TOKEN>` with your bot token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Find `"chat":{"id":123456789}` in the response
4. **Copy the chat ID number**

Example response:
```json
{
  "result": [{
    "message": {
      "chat": {
        "id": 123456789
      }
    }
  }]
}
```

---

## Step 3: Configure ClaudeGhost (1 minute)

### Option A: Setup Wizard (recommended)
```bash
python setup_interactive.py
```

### Option B: Manual
```bash
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
TELEGRAM_ENABLED=true
```

### Option C: CLI
```bash
python -m src.cli config set bot-token 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
python -m src.cli config set chat-id 123456789
```

---

## Step 4: Test Connection

```bash
python -m src.cli config test
```

Expected output:
```
Testing Telegram Bot connection...
  Token: ****jklMNOpqrsTUVwxyz
  Chat ID: 123456789

OK Telegram Bot connected
Send test message? [y/N]: y
OK Test message sent
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Bot auth failed" | Double-check your bot token |
| "Send failed" | Make sure you messaged the bot first |
| No chat ID in getUpdates | Send a message to the bot, then refresh |
| Empty getUpdates response | Wait a moment and try again |

---

## Done!

Run ClaudeGhost:
```bash
python -m src.launcher "your task here" --level 3
```

You'll receive Telegram notifications when approval is needed.
Reply with: **A** (approve), **B** (block), **C text** (context), **D** (kill).
