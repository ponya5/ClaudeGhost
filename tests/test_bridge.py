"""Tests for bridge (PTY/subprocess wrapper) module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    from src.bridge import GhostBridge, CliState, strip_ansi
    assert all([GhostBridge, CliState, strip_ansi])
    print("[PASS] Bridge imports successful")
    return True


def test_cli_states():
    from src.bridge import CliState
    assert CliState.IDLE == "IDLE"
    assert CliState.QUERY == "QUERY"
    assert CliState.THINKING == "THINKING"
    assert CliState.EXITED == "EXITED"
    print("[PASS] CliState enum correct")
    return True


def test_strip_ansi():
    from src.bridge import strip_ansi
    assert strip_ansi("hello world") == "hello world"
    assert strip_ansi("\x1b[32mgreen\x1b[0m") == "green"
    assert strip_ansi("\x1b[1mbold\x1b[0m") == "bold"
    assert strip_ansi("\x1b[38;5;196mred\x1b[0m text") == "red text"
    print("[PASS] ANSI stripping works")
    return True


def test_bridge_init():
    from src.bridge import GhostBridge, CliState
    bridge = GhostBridge(task="test task", on_query=lambda x: None)
    assert bridge.task == "test task"
    assert bridge.state == CliState.THINKING
    assert bridge.total_cost == 0.0
    assert not bridge._running
    print("[PASS] GhostBridge initialized correctly")
    return True


def test_query_detection_patterns():
    from src.bridge import _QUERY_RE, _TOOL_QUERY_RE
    assert _QUERY_RE.search("Do you want to run this command?")
    assert _QUERY_RE.search("(y/n)")
    assert _TOOL_QUERY_RE.search("claude wants to run bash")
    assert _TOOL_QUERY_RE.search("tool: write_file")
    print("[PASS] Query detection patterns work")
    return True


def test_cost_parsing_pattern():
    from src.bridge import _COST_RE
    m = _COST_RE.search("Total cost: $1.50")
    assert m and m.group(1) == "1.50"
    m = _COST_RE.search("Cost: $0.25")
    assert m and m.group(1) == "0.25"
    print("[PASS] Cost parsing works")
    return True


def run_all():
    tests = [
        test_imports,
        test_cli_states,
        test_strip_ansi,
        test_bridge_init,
        test_query_detection_patterns,
        test_cost_parsing_pattern,
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
    print(f"\nBridge Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
