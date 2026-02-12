"""Tests for utils module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test utils module imports."""
    from src.utils import logger, ghost_status, console
    print("[PASS] Utils imports successful")
    return True


def test_ghost_status_init():
    """Test GhostStatus initialization."""
    from src.utils import GhostStatus
    
    status = GhostStatus()
    
    assert status.current_task == "N/A"
    assert status.afk_level == 3
    assert status.budget_used == 0.0
    assert status.budget_max == 5.0
    assert status.state == "STARTING"
    assert isinstance(status._log_lines, list)
    
    print("[PASS] GhostStatus initialized correctly")
    return True


def test_ghost_status_add_log():
    """Test adding log lines."""
    from src.utils import GhostStatus
    
    status = GhostStatus()
    
    status.add_log("Test message 1")
    status.add_log("Test message 2")
    
    assert len(status._log_lines) == 2
    assert "Test message 1" in status._log_lines[0]
    assert "Test message 2" in status._log_lines[1]
    
    print("[PASS] Log adding works")
    return True


def test_ghost_status_log_limit():
    """Test log line limit (should keep max 300)."""
    from src.utils import GhostStatus
    
    status = GhostStatus()
    
    # Add more than 300 logs
    for i in range(350):
        status.add_log(f"Log entry {i}")
    
    assert len(status._log_lines) <= 300
    
    print("[PASS] Log limit enforced")
    return True


def test_logger_exists():
    """Test that logger is configured."""
    from src.utils import logger
    
    assert logger is not None
    assert logger.name == "claudeghost"
    
    print("[PASS] Logger configured")
    return True


def test_console_exists():
    """Test that Rich console is available."""
    from src.utils import console
    from rich.console import Console
    
    assert console is not None
    assert isinstance(console, Console)
    
    print("[PASS] Rich console available")
    return True


def test_build_layout():
    """Test dashboard layout building."""
    from src.utils import GhostStatus
    from rich.layout import Layout
    
    status = GhostStatus()
    status.current_task = "Test task"
    status.state = "RUNNING"
    status.add_log("Test log entry")
    
    layout = status.build_layout()
    
    assert layout is not None
    assert isinstance(layout, Layout)
    
    print("[PASS] Dashboard layout builds successfully")
    return True


def run_all():
    """Run all utils tests."""
    tests = [
        test_imports,
        test_ghost_status_init,
        test_ghost_status_add_log,
        test_ghost_status_log_limit,
        test_logger_exists,
        test_console_exists,
        test_build_layout,
    ]
    
    passed = 0
    failed = 0
    
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
