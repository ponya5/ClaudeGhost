"""Interactive launcher for ClaudeGhost sessions."""
from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

from src.config import (
    settings,
    SessionConfig,
    BUDGET_PRESETS,
    LEVEL_NAMES,
    LEVEL_DESCRIPTIONS,
)

console = Console()


def print_banner() -> None:
    """Display the ClaudeGhost ASCII banner."""
    banner = Text()
    banner.append("   _____ _                 _       ", style="bold blue")
    banner.append("\n")
    banner.append("  / ____| |               | |      ", style="bold blue")
    banner.append("\n")
    banner.append(" | |    | | __ _ _   _  __| | ___  ", style="bold blue")
    banner.append("\n")
    banner.append(" | |    | |/ _` | | | |/ _` |/ _ \\ ", style="bold blue")
    banner.append("\n")
    banner.append(" | |____| | (_| | |_| | (_| |  __/ ", style="bold blue")
    banner.append("\n")
    banner.append("  \\_____|_|\\__,_|\\__,_|\\__,_|\\___| ", style="bold blue")
    banner.append("\n")
    banner.append("   _____ _               _         ", style="bold cyan")
    banner.append("\n")
    banner.append("  / ____| |             | |        ", style="bold cyan")
    banner.append("\n")
    banner.append(" | |  __| |__   ___  ___| |_       ", style="bold cyan")
    banner.append("\n")
    banner.append(" | | |_ | '_ \\ / _ \\/ __| __|      ", style="bold cyan")
    banner.append("\n")
    banner.append(" | |__| | | | | (_) \\__ \\ |_       ", style="bold cyan")
    banner.append("\n")
    banner.append("  \\_____|_| |_|\\___/|___/\\__|      ", style="bold cyan")
    banner.append("\n\n")
    banner.append(" Headless Supervisor for Claude Code", style="dim")
    banner.append("\n")
    banner.append(" v2.0 - Telegram Edition", style="dim")
    console.print(Panel(banner, border_style="blue", padding=(0, 2)))
    console.print()


def select_afk_level() -> int:
    """Interactive AFK level selection."""
    console.print("[bold]Step 2: Select AFK Autonomy Level[/bold]\n")
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Level", style="bold", width=8)
    table.add_column("Name", width=12)
    table.add_column("Description", width=55)

    for level, name in LEVEL_NAMES.items():
        desc = LEVEL_DESCRIPTIONS[level]
        color = ["red", "yellow", "green", "cyan", "magenta"][level - 1]
        table.add_row(
            f"[{color}]{level}[/{color}]",
            f"[{color}]{name}[/{color}]",
            desc,
        )
    console.print(table)
    console.print()

    choice = Prompt.ask(
        "Select level",
        choices=["1", "2", "3", "4", "5"],
        default=str(settings.default_afk_level),
    )
    level = int(choice)
    console.print(
        f"  [green]>[/green] Selected: [bold]{level}[/bold]"
        f" ({LEVEL_NAMES[level]})\n"
    )
    return level


def select_budget() -> float:
    """Interactive budget selection with arrow keys."""
    from src.arrow_select import arrow_select
    from src.config import BUDGET_PRESETS

    console.print("[bold]Step 4: Set Budget Limit (Quota)[/bold]\n")

    options: list[tuple[str, str]] = []
    amounts: list[float] = []
    default_idx = 0

    for i, (name, amount) in enumerate(BUDGET_PRESETS.items()):
        if amount > 100:
            options.append((name.capitalize(), "No limit"))
        else:
            options.append((name.capitalize(), f"${amount:.2f}"))
        amounts.append(amount)
        if name == settings.budget_preset:
            default_idx = i

    options.append(("Custom", "Enter amount"))
    amounts.append(-1)

    idx = arrow_select(options, default_index=default_idx)
    if idx is None:
        idx = default_idx

    if amounts[idx] < 0:
        # Custom amount
        while True:
            try:
                amount = float(
                    Prompt.ask("Enter budget in USD", default="5.00")
                )
                if amount < 0:
                    console.print("[red]Budget must be positive[/red]")
                    continue
                break
            except ValueError:
                console.print("[red]Invalid number[/red]")
    else:
        amount = amounts[idx]

    if amount > 100:
        console.print(
            "  [green]>[/green] Budget: [bold]Unlimited[/bold]\n"
        )
    else:
        console.print(
            f"  [green]>[/green] Budget: [bold]${amount:.2f}[/bold]\n"
        )
    return amount


