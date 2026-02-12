from __future__ import annotations

import time
import threading
from typing import Callable, Optional, Dict

import requests

from src.config import settings
from src.utils import logger, ghost_status


class WahaClient:
    """WhatsApp HTTP API client using a local WAHA instance.

    Uses timestamp-based deduplication to avoid skipping messages that
    arrived between polls.
    
    Implements WAHA API with X-Api-Key authentication.
    See: https://waha.devlike.pro/docs/overview/quick-start/
    """

    def __init__(self) -> None:
        self._base = settings.waha_api_url.rstrip("/")
        self._api_key = getattr(settings, 'waha_api_key', '')
        self._phone = settings.target_phone
        self._session = settings.waha_session
        self._poll_interval = settings.poll_interval_seconds
        self._seen_ids: set[str] = set()
        self._seen_ids_max = 500
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None
        self._reply_callback: Optional[Callable[[str], None]] = None
        self._started_at: float = 0.0
        self._connected = False

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers with API key authentication."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["X-Api-Key"] = self._api_key
        return headers

    def check_connection(self) -> bool:
        """Verify WAHA is running and session is active."""
        url = f"{self._base}/api/sessions/{self._session}"
        try:
            r = requests.get(url, headers=self._get_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "UNKNOWN")
                self._connected = status == "WORKING"
                if self._connected:
                    logger.info("WAHA session '%s' is WORKING", self._session)
                    ghost_status.add_log(f"[green]WAHA connected[/green] (session: {self._session})")
                else:
                    logger.warning("WAHA session status: %s", status)
                    ghost_status.add_log(f"[yellow]WAHA session status: {status}[/yellow]")
                return self._connected
            else:
                logger.error("WAHA session check failed: %d", r.status_code)
                return False
        except requests.RequestException as exc:
            logger.error("WAHA connection check failed: %s", exc)
            ghost_status.add_log(f"[red]WAHA connection failed: {exc}[/red]")
            return False

    def send(self, text: str) -> bool:
        url = f"{self._base}/api/sendText"
        payload = {
            "chatId": self._phone,
            "text": text,
            "session": self._session,
        }
        try:
            r = requests.post(url, json=payload, headers=self._get_headers(), timeout=10)
            r.raise_for_status()
            logger.info("WAHA >>> %s", text[:80])
            ghost_status.add_log(f"[green]WAHA >>>[/green] {text[:60]}")
            return True
        except requests.RequestException as exc:
            logger.error("WAHA send failed: %s", exc)
            ghost_status.add_log(f"[red]WAHA send error[/red]")
            return False

    def start_polling(self, callback: Callable[[str], None]) -> None:
        self._reply_callback = callback
        self._polling = True
        self._started_at = time.time()
        
        # Check connection on startup
        self.check_connection()
        
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info("WAHA polling started (every %.1fs)", self._poll_interval)

    def stop_polling(self) -> None:
        self._polling = False

    def _poll_loop(self) -> None:
        # On first poll, mark all existing messages as seen so we only
        # react to messages that arrive after startup.
        first_poll = True
        while self._polling:
            try:
                self._check_messages(mark_only=first_poll)
                first_poll = False
            except Exception as exc:
                logger.error("WAHA poll error: %s", exc)
            time.sleep(self._poll_interval)

    def _check_messages(self, mark_only: bool = False) -> None:
        url = f"{self._base}/api/messages"
        params = {
            "chatId": self._phone,
            "limit": 10,
            "session": self._session,
        }
        try:
            r = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            r.raise_for_status()
            messages = r.json()
        except (requests.RequestException, ValueError) as exc:
            logger.debug("Poll fetch failed: %s", exc)
            return

        if not isinstance(messages, list):
            return

        # Trim seen-IDs set to prevent unbounded growth
        if len(self._seen_ids) > self._seen_ids_max:
            self._seen_ids = set(list(self._seen_ids)[-200:])

        new_inbound: list[tuple[str, str]] = []

        for msg in messages:
            msg_id = self._extract_id(msg)
            if not msg_id or msg_id in self._seen_ids:
                continue
            self._seen_ids.add(msg_id)

            if mark_only:
                continue

            from_me = msg.get("fromMe", msg.get("key", {}).get("fromMe", True))
            if from_me:
                continue

            body = (
                msg.get("body")
                or msg.get("text")
                or msg.get("message", {}).get("conversation", "")
            ).strip()
            if not body:
                continue

            new_inbound.append((msg_id, body))

        for _mid, body in new_inbound:
            logger.info("WAHA <<< %s", body[:80])
            ghost_status.last_waha_msg = body[:40]
            ghost_status.add_log(f"[cyan]WAHA <<<[/cyan] {body[:60]}")
            if self._reply_callback:
                try:
                    self._reply_callback(body)
                except Exception as exc:
                    logger.error("Reply callback error: %s", exc)

    @staticmethod
    def _extract_id(msg: dict) -> Optional[str]:
        return msg.get("id") or msg.get("key", {}).get("id")
