"""Tests for AFK level enforcement in ClaudeGhost.

Covers session loop exit conditions, reply handler behavior,
approve/block/detonate paths, and autonomy matrix correctness.
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.bridge import CliState
from src.config import SessionConfig
from src.guardian import Decision, RiskCategory, evaluate, _AUTONOMY_MATRIX
from src.main import ClaudeGhost


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockBridge:
    """Controllable stand-in for GhostBridge."""

    def __init__(self, state: CliState = CliState.IDLE) -> None:
        self._state = state
        self.sent: list[str] = []
        self.killed = False
        self.started = False

    @property
    def state(self) -> CliState:
        return self._state

    @state.setter
    def state(self, value: CliState) -> None:
        self._state = value

    @property
    def total_cost(self) -> float:
        return 0.0

    @property
    def num_turns(self) -> int:
        return 0

    def send(self, text: str) -> None:
        self.sent.append(text)

    def kill(self) -> None:
        self.killed = True
        self._state = CliState.EXITED

    def start(self) -> None:
        self.started = True
        self._state = CliState.IDLE


class MockScreenNotifier:
    """Controllable stand-in for ScreenNotifier."""

    def __init__(self) -> None:
        self.approvals: list[str] = []
        self.infos: list[str] = []
        self._callback = None

    def set_callback(self, callback):
        self._callback = callback

    def request_approval(self, message: str) -> None:
        self.approvals.append(message)

    def send_info(self, message: str) -> None:
        self.infos.append(message)

    def check_pending(self) -> bool:
        return False

    def process_pending(self) -> None:
        pass

    def disable(self) -> None:
        pass


def make_ghost(
    afk_level: int = 3,
    bridge_state: CliState = CliState.IDLE,
) -> tuple[ClaudeGhost, MockBridge]:
    """Create a ClaudeGhost wired to mock dependencies.

    Returns (ghost, mock_bridge).
    """
    config = SessionConfig(
        task="test task",
        afk_level=afk_level,
        budget_usd=5.0,
        telegram_enabled=False,
    )
    ghost = ClaudeGhost(config)

    bridge = MockBridge(state=bridge_state)
    ghost._bridge = bridge

    screen = MockScreenNotifier()
    ghost._screen = screen
    ghost._telegram = None

    return ghost, bridge


# ---------------------------------------------------------------------------
# Unit tests (Req 1.x, 2.x, 4.x, 5.x)
# ---------------------------------------------------------------------------

def test_session_loop_exits_when_no_pending_query():
    """_run_loop exits when bridge EXITED and no pending query.

    Validates: Requirement 1.2
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    # No pending query — loop should break immediately
    assert ghost._pending_query is None

    # Run the loop in a thread with a timeout so we don't hang
    finished = threading.Event()

    def run():
        ghost._run_loop()
        finished.set()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    assert finished.wait(timeout=5), "_run_loop did not exit within 5s"
    assert ghost._session_completed is True


def test_session_loop_continues_with_pending_query():
    """_run_loop does NOT exit when bridge EXITED but pending query is set.

    Validates: Requirements 1.1, 1.3
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    with ghost._pending_lock:
        ghost._pending_query = "mkdir test"

    exited = threading.Event()

    def run():
        ghost._run_loop()
        exited.set()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    # Loop should NOT exit while pending query is set
    assert not exited.wait(timeout=2), "_run_loop exited despite pending query"

    # Clear the pending query — loop should now exit
    with ghost._pending_lock:
        ghost._pending_query = None
    assert exited.wait(timeout=5), "_run_loop did not exit after clearing pending query"
    assert ghost._session_completed is True


def test_reply_handler_discards_when_no_pending():
    """_handle_reply_inner returns early when bridge EXITED and no pending query.

    Validates: Requirement 2.2
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    assert ghost._pending_query is None

    # Should silently discard — no side effects
    ghost._handle_reply_inner("A")
    assert bridge.sent == []


def test_reply_handler_processes_when_pending():
    """_handle_reply_inner processes reply when bridge EXITED and pending query set.

    Validates: Requirement 2.1
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    with ghost._pending_lock:
        ghost._pending_query = "mkdir test"

    ghost._handle_reply_inner("A")
    # Pending query should be cleared
    assert ghost._pending_query is None


def test_approve_clears_pending_when_bridge_exited():
    """Approve clears _pending_query when bridge is EXITED.

    Validates: Requirement 2.3
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    with ghost._pending_lock:
        ghost._pending_query = "touch file.txt"

    ghost._handle_reply_inner("A")
    assert ghost._pending_query is None
    # Should NOT send "y" to a dead bridge
    assert "y" not in bridge.sent


