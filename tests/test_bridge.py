"""Tests for bridge (PTY/subprocess wrapper) module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test bridge module imports."""
    from src.bridge import GhostBridge, CliState, strip_ansi
    print("[PASS] Bridge imports successful")
    return True


def test_cli_states():
    """Test CLI state enum."""
    from src.bridge import CliState
    
    assert CliState.IDLE == "IDLE"
    assert CliState.QUERY == "QUERY"
    assert CliState.THINKING == "THINKING"
    assert CliState.EXITED == "EXITED"
    
    print("[PASS] CliState enum correct")
    return True


def test_strip_ansi():
    """Test ANSI escape code stripping."""
    from src.bridge import strip_ansi
    
    # Plain text unchanged
    assert strip_ansi("hello world") == "hello world"
    
    # Color codes stripped
    assert strip_ansi("\x1b[32mgreen\x1b[0m") == "green"
    
    # Bold stripped
    assert strip_ansi("\x1b[1mbold\x1b[0m") == "bold"
    
    # Complex escape sequences
    assert strip_ansi("\x1b[38;5;196mred\x1b[0m text") == "red text"
    
    print("[PASS] ANSI stripping works")
    return True


def test_bridge_init():
    """Test GhostBridge initialization."""
    from src.bridge import GhostBridge, CliState
    
    def dummy_query(text):
        pass
    
    bridge = GhostBridge(
        task="test task",
        on_query=dummy_query,
    )
    
    assert bridge.task == "test task"
    assert bridge.state == CliState.THINKING
    assert bridge.total_cost == 0.0
    assert bridge._running == False
    
    print("[PASS] GhostBridge initialized correctly")
    return True


def test_bridge_state_property():
    """Test state property access."""
    from src.bridge import GhostBridge, CliState
    
    bridge = GhostBridge(task="test", on_query=lambda x: None)
    
    assert bridge.state == CliState.THINKING
    bridge._state = CliState.IDLE
    assert bridge.state == CliState.IDLE
    
    print("[PASS] State property works")
    return True


def test_cost_property():
    """Test total_cost property."""
    from src.bridge import GhostBridge
    
    bridge = GhostBridge(task="test", on_query=lambda x: None)
    
    assert bridge.total_cost == 0.0
    bridge._total_cost = 1.50
    assert bridge.total_cost == 1.50
    
    print("[PASS] Cost property works")
    return True


def test_query_detection_patterns():
    """Test that query detection patterns work."""
    from src.bridge import _QUERY_RE, _TOOL_QUERY_RE
    
    # Standard prompts
    assert _QUERY_RE.search("Do you want to run this command?")
    assert _QUERY_RE.search("(y/n)")
    assert _QUERY_RE.search("(Y)es or (N)o")
    assert _QUERY_RE.search("Allow this action?")
    
    # Tool queries
    assert _TOOL_QUERY_RE.search("claude wants to run bash")
    assert _TOOL_QUERY_RE.search("tool: write_file")
    
    print("[PASS] Query detection patterns work")
    return True


def test_cost_parsing_pattern():
    """Test cost parsing regex."""
    from src.bridge import _COST_RE
    
    match = _COST_RE.search("Total cost: $1.50")
    assert match
    assert match.group(1) == "1.50"
    
    match = _COST_RE.search("Cost: $0.25")
    assert match
    assert match.group(1) == "0.25"
    
    match = _COST_RE.search("Spent: $10.00 so far")
    assert match
    assert match.group(1) == "10.00"
    
    print("[PASS] Cost parsing works")
    return True


def run_all():
    """Run all bridge tests."""
    tests = [
        test_imports,
        test_cli_states,
        test_strip_ansi,
        test_bridge_init,
        test_bridge_state_property,
        test_cost_property,
        test_query_detection_patterns,
        test_cost_parsing_pattern,
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
    print(f"\nBridge Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
