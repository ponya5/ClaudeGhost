#!/usr/bin/env python3
"""
ClaudeGhost Installation & Setup Script

Usage:
    python install.py              # Full interactive setup
    python install.py --check      # Check dependencies only
    python install.py --configure  # Configure .env only
    python install.py --waha       # Setup WAHA only
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
   _____ _                 _       _____ _               _   
  / ____| |               | |     / ____| |             | |  
 | |    | | __ _ _   _  __| | ___| |  __| |__   ___  ___| |_ 
 | |    | |/ _` | | | |/ _` |/ _ \\ | |_ | '_ \\ / _ \\/ __| __|
 | |____| | (_| | |_| | (_| |  __/ |__| | | | | (_) \\__ \\ |_ 
  \\_____|_|\\__,_|\\__,_|\\__,_|\\___|\\_____|_| |_|\\___/|___/\\__|
                                                              
{Colors.END}  Headless Supervisor for Anthropic Claude CLI
  ================================================
""")


def print_step(step: int, msg: str):
    print(f"\n{Colors.BOLD}[{step}]{Colors.END} {msg}")


def print_ok(msg: str):
    print(f"    {Colors.GREEN}✓{Colors.END} {msg}")


def print_warn(msg: str):
    print(f"    {Colors.YELLOW}!{Colors.END} {msg}")


def print_error(msg: str):
    print(f"    {Colors.RED}x{Colors.END} {msg}")


def print_info(msg: str):
    print(f"    {Colors.CYAN}i{Colors.END} {msg}")


def run_cmd(cmd: str, capture: bool = True) -> tuple:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=capture, text=True)
        return result.returncode, result.stdout.strip()
    except Exception as e:
        return 1, str(e)


def check_python() -> bool:
    print_step(1, "Checking Python version...")
    version = sys.version_info
    if version >= (3, 10):
        print_ok(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} found, need 3.10+")
        return False


def check_claude_cli() -> bool:
    print_step(2, "Checking Claude CLI...")
    code, output = run_cmd("claude --version")
    if code == 0:
        print_ok(f"Claude CLI installed: {output}")
        return True
    else:
        print_warn("Claude CLI not found")
        print_info("Install with: npm install -g @anthropic-ai/claude-code")
        print_info("Then run: claude auth")
        return False


def check_docker() -> bool:
    print_step(3, "Checking Docker (for WAHA)...")
    code, output = run_cmd("docker --version")
    if code == 0:
        print_ok(f"Docker installed: {output}")
        return True
    else:
        print_warn("Docker not found (required for WAHA)")
        print_info("Install from: https://docs.docker.com/get-docker/")
        return False


def install_dependencies() -> bool:
    print_step(4, "Installing Python dependencies...")
    
    project_root = Path(__file__).parent
    requirements = project_root / "requirements.txt"
    
    if not requirements.exists():
        print_error("requirements.txt not found")
        return False
    
    code, _ = run_cmd(f"{sys.executable} -m pip install -r {requirements}")
    if code == 0:
        print_ok("Dependencies installed successfully")
        return True
    else:
        print_error("Failed to install dependencies")
        print_info(f"Try manually: pip install -r {requirements}")
        return False


def setup_env_file() -> bool:
    print_step(5, "Setting up configuration...")
    
    project_root = Path(__file__).parent
    env_example = project_root / ".env.example"
    env_file = project_root / ".env"
    
    if env_file.exists():
        print_warn(".env file already exists")
        response = input("    Overwrite? [y/N]: ").strip().lower()
        if response != "y":
            print_info("Keeping existing .env")
            return True
    
    if not env_example.exists():
        print_error(".env.example not found")
        return False
    
    shutil.copy(env_example, env_file)
    print_ok(".env file created from template")
    
    print("\n    Configure your settings:")
    print("    " + "-" * 40)
    
    content = env_file.read_text()
    
    # WAHA API Key
    api_key = input(f"    {Colors.CYAN}WAHA API Key{Colors.END} (from WAHA init): ").strip()
    if api_key:
        content = content.replace("WAHA_API_KEY=", f"WAHA_API_KEY={api_key}")
    
    # Phone number
    phone = input(f"    {Colors.CYAN}Your WhatsApp number{Colors.END} (e.g., 14155551234): ").strip()
    if phone:
        if not phone.endswith("@c.us"):
            phone = f"{phone}@c.us"
        content = content.replace("TARGET_PHONE=1234567890@c.us", f"TARGET_PHONE={phone}")
    
    # Budget
    budget = input(f"    {Colors.CYAN}Max budget USD{Colors.END} [10.00]: ").strip()
    if budget:
        content = content.replace("MAX_BUDGET_USD=10.00", f"MAX_BUDGET_USD={budget}")
    
    # AFK Level
    level = input(f"    {Colors.CYAN}Default AFK level{Colors.END} (1-5) [3]: ").strip()
    if level and level.isdigit() and 1 <= int(level) <= 5:
        content = content.replace("DEFAULT_AFK_LEVEL=3", f"DEFAULT_AFK_LEVEL={level}")
    
    env_file.write_text(content)
    print_ok("Configuration saved to .env")
    return True


