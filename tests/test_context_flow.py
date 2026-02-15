"""Tests for the Context (C) flow, approval flow, and bridge restart logic.

Simulates user interactions via Telegram-like replies without spawning
a real Claude CLI process. Includes Telegram message verification.
"""
import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Helpers ────────────────────────────────────────────────────────────────

class FakeTelegram:
    """Simulates TelegramBot — records sent messages and lets tests
    inject user replies via the registered callback."""

    def __init__(self):
        self.sent: list[str] = []
        self.files_sent: list[str] = []
        self._callback = None

    def start_polling(self, callback):
        self._callback = callback

    def stop_polling(self):
        self._callback = None

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True

    def send_file(self, path: str, caption: str = "") -> bool:
        self.files_sent.append(path)
        return True

    def inject_reply(self, text: str):
        """Simulate a user sending a Telegram message."""
        if self._callback:
            self._callback(text)


def _make_ghost(task="create daniel4.md", afk_level=1, use_telegram=True):
    """Create a ClaudeGhost with mocked bridge and optional fake Telegram."""
    from src.config import SessionConfig
    from src.main import ClaudeGhost

    config = SessionConfig(
        task=task,
        afk_level=afk_level,
        budget_usd=0.50,
        telegram_enabled=use_telegram,
        model="sonnet",
    )
    ghost = ClaudeGhost(config=config)

    # Mock the bridge so we don't spawn a real process
    ghost._bridge = MagicMock()
    ghost._bridge.state = "THINKING"
    ghost._bridge.total_cost = 0.0
    ghost._bridge.num_turns = 1

    if use_telegram:
        # Replace real TelegramBot with our fake
        fake_tg = FakeTelegram()
        ghost._telegram = fake_tg
        ghost._screen = None
        # Wire up the reply callback (normally done by ghost.run())
        fake_tg.start_polling(ghost._handle_reply)
    else:
        ghost._telegram = None

    return ghost


def _patch_bridge_constructor():
    """Returns a context manager that captures tasks passed to new bridges."""
    captured = []

    from src.bridge import GhostBridge
    original_init = GhostBridge.__init__

    def mock_init(self_bridge, task, **kwargs):
        captured.append(task)
        self_bridge.task = task
        self_bridge._state = "THINKING"
        self_bridge._running = False
        self_bridge._total_cost = 0.0
        self_bridge._num_turns = 0
        self_bridge._lock = __import__('threading').Lock()
        self_bridge._last_output_time = __import__('time').time()
        self_bridge._approval_event = __import__('threading').Event()
        self_bridge._approval_event.set()
        self_bridge.start = MagicMock()
        self_bridge.kill = MagicMock()
        self_bridge.send = MagicMock()

    return patch.object(GhostBridge, '__init__', mock_init), captured


# ── Core Context Flow Tests ───────────────────────────────────────────────

def test_original_task_stored():
    """_original_task should always hold the initial task."""
    ghost = _make_ghost("create daniel4.md")
    assert ghost._original_task == "create daniel4.md"
    assert ghost.task == "create daniel4.md"
    print("[PASS] _original_task stored correctly")


def test_context_c_text_y():
    """C -> type context -> Y: new task has original + context, no newlines."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("C")
        assert ghost._context_state == "awaiting_text"
        assert any("Type your context" in m for m in tg.sent)

        tg.inject_reply("change the file name to daniel5.md")
        assert ghost._context_state == "awaiting_confirm"
        assert any("daniel5.md" in m for m in tg.sent)

        tg.inject_reply("Y")

    assert ghost._context_state is None
    assert len(captured) == 1
    new_task = captured[0]
    assert "create daniel4.md" in new_task
    assert "daniel5.md" in new_task
    assert "OVERRIDE" in new_task
    assert "\n" not in new_task, f"Newlines in task: {repr(new_task)}"
    assert any("Restarting" in m for m in tg.sent)
    print("[PASS] Context C -> text -> Y (with Telegram)")


def test_context_c_text_n():
    """C -> type context -> N: cancels, task unchanged."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    tg.inject_reply("C")
    tg.inject_reply("rename to daniel5.md")
    tg.inject_reply("N")

    assert ghost._context_state is None
    assert ghost._pending_context is None
    assert ghost.task == "create daniel4.md"
    assert any("cancelled" in m.lower() for m in tg.sent)
    print("[PASS] Context C -> text -> N cancels (with Telegram)")


