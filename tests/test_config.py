"""Tests for configuration module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_settings_load():
    from src.config import settings
    assert settings is not None
    assert hasattr(settings, "telegram_bot_token")
    assert hasattr(settings, "telegram_chat_id")
    assert hasattr(settings, "telegram_enabled")
    assert hasattr(settings, "default_afk_level")
    assert hasattr(settings, "max_budget_usd")
    print("[PASS] Settings loaded successfully")
    return True


def test_settings_defaults():
    from src.config import settings
    assert 1 <= settings.default_afk_level <= 5
    assert settings.max_budget_usd >= 0
    assert settings.poll_interval_seconds > 0
    assert settings.heartbeat_timeout_seconds > 0
    print("[PASS] Default values are valid")
    return True


def test_level_names():
    from src.config import LEVEL_NAMES, LEVEL_DESCRIPTIONS
    assert len(LEVEL_NAMES) == 5
    assert len(LEVEL_DESCRIPTIONS) == 5
    for i in range(1, 6):
        assert i in LEVEL_NAMES
        assert i in LEVEL_DESCRIPTIONS
    print("[PASS] Level names/descriptions exist")
    return True


def test_session_config():
    from src.config import SessionConfig
    session = SessionConfig(task="Test task", afk_level=3, budget_usd=10.0)
    assert session.task == "Test task"
    assert session.afk_level == 3
    assert session.budget_usd == 10.0
    assert session.level_name == "Manager"
    print("[PASS] SessionConfig works")
    return True


def test_session_config_telegram():
    from src.config import SessionConfig
    s1 = SessionConfig(task="t", telegram_enabled=True)
    assert s1.telegram_enabled is True
    s2 = SessionConfig(task="t", telegram_enabled=False)
    assert s2.telegram_enabled is False
    print("[PASS] SessionConfig telegram flag works")
    return True


def run_all():
    tests = [
        test_settings_load,
        test_settings_defaults,
        test_level_names,
        test_session_config,
        test_session_config_telegram,
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
    print(f"\nConfig Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
