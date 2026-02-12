"""Tests for WAHA client module."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test WAHA module imports."""
    from src.waha import WahaClient
    print("[PASS] WahaClient import successful")
    return True


def test_client_init():
    """Test WahaClient initialization."""
    from src.waha import WahaClient
    from src.config import settings
    
    client = WahaClient()
    
    assert client._base == settings.waha_api_url.rstrip("/")
    assert client._session == settings.waha_session
    assert client._phone == settings.target_phone
    assert client._polling == False
    assert client._connected == False
    
    print("[PASS] WahaClient initialized correctly")
    return True


def test_headers():
    """Test that headers include API key when set."""
    from src.waha import WahaClient
    
    client = WahaClient()
    headers = client._get_headers()
    
    assert "Accept" in headers
    assert "Content-Type" in headers
    assert headers["Accept"] == "application/json"
    
    # API key should be included if set
    if client._api_key:
        assert "X-Api-Key" in headers
        assert headers["X-Api-Key"] == client._api_key
    
    print("[PASS] Headers built correctly")
    return True


def test_seen_ids_tracking():
    """Test message ID deduplication."""
    from src.waha import WahaClient
    
    client = WahaClient()
    
    # Simulate seen IDs
    client._seen_ids.add("msg1")
    client._seen_ids.add("msg2")
    
    assert "msg1" in client._seen_ids
    assert "msg2" in client._seen_ids
    assert "msg3" not in client._seen_ids
    
    print("[PASS] Message ID tracking works")
    return True


def test_extract_id():
    """Test message ID extraction."""
    from src.waha import WahaClient
    
    # Direct ID
    msg1 = {"id": "abc123"}
    assert WahaClient._extract_id(msg1) == "abc123"
    
    # Nested key.id
    msg2 = {"key": {"id": "xyz789"}}
    assert WahaClient._extract_id(msg2) == "xyz789"
    
    # No ID
    msg3 = {"body": "hello"}
    assert WahaClient._extract_id(msg3) is None
    
    print("[PASS] Message ID extraction works")
    return True


def test_connection_check_offline():
    """Test connection check when WAHA is not running."""
    from src.waha import WahaClient
    
    client = WahaClient()
    # This should fail gracefully if WAHA is not running
    result = client.check_connection()
    
    # We just verify it doesn't crash
    assert isinstance(result, bool)
    print("[PASS] Connection check handles offline gracefully")
    return True


def run_all():
    """Run all WAHA tests."""
    tests = [
        test_imports,
        test_client_init,
        test_headers,
        test_seen_ids_tracking,
        test_extract_id,
        test_connection_check_offline,
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
    print(f"\nWAHA Tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
