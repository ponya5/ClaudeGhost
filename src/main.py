"""ClaudeGhost - Headless Supervisor for the Anthropic Claude CLI."""
from __future__ import annotations

import argparse
import signal
import sys
import time
import threading
import uuid
from typing import Optional

from rich.live import Live
from rich.prompt import Confirm

from src.bridge import GhostBridge, CliState, StreamEvent
from src.guardian import (
    Decision,
    evaluate,
    extract_command_from_query,
    format_approval_message,
)
from src.config import settings, SessionConfig
from src.telegram_bot import TelegramBot
from src.screen_notifier import ScreenNotifier
from src.utils import logger, ghost_status, console
from src.launcher import run_interactive_launcher, run_quick_launcher
from src.changelog import ChangeLog
from src.updater import auto_update


class ClaudeGhost:
    """Orchestrates the Ghost Bridge, Guardian, and notification medium."""

    def __init__(self, config: SessionConfig) -> None:
        self.config = config
        self.task = config.task
        self.afk_level = config.afk_level
        self.session_id = str(uuid.uuid4())

        self._telegram: Optional[TelegramBot] = None
        self._screen: Optional[ScreenNotifier] = None

        if config.telegram_enabled:
            self._telegram = TelegramBot()
        else:
            self._screen = ScreenNotifier()

        self._bridge: Optional[GhostBridge] = None
        self._pending_query: Optional[str] = None
        self._pending_lock = threading.Lock()
        self._budget_warned = False
        self._budget_warning_sent = False
        self._budget_paused = False
        self._shutdown = threading.Event()
        self._changelog = ChangeLog(config.task, self.session_id)

        ghost_status.reset()
        ghost_status.current_task = config.task
        ghost_status.afk_level = config.afk_level
        ghost_status.level_name = config.level_name
        ghost_status.model = config.model
        ghost_status.budget_max = config.budget_usd
        ghost_status.telegram_enabled = config.telegram_enabled

    def run(self) -> None:
        """Start the supervised session."""
        settings.max_budget_usd = self.config.budget_usd
        settings.working_directory = self.config.working_directory

        self._bridge = GhostBridge(
            task=self.task,
            on_query=self._handle_query,
            on_idle=self._handle_idle,
            on_stall=self._handle_stall,
            on_event=self._handle_event,
            afk_level=self.afk_level,
            model=self.config.model,
        )

        if self._telegram:
            self._telegram.start_polling(self._handle_reply)
            self._notify(
                f"ClaudeGhost started\n"
                f"Task: {self.task}\n"
                f"AFK Level: {self.afk_level} ({self.config.level_name})\n"
                f"Budget: ${self.config.budget_usd:.2f}"
            )
        elif self._screen:
            self._screen.set_callback(self._handle_reply)

        self._bridge.start()
        ghost_status.state = "RUNNING"

        original_sigint = signal.getsignal(signal.SIGINT)

        def _on_sigint(_signum: int, _frame: object) -> None:
            logger.info("SIGINT received, shutting down...")
            self._shutdown.set()

        signal.signal(signal.SIGINT, _on_sigint)

        try:
            self._run_loop()
        finally:
            signal.signal(signal.SIGINT, original_sigint)

        if self._bridge.state != CliState.EXITED:
            self._bridge.kill()
        if self._telegram:
            self._telegram.stop_polling()
        if self._screen:
            self._screen.disable()

        self._send_summary()

    def _run_loop(self) -> None:
        assert self._bridge is not None
        with Live(
            ghost_status.build_layout(),
            console=console,
            refresh_per_second=2,
            transient=False,
        ) as live:
            while not self._shutdown.is_set():
                # Keep looping while budget-paused (waiting for
                # user to top-up or stop) even if bridge exited
                if (
                    self._bridge.state == CliState.EXITED
                    and not self._budget_paused
                ):
                    break
                if self._screen and self._screen.check_pending():
                    live.stop()
                    self._screen.process_pending()
                    live.start()
                live.update(ghost_status.build_layout())
                self._check_budget()
                time.sleep(0.5)

    # -- Notification helpers ------------------------------------------------

    def _notify(self, message: str) -> None:
        if self._telegram:
            self._telegram.send(message)
            ghost_status.stats.record_telegram_sent()
        elif self._screen:
            self._screen.send_info(message)

    def _request_approval(self, message: str) -> None:
        if self._telegram:
            self._telegram.send(message)
            ghost_status.stats.record_telegram_sent()
        elif self._screen:
            self._screen.request_approval(message)

    # -- Query handling ------------------------------------------------------

    def _handle_query(self, query_text: str) -> None:
        command = extract_command_from_query(query_text)
        if not command:
            command = self._fallback_command(query_text)

        decision, category = evaluate(command, self.afk_level)

        if decision == Decision.AUTO_APPROVE:
            ghost_status.add_log(
                f"[green]Auto-approved:[/green] {command[:60]}"
            )
            ghost_status.stats.record_auto_approve()
            self._changelog.add_command(command)
            if self.afk_level == 5:
                self._notify(f"Auto-approved (God Mode): {command[:200]}")
            assert self._bridge is not None
            self._bridge.send("y")
        else:
            msg = format_approval_message(command, category)
            self._request_approval(msg)
            with self._pending_lock:
                self._pending_query = command
            ghost_status.state = "WAITING"
            mode = "Telegram" if self._telegram else "screen"
            ghost_status.add_log(
                f"[bold yellow]Waiting for {mode} reply...[/bold yellow]"
            )

    # -- Reply handling ------------------------------------------------------

    def _handle_reply(self, body: str) -> None:
        if self._bridge is None and not self._budget_paused:
            return
        if self._telegram:
            ghost_status.stats.record_telegram_received()

        # Budget-paused state takes priority
        if self._handle_budget_reply(body):
            return

        reply = body.strip()
        first_char = reply[0].upper() if reply else ""

        with self._pending_lock:
            has_pending = self._pending_query is not None

        if first_char == "A":
            ghost_status.add_log("[green]User APPROVED.[/green]")
            ghost_status.stats.record_user_approve()
            with self._pending_lock:
                if self._pending_query:
                    self._changelog.add_command(self._pending_query)
                self._pending_query = None
            self._bridge.send("y")
            ghost_status.state = "RUNNING"

        elif first_char == "B":
            ghost_status.add_log("[red]User BLOCKED.[/red]")
            ghost_status.stats.record_blocked()
            self._bridge.send("n")
            with self._pending_lock:
                self._pending_query = None
            ghost_status.state = "RUNNING"

        elif first_char == "D":
            ghost_status.add_log(
                "[bold red]DETONATE - killing process.[/bold red]"
            )
            self._notify("Process killed by user.")
            self._bridge.kill()
            with self._pending_lock:
                self._pending_query = None

        elif first_char == "C" or has_pending:
            context = reply
            if first_char == "C" and len(reply) > 1:
                context = reply[1:].strip()
            ghost_status.add_log(
                f"[cyan]Context injected:[/cyan] {context[:60]}"
            )
            self._bridge.send(context)
            with self._pending_lock:
                self._pending_query = None
            ghost_status.state = "RUNNING"

        else:
            self._notify(
                "Unknown reply. Use:\n"
                "[A] Approve\n[B] Block\n"
                "[C <text>] Context\n[D] Detonate"
            )

    # -- Other callbacks -----------------------------------------------------

    def _handle_idle(self) -> None:
        ghost_status.add_log("[dim]CLI is idle.[/dim]")

    def _handle_stall(self) -> None:
        self._notify(
            f"Stall detected - no output for "
            f"{settings.heartbeat_timeout_seconds:.0f}s.\n"
            f"The process may be hanging."
        )

    def _handle_event(self, event: StreamEvent) -> None:
        """Record stream events into the changelog."""
        if event.tool_name:
            name = event.tool_name.lower()
            if name in ("write", "edit", "editfile",
                        "writefile", "create"):
                if event.file_path:
                    self._changelog.add_file_change(event.file_path)
                    self._changelog.add_change(
                        f"{event.tool_name}: {event.file_path}"
                    )
            elif name in ("bash", "execute"):
                if event.tool_input:
                    self._changelog.add_command(event.tool_input)
                    self._changelog.add_change(
                        f"Executed: {event.tool_input[:200]}"
                    )
            elif name in ("read", "readfile"):
                if event.file_path:
                    self._changelog.add_change(
                        f"Read: {event.file_path}"
                    )
            else:
                desc = event.tool_input or ""
                self._changelog.add_change(
                    f"{event.tool_name}: {desc[:200]}"
                )
        if event.result_text:
            self._changelog.add_change(
                f"Result: {event.result_text[:300]}"
            )

    def _check_budget(self) -> None:
        if self._bridge is None or self._budget_paused:
            return
        cost = self._bridge.total_cost
        budget = self.config.budget_usd

        if cost <= 0 or budget <= 0:
            return

        pct = (cost / budget) * 100

        # Early warning at 80%
        if pct >= 80 and not self._budget_warning_sent:
            self._budget_warning_sent = True
            ghost_status.add_log(
                f"[bold yellow]Budget warning: "
                f"{pct:.0f}% used[/bold yellow]"
            )
            self._notify(
                f"⚠️ Budget at {pct:.0f}%\n"
                f"Used: ${cost:.2f} / ${budget:.2f}\n"
                f"The session will stop when the budget is reached."
            )

        # Budget exceeded — stop and ask user
        if cost >= budget and not self._budget_warned:
            self._budget_warned = True
            self._budget_paused = True
            ghost_status.add_log(
                "[bold red]BUDGET EXCEEDED — paused[/bold red]"
            )
            ghost_status.state = "BUDGET_PAUSE"

            # Kill the running process to stop spending
            self._bridge.kill()

            self._request_approval(
                f"⛔ BUDGET REACHED — execution stopped\n"
                f"Used: ${cost:.2f} / ${budget:.2f}\n\n"
                f"Options:\n"
                f"[T <amount>] Top-up budget "
                f"(e.g. T 5 adds $5.00)\n"
                f"[S] Stop — end the session"
            )

    def _handle_budget_reply(self, reply: str) -> bool:
        """Handle a reply while in budget-paused state.

        Returns True if the reply was consumed, False otherwise.
        """
        if not self._budget_paused:
            return False

        upper = reply.strip().upper()

        # --- Stop / terminate ---
        if upper.startswith("S") or upper.startswith("D"):
            self._budget_paused = False
            ghost_status.add_log(
                "[red]User chose to stop after budget limit.[/red]"
            )
            ghost_status.state = "EXITED"
            self._notify("Session ended by user (budget limit).")
            self._shutdown.set()
            return True

        # --- Top-up: "T 5" or "T 10.00" ---
        if upper.startswith("T"):
            parts = reply.strip().split(None, 1)
            topup = 0.0
            if len(parts) > 1:
                try:
                    topup = float(
                        parts[1].strip().lstrip("$")
                    )
                except ValueError:
                    pass

            if topup <= 0:
                self._notify(
                    "Invalid amount. Reply with:\n"
                    "[T <amount>] e.g. T 5\n"
                    "[S] Stop"
                )
                return True

            old_budget = self.config.budget_usd
            new_budget = old_budget + topup
            self.config.budget_usd = new_budget
            settings.max_budget_usd = new_budget
            ghost_status.budget_max = new_budget

            # Reset budget flags so checks work for the new limit
            self._budget_warned = False
            self._budget_warning_sent = False
            self._budget_paused = False

            ghost_status.add_log(
                f"[green]Budget topped up: "
                f"${old_budget:.2f} → ${new_budget:.2f}[/green]"
            )
            self._notify(
                f"✅ Budget updated: ${new_budget:.2f}\n"
                f"Resuming task..."
            )

            # Restart the Claude process with the new budget
            self._bridge = GhostBridge(
                task=self.task,
                on_query=self._handle_query,
                on_idle=self._handle_idle,
                on_stall=self._handle_stall,
                on_event=self._handle_event,
                afk_level=self.afk_level,
                model=self.config.model,
            )
            self._bridge.start()
            ghost_status.state = "RUNNING"
            return True

        # Unrecognised reply while paused
        self._notify(
            "Budget is paused. Reply with:\n"
            "[T <amount>] Top-up (e.g. T 5)\n"
            "[S] Stop"
        )
        return True

    def _send_summary(self) -> None:
        assert self._bridge is not None
        s = ghost_status.stats
        turns = self._bridge.num_turns

        # Finalize and save changelog
        self._changelog.finalize()
        changelog_path = self._changelog.save()

        summary = (
            f"ClaudeGhost session ended\n"
            f"Task: {self.task}\n"
            f"Duration: {s.elapsed_formatted}\n"
            f"Cost: ${self._bridge.total_cost:.2f}\n"
            f"Turns: {turns}\n"
            f"Queries: {s.queries_total} "
            f"(auto:{s.queries_auto_approved} "
            f"user:{s.queries_user_approved} "
            f"blocked:{s.queries_blocked})\n"
            f"Commands: {s.commands_executed}\n"
            f"\n{self._changelog.get_summary()}"
        )

        self._notify(summary)

        # Send the session log file as a Telegram document
        # so the user can tap to open it directly
        if changelog_path and self._telegram:
            self._telegram.send_file(
                str(changelog_path),
                caption="📄 Session changelog",
            )

        ghost_status.add_log(
            "[bold green]Session complete.[/bold green]"
        )
        console.print()
        console.print("[bold green]Session Complete[/bold green]")
        console.print(f"  Duration: {s.elapsed_formatted}")
        console.print(
            f"  Cost: ${self._bridge.total_cost:.2f}"
            f" / ${self.config.budget_usd:.2f}"
        )
        console.print(f"  Turns: {turns}")
        if s.queries_total > 0:
            console.print(
                f"  Queries: {s.queries_total} total"
            )

        if changelog_path:
            console.print(
                f"\n[cyan]📄 Changelog saved:[/cyan]"
                f" {changelog_path}"
            )

    @staticmethod
    def _fallback_command(query_text: str) -> str:
        lines = [
            ln.strip()
            for ln in query_text.strip().splitlines()
            if ln.strip()
        ]
        return lines[-1] if lines else "unknown"