def test_context_c_text_m_text_y():
    """C -> text -> M -> new text -> Y: modify then accept."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("C")
        tg.inject_reply("rename to daniel5.md")
        assert ghost._context_state == "awaiting_confirm"

        tg.inject_reply("M")
        assert ghost._context_state == "awaiting_text"

        tg.inject_reply("actually rename to daniel6.md")
        assert ghost._pending_context == "actually rename to daniel6.md"

        tg.inject_reply("Y")

    assert len(captured) == 1
    assert "daniel6.md" in captured[0]
    assert "daniel5.md" not in captured[0]
    print("[PASS] Context C -> text -> M -> text -> Y (with Telegram)")


def test_context_inline():
    """C rename to daniel5.md: inline context skips to confirm."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    tg.inject_reply("C rename to daniel5.md")
    assert ghost._context_state == "awaiting_confirm"
    assert ghost._pending_context == "rename to daniel5.md"
    assert any("daniel5.md" in m for m in tg.sent)
    print("[PASS] Inline context C <text> (with Telegram)")


def test_context_preserves_original_across_multiple():
    """Multiple context changes always build from the original task."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        # First context change
        tg.inject_reply("C")
        tg.inject_reply("rename to daniel5.md")
        tg.inject_reply("Y")

        # Second context change
        tg.inject_reply("C")
        tg.inject_reply("rename to daniel6.md")
        tg.inject_reply("Y")

    assert ghost._original_task == "create daniel4.md"
    assert len(captured) == 2
    # Both tasks should reference the ORIGINAL, not each other
    assert "create daniel4.md" in captured[0]
    assert "create daniel4.md" in captured[1]
    assert "daniel5.md" in captured[0]
    assert "daniel6.md" in captured[1]
    # Second task should NOT contain daniel5.md (no accumulation)
    assert "daniel5.md" not in captured[1]
    print("[PASS] Original task preserved across multiple context changes")


# ── Approval / Block / Detonate Tests ─────────────────────────────────────

def test_approve_sends_y():
    """A sends 'y' to bridge and records stats."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram
    ghost._pending_query = "Write: daniel4.md"

    tg.inject_reply("A")
    ghost._bridge.send.assert_called_with("y")
    assert ghost._pending_query is None
    from src.utils import ghost_status
    print("[PASS] Approve (A) sends y to bridge (with Telegram)")


def test_block_restarts_bridge():
    """B kills bridge and restarts with 'blocked' instruction."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram
    ghost._pending_query = "Write: daniel4.md"
    old_bridge = ghost._bridge

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("B")

    old_bridge.kill.assert_called_once()
    assert len(captured) == 1
    assert "blocked" in captured[0].lower()
    assert ghost._pending_query is None
    print("[PASS] Block (B) kills and restarts (with Telegram)")


def test_detonate_kills_session():
    """D kills bridge and sets shutdown event."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    tg.inject_reply("D")
    ghost._bridge.kill.assert_called_once()
    assert ghost._shutdown.is_set()
    assert any("terminated" in m.lower() for m in tg.sent)
    print("[PASS] Detonate (D) kills session (with Telegram)")


def test_unknown_reply_shows_help():
    """Unknown reply shows the A/B/C/D menu."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    tg.inject_reply("X")
    assert any("Approve" in m and "Block" in m for m in tg.sent)
    print("[PASS] Unknown reply shows help menu (with Telegram)")


# ── Telegram Message Format Tests ─────────────────────────────────────────

def test_telegram_no_box_drawing():
    """No ╔║╚ box-drawing characters in any Telegram message."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    # Trigger various messages
    tg.inject_reply("C")
    tg.inject_reply("rename file")
    tg.inject_reply("N")
    tg.inject_reply("X")

    box_chars = set("╔╗╚╝║═┌┐└┘│─")
    for msg in tg.sent:
        found = [c for c in msg if c in box_chars]
        assert not found, (
            f"Box-drawing chars {found} in message: {msg[:80]}"
        )
    print("[PASS] No box-drawing characters in Telegram messages")


def test_telegram_started_message_format():
    """ClaudeGhost Started message uses ━ borders, not ╔║╚."""
    from src.config import SessionConfig
    from src.main import ClaudeGhost

    config = SessionConfig(
        task="test task",
        afk_level=2,
        budget_usd=1.00,
        telegram_enabled=True,
        model="sonnet",
    )
    ghost = ClaudeGhost(config=config)
    fake_tg = FakeTelegram()
    ghost._telegram = fake_tg
    ghost._screen = None

    # Simulate what run() does for the start message
    ghost._notify(
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  👻 ClaudeGhost Started\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📋 Task: {ghost.task}\n"
        f"🤖 AFK Level: {ghost.afk_level} ({ghost.config.level_name})\n"
        f"💰 Budget (Limit/Quota): ${ghost.config.budget_usd:.2f}"
    )

    assert len(fake_tg.sent) == 1
    msg = fake_tg.sent[0]
    assert "━" in msg
    assert "╔" not in msg
    assert "║" not in msg
    assert "Budget (Limit/Quota)" in msg
    print("[PASS] Started message uses ━ borders")


