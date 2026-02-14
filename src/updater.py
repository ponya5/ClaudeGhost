"""Update checker for ClaudeGhost."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Tuple

from src.utils import logger

CURRENT_VERSION = "2.0.0"


def check_for_updates() -> Tuple[bool, str]:
    """Check if local repo is behind remote.

    Returns:
        (update_available, message)
    """
    try:
        cg_dir = Path(__file__).parent.parent
        git_dir = cg_dir / ".git"
        if not git_dir.exists():
            return False, ""

        # Fetch latest from remote (silent)
        subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            cwd=cg_dir,
            capture_output=True,
            check=False,
            timeout=10,
        )

        # Compare local HEAD vs remote HEAD
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        remote = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if local.returncode != 0 or remote.returncode != 0:
            return False, ""

        local_hash = local.stdout.strip()
        remote_hash = remote.stdout.strip()

        if local_hash == remote_hash:
            return False, ""

        # Count commits behind
        behind = subprocess.run(
            ["git", "rev-list", "--count", f"HEAD..origin/main"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        count = behind.stdout.strip() if behind.returncode == 0 else "?"

        return True, f"{count} commit(s) behind remote"

    except Exception as e:
        logger.debug("Update check failed: %s", e)
        return False, ""


def update_claudeghost() -> bool:
    """Pull latest from git and update dependencies."""
    try:
        cg_dir = Path(__file__).parent.parent

        git_dir = cg_dir / ".git"
        if not git_dir.exists():
            logger.error(
                "Not a git repository. "
                "Clone from GitHub to enable updates."
            )
            return False

        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error("Git pull failed: %s", result.stderr)
            return False

        logger.info("Pull: %s", result.stdout.strip())

        # Update dependencies
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install",
                "-r", "requirements.txt", "--quiet",
            ],
            cwd=cg_dir,
            capture_output=True,
            check=False,
        )

        return True

    except Exception as e:
        logger.error("Update failed: %s", e)
        return False


def print_update_notification(message: str) -> None:
    """Print update notification to console."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    text = (
        f"[bold yellow]Update Available[/bold yellow]\n\n"
        f"[cyan]{message}[/cyan]\n\n"
        f"Run: [bold]python -m src.updater[/bold] to update"
    )
    console.print(Panel(text, border_style="yellow", padding=(1, 2)))


def auto_update() -> None:
    """Check for updates and apply them automatically with a spinner.

    Called at launch — if an update is found the repo is pulled,
    dependencies are installed, and the user sees a progress message
    the whole time.  If anything fails it is silently skipped so the
    normal launch flow is never blocked.
    """
    from rich.console import Console
    from rich.status import Status

    console = Console()

    try:
        cg_dir = Path(__file__).parent.parent
        git_dir = cg_dir / ".git"
        if not git_dir.exists():
            return

        # --- Phase 1: fetch + compare (quick) ---
        with Status(
            "[cyan]Checking for updates...[/cyan]",
            console=console,
            spinner="dots",
        ):
            subprocess.run(
                ["git", "fetch", "origin", "--quiet"],
                cwd=cg_dir,
                capture_output=True,
                check=False,
                timeout=15,
            )

            local = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=cg_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            remote = subprocess.run(
                ["git", "rev-parse", "origin/main"],
                cwd=cg_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if (
                local.returncode != 0
                or remote.returncode != 0
            ):
                return

            if local.stdout.strip() == remote.stdout.strip():
                console.print(
                    f"[green]✓[/green] ClaudeGhost is up to date "
                    f"(v{CURRENT_VERSION})"
                )
                return

            # How far behind?
            behind = subprocess.run(
                [
                    "git", "rev-list", "--count",
                    "HEAD..origin/main",
                ],
                cwd=cg_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            count = (
                behind.stdout.strip()
                if behind.returncode == 0
                else "new"
            )

        # --- Phase 2: pull + install (may take a moment) ---
        with Status(
            f"[yellow]Updating ClaudeGhost "
            f"({count} update(s))...[/yellow]",
            console=console,
            spinner="dots",
        ):
            pull = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=cg_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
            if pull.returncode != 0:
                console.print(
                    "[red]✗ Update failed "
                    "(git pull error)[/red]"
                )
                logger.debug(
                    "git pull stderr: %s", pull.stderr
                )
                return

            subprocess.run(
                [
                    sys.executable, "-m", "pip", "install",
                    "-r", "requirements.txt", "--quiet",
                ],
                cwd=cg_dir,
                capture_output=True,
                check=False,
                timeout=120,
            )

        console.print(
            f"[green]✓ Updated to latest "
            f"({count} update(s) applied)[/green]"
        )

    except Exception as exc:
        logger.debug("Auto-update failed: %s", exc)


def main() -> None:
    """CLI entry point for updating ClaudeGhost."""
    from rich.console import Console
    from rich.prompt import Confirm

    console = Console()

    console.print("[bold]Checking for updates...[/bold]")
    update_available, message = check_for_updates()

    if not update_available:
        console.print(
            f"[green]✓[/green] Already up to date "
            f"(v{CURRENT_VERSION})"
        )
        return

    console.print(f"\n[yellow]Update available:[/yellow] {message}")

    if Confirm.ask("Update now?", default=True):
        console.print("\n[bold]Updating...[/bold]")
        if update_claudeghost():
            console.print(
                "\n[green]✓ Updated successfully![/green]\n"
                "Restart ClaudeGhost to use the new version."
            )
        else:
            console.print(
                "\n[red]✗ Update failed.[/red]\n"
                "Try manually:\n"
                "  git pull origin main\n"
                "  pip install -r requirements.txt"
            )
    else:
        console.print("[yellow]Skipped.[/yellow]")


if __name__ == "__main__":
    main()
