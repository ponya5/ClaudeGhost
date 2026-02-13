"""CLI utilities for ClaudeGhost configuration management."""
from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def cmd_config_show():
    """Show current configuration."""
    from src.config import settings

    table = Table(title="ClaudeGhost Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Section", style="dim")

    token_display = (
        "****" + settings.telegram_bot_token[-6:]
        if len(settings.telegram_bot_token) > 6
        else "(not set)"
    )
    configs = [
        ("Bot Token", token_display, "telegram"),
        ("Chat ID", settings.telegram_chat_id or "(not set)", "telegram"),
        ("Telegram Enabled", str(settings.telegram_enabled), "telegram"),
        ("AFK Level", str(settings.default_afk_level), "autonomy"),
        ("Max Budget", f"${settings.max_budget_usd:.2f}", "budget"),
        ("Claude Binary", settings.claude_binary, "claude"),
        ("Working Dir", settings.working_directory, "claude"),
        ("Poll Interval", f"{settings.poll_interval_seconds}s", "timing"),
        ("Heartbeat", f"{settings.heartbeat_timeout_seconds}s", "timing"),
    ]
    for name, value, section in configs:
        table.add_row(name, str(value), section)

    console.print(table)
    console.print()
    env_file = PROJECT_ROOT / ".env"
    config_file = PROJECT_ROOT / "config.yaml"
    e = "[green]exists[/green]" if env_file.exists() else "[red]missing[/red]"
    c = "[green]exists[/green]" if config_file.exists() else "[yellow]defaults[/yellow]"
    console.print(f"[dim]Config files:[/dim]")
    console.print(f"  .env:        {e}")
    console.print(f"  config.yaml: {c}")


def cmd_config_set(key: str, value: str):
    """Set a configuration value in .env file."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        console.print("[red]Error:[/red] .env file not found. Copy .env.example first.")
        return False

    key_map = {
        "bot-token": "TELEGRAM_BOT_TOKEN",
        "chat-id": "TELEGRAM_CHAT_ID",
        "level": "DEFAULT_AFK_LEVEL",
        "budget": "MAX_BUDGET_USD",
        "poll-interval": "POLL_INTERVAL_SECONDS",
        "heartbeat": "HEARTBEAT_TIMEOUT_SECONDS",
    }
    env_key = key_map.get(key.lower(), key.upper())

    content = env_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{env_key}=") or line.startswith(f"# {env_key}="):
            lines[i] = f"{env_key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{env_key}={value}")

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"[green]OK[/green] Set {env_key}={value}")
    return True


def cmd_config_test():
    """Test Telegram Bot API connection."""
    from src.telegram_bot import TelegramBot
    from src.config import settings

    console.print("[bold]Testing Telegram Bot connection...[/bold]")
    if settings.telegram_bot_token:
        console.print(f"  Token: ****{settings.telegram_bot_token[-6:]}")
    else:
        console.print("  Token: (not set)")
    console.print(f"  Chat ID: {settings.telegram_chat_id or '(not set)'}")
    console.print()

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        console.print("[red]Error:[/red] Telegram not configured")
        console.print()
        console.print("[yellow]Setup required:[/yellow]")
        console.print("  1. Message @BotFather on Telegram -> /newbot")
        console.print("  2. Copy the bot token to .env")
        console.print("  3. Get your chat_id (see docs/TELEGRAM_SETUP.md)")
        return

    bot = TelegramBot()
    if bot.check_connection():
        console.print("[green]OK[/green] Telegram Bot connected")
        console.print()
        response = input("Send test message? [y/N]: ").strip().lower()
        if response == "y":
            if bot.send("ClaudeGhost test - Telegram Bot verified!"):
                console.print("[green]OK[/green] Test message sent")
            else:
                console.print("[red]FAIL[/red] Could not send test message")
    else:
        console.print("[red]FAIL[/red] Telegram Bot connection failed")
        console.print()
        console.print("[yellow]Troubleshooting:[/yellow]")
        console.print("  1. Verify bot token is correct")
        console.print("  2. Verify chat_id is correct")
        console.print("  3. Make sure you messaged the bot first")


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
        console.print("[bold]Next:[/bold] Edit .env with your settings:")
        console.print("  python -m src.cli config set bot-token YOUR_TOKEN")
        console.print("  python -m src.cli config set chat-id YOUR_CHAT_ID")
    else:
        console.print("[red]Error:[/red] .env.example not found")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="claudeghost-cli",
        description="ClaudeGhost CLI utilities",
    )
    subparsers = parser.add_subparsers(dest="command")

    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_cmd")

    config_sub.add_parser("show", help="Show current configuration")

    set_parser = config_sub.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Config key (bot-token, chat-id, budget, level)")
    set_parser.add_argument("value", help="Value to set")

    config_sub.add_parser("test", help="Test Telegram Bot connection")
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