def select_notification_mode() -> bool:
    """Select Telegram or screen-only notification."""
    console.print("[bold]Step 3: Communication Method[/bold]\n")
    console.print("  [1] [green]Telegram[/green] - Get approval requests on your phone")
    console.print("  [2] [cyan]Screen Only[/cyan] - Show prompts in terminal\n")

    choice = Prompt.ask(
        "Select mode",
        choices=["1", "2", "telegram", "screen"],
        default="1" if settings.telegram_enabled else "2",
    )
    telegram_enabled = choice in ("1", "telegram")

    if telegram_enabled:
        console.print("  [green]>[/green] Mode: [bold]Telegram[/bold]\n")
    else:
        console.print("  [green]>[/green] Mode: [bold]Screen Only[/bold]\n")
    return telegram_enabled


def enter_task() -> str:
    """Get the task description from user."""
    console.print("[bold]Step 1: Enter Your Task[/bold]\n")
    console.print("[dim]Examples:[/dim]")
    console.print("[dim]  - Refactor auth_service.py to use JWT[/dim]")
    console.print("[dim]  - Add unit tests for UserController[/dim]")
    console.print("[dim]  - Fix the bug in payment processing[/dim]\n")

    while True:
        task = Prompt.ask("Task").strip()
        if len(task) >= 5:
            break
        console.print("[red]Please provide a more detailed task[/red]")

    short = task[:60] + ("..." if len(task) > 60 else "")
    console.print(f"  [green]>[/green] Task: [bold]{short}[/bold]\n")
    return task


def confirm_and_execute(config: SessionConfig) -> bool:
    """Show summary and confirm execution."""
    console.print("[bold]Session Configuration Summary[/bold]\n")
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Key", style="dim")
    summary.add_column("Value", style="bold")

    short_task = config.task[:60] + ("..." if len(config.task) > 60 else "")
    summary.add_row("Task:", short_task)
    summary.add_row("AFK Level:", f"{config.afk_level} ({config.level_name})")
    budget_str = "Unlimited" if config.budget_usd > 100 else f"${config.budget_usd:.2f}"
    summary.add_row("Budget:", budget_str)
    notify = "Telegram" if config.telegram_enabled else "Screen Only"
    summary.add_row("Notifications:", notify)
    summary.add_row("Working Dir:", config.working_directory)

    console.print(Panel(summary, border_style="green"))
    console.print()
    return Confirm.ask("[bold]Execute task?[/bold]", default=True)


def run_interactive_launcher() -> Optional[SessionConfig]:
    """Run the full interactive launcher flow."""
    print_banner()
    try:
        # Step 1: Task
        task = enter_task()
        
        # Step 2: AFK Level
        afk_level = select_afk_level()
        
        # Step 3: Communication Method
        telegram_enabled = select_notification_mode()
        
        # Step 4: Budget/Quota
        budget = select_budget()

        config = SessionConfig(
            task=task,
            afk_level=afk_level,
            budget_usd=budget,
            telegram_enabled=telegram_enabled,
        )
        if confirm_and_execute(config):
            return config
        console.print("[yellow]Cancelled.[/yellow]")
        return None
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None


def run_quick_launcher(
    task: str,
    level: int = 3,
    budget: float = 5.0,
    telegram: bool = True,
) -> SessionConfig:
    """Create a session config directly without interactive prompts."""
    return SessionConfig(
        task=task,
        afk_level=level,
        budget_usd=budget,
        telegram_enabled=telegram,
    )
