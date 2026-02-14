"""Screen-only notification handler for when Telegram is disabled."""
from __future__ import annotations

import queue
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.utils import logger, ghost_status

console = Console()


class ScreenNotifier:
    """Handles approval requests via terminal when Telegram is disabled."""

    def __init__(self) -> None:
        self._pending_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._response_callback: Optional[Callable[[str], None]] = None
        self._enabled = True

    def set_callback(self, callback: Callable[[str], None]) -> None:
        """Set the response callback."""
        self._response_callback = callback

    def request_approval(self, message: str) -> None:
        """Queue an approval request to be shown on screen."""
        if not self._enabled:
            return
        self._pending_queue.put(("approval", message))
        logger.info("Screen approval queued")
        ghost_status.add_log(
            "[bold yellow]>>> APPROVAL NEEDED (see below) <<<[/bold yellow]"
        )

    def send_info(self, message: str) -> None:
        """Queue an informational message."""
        if not self._enabled:
            return
        self._pending_queue.put(("info", message))

    def check_pending(self) -> bool:
        """Check if there's a pending approval request."""
        return not self._pending_queue.empty()

    def process_pending(self) -> None:
        """Process one pending request (call when Live display is paused)."""
        if self._pending_queue.empty():
            return

        msg_type, message = self._pending_queue.get_nowait()

        if msg_type == "info":
            console.print(Panel(message, title="Info", border_style="blue"))
            return

        console.print()

        # Detect budget-pause messages to show the right options
        is_budget = "BUDGET" in message.upper() or "Top-up" in message

        if is_budget:
            console.print(Panel(
                message,
                title="[bold red]Budget Limit Reached[/bold red]",
                border_style="red",
                padding=(1, 2),
            ))
            console.print()
            console.print("[bold]Options:[/bold]")
            console.print(
                "  [T <amount>] Top-up budget (e.g. T 5)"
            )
            console.print("  [S] Stop — end the session")
            console.print()

            while True:
                raw = Prompt.ask("Your choice").strip()
                upper = raw.upper()
                if upper.startswith("T") or upper.startswith("S"):
                    ghost_status.add_log(
                        f"[cyan]Screen response:[/cyan] {raw[:30]}"
                    )
                    if self._response_callback:
                        self._response_callback(raw)
                    return
                console.print(
                    "[red]Please reply T <amount> or S[/red]"
                )
        else:
            console.print(Panel(
                message,
                title="[bold yellow]Approval Required[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            ))
            console.print()
            console.print("[bold]Options:[/bold]")
            console.print(
                "  [A] Approve  [B] Block  "
                "[C] Context  [D] Detonate"
            )
            console.print()

            response = Prompt.ask(
                "Your choice",
                choices=[
                    "a", "A", "b", "B",
                    "c", "C", "d", "D",
                ],
                show_choices=False,
            ).upper()

            if response == "C":
                context = Prompt.ask("Enter context/instruction")
                response = f"C {context}"

            ghost_status.add_log(
                f"[cyan]Screen response:[/cyan] {response[:30]}"
            )
            if self._response_callback:
                self._response_callback(response)

    def disable(self) -> None:
        """Disable and clear pending requests."""
        self._enabled = False
        while not self._pending_queue.empty():
            try:
                self._pending_queue.get_nowait()
            except queue.Empty:
                break