def setup_waha():
    print_step(6, "WAHA Setup Guide")
    
    print(f"""
    {Colors.BOLD}To set up WAHA (WhatsApp HTTP API):{Colors.END}
    
    1. Pull the WAHA Docker image:
       {Colors.CYAN}docker pull devlikeapro/waha{Colors.END}
    
    2. Initialize WAHA (generates API key):
       {Colors.CYAN}docker run --rm -v ".:/app/env" devlikeapro/waha init-waha /app/env{Colors.END}
       
       {Colors.YELLOW}Save the generated API key!{Colors.END}
    
    3. Run WAHA:
       {Colors.CYAN}docker run -it --env-file .env -p 3000:3000 --name waha devlikeapro/waha{Colors.END}
    
    4. Open dashboard: {Colors.CYAN}http://localhost:3000/dashboard{Colors.END}
    
    5. Start a session and scan the QR code with WhatsApp
    
    {Colors.BOLD}Documentation:{Colors.END} https://waha.devlike.pro/docs/overview/quick-start/
    """)


def install_package() -> bool:
    print_step(7, "Installing ClaudeGhost package...")
    
    project_root = Path(__file__).parent
    code, _ = run_cmd(f"{sys.executable} -m pip install -e {project_root}")
    
    if code == 0:
        print_ok("ClaudeGhost installed successfully")
        print_info("You can now run: claudeghost \"your task\" --level 3")
        return True
    else:
        print_warn("Package install failed, using module mode")
        print_info("Run with: python -m src.launcher \"your task\" --level 3")
        return True


def verify_installation() -> bool:
    print_step(8, "Verifying installation...")
    
    try:
        from src.config import settings
        print_ok("Configuration loaded")
        
        from src.waha import WahaClient
        print_ok("WAHA client imported")
        
        from src.bridge import GhostBridge
        print_ok("Bridge module imported")
        
        from src.guardian import evaluate
        print_ok("Guardian module imported")
        
        return True
    except ImportError as e:
        print_error(f"Import failed: {e}")
        return False


def main():
    print_banner()
    
    args = sys.argv[1:]
    
    if "--check" in args:
        check_python()
        check_claude_cli()
        check_docker()
        return
    
    if "--configure" in args:
        setup_env_file()
        return
    
    if "--waha" in args:
        setup_waha()
        return
    
    # Full installation
    all_ok = True
    
    all_ok &= check_python()
    check_claude_cli()
    check_docker()
    all_ok &= install_dependencies()
    all_ok &= setup_env_file()
    setup_waha()
    all_ok &= install_package()
    all_ok &= verify_installation()
    
    print("\n" + "=" * 60)
    if all_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}Installation complete!{Colors.END}")
        print(f"""
{Colors.BOLD}Next steps:{Colors.END}

1. Ensure WAHA is running with your WhatsApp linked
2. Test the connection:
   {Colors.CYAN}python -m src.cli config test{Colors.END}

3. Run ClaudeGhost:
   {Colors.CYAN}python -m src.launcher "Build a hello world Flask app" --level 3{Colors.END}

{Colors.BOLD}Documentation:{Colors.END} See README.md and MANUAL.md
""")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}Installation completed with warnings{Colors.END}")
        print("    Please review the messages above and fix any issues.")


if __name__ == "__main__":
    main()
