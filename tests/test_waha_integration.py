#!/usr/bin/env python3
"""
WAHA Integration Tests

Tests WhatsApp HTTP API integration:
1. Server connectivity
2. Session management
3. Message sending (optional)

Usage:
    python tests/test_waha_integration.py              # Run all tests
    python tests/test_waha_integration.py --live       # Include live message test
    python tests/test_waha_integration.py --skip-send  # Skip send test even if session is working
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

WAHA_URL = "http://localhost:3000"


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_result(name, passed, message=""):
    status = f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
    msg = f" - {message}" if message else ""
    print(f"  [{status}] {name}{msg}")
    return passed


def test_requests_available():
    """Test that requests library is available."""
    return print_result(
        "requests library",
        HAS_REQUESTS,
        "installed" if HAS_REQUESTS else "not installed - run: pip install requests"
    )


def test_server_reachable():
    """Test that WAHA server is reachable."""
    if not HAS_REQUESTS:
        return print_result("server reachable", False, "requests not available")
    
    try:
        response = requests.get(f"{WAHA_URL}/api/sessions", timeout=5)
        return print_result(
            "server reachable",
            response.status_code == 200,
            f"status {response.status_code}"
        )
    except requests.exceptions.ConnectionError:
        return print_result("server reachable", False, "connection refused - is WAHA running?")
    except Exception as e:
        return print_result("server reachable", False, str(e))


def test_session_exists():
    """Test that a session exists."""
    if not HAS_REQUESTS:
        return print_result("session exists", False, "requests not available")
    
    try:
        response = requests.get(f"{WAHA_URL}/api/sessions/default", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "UNKNOWN")
            return print_result("session exists", True, f"status: {status}")
        elif response.status_code == 404:
            return print_result("session exists", False, "no 'default' session - start one in dashboard")
        else:
            return print_result("session exists", False, f"status {response.status_code}")
    except Exception as e:
        return print_result("session exists", False, str(e))


def test_session_working():
    """Test that session is in WORKING state."""
    if not HAS_REQUESTS:
        return print_result("session working", False, "requests not available")
    
    try:
        response = requests.get(f"{WAHA_URL}/api/sessions/default", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "UNKNOWN")
            if status == "WORKING":
                return print_result("session working", True, "WhatsApp connected!")
            elif status == "SCAN_QR":
                return print_result("session working", False, "needs QR scan - check dashboard")
            else:
                return print_result("session working", False, f"status: {status}")
        else:
            return print_result("session working", False, f"status {response.status_code}")
    except Exception as e:
        return print_result("session working", False, str(e))


def test_api_health():
    """Test API health endpoint."""
    if not HAS_REQUESTS:
        return print_result("API health", False, "requests not available")
    
    try:
        # Try health endpoint if available
        response = requests.get(f"{WAHA_URL}/health", timeout=5)
        if response.status_code == 200:
            return print_result("API health", True)
        
        # Fall back to sessions endpoint
        response = requests.get(f"{WAHA_URL}/api/sessions", timeout=5)
        return print_result("API health", response.status_code == 200)
    except Exception as e:
        return print_result("API health", False, str(e))


def test_config_loaded():
    """Test that ClaudeGhost config loads WAHA settings."""
    try:
        from src.config import settings
        
        has_url = bool(settings.waha_api_url)
        has_session = bool(settings.waha_session)
        has_phone = settings.target_phone != "1234567890@c.us"
        
        if has_url and has_session:
            msg = "phone configured" if has_phone else "phone not configured (using default)"
            return print_result("config loaded", True, msg)
        else:
            return print_result("config loaded", False, "missing WAHA settings")
    except Exception as e:
        return print_result("config loaded", False, str(e))


def test_waha_client():
    """Test WahaClient class."""
    try:
        from src.waha import WahaClient
        
        client = WahaClient()
        
        # Check initialization
        assert client._base is not None
        assert client._session is not None
        
        # Check headers method
        headers = client._get_headers()
        assert "Content-Type" in headers
        
        return print_result("WahaClient class", True)
    except Exception as e:
        return print_result("WahaClient class", False, str(e))


def test_waha_client_connection():
    """Test WahaClient connection check."""
    try:
        from src.waha import WahaClient
        
        client = WahaClient()
        result = client.check_connection()
        
        return print_result(
            "WahaClient connection",
            result,
            "connected" if result else "not connected"
        )
    except Exception as e:
        return print_result("WahaClient connection", False, str(e))


def test_send_message(skip=False):
    """Test sending a message (optional)."""
    if skip:
        return print_result("send message", True, "skipped")
    
    try:
        from src.waha import WahaClient
        from src.config import settings
        
        if settings.target_phone == "1234567890@c.us":
            return print_result("send message", False, "TARGET_PHONE not configured")
        
        client = WahaClient()
        
        # First check if connected
        if not client.check_connection():
            return print_result("send message", False, "session not working")
        
        # Send test message
        result = client.send("ClaudeGhost integration test - WAHA verified!")
        
        return print_result(
            "send message",
            result,
            f"sent to {settings.target_phone}" if result else "failed"
        )
    except Exception as e:
        return print_result("send message", False, str(e))


def run_all(live_test=False, skip_send=False):
    """Run all WAHA integration tests."""
    print(f"\n{Colors.BOLD}WAHA Integration Tests{Colors.END}")
    print("=" * 50)
    
    results = []
    
    # Basic tests
    print(f"\n{Colors.CYAN}Basic Checks:{Colors.END}")
    results.append(test_requests_available())
    results.append(test_config_loaded())
    results.append(test_waha_client())
    
    # Server tests
    print(f"\n{Colors.CYAN}Server Tests:{Colors.END}")
    results.append(test_server_reachable())
    results.append(test_api_health())
    
    # Session tests
    print(f"\n{Colors.CYAN}Session Tests:{Colors.END}")
    results.append(test_session_exists())
    results.append(test_session_working())
    results.append(test_waha_client_connection())
    
    # Message test (optional)
    print(f"\n{Colors.CYAN}Message Tests:{Colors.END}")
    if live_test and not skip_send:
        results.append(test_send_message(skip=False))
    else:
        results.append(test_send_message(skip=True))
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}All {total} tests passed!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}{passed}/{total} tests passed{Colors.END}")
    
    return passed, total - passed


def main():
    parser = argparse.ArgumentParser(description="WAHA Integration Tests")
    parser.add_argument("--live", action="store_true", help="Include live message test")
    parser.add_argument("--skip-send", action="store_true", help="Skip send test")
    args = parser.parse_args()
    
    passed, failed = run_all(live_test=args.live, skip_send=args.skip_send)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