def main() -> None:
    """Main entry point with session loop and update checker."""
    parser = argparse.ArgumentParser(
        prog="claudeghost",
        description="Headless Supervisor for the Anthropic Claude CLI",
    )
    parser.add_argument(
        "task", nargs="?", default=None,
        help="Task/prompt for claude (omit for interactive mode)",
    )
    parser.add_argument(
        "--level", "-l", type=int, default=None,
        choices=[1, 2, 3, 4, 5],
        help="AFK autonomy level (1-5)",
    )
    parser.add_argument(
        "--budget", "-b", type=float, default=None,
        help="Budget limit in USD",
    )
    parser.add_argument(
        "--no-telegram", action="store_true",
        help="Disable Telegram, use screen-only notifications",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Force interactive mode",
    )
    parser.add_argument(
        "--model", "-m", type=str, default=None,
        help="Claude model (sonnet, opus, haiku, or full name)",
    )
    args = parser.parse_args()

    # Auto-update before anything else
    auto_update()
    console.print()

    # Session loop
    while True:
        if args.interactive or args.task is None:
            config = run_interactive_launcher()
            if config is None:
                sys.exit(0)
        else:
            config = run_quick_launcher(
                task=args.task,
                level=args.level or settings.default_afk_level,
                budget=args.budget or settings.max_budget_usd,
                telegram=not args.no_telegram,
                model=args.model,
            )
            console.print("[bold blue]ClaudeGhost v2.0[/bold blue]")
            console.print(f"  Task  : {config.task[:60]}")
            console.print(f"  Model : {config.model}")
            console.print(
                f"  Level : {config.afk_level}"
                f" ({config.level_name})"
            )
            console.print(f"  Budget: ${config.budget_usd:.2f}")
            notify = "Telegram" if config.telegram_enabled else "Screen"
            console.print(f"  Notify: {notify}")
            console.print()

        # Run session
        ghost = ClaudeGhost(config=config)
        ghost.run()

        # Ask if user wants another session
        console.print()
        try:
            another = Confirm.ask(
                "[bold]Start another session?[/bold]",
                default=False
            )
            if not another:
                console.print("[green]Goodbye![/green]")
                break
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        # Reset args for next session (force interactive)
        args.task = None
        args.interactive = True
        console.print()


if __name__ == "__main__":
    main()
