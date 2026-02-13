"""Integration tests for ClaudeGhost."""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_modules_import():
    """Test that all modules can be imported without conflicts."""
    # Import all modules to verify no conflicts
    import src.config  # noqa: F401
    import src.utils  # noqa: F401
    import src.guardian  # noqa: F401
    import src.telegram_bot  # noqa: F401
    import src.bridge  # noqa: F401
    import src.main  # noqa: F401
    import src.cli  # noqa: F401
    import src.screen_notifier  # noqa: F401
    print("[PASS] All modules import without conflict")
    return True


def test_config_to_telegram_flow():
    """Test that config values flow correctly to TelegramBot."""
    from src.config import settings
    from src.telegram_bot import TelegramBot
    bot = TelegramBot()
    assert bot.token == settings.telegram_bot_token
    assert bot.chat_id == settings.telegram_chat_id
    print("[PASS] Config values flow to TelegramBot")
    return True


def test_guardian_decision_matrix():
    from src.guardian import evaluate, Decision
    for cmd in ["ls", "mkdir x", "npm i", "rm -rf"]:
        d, _ = evaluate(cmd, 1)
        assert d == Decision.ASK_USER
    for cmd in ["ls", "mkdir x", "npm i", "rm -rf"]:
        d, _ = evaluate(cmd, 5)
        assert d == Decision.AUTO_APPROVE
    print("[PASS] Decision matrix works across all levels")
    return True


def test_env_file_exists():
    env_example = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.exists(env_example)
    with open(env_example, "r", encoding="utf-8") as f:
        content = f.read()
    assert "TELEGRAM_BOT_TOKEN" in content
    assert "TELEGRAM_CHAT_ID" in content
    print("[PASS] .env.example exists with Telegram fields")
    return True


def test_no_whatsapp_references():
    """Ensure no WhatsApp/WAHA references remain in source code."""
    src_dir = os.path.join(PROJECT_ROOT, "src")
    for filename in os.listdir(src_dir):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(src_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().lower()
        msg = f"WhatsApp ref in {filename}"
        assert "whatsapp" not in content, msg
        msg = f"WAHA ref in {filename}"
        assert "waha" not in content, msg
    print("[PASS] No WhatsApp/WAHA references in src/")
    return True


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "--help"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, check=False,
    )
    assert result.returncode == 0, f"CLI help failed: {result.stderr}"
    assert "config" in result.stdout.lower()
    print("[PASS] CLI help works")
    return True


def test_launcher_imports():
    """Test launcher quick mode functionality."""
    from src.launcher import run_quick_launcher
    from src.config import SessionConfig
    config = run_quick_launcher(
        task="test", level=3, budget=5.0, telegram=False
    )
    assert isinstance(config, SessionConfig)
    assert config.task == "test"
    assert config.afk_level == 3
    assert config.telegram_enabled is False
    print("[PASS] Launcher quick mode works")
    return True


def run_all():
    """Run all integration tests."""
    tests = [
        test_all_modules_import,
        test_config_to_telegram_flow,
        test_guardian_decision_matrix,
        test_env_file_exists,
        test_no_whatsapp_references,
        test_cli_help,
        test_launcher_imports,
    ]
    test_passed = test_failed = 0
    for test in tests:
        try:
            test()
            test_passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            test_failed += 1
    return test_passed, test_failed


if __name__ == "__main__":
    passed, failed = run_all()
    print(f"\nIntegration Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
