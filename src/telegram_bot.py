"""Telegram Bot API integration for ClaudeGhost.

Uses the official Telegram Bot API for sending notifications
and receiving approval responses. No rate limits, free, instant.

Docs: https://core.telegram.org/bots/api
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import requests

from src.config import settings
from src.utils import logger, ghost_status

_BASE_URL = "https://api.telegram.org/bot"


class TelegramBot:
    """Official Telegram Bot API client.

    Setup:
        1. Message @BotFather on Telegram -> /newbot
        2. Copy the bot token
        3. Message your bot, then get your chat_id
        4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
    """

    def __init__(self) -> None:
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        self._api = f"{_BASE_URL}{self._token}"
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None
        self._reply_callback: Optional[Callable[[str], None]] = None
        self._last_update_id = 0
        self._connected = False

    @property
    def token(self) -> str:
        """Get bot token."""
        return self._token

    @property
    def chat_id(self) -> str:
        """Get chat ID."""
        return self._chat_id

    def check_connection(self) -> bool:
        """Verify bot token is valid via getMe."""
        try:
            r = requests.get(
                f"{self._api}/getMe", timeout=10
            )
            data = r.json()
            if data.get("ok"):
                bot_name = data["result"].get("username", "unknown")
                self._connected = True
                logger.info("Telegram bot connected: @%s", bot_name)
                ghost_status.add_log(
                    f"[green]Telegram connected: @{bot_name}[/green]"
                )
                return True
            logger.error("Telegram auth failed: %s", data)
            return False
        except requests.RequestException as exc:
            logger.error("Telegram connection failed: %s", exc)
            ghost_status.add_log("[red]Telegram connection failed[/red]")
            return False

    def send(self, text: str) -> bool:
        """Send a Telegram message to the configured chat."""
        try:
            r = requests.post(
                f"{self._api}/sendMessage",
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            data = r.json()
            if data.get("ok"):
                logger.info("Telegram >>> %s", text[:80])
                ghost_status.add_log(
                    f"[green]Telegram >>>[/green] {text[:60]}"
                )
                return True
            logger.error("Telegram send failed: %s", data)
            ghost_status.add_log("[red]Telegram send error[/red]")
            return False
        except requests.RequestException as exc:
            logger.error("Telegram send failed: %s", exc)
            ghost_status.add_log("[red]Telegram send error[/red]")
            return False

    def send_file(self, file_path: str, caption: str = "") -> bool:
        """Send a file as a Telegram document attachment."""
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            logger.error(
                "File not found for upload: %s", file_path
            )
            return False

        try:
            with open(path, "rb") as f:
                r = requests.post(
                    f"{self._api}/sendDocument",
                    data={
                        "chat_id": self._chat_id,
                        "caption": caption[:1024],
                        "parse_mode": "HTML",
                    },
                    files={"document": (path.name, f)},
                    timeout=30,
                )
            data = r.json()
            if data.get("ok"):
                logger.info(
                    "Telegram file >>> %s", path.name
                )
                ghost_status.add_log(
                    f"[green]Telegram file >>>[/green] "
                    f"{path.name}"
                )
                return True
            logger.error(
                "Telegram file send failed: %s", data
            )
            return False
        except requests.RequestException as exc:
            logger.error(
                "Telegram file send failed: %s", exc
            )
            return False

    def start_polling(self, callback: Callable[[str], None]) -> None:
        """Start long-polling for incoming messages."""
        self._reply_callback = callback
        self._polling = True
        self.check_connection()
        self._flush_old_updates()
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True
        )
        self._poll_thread.start()
        logger.info("Telegram polling started")
        ghost_status.add_log("[cyan]Telegram polling active[/cyan]")

    def stop_polling(self) -> None:
        """Stop polling for messages."""
        self._polling = False

    def _flush_old_updates(self) -> None:
        """Discard any updates that arrived before we started."""
        try:
            r = requests.get(
                f"{self._api}/getUpdates",
                params={"offset": -1, "limit": 1},
                timeout=10,
            )
            data = r.json()
            if data.get("ok") and data.get("result"):
                self._last_update_id = (
                    data["result"][-1]["update_id"] + 1
                )
        except requests.RequestException:
            pass

    def _poll_loop(self) -> None:
        """Long-poll Telegram for new messages."""
        while self._polling:
            try:
                r = requests.get(
                    f"{self._api}/getUpdates",
                    params={
                        "offset": self._last_update_id,
                        "timeout": 30,
                    },
                    timeout=35,
                )
                data = r.json()
                if not data.get("ok"):
                    continue
                for update in data.get("result", []):
                    self._last_update_id = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    if text and chat_id == self._chat_id:
                        ghost_status.add_log(
                            f"[cyan]Telegram <<<[/cyan] {text[:60]}"
                        )
                        if self._reply_callback:
                            self._reply_callback(text)
            except requests.RequestException:
                pass