def test_approve_sends_y_to_live_bridge():
    """Approve sends 'y' to bridge when bridge is alive.

    Validates: Requirement 4.3
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.QUERY
    with ghost._pending_lock:
        ghost._pending_query = "touch file.txt"

    ghost._handle_reply_inner("A")
    assert ghost._pending_query is None
    assert "y" in bridge.sent


def test_approve_does_not_send_y_to_exited_bridge():
    """Approve does NOT send 'y' when bridge is EXITED.

    Validates: Requirement 2.3
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.EXITED
    with ghost._pending_lock:
        ghost._pending_query = "mkdir test"

    ghost._handle_reply_inner("A")
    assert "y" not in bridge.sent
    assert ghost._pending_query is None


def test_block_sends_n_kills_restarts():
    """Block sends 'n', kills bridge, restarts with new bridge.

    Validates: Requirement 4.4
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.QUERY
    with ghost._pending_lock:
        ghost._pending_query = "rm -rf /"

    # Patch GhostBridge constructor so the restart creates a MockBridge
    new_bridge = MockBridge(state=CliState.IDLE)
    with patch("src.main.GhostBridge", return_value=new_bridge):
        ghost._handle_reply_inner("B")

    # Original bridge should have received "n" and been killed
    assert "n" in bridge.sent
    assert bridge.killed is True
    # Pending query cleared
    assert ghost._pending_query is None
    # New bridge should have been started
    assert new_bridge.started is True
    assert ghost._bridge is new_bridge


def test_detonate_kills_and_terminates():
    """Detonate kills bridge and terminates session.

    Validates: Requirement 4.5
    """
    ghost, bridge = make_ghost()
    bridge.state = CliState.QUERY
    with ghost._pending_lock:
        ghost._pending_query = "rm -rf /"

    ghost._handle_reply_inner("D")

    assert bridge.killed is True
    assert ghost._pending_query is None
    assert ghost._session_terminated is True
    assert ghost._shutdown.is_set()


def test_level1_triggers_approval_for_write():
    """Level 1 triggers approval for 'create test.md' write command.

    Validates: Requirement 5.5
    """
    ghost, bridge = make_ghost(afk_level=1)
    bridge.state = CliState.QUERY

    # Simulate a query that contains a write command
    query_text = (
        "Do you want to run this tool?\n"
        "  Write: test.md"
    )
    ghost._handle_query_inner(query_text)

    # At level 1, everything is ASK_USER — pending query should be set
    assert ghost._pending_query is not None
    # Bridge should NOT have received "y" (no auto-approve)
    assert "y" not in bridge.sent
    # Screen notifier should have an approval request
    assert len(ghost._screen.approvals) > 0


# ---------------------------------------------------------------------------
# Parametrized autonomy matrix test (Req 3.x / 5.1)
# ---------------------------------------------------------------------------

# Expected matrix: level -> {category: decision}
_EXPECTED_MATRIX = {
    1: {
        RiskCategory.READ_ONLY: Decision.ASK_USER,
        RiskCategory.WRITE: Decision.ASK_USER,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    2: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.ASK_USER,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    3: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    4: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.AUTO_APPROVE,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    5: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.AUTO_APPROVE,
        RiskCategory.HIGH_RISK: Decision.AUTO_APPROVE,
    },
}

# Representative commands per risk category
_CATEGORY_COMMANDS = {
    RiskCategory.READ_ONLY: "ls -la",
    RiskCategory.WRITE: "mkdir testdir",
    RiskCategory.EXECUTE: "npm install",
    RiskCategory.HIGH_RISK: "rm -rf /tmp/test",
}

_MATRIX_PARAMS = [
    (level, cat, _CATEGORY_COMMANDS[cat], _EXPECTED_MATRIX[level][cat])
    for level in range(1, 6)
    for cat in RiskCategory
]


@pytest.mark.parametrize(
    "level,category,command,expected_decision",
    _MATRIX_PARAMS,
    ids=[
        f"L{level}-{cat.name}"
        for level in range(1, 6)
        for cat in RiskCategory
    ],
)
def test_each_afk_level_matrix(level, category, command, expected_decision):
    """Verify correct Decision for every AFK level / RiskCategory pair.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 5.1
    """
    decision, classified_cat = evaluate(command, level)
    assert classified_cat == category, (
        f"Command '{command}' classified as {classified_cat.name}, "
        f"expected {category.name}"
    )
    assert decision == expected_decision, (
        f"Level {level}, {category.name}: got {decision.name}, "
        f"expected {expected_decision.name}"
    )
