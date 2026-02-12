"""Screen-only notification handler for when WhatsApp is disabled."""
from __future__ import annotations

import threading
import queue
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.utils import logger, ghost_status

console = Console()


class ScreenNotifier:
    """Handles approval requests via terminal when WhatsApp is disabled.

    Uses a queue to manage approval requests from the bridge thread,
    with responses processed in the main thread during the Live display loop.
    """

    def __init__(self) -> None:
        self._pending_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._response_callback: Optional[Callable[[str], None]] = None
        self._enabled = True

    def set_callback(self, callback: Callable[[str], None]) -> None:
        self._response_callback = callback

    def request_approval(self, message: str) -> None:
        """Queue an approval request to be shown on screen."""
        if not self._enabled:
            return
        self._pending_queue.put(("approval", message))
        logger.info("Screen approval queued")
        ghost_status.add_log("[bold yellow]>>> APPROVAL NEEDED (see below) <<<[/bold yellow]")

    def send_info(self, message: str) -> None:
        """Queue an informational message."""
        if not self._enabled:
            return
        self._pending_queue.put(("info", message))

    def check_pending(self) -> bool:
        """Check if there's a pending approval request.
        Called from the main loop to see if we need to pause for input."""
        return not self._pending_queue.empty()

    def process_pending(self) -> None:
        """Process one pending request. Call this when Live display is paused."""
        if self._pending_queue.empty():
            return

        msg_type, message = self._pending_queue.get_nowait()

        if msg_type == "info":
            console.print(Panel(message, title="Info", border_style="blue"))
            return

        # Approval request
        console.print()
        console.print(Panel(
            message,
            title="[bold yellow]Approval Required[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        ))
        console.print()
        console.print("[bold]Options:[/bold]")
        console.print("  [A] Approve - Allow this action")
        console.print("  [B] Block   - Deny this action")
        console.print("  [C] Context - Provide alternative instruction")
        console.print("  [D] Detonate - Kill the process immediately")
        console.print()

        while True:
            response = Prompt.ask(
                "Your choice",
                choices=["a", "A", "b", "B", "c", "C", "d", "D"],
                show_choices=False,
            )
            response = response.upper()

            if response == "C":
                context = Prompt.ask("Enter context/instruction")
                response = f"C {context}"

            break

        ghost_status.add_log(f"[cyan]Screen response:[/cyan] {response[:30]}")

        if self._response_callback:
            self._response_callback(response)

    def disable(self) -> None:
        self._enabled = False
        # Clear any pending
        while not self._pending_queue.empty():
            try:
                self._pending_queue.get_nowait()
            except queue.Empty:
                break