def test_guardian_approval_message_format():
    """Guardian approval message uses ━ borders."""
    from src.guardian import format_approval_message, RiskCategory
    msg = format_approval_message("Write: daniel4.md", RiskCategory.WRITE)
    assert "━" in msg
    assert "╔" not in msg
    assert "║" not in msg
    assert "ACTION DETECTED" in msg
    assert "Approve" in msg
    print("[PASS] Guardian approval message uses ━ borders")


# ── Restarting Flag Tests ─────────────────────────────────────────────────

def test_restarting_flag_prevents_exit():
    """_restarting flag prevents _run_loop from breaking on EXITED state."""
    ghost = _make_ghost("create daniel4.md")
    assert ghost._restarting is False

    ghost._restarting = True
    ghost._bridge.state = "EXITED"
    should_break = (
        ghost._bridge.state == "EXITED"
        and not ghost._budget_paused
        and not ghost._restarting
    )
    assert not should_break, "Run loop would exit during restart!"

    ghost._restarting = False
    should_break = (
        ghost._bridge.state == "EXITED"
        and not ghost._budget_paused
        and not ghost._restarting
    )
    assert should_break
    print("[PASS] _restarting flag prevents premature exit")


def test_block_sets_restarting_flag():
    """Block (B) sets _restarting before kill, clears after start."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram
    ghost._pending_query = "Write: daniel4.md"

    restarting_during_kill = []

    original_kill = ghost._bridge.kill
    def track_kill():
        restarting_during_kill.append(ghost._restarting)
        original_kill()
    ghost._bridge.kill = track_kill

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("B")

    assert restarting_during_kill == [True], (
        f"_restarting was {restarting_during_kill} during kill"
    )
    assert ghost._restarting is False
    print("[PASS] Block sets _restarting during kill/restart cycle")


def test_context_y_sets_restarting_flag():
    """Context Y sets _restarting before kill, clears after start."""
    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    restarting_during_kill = []
    original_kill = ghost._bridge.kill
    def track_kill():
        restarting_during_kill.append(ghost._restarting)
        original_kill()
    ghost._bridge.kill = track_kill

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("C")
        tg.inject_reply("rename to daniel5.md")
        tg.inject_reply("Y")

    assert restarting_during_kill == [True]
    assert ghost._restarting is False
    print("[PASS] Context Y sets _restarting during kill/restart cycle")


# ── Ghost Status / Changelog Tests ────────────────────────────────────────

def test_ghost_status_plain_logs():
    """get_plain_logs strips Rich markup."""
    from src.utils import ghost_status
    ghost_status.reset()
    ghost_status.add_log("[bold green]Test message[/bold green]")
    ghost_status.add_event("[cyan]Event here[/cyan]")

    logs = ghost_status.get_plain_logs()
    events = ghost_status.get_plain_events()

    assert len(logs) >= 1
    assert len(events) >= 1
    assert "[bold green]" not in logs[-1]
    assert "Test message" in logs[-1]
    assert "[cyan]" not in events[-1]
    assert "Event here" in events[-1]
    print("[PASS] Plain log stripping works")


def test_changelog_includes_stats():
    """Changelog includes stats, activity log, and events."""
    from src.changelog import ChangeLog

    cl = ChangeLog("test task", "test-session-id")
    cl.activity_log = ["18:00:00 Started", "18:01:00 Auto-approved: ls"]
    cl.event_log = ["18:00:01 Initialized model=sonnet"]
    cl.stats_data = {
        "model": "sonnet",
        "afk_level": 1,
        "level_name": "Paranoid",
        "budget_used": 0.05,
        "budget_max": 0.50,
        "elapsed": "1m 30s",
        "turns": 5,
        "queries_total": 3,
        "queries_auto": 1,
        "queries_user": 1,
        "queries_blocked": 1,
        "commands": 2,
        "telegram_enabled": True,
        "telegram_sent": 4,
        "telegram_received": 2,
    }
    cl.add_command("ls -la")
    cl.add_file_change("daniel4.md")
    cl.finalize()

    content = cl._build_changelog_content("1m 30s")
    assert "Session Statistics" in content
    assert "sonnet" in content
    assert "Paranoid" in content
    assert "Activity Log" in content
    assert "Claude Code Events" in content
    assert "Telegram I/O" in content
    assert "daniel4.md" in content
    assert "ls -la" in content
    print("[PASS] Changelog includes full session data")


def test_context_event_logged():
    """Context Y adds an event to ghost_status for terminal visibility."""
    from src.utils import ghost_status
    ghost_status.reset()

    ghost = _make_ghost("create daniel4.md")
    tg = ghost._telegram

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("C")
        tg.inject_reply("rename to daniel5.md")
        tg.inject_reply("Y")

    events = ghost_status.get_plain_events()
    # Should have a "User context applied" event
    context_events = [e for e in events if "context applied" in e.lower()]
    assert len(context_events) >= 1, (
        f"No context event found in: {events}"
    )
    assert "daniel5.md" in context_events[0]
    print("[PASS] Context Y logs event to terminal")


# ── Full Telegram Conversation Simulation ─────────────────────────────────

def test_full_telegram_flow_approve():
    """Simulate full flow: start -> tool detected -> A (approve)."""
    ghost = _make_ghost("create daniel4.md", afk_level=1)
    tg = ghost._telegram

    # Simulate a tool query arriving from bridge
    ghost._handle_query(
        "Do you want to run this tool?\n  Write: daniel4.md"
    )
    # Should have sent approval request
    assert any("ACTION DETECTED" in m for m in tg.sent), (
        f"No ACTION DETECTED in: {tg.sent}"
    )
    assert ghost._pending_query is not None

    # User approves
    tg.inject_reply("A")
    ghost._bridge.send.assert_called_with("y")
    assert ghost._pending_query is None
    print("[PASS] Full Telegram flow: query -> A (approve)")


def test_full_telegram_flow_context_override():
    """Simulate: start -> tool detected -> C -> text -> Y -> new bridge."""
    ghost = _make_ghost("create daniel4.md", afk_level=1)
    tg = ghost._telegram

    # Tool query arrives
    ghost._handle_query(
        "Do you want to run this tool?\n  Write: daniel4.md"
    )
    assert ghost._pending_query is not None

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        # User presses C
        tg.inject_reply("C")
        assert ghost._context_state == "awaiting_text"

        # User types context
        tg.inject_reply("change the file name to daniel5.md")
        assert ghost._context_state == "awaiting_confirm"

        # User confirms
        tg.inject_reply("Y")

    assert ghost._context_state is None
    assert len(captured) == 1
    assert "daniel5.md" in captured[0]
    assert "create daniel4.md" in captured[0]
    assert "\n" not in captured[0]

    # Verify Telegram message sequence
    msg_types = []
    for m in tg.sent:
        if "ACTION DETECTED" in m:
            msg_types.append("ACTION")
        elif "Type your context" in m:
            msg_types.append("PROMPT")
        elif "Your context change" in m:
            msg_types.append("CONFIRM")
        elif "Restarting" in m:
            msg_types.append("RESTART")

    assert msg_types == ["ACTION", "PROMPT", "CONFIRM", "RESTART"], (
        f"Unexpected message sequence: {msg_types}"
    )
    print("[PASS] Full Telegram flow: query -> C -> text -> Y")


def test_full_telegram_flow_block_then_approve():
    """Simulate: tool detected -> B (block) -> new tool -> A (approve)."""
    ghost = _make_ghost("create daniel4.md", afk_level=1)
    tg = ghost._telegram

    ghost._handle_query(
        "Do you want to run this tool?\n  Write: daniel4.md"
    )

    patcher, captured = _patch_bridge_constructor()
    with patcher:
        tg.inject_reply("B")

    assert len(captured) == 1
    assert "blocked" in captured[0].lower()
    assert ghost._pending_query is None

    # New bridge sends another query
    ghost._handle_query(
        "Do you want to run this tool?\n  Edit: daniel4.md"
    )
    assert ghost._pending_query is not None

    tg.inject_reply("A")
    ghost._bridge.send.assert_called_with("y")
    print("[PASS] Full Telegram flow: query -> B -> new query -> A")


# ── Runner ────────────────────────────────────────────────────────────────

def run_all():
    tests = [
        test_original_task_stored,
        test_context_c_text_y,
        test_context_c_text_n,
        test_context_c_text_m_text_y,
        test_context_inline,
        test_context_preserves_original_across_multiple,
        test_approve_sends_y,
        test_block_restarts_bridge,
        test_detonate_kills_session,
        test_unknown_reply_shows_help,
        test_telegram_no_box_drawing,
        test_telegram_started_message_format,
        test_guardian_approval_message_format,
        test_restarting_flag_prevents_exit,
        test_block_sets_restarting_flag,
        test_context_y_sets_restarting_flag,
        test_ghost_status_plain_logs,
        test_changelog_includes_stats,
        test_context_event_logged,
        test_full_telegram_flow_approve,
        test_full_telegram_flow_context_override,
        test_full_telegram_flow_block_then_approve,
    ]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all()
    print(f"\nContext Flow Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
