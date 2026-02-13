#!/usr/bin/env python3
"""
WAHA Server Launcher & WhatsApp Integration Test

Cross-platform script to:
1. Start WAHA Docker container
2. Wait for server readiness
3. Test WhatsApp connection
4. Send test message

Usage:
    python start_waha.py              # Start WAHA and test
    python start_waha.py --start      # Start WAHA only
    python start_waha.py --test       # Test connection only
    python start_waha.py --stop       # Stop WAHA container
    python start_waha.py --status     # Check WAHA status
"""
import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"

    @staticmethod
    def disable():
        Colors.GREEN = ""
        Colors.YELLOW = ""
        Colors.RED = ""
        Colors.CYAN = ""
        Colors.BOLD = ""
        Colors.DIM = ""
        Colors.END = ""


# Disable colors on Windows if not supported
if sys.platform == "win32":
    try:
        os.system("")  # Enable ANSI on Windows 10+
    except:
        Colors.disable()


def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
 __        __    _   _    _    
 \\ \\      / /_ _| | | |  / \\   
  \\ \\ /\\ / / _` | |_| | / _ \\  
   \\ V  V / (_| |  _  |/ ___ \\ 
    \\_/\\_/ \\__,_|_| |_/_/   \\_\\
{Colors.END}
  WhatsApp HTTP API Server Manager
  ==================================
""")


def log_info(msg):
    print(f"  {Colors.CYAN}[INFO]{Colors.END} {msg}")


def log_ok(msg):
    print(f"  {Colors.GREEN}[OK]{Colors.END} {msg}")


def log_warn(msg):
    print(f"  {Colors.YELLOW}[WARN]{Colors.END} {msg}")


def log_error(msg):
    print(f"  {Colors.RED}[ERROR]{Colors.END} {msg}")


def log_step(step, msg):
    print(f"\n{Colors.BOLD}[Step {step}]{Colors.END} {msg}")


def run_cmd(cmd, capture=True, timeout=60):
    """Run a shell command."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def check_docker():
    """Check if Docker is installed and running."""
    log_step(1, "Checking Docker...")
    
    code, out, err = run_cmd("docker --version")
    if code != 0:
        log_error("Docker not found!")
        log_info("Install Docker from: https://docs.docker.com/get-docker/")
        return False
    
    log_ok(f"Docker installed: {out}")
    
    # Check if Docker daemon is running
    code, out, err = run_cmd("docker info", timeout=10)
    if code != 0:
        log_error("Docker daemon not running!")
        log_info("Start Docker Desktop or run: sudo systemctl start docker")
        return False
    
    log_ok("Docker daemon is running")
    return True


def check_waha_container():
    """Check if WAHA container exists and its status."""
    code, out, err = run_cmd('docker ps -a --filter "name=waha" --format "{{.Status}}"')
    
    if code != 0 or not out:
        return "not_found"
    
    if "Up" in out:
        return "running"
    else:
        return "stopped"


def pull_waha_image():
    """Pull the WAHA Docker image."""
    log_step(2, "Pulling WAHA Docker image...")
    
    code, out, err = run_cmd("docker pull devlikeapro/waha", capture=False, timeout=300)
    
    if code != 0:
        log_error("Failed to pull WAHA image")
        return False
    
    log_ok("WAHA image pulled successfully")
    return True


def start_waha_container():
    """Start or create the WAHA container."""
    log_step(3, "Starting WAHA container...")
    
    status = check_waha_container()
    
    if status == "running":
        log_ok("WAHA container already running")
        return True
    
    if status == "stopped":
        log_info("Starting existing WAHA container...")
        code, _, err = run_cmd("docker start waha")
        if code != 0:
            log_error(f"Failed to start container: {err}")
            return False
        log_ok("WAHA container started")
        return True
    
    # Create new container
    log_info("Creating new WAHA container...")
    
    # Check for .env file with WAHA settings
    env_file = PROJECT_ROOT / ".env"
    waha_env = PROJECT_ROOT / "waha.env"
    
    # Build docker run command
    cmd_parts = [
        "docker run -d",
        "--name waha",
        "-p 3000:3000",
        "-v waha_sessions:/app/.sessions",
    ]
    
    # Add environment file if exists
    if waha_env.exists():
        cmd_parts.append(f'--env-file "{waha_env}"')
    
    cmd_parts.append("devlikeapro/waha")
    cmd = " ".join(cmd_parts)
    
    code, out, err = run_cmd(cmd)
    
    if code != 0:
        log_error(f"Failed to create container: {err}")
        return False
    
    log_ok(f"WAHA container created: {out[:12]}")
    return True


def wait_for_waha(max_wait=60):
    """Wait for WAHA server to be ready."""
    log_step(4, "Waiting for WAHA server to be ready...")
    
    if not HAS_REQUESTS:
        log_warn("requests module not found, skipping health check")
        time.sleep(5)
        return True
    
    start_time = time.time()
    url = "http://localhost:3000/api/sessions"
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                log_ok("WAHA server is ready!")
                return True
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            log_warn(f"Health check error: {e}")
        
        elapsed = int(time.time() - start_time)
        print(f"\r  {Colors.DIM}Waiting... {elapsed}s{Colors.END}    ", end="", flush=True)
        time.sleep(2)
    
    print()
    log_error(f"WAHA server not ready after {max_wait}s")
    return False


def check_session_status():
    """Check if WhatsApp session is linked."""
    if not HAS_REQUESTS:
        return None, "requests module not available"
    
    try:
        response = requests.get("http://localhost:3000/api/sessions/default", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("status", "UNKNOWN"), data
        elif response.status_code == 404:
            return "NOT_FOUND", None
        else:
            return "ERROR", None
    except Exception as e:
        return "CONNECTION_ERROR", str(e)


def start_session():
    """Start a new WhatsApp session."""
    if not HAS_REQUESTS:
        return False
    
    try:
        response = requests.post(
            "http://localhost:3000/api/sessions/start",
            json={"name": "default"},
            timeout=10
        )
        return response.status_code in [200, 201]
    except:
        return False


def test_waha_connection():
    """Test WAHA connection and session status."""
    log_step(5, "Testing WAHA connection...")
    
    if not HAS_REQUESTS:
        log_error("requests module required for testing")
        log_info("Install with: pip install requests")
        return False
    
    # Check server
    try:
        response = requests.get("http://localhost:3000/api/sessions", timeout=10)
        if response.status_code != 200:
            log_error(f"WAHA server returned status {response.status_code}")
            return False
        log_ok("WAHA server responding")
    except requests.exceptions.ConnectionError:
        log_error("Cannot connect to WAHA server")
        log_info("Make sure WAHA is running on port 3000")
        return False
    except Exception as e:
        log_error(f"Connection error: {e}")
        return False
    
    # Check session
    status, data = check_session_status()
    
    if status == "NOT_FOUND":
        log_warn("No session found, creating one...")
        if start_session():
            log_ok("Session 'default' created")
            time.sleep(2)
            status, data = check_session_status()
        else:
            log_error("Failed to create session")
            return False
    
    if status == "WORKING":
        log_ok("WhatsApp session is WORKING!")
        return True
    elif status == "SCAN_QR":
        log_warn("WhatsApp needs QR code scan")
        print(f"""
  {Colors.YELLOW}======================================{Colors.END}
  {Colors.BOLD}Action Required: Link WhatsApp{Colors.END}
  {Colors.YELLOW}======================================{Colors.END}
  
  1. Open: {Colors.CYAN}http://localhost:3000/dashboard{Colors.END}
  2. Click on the session to view QR code
  3. Open WhatsApp on your phone
  4. Go to Settings > Linked Devices
  5. Scan the QR code
  
  Then run: {Colors.CYAN}python start_waha.py --test{Colors.END}
""")
        return False
    elif status == "STARTING":
        log_info("Session is starting, please wait...")
        return False
    else:
        log_warn(f"Session status: {status}")
        return False


def send_test_message():
    """Send a test message via WAHA."""
    log_step(6, "Sending test message...")
    
    if not HAS_REQUESTS:
        log_error("requests module required")
        return False
    
    # Load config
    try:
        from src.config import settings
        target_phone = settings.target_phone
        api_key = getattr(settings, 'waha_api_key', '')
    except ImportError:
        log_warn("Could not load config, using defaults")
        target_phone = input("  Enter target phone (e.g., 14155551234@c.us): ").strip()
        api_key = ""
    
    if not target_phone or target_phone == "1234567890@c.us":
        log_warn("Target phone not configured")
        log_info("Set TARGET_PHONE in .env file")
        return False
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key
    
    payload = {
        "chatId": target_phone,
        "text": "ClaudeGhost WAHA test message - connection verified!",
        "session": "default"
    }
    
    try:
        response = requests.post(
            "http://localhost:3000/api/sendText",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            log_ok(f"Test message sent to {target_phone}")
            return True
        else:
            log_error(f"Failed to send message: {response.status_code}")
            log_info(response.text[:200])
            return False
    except Exception as e:
        log_error(f"Send failed: {e}")
        return False


def stop_waha():
    """Stop the WAHA container."""
    log_info("Stopping WAHA container...")
    
    code, _, err = run_cmd("docker stop waha")
    if code == 0:
        log_ok("WAHA container stopped")
        return True
    else:
        log_error(f"Failed to stop: {err}")
        return False


def show_status():
    """Show current WAHA status."""
    print(f"\n{Colors.BOLD}WAHA Status{Colors.END}")
    print("-" * 40)
    
    # Container status
    status = check_waha_container()
    if status == "running":
        print(f"  Container: {Colors.GREEN}Running{Colors.END}")
    elif status == "stopped":
        print(f"  Container: {Colors.YELLOW}Stopped{Colors.END}")
    else:
        print(f"  Container: {Colors.RED}Not found{Colors.END}")
        return
    
    # Session status
    if status == "running" and HAS_REQUESTS:
        session_status, data = check_session_status()
        status_color = {
            "WORKING": Colors.GREEN,
            "SCAN_QR": Colors.YELLOW,
            "STARTING": Colors.CYAN,
        }.get(session_status, Colors.RED)
        print(f"  Session:   {status_color}{session_status}{Colors.END}")
    
    # URLs
    print(f"\n  Dashboard: {Colors.CYAN}http://localhost:3000/dashboard{Colors.END}")
    print(f"  API Docs:  {Colors.CYAN}http://localhost:3000/{Colors.END}")


def main():
    parser = argparse.ArgumentParser(
        description="WAHA Server Manager for ClaudeGhost"
    )
    parser.add_argument("--start", action="store_true", help="Start WAHA only")
    parser.add_argument("--test", action="store_true", help="Test connection only")
    parser.add_argument("--stop", action="store_true", help="Stop WAHA container")
    parser.add_argument("--status", action="store_true", help="Show WAHA status")
    parser.add_argument("--send", action="store_true", help="Send test message")
    args = parser.parse_args()
    
    print_banner()
    
    if args.stop:
        stop_waha()
        return 0
    
    if args.status:
        show_status()
        return 0
    
    if args.test:
        if test_waha_connection():
            return 0
        return 1
    
    if args.send:
        if send_test_message():
            return 0
        return 1
    
    # Full startup sequence
    if not check_docker():
        return 1
    
    if not args.start:
        # Check if image exists, pull if not
        code, out, _ = run_cmd('docker images devlikeapro/waha --format "{{.Repository}}"')
        if not out:
            if not pull_waha_image():
                return 1
    
    if not start_waha_container():
        return 1
    
    if not wait_for_waha():
        return 1
    
    if not test_waha_connection():
        return 1
    
    # Offer to send test message
    if args.start:
        return 0
    
    print()
    response = input(f"  Send test message? [y/N]: ").strip().lower()
    if response == "y":
        send_test_message()
    
    print(f"""
{Colors.GREEN}{Colors.BOLD}WAHA is ready!{Colors.END}

  Dashboard: {Colors.CYAN}http://localhost:3000/dashboard{Colors.END}
  
  Next steps:
  1. Configure .env with your WAHA_API_KEY and TARGET_PHONE
  2. Run: {Colors.CYAN}python -m src.cli config test{Colors.END}
  3. Start ClaudeGhost: {Colors.CYAN}python -m src.launcher{Colors.END}
""")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
