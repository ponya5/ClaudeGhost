"""Update checker for ClaudeGhost."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import requests

from src.utils import logger

CURRENT_VERSION = "2.0.0"
GITHUB_REPO = "yourusername/ClaudeGhost"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def get_latest_version() -> Optional[str]:
    """Fetch the latest version from GitHub releases."""
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            tag = data.get("tag_name", "")
            # Remove 'v' prefix if present
            return tag.lstrip("v")
        return None
    except Exception as e:
        logger.debug("Failed to check for updates: %s", e)
        return None


def compare_versions(current: str, latest: str) -> bool:
    """Compare version strings. Returns True if update available."""
    try:
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        return latest_parts > current_parts
    except Exception:
        return False


def check_for_updates() -> Tuple[bool, Optional[str]]:
    """Check if an update is available.
    
    Returns:
        (update_available, latest_version)
    """
    latest = get_latest_version()
    if latest is None:
        return False, None
    
    if compare_versions(CURRENT_VERSION, latest):
        return True, latest
    
    return False, latest


def update_claudeghost() -> bool:
    """Update ClaudeGhost by pulling latest from git.
    
    Returns:
        True if update successful, False otherwise
    """
    try:
        # Get the ClaudeGhost directory
        claudeghost_dir = Path(__file__).parent.parent
        
        logger.info("Updating ClaudeGhost...")
        
        # Check if it's a git repository
        git_dir = claudeghost_dir / ".git"
        if not git_dir.exists():
            logger.error(
                "Not a git repository. "
                "Please clone from GitHub to enable updates."
            )
            return False
        
        # Pull latest changes
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=claudeghost_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            logger.error("Git pull failed: %s", result.stderr)
            return False
        
        logger.info("Update successful: %s", result.stdout.strip())
        
        # Reinstall dependencies
        logger.info("Updating dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=claudeghost_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        
        if result.returncode != 0:
            logger.warning("Failed to update dependencies: %s", result.stderr)
        
        return True
        
    except Exception as e:
        logger.error("Update failed: %s", e)
        return False


def print_update_notification(latest_version: str) -> None:
    """Print update notification to console."""
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    message = (
        f"[bold yellow]Update Available![/bold yellow]\n\n"
        f"Current version: [cyan]{CURRENT_VERSION}[/cyan]\n"
        f"Latest version: [green]{latest_version}[/green]\n\n"
        f"Run: [bold]python -m src.updater[/bold] to update"
    )
    console.print(Panel(message, border_style="yellow", padding=(1, 2)))


def main() -> None:
    """CLI entry point for updating ClaudeGhost."""
    from rich.console import Console
    from rich.prompt import Confirm
    
    console = Console()
    
    console.print("[bold]Checking for updates...[/bold]")
    update_available, latest_version = check_for_updates()
    
    if not update_available:
        console.print(
            f"[green]✓[/green] You're running the latest version "
            f"({CURRENT_VERSION})"
        )
        return
    
    console.print(
        f"\n[yellow]Update available:[/yellow] "
        f"{CURRENT_VERSION} → {latest_version}"
    )
    
    if Confirm.ask("Update now?", default=True):
        console.print("\n[bold]Updating ClaudeGhost...[/bold]")
        if update_claudeghost():
            console.print(
                "\n[green]✓ Update successful![/green]\n"
                "Please restart ClaudeGhost."
            )
        else:
            console.print(
                "\n[red]✗ Update failed.[/red]\n"
                "Please update manually:\n"
                "  git pull origin main\n"
                "  pip install -r requirements.txt"
            )
    else:
        console.print("[yellow]Update cancelled.[/yellow]")


if __name__ == "__main__":
    main()
