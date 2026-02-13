"""Tests for guardian (risk classification) module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    from src.guardian import evaluate, classify_command, Decision, RiskCategory
    assert all([evaluate, classify_command, Decision, RiskCategory])
    print("[PASS] Guardian imports successful")
    return True


def test_classify_read_only():
    from src.guardian import classify_command, RiskCategory
    for cmd in ["ls", "cat file.txt", "grep pattern", "find .", "pwd"]:
        assert classify_command(cmd) == RiskCategory.READ_ONLY, f"Failed for '{cmd}'"
    print("[PASS] Read-only commands classified correctly")
    return True


def test_classify_write():
    from src.guardian import classify_command, RiskCategory
    for cmd in ["mkdir dir", "touch file", "cp a b", "mv a b"]:
        assert classify_command(cmd) == RiskCategory.WRITE, f"Failed for '{cmd}'"
    print("[PASS] Write commands classified correctly")
    return True


def test_classify_execute():
    from src.guardian import classify_command, RiskCategory
    for cmd in ["npm install", "python script.py", "docker build", "make"]:
        assert classify_command(cmd) == RiskCategory.EXECUTE, f"Failed for '{cmd}'"
    print("[PASS] Execute commands classified correctly")
    return True


def test_classify_high_risk():
    from src.guardian import classify_command, RiskCategory
    for cmd in ["rm -rf", "sudo apt", "git push", "drop table"]:
        assert classify_command(cmd) == RiskCategory.HIGH_RISK, f"Failed for '{cmd}'"
    print("[PASS] High-risk commands classified correctly")
    return True


def test_evaluate_level_1():
    from src.guardian import evaluate, Decision
    for cmd in ["ls", "npm install"]:
        d, _ = evaluate(cmd, 1)
        assert d == Decision.ASK_USER
    print("[PASS] Level 1 asks for everything")
    return True


def test_evaluate_level_3():
    from src.guardian import evaluate, Decision
    d, _ = evaluate("ls", 3)
    assert d == Decision.AUTO_APPROVE
    d, _ = evaluate("mkdir test", 3)
    assert d == Decision.AUTO_APPROVE
    d, _ = evaluate("npm install", 3)
    assert d == Decision.ASK_USER
    d, _ = evaluate("rm -rf", 3)
    assert d == Decision.ASK_USER
    print("[PASS] Level 3 behavior correct")
    return True


def test_evaluate_level_5():
    from src.guardian import evaluate, Decision
    for cmd in ["ls", "mkdir x", "npm install", "rm -rf test"]:
        d, _ = evaluate(cmd, 5)
        assert d == Decision.AUTO_APPROVE, f"Failed for '{cmd}'"
    print("[PASS] Level 5 auto-approves everything")
    return True


def run_all():
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
    print(f"\nGuardian Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
