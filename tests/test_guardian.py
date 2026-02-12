"""Tests for guardian (risk classification) module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test guardian module imports."""
    from src.guardian import (
        evaluate,
        classify_command,
        Decision,
        RiskCategory,
    )
    print("[PASS] Guardian imports successful")
    return True


def test_classify_read_only():
    """Test read-only command classification."""
    from src.guardian import classify_command, RiskCategory
    
    read_commands = ["ls", "cat file.txt", "grep pattern", "find .", "pwd", "echo hello"]
    
    for cmd in read_commands:
        category = classify_command(cmd)
        assert category == RiskCategory.READ_ONLY, f"Expected READ_ONLY for '{cmd}', got {category}"
    
    print("[PASS] Read-only commands classified correctly")
    return True


def test_classify_write():
    """Test write command classification."""
    from src.guardian import classify_command, RiskCategory
    
    write_commands = ["mkdir dir", "touch file", "cp a b", "mv a b", "chmod 755 file"]
    
    for cmd in write_commands:
        category = classify_command(cmd)
        assert category == RiskCategory.WRITE, f"Expected WRITE for '{cmd}', got {category}"
    
    print("[PASS] Write commands classified correctly")
    return True


def test_classify_execute():
    """Test execute command classification."""
    from src.guardian import classify_command, RiskCategory
    
    exec_commands = ["npm install", "python script.py", "docker build", "make", "curl url"]
    
    for cmd in exec_commands:
        category = classify_command(cmd)
        assert category == RiskCategory.EXECUTE, f"Expected EXECUTE for '{cmd}', got {category}"
    
    print("[PASS] Execute commands classified correctly")
    return True


def test_classify_high_risk():
    """Test high-risk command classification."""
    from src.guardian import classify_command, RiskCategory
    
    risky_commands = ["rm -rf", "sudo apt", "git push", "drop table"]
    
    for cmd in risky_commands:
        category = classify_command(cmd)
        assert category == RiskCategory.HIGH_RISK, f"Expected HIGH_RISK for '{cmd}', got {category}"
    
    print("[PASS] High-risk commands classified correctly")
    return True


def test_evaluate_level_1():
    """Test evaluation at level 1 (paranoid)."""
    from src.guardian import evaluate, Decision
    
    # At level 1, everything should ask
    decision, _ = evaluate("ls", 1)
    assert decision == Decision.ASK_USER
    
    decision, _ = evaluate("npm install", 1)
    assert decision == Decision.ASK_USER
    
    print("[PASS] Level 1 asks for everything")
    return True


def test_evaluate_level_3():
    """Test evaluation at level 3 (manager)."""
    from src.guardian import evaluate, Decision
    
    # Read: auto
    decision, _ = evaluate("ls", 3)
    assert decision == Decision.AUTO_APPROVE
    
    # Write: auto
    decision, _ = evaluate("mkdir test", 3)
    assert decision == Decision.AUTO_APPROVE
    
    # Execute: ask
    decision, _ = evaluate("npm install", 3)
    assert decision == Decision.ASK_USER
    
    # High-risk: ask
    decision, _ = evaluate("rm -rf", 3)
    assert decision == Decision.ASK_USER
    
    print("[PASS] Level 3 behavior correct")
    return True


def test_evaluate_level_5():
    """Test evaluation at level 5 (god mode)."""
    from src.guardian import evaluate, Decision
    
    # Everything should auto-approve at level 5
    commands = ["ls", "mkdir x", "npm install", "rm -rf test"]
    
    for cmd in commands:
        decision, _ = evaluate(cmd, 5)
        assert decision == Decision.AUTO_APPROVE, f"Expected AUTO_APPROVE for '{cmd}' at level 5"
    
    print("[PASS] Level 5 auto-approves everything")
    return True


def run_all():
    """Run all guardian tests."""
    tests = [
        test_imports,
        test_classify_read_only,
        test_classify_write,
        test_classify_execute,
        test_classify_high_risk,
        test_evaluate_level_1,
        test_evaluate_level_3,
        test_evaluate_level_5,
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
    print(f"\nGuardian Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
