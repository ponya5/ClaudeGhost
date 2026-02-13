"""Tests for utils module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    from src.utils import logger, ghost_status, console
    assert all([logger, ghost_status, console])
    print("[PASS] Utils imports successful")
    return True


def test_ghost_status_init():
    from src.utils import GhostStatus
    status = GhostStatus()
    assert status.current_task == "N/A"
    assert status.afk_level == 3
    assert status.budget_used == 0.0
    assert status.state == "STARTING"
    print("[PASS] GhostStatus initialized correctly")
    return True


def test_ghost_status_add_log():
    from src.utils import GhostStatus
    status = GhostStatus()
    status.add_log("Test message 1")
    status.add_log("Test message 2")
    assert len(status._log_lines) == 2
    print("[PASS] Log adding works")
    return True


def test_ghost_status_log_limit():
    from src.utils import GhostStatus
    status = GhostStatus()
    for i in range(350):
        status.add_log(f"Log entry {i}")
    assert len(status._log_lines) <= 300
    print("[PASS] Log limit enforced")
    return True


def test_session_stats():
    from src.utils import SessionStats
    stats = SessionStats()
    stats.record_auto_approve()
    stats.record_user_approve()
    stats.record_blocked()
    stats.record_telegram_sent()
    stats.record_telegram_received()
    assert stats.queries_total == 3
    assert stats.queries_auto_approved == 1
    assert stats.queries_user_approved == 1
    assert stats.queries_blocked == 1
    assert stats.telegram_sent == 1
    assert stats.telegram_received == 1
    print("[PASS] SessionStats tracking works")
    return True


def test_build_layout():
    from src.utils import GhostStatus
    from rich.layout import Layout
    status = GhostStatus()
    status.current_task = "Test task"
    status.state = "RUNNING"
    status.add_log("Test log entry")
    layout = status.build_layout()
    assert isinstance(layout, Layout)
    print("[PASS] Dashboard layout builds successfully")
    return True


def run_all():
    tests = [
        test_imports,
        test_ghost_status_init,
        test_ghost_status_add_log,
        test_ghost_status_log_limit,
        test_session_stats,
        test_build_layout,
    ]
    passed = failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all()
    print(f"\nUtils Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
