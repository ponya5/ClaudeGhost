"""Tests for configuration module."""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_settings_load():
    """Test that settings load without errors."""
    from src.config import settings
    
    assert settings is not None
    assert hasattr(settings, 'waha_api_url')
    assert hasattr(settings, 'waha_api_key')
    assert hasattr(settings, 'waha_session')
    assert hasattr(settings, 'target_phone')
    assert hasattr(settings, 'default_afk_level')
    assert hasattr(settings, 'max_budget_usd')
    print("[PASS] Settings loaded successfully")
    return True


def test_settings_defaults():
    """Test default values are sensible."""
    from src.config import settings
    
    assert settings.waha_api_url.startswith("http")
    assert 1 <= settings.default_afk_level <= 5
    assert settings.max_budget_usd >= 0
    assert settings.poll_interval_seconds > 0
    assert settings.heartbeat_timeout_seconds > 0
    print("[PASS] Default values are valid")
    return True


def test_level_names():
    """Test level name mappings exist."""
    from src.config import LEVEL_NAMES, LEVEL_DESCRIPTIONS
    
    assert len(LEVEL_NAMES) == 5
    assert len(LEVEL_DESCRIPTIONS) == 5
    for i in range(1, 6):
        assert i in LEVEL_NAMES
        assert i in LEVEL_DESCRIPTIONS
    print("[PASS] Level names/descriptions exist")
    return True


def test_session_config():
    """Test SessionConfig class."""
    from src.config import SessionConfig
    
    session = SessionConfig(
        task="Test task",
        afk_level=3,
        budget_usd=10.0,
    )
    
    assert session.task == "Test task"
    assert session.afk_level == 3
    assert session.budget_usd == 10.0
    assert session.level_name == "Manager"
    print("[PASS] SessionConfig works")
    return True


def run_all():
    """Run all config tests."""
    tests = [
        test_settings_load,
        test_settings_defaults,
        test_level_names,
        test_session_config,
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
    print(f"\nConfig Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
