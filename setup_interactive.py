#!/usr/bin/env python3
"""ClaudeGhost - Interactive Setup Wizard for Telegram Bot integration."""
from __future__ import annotations

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None


def _print(msg: str) -> None:
    if console:
        console.print(msg)
    else:
        print(msg)


def _ask(prompt: str, default: str = "") -> str:
    if HAS_RICH and console:
        return Prompt.ask(prompt, default=default)
    val = input(f"{prompt} [{default}]: ").strip()
    return val or default


class ClaudeGhostSetup:
    """Interactive setup for ClaudeGhost with Telegram Bot."""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        self.config: dict[str, str] = {}

    def show_welcome(self):
        if HAS_RICH and console:
            console.print(Panel.fit(
                "[bold cyan]ClaudeGhost Setup Wizard[/bold cyan]\n\n"
                "This wizard will help you set up ClaudeGhost with Telegram.\n"
                "You'll need about 5 minutes.\n\n"
                "[dim]Headless supervisor for the Anthropic Claude CLI[/dim]",
                border_style="cyan",
                box=box.DOUBLE,
            ))
        else:
            print("\n" + "=" * 50)
            print("  ClaudeGhost Setup Wizard")
            print("=" * 50)
            print("\nThis wizard will help you set up ClaudeGhost with Telegram.\n")

    def check_dependencies(self) -> bool:
        _print("\n[bold]Step 1:[/bold] Checking dependencies...\n")

        if sys.version_info < (3, 10):
            _print("  [red]X[/red] Python 3.10+ required")
            return False
        _print(f"  [green]OK[/green] Python {sys.version_info.major}.{sys.version_info.minor}")

        try:
            import requests  # noqa: F401
            _print("  [green]OK[/green] requests")
        except ImportError:
            _print("  [yellow]![/yellow] Installing requests...")
            subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)

        try:
            import rich  # noqa: F401
            _print("  [green]OK[/green] rich")
        except ImportError:
            _print("  [yellow]![/yellow] Installing rich...")
            subprocess.run([sys.executable, "-m", "pip", "install", "rich"], check=True)

        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.returncode == 0:
                _print(f"  [green]OK[/green] Claude CLI: {result.stdout.strip()}")
            else:
                _print("  [yellow]![/yellow] Claude CLI not found (install later)")
        except Exception:
            _print("  [yellow]![/yellow] Claude CLI not found (install later)")

        return True

    def configure_telegram(self):
        _print("\n[bold]Step 2:[/bold] Telegram Bot Setup\n")
        _print("  Follow these steps in Telegram:")
        _print("  1. Open Telegram and search for [bold]@BotFather[/bold]")
        _print("  2. Send [bold]/newbot[/bold]")
        _print("  3. Choose a name and username for your bot")
        _print("  4. Copy the token BotFather gives you\n")

        self.config["TELEGRAM_BOT_TOKEN"] = _ask("Paste your bot token")

        _print("\n  Now get your Chat ID:")
        _print("  1. Send any message to your new bot")
        _print("  2. Open: https://api.telegram.org/bot<TOKEN>/getUpdates")
        _print("  3. Find your chat id in the response\n")

        self.config["TELEGRAM_CHAT_ID"] = _ask("Your chat ID")

    def configure_autonomy(self):
        _print("\n[bold]Step 3:[/bold] Autonomy & Budget\n")

        if HAS_RICH and console:
            table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
            table.add_column("Level", style="cyan", width=6)
            table.add_column("Name", style="yellow", width=12)
            table.add_column("Description")
            table.add_row("1", "Paranoid", "Ask for everything")
            table.add_row("2", "Auditor", "Auto-approve reads only")
            table.add_row("3", "Manager", "Auto-approve reads + writes")
            table.add_row("4", "Director", "Auto-approve reads + writes + execute")
            table.add_row("5", "God Mode", "Auto-approve everything")
            console.print(table)

        level = _ask("Choose AFK level (1-5)", "3")
        self.config["DEFAULT_AFK_LEVEL"] = level

        budget = _ask("Max budget per session (USD)", "10.00")
        self.config["MAX_BUDGET_USD"] = budget

    def write_env(self) -> bool:
        if not self.env_example.exists():
            _print("[red]Error: .env.example not found[/red]")
            return False

        content = self.env_example.read_text(encoding="utf-8")
        for key, value in self.config.items():
            placeholder = f"{key}=" + {
                "TELEGRAM_BOT_TOKEN": "your_bot_token_here",
                "TELEGRAM_CHAT_ID": "your_chat_id_here",
                "DEFAULT_AFK_LEVEL": "3",
                "MAX_BUDGET_USD": "10.00",
            }.get(key, "")
            content = content.replace(placeholder, f"{key}={value}")

        self.env_file.write_text(content, encoding="utf-8")
        _print("\n[green]OK[/green] Configuration saved to .env")
        return True

    def test_connection(self) -> bool:
        _print("\n[bold]Step 4:[/bold] Testing Telegram connection...\n")

        try:
            import requests
            token = self.config.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = self.config.get("TELEGRAM_CHAT_ID", "")

            r = requests.get(
                f"https://api.telegram.org/bot{token}/getMe", timeout=10
            )
            data = r.json()
            if data.get("ok"):
                name = data["result"].get("username", "unknown")
                _print(f"  [green]OK[/green] Bot connected: @{name}")
            else:
                _print(f"  [red]X[/red] Bot auth failed: {data}")
                return False

            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": "ClaudeGhost setup complete!"},
                timeout=10,
            )
            if r.json().get("ok"):
                _print("  [green]OK[/green] Test message sent! Check Telegram.")
                return True
            _print(f"  [red]X[/red] Send failed: {r.json()}")
            return False
        except Exception as e:
            _print(f"  [red]X[/red] Connection error: {e}")
            return False

    def show_completion(self):
        if HAS_RICH and console:
            console.print(Panel.fit(
                "[bold green]Setup Complete![/bold green]\n\n"
                "[bold]Quick Start:[/bold]\n"
                '  python -m src.launcher "your task" --level 3\n\n'
                "[bold]Test connection:[/bold]\n"
                "  python -m src.cli config test\n\n"
                "[dim]Docs: README.md | MANUAL.md[/dim]",
                border_style="green",
                box=box.DOUBLE,
            ))
        else:
            print("\n" + "=" * 50)
            print("  Setup Complete!")
            print("=" * 50)
            print('\n  Quick Start: python -m src.launcher "your task" --level 3')
            print("  Test: python -m src.cli config test\n")

    def run(self) -> bool:
        try:
            self.show_welcome()
            if not self.check_dependencies():
                return False
            self.configure_telegram()
            self.configure_autonomy()
            if not self.write_env():
                return False
            self.test_connection()
            self.show_completion()
            return True
        except KeyboardInterrupt:
            _print("\n\n[yellow]Setup cancelled.[/yellow]")
            return False
        except Exception as e:
            _print(f"\n\n[red]Setup failed: {e}[/red]")
            return False


def main():
    setup = ClaudeGhostSetup()
    success = setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
