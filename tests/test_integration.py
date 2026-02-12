"""Integration tests for ClaudeGhost."""
import os
import sys
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_modules_import():
    """Test that all modules can be imported together."""
    from src.config import settings
    from src.utils import logger, ghost_status
    from src.guardian import evaluate, Decision
    from src.waha import WahaClient
    from src.bridge import GhostBridge, CliState
    from src.main import ClaudeGhost
    from src.cli import cmd_config_show
    
    print("[PASS] All modules import together without conflict")
    return True


def test_config_to_waha_flow():
    """Test that config values flow to WAHA client."""
    from src.config import settings
    from src.waha import WahaClient
    
    client = WahaClient()
    
    assert client._base == settings.waha_api_url.rstrip("/")
    assert client._session == settings.waha_session
    assert client._phone == settings.target_phone
    
    print("[PASS] Config values flow to WAHA client")
    return True


def test_guardian_decision_matrix():
    """Test full decision matrix across all levels."""
    from src.guardian import evaluate, Decision, RiskCategory
    
    # Level 1: everything asks
    for cmd in ["ls", "mkdir x", "npm i", "rm -rf"]:
        d, _ = evaluate(cmd, 1)
        assert d == Decision.ASK_USER, f"Level 1 should ask for '{cmd}'"
    
    # Level 5: everything auto
    for cmd in ["ls", "mkdir x", "npm i", "rm -rf"]:
        d, _ = evaluate(cmd, 5)
        assert d == Decision.AUTO_APPROVE, f"Level 5 should auto-approve '{cmd}'"
    
    print("[PASS] Decision matrix works across all levels")
    return True


def test_env_file_exists():
    """Test that .env.example exists."""
    env_example = os.path.join(PROJECT_ROOT, ".env.example")
    assert os.path.exists(env_example), ".env.example should exist"
    
    with open(env_example, 'r') as f:
        content = f.read()
    
    assert "WAHA_API_URL" in content
    assert "WAHA_API_KEY" in content
    assert "TARGET_PHONE" in content
    
    print("[PASS] .env.example exists with required fields")
    return True


def test_config_yaml_exists():
    """Test that config.yaml exists."""
    config_yaml = os.path.join(PROJECT_ROOT, "config.yaml")
    assert os.path.exists(config_yaml), "config.yaml should exist"
    
    print("[PASS] config.yaml exists")
    return True


def test_readme_exists():
    """Test that README.md exists."""
    readme = os.path.join(PROJECT_ROOT, "README.md")
    assert os.path.exists(readme), "README.md should exist"
    
    with open(readme, 'r') as f:
        content = f.read()
    
    assert "ClaudeGhost" in content
    
    print("[PASS] README.md exists")
    return True


def test_cli_help():
    """Test CLI help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    
    assert result.returncode == 0, f"CLI help failed: {result.stderr}"
    assert "config" in result.stdout.lower()
    
    print("[PASS] CLI help works")
    return True


def test_launcher_imports():
    """Test launcher module can be imported."""
    from src.launcher import SessionConfig, print_banner
    
    # Test that SessionConfig can be created
    config = SessionConfig(task="test", afk_level=3)
    assert config.task == "test"
    assert config.afk_level == 3
    
    print("[PASS] Launcher imports and SessionConfig works")
    return True


def test_claude_cli_available():
    """Test if Claude CLI is available (warning only if not)."""
    result = subprocess.run(
        ["claude", "--version"],
        capture_output=True,
        text=True,
        shell=True,
    )
    
    if result.returncode == 0:
        print(f"[PASS] Claude CLI available: {result.stdout.strip()}")
    else:
        print("[WARN] Claude CLI not found - install with: npm install -g @anthropic-ai/claude-code")
    
    return True  # Don't fail test, just warn


def run_all():
    """Run all integration tests."""
    tests = [
        test_all_modules_import,
        test_config_to_waha_flow,
        test_guardian_decision_matrix,
        test_env_file_exists,
        test_config_yaml_exists,
        test_readme_exists,
        test_cli_help,
        test_launcher_imports,
        test_claude_cli_available,
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
    print(f"\nIntegration Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
