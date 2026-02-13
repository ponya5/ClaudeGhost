"""Shared utilities: logging, stats, and Rich TUI dashboard."""
from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

logger = logging.getLogger("claudeghost")
logger.setLevel(logging.DEBUG)
logger.propagate = False

_MARKUP_ESCAPE_RE = re.compile(r"[\[\]]")


def _safe_markup(text: str) -> str:
    """Escape Rich markup brackets in untrusted text."""
    return _MARKUP_ESCAPE_RE.sub(lambda m: "\\" + m.group(), text)


class SessionStats:
    """Tracks statistics for a ClaudeGhost session."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.start_time: float = time.time()
        self.queries_total: int = 0
        self.queries_auto_approved: int = 0
        self.queries_user_approved: int = 0
        self.queries_blocked: int = 0
        self.commands_executed: int = 0
        self.telegram_sent: int = 0
        self.telegram_received: int = 0

    def record_auto_approve(self) -> None:
        with self._lock:
            self.queries_total += 1
            self.queries_auto_approved += 1
            self.commands_executed += 1

    def record_user_approve(self) -> None:
        with self._lock:
            self.queries_total += 1
            self.queries_user_approved += 1
            self.commands_executed += 1

    def record_blocked(self) -> None:
        with self._lock:
            self.queries_total += 1
            self.queries_blocked += 1

    def record_telegram_sent(self) -> None:
        with self._lock:
            self.telegram_sent += 1

    def record_telegram_received(self) -> None:
        with self._lock:
            self.telegram_received += 1

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def elapsed_formatted(self) -> str:
        elapsed = int(self.elapsed_seconds)
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}h {mins}m {secs}s"
        if mins:
            return f"{mins}m {secs}s"
        return f"{secs}s"


class GhostStatus:
    """Thread-safe live state for the Rich TUI."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.current_task: str = "N/A"
        self.afk_level: int = 3
        self.level_name: str = "Manager"
        self.budget_used: float = 0.0
        self.budget_max: float = 5.0
        self.state: str = "STARTING"
        self.telegram_enabled: bool = True
        self.stats: SessionStats = SessionStats()
        self._log_lines: list[str] = []

    def reset(self) -> None:
        """Reset for a new session."""
        with self._lock:
            self._log_lines = []
        self.state = "STARTING"
        self.budget_used = 0.0
        self.stats = SessionStats()

    def add_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._log_lines.append(f"[dim]{ts}[/dim] {msg}")
            if len(self._log_lines) > 300:
                self._log_lines = self._log_lines[-300:]

    def build_layout(self) -> Layout:
        layout = Layout()
        layout.split_row(
            Layout(name="logs", ratio=2),
            Layout(name="right", ratio=1),
        )
        layout["right"].split_column(
            Layout(name="status", ratio=1),
            Layout(name="stats", ratio=1),
        )

        # Logs panel
        with self._lock:
            recent = list(self._log_lines[-25:])
        log_body = "\n".join(recent) if recent else "[dim]No logs yet[/dim]"
        try:
            log_renderable = Text.from_markup(log_body)
        except Exception:
            log_renderable = Text(log_body)
        layout["logs"].update(
            Panel(log_renderable, title="Activity Log", border_style="blue")
        )

        # Status panel
        status_tbl = Table.grid(padding=(0, 1))
        state_color = {
            "RUNNING": "green", "THINKING": "cyan",
            "QUERY": "yellow", "WAITING": "yellow",
            "BUDGET_PAUSE": "red", "EXITED": "dim",
        }.get(self.state, "white")

        status_tbl.add_row(
            "State:",
            f"[bold {state_color}]{self.state}[/bold {state_color}]",
        )
        status_tbl.add_row("Task:", _safe_markup(self.current_task[:50]))
        status_tbl.add_row(
            "AFK Level:", f"{self.afk_level} ({self.level_name})"
        )

        budget_pct = (
            (self.budget_used / self.budget_max * 100)
            if self.budget_max > 0 else 0
        )
        bc = "green" if budget_pct < 70 else "yellow" if budget_pct < 90 else "red"
        status_tbl.add_row(
            "Budget:",
            f"[{bc}]${self.budget_used:.2f}[/{bc}]"
            f" / ${self.budget_max:.2f} ({budget_pct:.0f}%)",
        )

        mode = (
            "[green]Telegram[/green]"
            if self.telegram_enabled
            else "[cyan]Screen Only[/cyan]"
        )
        status_tbl.add_row("Notify:", mode)

        layout["status"].update(
            Panel(status_tbl, title="Session Status", border_style="green")
        )

        # Stats panel
        stats_tbl = Table.grid(padding=(0, 1))
        stats_tbl.add_row(
            "Elapsed:", f"[bold]{self.stats.elapsed_formatted}[/bold]"
        )
        stats_tbl.add_row("Queries:", str(self.stats.queries_total))
        stats_tbl.add_row(
            "  Auto:", f"[green]{self.stats.queries_auto_approved}[/green]"
        )
        stats_tbl.add_row(
            "  User:", f"[yellow]{self.stats.queries_user_approved}[/yellow]"
        )
        stats_tbl.add_row(
            "  Blocked:", f"[red]{self.stats.queries_blocked}[/red]"
        )
        stats_tbl.add_row("Commands:", str(self.stats.commands_executed))
        if self.telegram_enabled:
            stats_tbl.add_row(
                "Telegram I/O:",
                f"{self.stats.telegram_sent}"
                f" / {self.stats.telegram_received}",
            )

        layout["stats"].update(
            Panel(stats_tbl, title="Statistics", border_style="magenta")
        )
        return layout


ghost_status = GhostStatus()


class _RichLogHandler(logging.Handler):
    """Routes log records into GhostStatus instead of stderr."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            level = record.levelname
            if level == "WARNING":
                ghost_status.add_log(f"[yellow]{_safe_markup(msg)}[/yellow]")
            elif level == "ERROR":
                ghost_status.add_log(f"[red]{_safe_markup(msg)}[/red]")
            else:
                ghost_status.add_log(_safe_markup(msg))
        except Exception:
            pass


_rich_handler = _RichLogHandler()
_rich_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(_rich_handler)
