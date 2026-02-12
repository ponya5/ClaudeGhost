"""CLI utilities for ClaudeGhost configuration management."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def cmd_config_show():
    """Show current configuration."""
    from src.config import settings
    
    table = Table(title="ClaudeGhost Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Section", style="dim")
    
    configs = [
        ("WAHA URL", settings.waha_api_url, "waha"),
        ("WAHA API Key", "****" + settings.waha_api_key[-4:] if len(settings.waha_api_key) > 4 else "(not set)", "waha"),
        ("WAHA Session", settings.waha_session, "waha"),
        ("WAHA Enabled", str(settings.waha_enabled), "waha"),
        ("Target Phone", settings.target_phone, "waha"),
        ("AFK Level", str(settings.default_afk_level), "autonomy"),
        ("Max Budget", f"${settings.max_budget_usd:.2f}", "budget"),
        ("Claude Binary", settings.claude_binary, "claude"),
        ("Working Dir", settings.working_directory, "claude"),
        ("Poll Interval", f"{settings.poll_interval_seconds}s", "timing"),
        ("Heartbeat Timeout", f"{settings.heartbeat_timeout_seconds}s", "timing"),
    ]
    
    for name, value, section in configs:
        table.add_row(name, str(value), section)
    
    console.print(table)
    console.print()
    
    env_file = PROJECT_ROOT / ".env"
    config_file = PROJECT_ROOT / "config.yaml"
    console.print(f"[dim]Config files:[/dim]")
    console.print(f"  .env:        {'[green]exists[/green]' if env_file.exists() else '[red]missing[/red]'}")
    console.print(f"  config.yaml: {'[green]exists[/green]' if config_file.exists() else '[yellow]using defaults[/yellow]'}")


def cmd_config_set(key: str, value: str):
    """Set a configuration value in .env file."""
    env_file = PROJECT_ROOT / ".env"
    
    if not env_file.exists():
        console.print("[red]Error:[/red] .env file not found. Run 'python install.py' first.")
        return False
    
    key_map = {
        "waha-url": "WAHA_API_URL",
        "waha-key": "WAHA_API_KEY",
        "waha-session": "WAHA_SESSION",
        "phone": "TARGET_PHONE",
        "level": "DEFAULT_AFK_LEVEL",
        "budget": "MAX_BUDGET_USD",
        "poll-interval": "POLL_INTERVAL_SECONDS",
        "heartbeat": "HEARTBEAT_TIMEOUT_SECONDS",
    }
    
    env_key = key_map.get(key.lower(), key.upper())
    
    content = env_file.read_text()
    lines = content.splitlines()
    found = False
    
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}=") or line.startswith(f"# {env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break
    
    if not found:
        lines.append(f"{env_key}={value}")
    
    env_file.write_text("\n".join(lines) + "\n")
    console.print(f"[green]OK[/green] Set {env_key}={value}")
    return True


def cmd_config_test():
    """Test WAHA connection."""
    from src.waha import WahaClient
    from src.config import settings
    
    console.print("[bold]Testing WAHA connection...[/bold]")
    console.print(f"  URL: {settings.waha_api_url}")
    console.print(f"  Session: {settings.waha_session}")
    console.print(f"  Phone: {settings.target_phone}")
    console.print()
    
    client = WahaClient()
    if client.check_connection():
        console.print("[green]WAHA connection successful![/green]")
        
        response = input("Send test message? [y/N]: ").strip().lower()
        if response == "y":
            if client.send("ClaudeGhost test - connection verified!"):
                console.print("[green]Test message sent![/green]")
            else:
                console.print("[red]Failed to send test message[/red]")
    else:
        console.print("[red]WAHA connection failed[/red]")
        console.print()
        console.print("[yellow]Troubleshooting:[/yellow]")
        console.print("  1. Is WAHA running? Check: docker ps")
        console.print("  2. Is the session started and linked?")
        console.print("  3. Is the API key correct?")
        console.print(f"  4. Can you reach {settings.waha_api_url}?")


def cmd_config_init():
    """Initialize configuration files."""
    import shutil
    
    env_example = PROJECT_ROOT / ".env.example"
    env_file = PROJECT_ROOT / ".env"
    
    if env_file.exists():
        console.print("[yellow]Warning:[/yellow] .env already exists")
        response = input("Overwrite? [y/N]: ").strip().lower()
        if response != "y":
            return
    
    if env_example.exists():
        shutil.copy(env_example, env_file)
        console.print("[green]OK[/green] Created .env from template")
        console.print()
        console.print("[bold]Next:[/bold] Edit .env with your settings, or use:")
        console.print("  python -m src.cli config set phone YOUR_NUMBER")
        console.print("  python -m src.cli config set waha-key YOUR_API_KEY")
    else:
        console.print("[red]Error:[/red] .env.example not found")


def main():
    parser = argparse.ArgumentParser(
        prog="claudeghost-cli",
        description="ClaudeGhost CLI utilities"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    
    config_sub.add_parser("show", help="Show current configuration")
    
    set_parser = config_sub.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Config key (e.g., phone, waha-key, budget)")
    set_parser.add_argument("value", help="Value to set")
    
    config_sub.add_parser("test", help="Test WAHA connection")
    config_sub.add_parser("init", help="Initialize .env file")
    
    args = parser.parse_args()
    
    if args.command == "config":
        if args.config_cmd == "show":
            cmd_config_show()
        elif args.config_cmd == "set":
            cmd_config_set(args.key, args.value)
        elif args.config_cmd == "test":
            cmd_config_test()
        elif args.config_cmd == "init":
            cmd_config_init()
        else:
            config_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
