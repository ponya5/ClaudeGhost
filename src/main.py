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
from src.version import __version__


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

        # Context flow: None | "awaiting_text" | "awaiting_confirm"
        self._context_state: Optional[str] = None
        self._pending_context: Optional[str] = None
        # Prevent _run_loop exit during bridge restart
        self._restarting = False
        self._original_task = config.task

        # Session outcome tracking
        self._session_completed = False
        self._session_failed = False
        self._session_terminated = False
        self._session_error_message = ""

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
                "👻 ClaudeGhost Started\n"
                "\n"
                f"📋 Task: {self.task}\n"
                f"🤖 AFK Level: {self.afk_level} "
                f"({self.config.level_name})\n"
                f"🔧 Mode: "
                f"{self.config.level_description}\n"
                f"💰 Budget: ${self.config.budget_usd:.2f}"
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
        except Exception as exc:
            logger.exception("Session error: %s", exc)
            self._session_failed = True
            self._session_error_message = str(exc)
            self._notify_error(
                "Unexpected error during session",
                str(exc),
            )
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
        try:
            with Live(
                ghost_status.build_layout(),
                console=console,
                refresh_per_second=2,
                transient=True,
            ) as live:
                while not self._shutdown.is_set():
                    if (
                        self._bridge.state
                        == CliState.EXITED
                        and not self._budget_paused
                        and not self._restarting
                    ):
                        self._session_completed = True
                        break
                    if (
                        self._screen
                        and self._screen.check_pending()
                    ):
                        live.stop()
                        self._screen.process_pending()
                        live.start()
                    try:
                        live.update(
                            ghost_status.build_layout(),
                        )
                    except Exception:
                        pass
                    self._check_budget()
                    time.sleep(0.5)
        except Exception as exc:
            logger.warning(
                "Live display error: %s", exc,
            )
        finally:
            # Reset terminal state after Live exits
            try:
                console.clear()
            except Exception:
                pass

    # -- Notification helpers ----------------------------------------

    def _notify(self, message: str) -> None:
        try:
            if self._telegram:
                self._telegram.send(message)
                ghost_status.stats.record_telegram_sent()
            elif self._screen:
                self._screen.send_info(message)
        except Exception as exc:
            logger.error("Notification failed: %s", exc)

    def _request_approval(self, message: str) -> None:
        try:
            if self._telegram:
                self._telegram.send(message)
                ghost_status.stats.record_telegram_sent()
            elif self._screen:
                self._screen.request_approval(message)
        except Exception as exc:
            logger.error("Approval request failed: %s", exc)

    def _notify_error(
        self, title: str, detail: str,
    ) -> None:
        """Send an informative error message via Telegram."""
        # Gather what we know about changes so far
        files = self._changelog.files_modified
        cmds = self._changelog.commands_executed
        files_str = (
            "\n".join(f"  • {f}" for f in files[-5:])
            if files else "  (none)"
        )
        cmds_str = (
            "\n".join(f"  • {c[:80]}" for c in cmds[-5:])
            if cmds else "  (none)"
        )
        msg = (
            "❌ SESSION ERROR\n"
            "\n"
            f"⚠️ {title}\n"
            f"📝 Detail: {detail[:300]}\n"
            "\n"
            f"📂 Files modified so far:\n{files_str}\n"
            f"⚡ Commands executed:\n{cmds_str}\n"
            "\n"
            "The session has been terminated."
        )
        self._notify(msg)

    # -- Query handling ----------------------------------------------

    def _handle_query(self, query_text: str) -> None:
        try:
            self._handle_query_inner(query_text)
        except Exception as exc:
            logger.exception(
                "Query handler error: %s", exc,
            )
            ghost_status.add_log(
                f"[bold red]Query handler error: "
                f"{str(exc)[:80]}[/bold red]"
            )

    def _handle_query_inner(self, query_text: str) -> None:
        command = extract_command_from_query(query_text)
        if not command:
            command = self._fallback_command(query_text)

        decision, category = evaluate(
            command, self.afk_level,
        )

        if decision == Decision.AUTO_APPROVE:
            ghost_status.add_log(
                f"[green]Auto-approved:[/green] "
                f"{command[:60]}"
            )
            ghost_status.stats.record_auto_approve()
            self._changelog.add_command(command)
        else:
            # ASK_USER: notify via Telegram/screen.
            # The tool already executed (headless mode),
            # but the user can Block & Redo (B) if they
            # disagree with the action.
            ghost_status.add_log(
                f"[yellow]⚠ User attention:[/yellow] "
                f"{command[:60]}"
            )
            ghost_status.stats.record_auto_approve()
            self._changelog.add_command(command)
            msg = format_approval_message(
                command, category,
            )
            self._notify(msg)

    # -- Reply handling ----------------------------------------------

    def _handle_reply(self, body: str) -> None:
        try:
            self._handle_reply_inner(body)
        except Exception as exc:
            logger.warning(
                "Reply handler error: %s", exc,
            )
            ghost_status.add_log(
                f"[dim]Reply skipped: "
                f"{str(exc)[:80]}[/dim]"
            )

    def _handle_reply_inner(self, body: str) -> None:
        if self._bridge is None and not self._budget_paused:
            return
        # Ignore replies if bridge already exited
        if (
            self._bridge is not None
            and self._bridge.state == CliState.EXITED
            and not self._budget_paused
            and not self._restarting
        ):
            return
        if self._telegram:
            ghost_status.stats.record_telegram_received()

        # Budget-paused state takes priority
        if self._handle_budget_reply(body):
            return

        # Context flow state machine
        if self._handle_context_reply(body):
            return

        reply = body.strip()
        if not reply:
            return
        first_char = reply[0].upper()

        # ── A: Approve ──────────────────────────────────
        if first_char == "A":
            ghost_status.add_log(
                "[green]User acknowledged.[/green]"
            )
            ghost_status.stats.record_user_approve()
            with self._pending_lock:
                if self._pending_query:
                    self._changelog.add_command(
                        self._pending_query,
                    )
                self._pending_query = None
            ghost_status.state = "RUNNING"

        # ── B: Block & Redo ─────────────────────────────
        elif first_char == "B":
            ghost_status.add_log(
                "[red]User BLOCKED — restarting with "
                "alternative approach.[/red]"
            )
            ghost_status.add_event(
                "[bold red]🚫 User blocked action — "
                "restarting[/bold red]"
            )
            ghost_status.stats.record_blocked()
            self._restarting = True
            self._bridge.kill()
            with self._pending_lock:
                self._pending_query = None

            new_task = (
                f"{self.task} --- "
                f"IMPORTANT: The user blocked the last "
                f"action. Try a completely different "
                f"approach. Do NOT repeat the same "
                f"command or tool."
            )
            self._bridge = GhostBridge(
                task=new_task,
                on_query=self._handle_query,
                on_idle=self._handle_idle,
                on_stall=self._handle_stall,
                on_event=self._handle_event,
                afk_level=self.afk_level,
                model=self.config.model,
            )
            self._bridge.start()
            self._restarting = False
            ghost_status.state = "RUNNING"
            self._notify(
                "🔄 Blocked. Restarting with a "
                "different approach..."
            )

        # ── C: Add Context ──────────────────────────────
        elif first_char == "C":
            context_inline = (
                reply[1:].strip() if len(reply) > 1
                else ""
            )
            if context_inline:
                # User provided context inline: "C <text>"
                self._pending_context = context_inline
                self._context_state = "awaiting_confirm"
                self._notify(
                    "📝 CONFIRM CONTEXT\n"
                    "\n"
                    f"Your instruction:\n"
                    f"  \"{context_inline}\"\n"
                    "\n"
                    "Reply:\n"
                    "  Y - ✅ Accept & Apply\n"
                    "  N - ❌ Cancel\n"
                    "  M - ✏️ Modify"
                )
            else:
                # Just "C" — ask for the text
                self._context_state = "awaiting_text"
                self._notify(
                    "💬 ADD CONTEXT\n"
                    "\n"
                    "Type your instruction or context "
                    "below.\n"
                    "This will be added to the current "
                    "task."
                )

        # ── D: Detonate (kill) ──────────────────────────
        elif first_char == "D":
            ghost_status.add_log(
                "[bold red]DETONATE — session terminated "
                "by user.[/bold red]"
            )
            ghost_status.add_event(
                "[bold red]💀 Session terminated by "
                "user (Detonate)[/bold red]"
            )
            with self._pending_lock:
                self._pending_query = None
            self._bridge.kill()
            self._session_terminated = True

            # Gather outcome info for the user
            files = self._changelog.files_modified
            cmds = self._changelog.commands_executed
            files_str = (
                "\n".join(f"  • {f}" for f in files[-5:])
                if files else "  (none)"
            )
            cmds_str = (
                "\n".join(
                    f"  • {c[:80]}" for c in cmds[-5:]
                )
                if cmds else "  (none)"
            )
            self._notify(
                "💀 SESSION TERMINATED\n"
                "\n"
                "The session was killed by your request.\n"
                "\n"
                f"📂 Files modified:\n{files_str}\n"
                f"⚡ Commands executed:\n{cmds_str}\n"
                "\n"
                "⚠️ Some changes may be incomplete.\n"
                "Review your working directory."
            )
            ghost_status.state = "EXITED"
            self._shutdown.set()

        # ── Unknown ─────────────────────────────────────
        else:
            self._notify(
                "❓ Unknown reply.\n"
                "\n"
                "Reply:\n"
                "  A - ✅ Acknowledge\n"
                "  B - 🚫 Block & Redo\n"
                "  C - 💬 Add Context\n"
                "  D - 💀 Detonate (kill)"
            )

    def _handle_context_reply(self, body: str) -> bool:
        """Handle replies during the multi-step context flow.

        Returns True if the reply was consumed.
        """
        if self._context_state is None:
            return False

        reply = body.strip()

        if self._context_state == "awaiting_text":
            if not reply:
                self._notify(
                    "💬 Type your instruction below:"
                )
                return True
            self._pending_context = reply
            self._context_state = "awaiting_confirm"
            self._notify(
                "📝 CONFIRM CONTEXT\n"
                "\n"
                f"Your instruction:\n"
                f"  \"{reply}\"\n"
                "\n"
                "Reply:\n"
                "  Y - ✅ Accept & Apply\n"
                "  N - ❌ Cancel\n"
                "  M - ✏️ Modify"
            )
            return True

        if self._context_state == "awaiting_confirm":
            first = reply[0].upper() if reply else ""

            if first == "Y":
                context = self._pending_context or ""
                self._context_state = None
                self._pending_context = None

                ghost_status.add_log(
                    f"[cyan]Context accepted:[/cyan] "
                    f"{context[:60]}"
                )
                ghost_status.add_event(
                    f"[bold cyan]🔄 User context "
                    f"applied:[/bold cyan] "
                    f"{context[:100]}"
                )
                self._restarting = True
                self._bridge.kill()
                with self._pending_lock:
                    self._pending_query = None

                new_task = (
                    f"{self._original_task} --- "
                    f"IMPORTANT ADDITIONAL CONTEXT FROM "
                    f"THE USER: {context} --- "
                    f"You MUST incorporate this context. "
                    f"It takes priority over any "
                    f"conflicting part of the original "
                    f"task. If the user is changing the "
                    f"file name or target, use the NEW "
                    f"name/target they specified."
                )
                self.task = new_task
                self._notify(
                    f"🔄 Restarting with your context:\n"
                    f"  \"{context[:200]}\""
                )
                self._bridge = GhostBridge(
                    task=new_task,
                    on_query=self._handle_query,
                    on_idle=self._handle_idle,
                    on_stall=self._handle_stall,
                    on_event=self._handle_event,
                    afk_level=self.afk_level,
                    model=self.config.model,
                )
                self._bridge.start()
                self._restarting = False
                ghost_status.state = "RUNNING"
                return True

            elif first == "N":
                self._context_state = None
                self._pending_context = None
                self._notify(
                    "❌ Context cancelled.\n"
                    "\n"
                    "Reply:\n"
                    "  A - ✅ Approve\n"
                    "  B - 🚫 Block & Redo\n"
                    "  C - 💬 Add Context\n"
                    "  D - 💀 Detonate (kill)"
                )
                return True

            elif first == "M":
                self._context_state = "awaiting_text"
                self._pending_context = None
                self._notify(
                    "✏️ Type your updated instruction:"
                )
                return True

            else:
                self._notify(
                    "❓ Reply with:\n"
                    "  Y - ✅ Accept & Apply\n"
                    "  N - ❌ Cancel\n"
                    "  M - ✏️ Modify"
                )
                return True

        return False

    # -- Other callbacks ---------------------------------------------

    def _handle_idle(self) -> None:
        ghost_status.add_log("[dim]CLI is idle.[/dim]")

    def _handle_stall(self) -> None:
        with self._pending_lock:
            has_pending = self._pending_query is not None
        if has_pending:
            self._notify(
                f"⏳ Stall detected — no output for "
                f"{settings.heartbeat_timeout_seconds:.0f}"
                f"s.\nStill waiting for your approval.\n"
                f"Send A, B, C, or D."
            )
        else:
            self._notify(
                f"⏳ Stall detected\n"
                f"No output for "
                f"{settings.heartbeat_timeout_seconds:.0f}"
                f"s.\nThe process may be hanging."
            )

    def _handle_event(self, event: StreamEvent) -> None:
        """Record stream events into the changelog."""
        try:
            self._handle_event_inner(event)
        except Exception as exc:
            logger.error(
                "Event handler error: %s", exc,
            )

    def _handle_event_inner(
        self, event: StreamEvent,
    ) -> None:
        """Record stream events and apply guardian logic.

        The guardian evaluates each tool against the AFK
        level to decide: auto-approve (silent) or notify
        the user.  Since we run in headless mode, tools
        execute first — the user can Block & Redo (B) if
        they disagree.

        Level 1: user notified of EVERY action
        Level 2: auto reads, notify writes/executes
        Level 3: auto reads+writes, notify executes
        Level 4: auto reads+writes+executes, notify high-risk
        Level 5: auto everything (notify only on errors)
        """
        if event.tool_name:
            name = event.tool_name.lower()

            # Build a command string for the guardian
            path = event.file_path or ""
            inp = event.tool_input or ""
            cmd_str = (
                f"{event.tool_name}: {path or inp}"
                if (path or inp)
                else event.tool_name
            )

            # Guardian decides based on AFK level
            decision, category = evaluate(
                cmd_str, self.afk_level,
            )

            # Record the action in the changelog
            if name in (
                "write", "edit", "editfile",
                "writefile", "create",
            ):
                if event.file_path:
                    self._changelog.add_file_change(
                        event.file_path,
                    )
                    self._changelog.add_change(
                        f"{event.tool_name}: "
                        f"{event.file_path}"
                    )
            elif name in ("bash", "execute"):
                if event.tool_input:
                    self._changelog.add_command(
                        event.tool_input,
                    )
                    self._changelog.add_change(
                        f"Executed: "
                        f"{event.tool_input[:200]}"
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

            # Notify user based on guardian decision
            if decision == Decision.AUTO_APPROVE:
                ghost_status.add_log(
                    f"[green]Auto-approved:[/green] "
                    f"{cmd_str[:60]}"
                )
                ghost_status.stats.record_auto_approve()
            else:
                # ASK_USER: notify via Telegram/screen
                ghost_status.add_log(
                    f"[yellow]⚠ User attention:[/yellow]"
                    f" {cmd_str[:60]}"
                )
                ghost_status.stats.record_auto_approve()
                msg = format_approval_message(
                    cmd_str, category,
                )
                self._notify(msg)

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

        if pct >= 80 and not self._budget_warning_sent:
            self._budget_warning_sent = True
            ghost_status.add_log(
                f"[bold yellow]Budget warning: "
                f"{pct:.0f}% used[/bold yellow]"
            )
            self._notify(
                "⚠️ BUDGET WARNING\n"
                "\n"
                f"📊 Usage: {pct:.0f}%\n"
                f"💰 Used: ${cost:.4f} / ${budget:.2f}\n"
                "\n"
                "Session will stop at budget limit."
            )

        if cost >= budget and not self._budget_warned:
            self._budget_warned = True
            self._budget_paused = True
            ghost_status.add_log(
                "[bold red]BUDGET EXCEEDED — "
                "paused[/bold red]"
            )
            ghost_status.state = "BUDGET_PAUSE"
            self._bridge.kill()
            self._request_approval(
                "⛔ BUDGET REACHED\n"
                "\n"
                f"💰 Used: ${cost:.4f} / ${budget:.2f}\n"
                "   Execution stopped.\n"
                "\n"
                "Reply:\n"
                "  T <amount> - 💵 Top-up\n"
                "  S - 🛑 Stop session"
            )

    def _handle_budget_reply(self, reply: str) -> bool:
        """Handle a reply while in budget-paused state."""
        if not self._budget_paused:
            return False

        upper = reply.strip().upper()

        if upper.startswith("S") or upper.startswith("D"):
            self._budget_paused = False
            ghost_status.add_log(
                "[red]User stopped after budget "
                "limit.[/red]"
            )
            ghost_status.state = "EXITED"
            self._notify(
                "🛑 Session ended by user (budget limit)."
            )
            self._shutdown.set()
            return True

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
                    "❓ Invalid amount.\n"
                    "\n"
                    "Reply:\n"
                    "  T <amount> - 💵 Top-up\n"
                    "  S - 🛑 Stop session"
                )
                return True

            old_budget = self.config.budget_usd
            new_budget = old_budget + topup
            self.config.budget_usd = new_budget
            settings.max_budget_usd = new_budget
            ghost_status.budget_max = new_budget

            self._budget_warned = False
            self._budget_warning_sent = False
            self._budget_paused = False

            ghost_status.add_log(
                f"[green]Budget topped up: "
                f"${old_budget:.2f} → "
                f"${new_budget:.2f}[/green]"
            )
            self._notify(
                f"✅ Budget updated: ${new_budget:.2f}\n"
                f"▶️ Resuming task..."
            )

            self._restarting = True
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
            self._restarting = False
            ghost_status.state = "RUNNING"
            return True

        self._notify(
            "⏸️ Budget paused.\n"
            "\n"
            "Reply:\n"
            "  T <amount> - 💵 Top-up\n"
            "  S - 🛑 Stop session"
        )
        return True

    def _send_summary(self) -> None:
        try:
            self._send_summary_inner()
        except Exception as exc:
            logger.exception(
                "Summary generation failed: %s", exc,
            )
            ghost_status.add_log(
                f"[bold red]Summary error: "
                f"{str(exc)[:80]}[/bold red]"
            )
            # Try to send a minimal notification
            try:
                self._notify(
                    f"⚠️ Session ended but summary "
                    f"generation failed: {str(exc)[:200]}"
                )
            except Exception:
                pass

    def _send_summary_inner(self) -> None:
        assert self._bridge is not None
        s = ghost_status.stats
        turns = self._bridge.num_turns

        # Populate changelog with full session data
        self._changelog.activity_log = (
            ghost_status.get_plain_logs()
        )
        self._changelog.event_log = (
            ghost_status.get_plain_events()
        )
        self._changelog.stats_data = {
            "model": ghost_status.model,
            "afk_level": ghost_status.afk_level,
            "level_name": ghost_status.level_name,
            "budget_used": self._bridge.total_cost,
            "budget_max": self.config.budget_usd,
            "elapsed": s.elapsed_formatted,
            "turns": turns,
            "queries_total": s.queries_total,
            "queries_auto": s.queries_auto_approved,
            "queries_user": s.queries_user_approved,
            "queries_blocked": s.queries_blocked,
            "commands": s.commands_executed,
            "telegram_enabled": ghost_status.telegram_enabled,
            "telegram_sent": s.telegram_sent,
            "telegram_received": s.telegram_received,
        }

        # Determine session status
        if self._session_terminated:
            status_emoji = "💀"
            status_text = "Session Terminated by User"
        elif self._session_failed:
            status_emoji = "❌"
            status_text = "Session Completed with Error"
        elif self._session_completed:
            status_emoji = "✅"
            status_text = "Task COMPLETED"
        else:
            status_emoji = "⚠️"
            status_text = "Session ENDED"

        self._changelog.session_outcome = (
            f"{status_emoji} {status_text}"
        )
        if self._session_error_message:
            self._changelog.session_error = (
                self._session_error_message
            )

        self._changelog.finalize()
        changelog_path = self._changelog.save()

        summary = (
            f"{status_emoji} {status_text}\n"
            "\n"
            f"📋 Task: {self._original_task}\n"
            f"⏱ Duration: {s.elapsed_formatted}\n"
            f"💰 Cost: ${self._bridge.total_cost:.4f}"
            f" / ${self.config.budget_usd:.2f}\n"
            f"🔄 Turns: {turns}\n"
            f"📊 Queries: {s.queries_total} "
            f"(auto:{s.queries_auto_approved} "
            f"user:{s.queries_user_approved} "
            f"blocked:{s.queries_blocked})\n"
            f"⚡ Commands: {s.commands_executed}\n"
        )
        if self._session_failed and self._session_error_message:
            summary += (
                f"\n⚠️ Error: {self._session_error_message}\n"
            )

        # Files & commands summary
        files = self._changelog.files_modified
        cmds = self._changelog.commands_executed
        summary += "\n"
        if files:
            summary += (
                f"📂 Files modified ({len(files)}):\n"
            )
            for f in files[-10:]:
                summary += f"  • {f}\n"
        else:
            summary += "📂 Files modified: 0\n"
        if cmds:
            summary += (
                f"⚡ Commands executed ({len(cmds)}):\n"
            )
            for c in cmds[-5:]:
                summary += f"  • {c[:80]}\n"
        else:
            summary += "⚡ Commands executed: 0\n"

        self._notify(summary)

        if changelog_path and self._telegram:
            try:
                self._telegram.send_file(
                    str(changelog_path),
                    caption="📄 Session changelog",
                )
            except Exception as exc:
                logger.error(
                    "Failed to send changelog: %s", exc,
                )

        ghost_status.add_log(
            "[bold green]Session complete.[/bold green]"
        )
        console.print("\n")
        console.rule(
            f"[bold green]{status_text}"
            f"[/bold green]"
        )
        console.print(
            f"  Duration: {s.elapsed_formatted}"
        )
        console.print(
            f"  Cost: ${self._bridge.total_cost:.4f}"
            f" / ${self.config.budget_usd:.2f}"
        )
        console.print(f"  Turns: {turns}")
        if s.queries_total > 0:
            console.print(
                f"  Queries: {s.queries_total} total"
            )
        if self._session_failed:
            console.print(
                f"  [red]Error: "
                f"{self._session_error_message}[/red]"
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
        description=(
            "Headless Supervisor for the Anthropic "
            "Claude CLI"
        ),
    )
    parser.add_argument(
        "task", nargs="?", default=None,
        help="Task/prompt for claude",
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
        help="Disable Telegram notifications",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Force interactive mode",
    )
    parser.add_argument(
        "--model", "-m", type=str, default=None,
        help="Claude model",
    )
    args = parser.parse_args()

    # Auto-update (skipped if already handled by
    # claudeghost.py or a previous re-exec).
    if "--skip-update" not in sys.argv:
        updated = auto_update()
        if updated:
            sys.stdout.flush()
            sys.stderr.flush()
            mods_to_drop = [
                k for k in sys.modules
                if k.startswith("src.") or k == "src"
            ]
            for k in mods_to_drop:
                del sys.modules[k]
            sys.argv.append("--skip-update")
            from src.main import main as _main
            _main()
            return

    # Clean up the flag so argparse doesn't choke
    if "--skip-update" in sys.argv:
        sys.argv.remove("--skip-update")
    console.print()

    while True:
        if args.interactive or args.task is None:
            config = run_interactive_launcher()
            if config is None:
                sys.exit(0)
        else:
            config = run_quick_launcher(
                task=args.task,
                level=(
                    args.level
                    or settings.default_afk_level
                ),
                budget=(
                    args.budget
                    or settings.max_budget_usd
                ),
                telegram=not args.no_telegram,
                model=args.model,
            )
            console.print(
                f"[bold blue]ClaudeGhost "
                f"v{__version__}[/bold blue]"
            )
            console.print(f"  Task  : {config.task[:60]}")
            console.print(f"  Model : {config.model}")
            console.print(
                f"  Level : {config.afk_level}"
                f" ({config.level_name})"
            )
            console.print(
                f"  Budget: ${config.budget_usd:.2f}"
            )
            notify = (
                "Telegram" if config.telegram_enabled
                else "Screen"
            )
            console.print(f"  Notify: {notify}")
            console.print()

        ghost = ClaudeGhost(config=config)
        ghost.run()

        console.print()
        try:
            another = Confirm.ask(
                "[bold]Start another session?[/bold]",
                default=False,
            )
            if not another:
                console.print("[green]Goodbye![/green]")
                break
        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        args.task = None
        args.interactive = True
        console.print()


if __name__ == "__main__":
    main()
