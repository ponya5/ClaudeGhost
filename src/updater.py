"""Update checker for ClaudeGhost."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Tuple

from src.utils import logger
from src.version import __version__

CURRENT_VERSION = __version__


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

        branch = _get_default_branch(cg_dir)

        # Compare local HEAD vs remote HEAD
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        remote = subprocess.run(
            ["git", "rev-parse", f"origin/{branch}"],
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
            [
                "git", "rev-list", "--count",
                f"HEAD..origin/{branch}",
            ],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        count = (
            behind.stdout.strip()
            if behind.returncode == 0
            else "?"
        )

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

        branch = _get_default_branch(cg_dir)
        result = subprocess.run(
            ["git", "pull", "origin", branch],
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


def _get_default_branch(cg_dir: Path) -> str:
    """Detect the default remote branch (main or master)."""
    for branch in ("main", "master"):
        r = subprocess.run(
            ["git", "rev-parse", "--verify", f"origin/{branch}"],
            cwd=cg_dir,
            capture_output=True,
            check=False,
        )
        if r.returncode == 0:
            return branch
    return "main"


_MAJOR_FILES = {
    "src/main.py", "src/bridge.py", "src/guardian.py",
    "src/telegram_bot.py", "src/launcher.py",
    "src/config.py", "src/updater.py",
}


def _auto_bump_version(
    cg_dir: Path,
    old_hash: str,
    branch: str,
) -> None:
    """Bump the version in src/version.py based on
    what files changed between old_hash and HEAD.

    Major files (core logic) → bump minor version.
    Only small/docs/tests → bump patch version.
    """
    try:
        diff = subprocess.run(
            [
                "git", "diff", "--name-only",
                old_hash, f"origin/{branch}",
            ],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        if diff.returncode != 0:
            return

        changed = {
            f.strip() for f in diff.stdout.splitlines()
            if f.strip()
        }
        if not changed:
            return

        # Read current version from the file on disk
        # (which is now the NEW code after reset)
        ver_path = cg_dir / "src" / "version.py"
        if not ver_path.exists():
            return

        content = ver_path.read_text(encoding="utf-8")
        import re
        m = re.search(
            r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"',
            content,
        )
        if not m:
            return

        major = int(m.group(1))
        minor = int(m.group(2))
        patch = int(m.group(3))

        # Decide bump level
        major_hit = changed & _MAJOR_FILES
        if major_hit:
            minor += 1
            patch = 0
        else:
            patch += 1

        new_ver = f"{major}.{minor}.{patch}"
        new_content = re.sub(
            r'__version__\s*=\s*"[^"]+"',
            f'__version__ = "{new_ver}"',
            content,
        )
        ver_path.write_text(
            new_content, encoding="utf-8",
        )
        logger.debug(
            "Version bumped to %s", new_ver,
        )
    except Exception as exc:
        logger.debug(
            "Version bump failed: %s", exc,
        )


def auto_update() -> bool:
    """Check for updates and apply them automatically with a spinner.

    Called at launch — if an update is found the repo is pulled,
    dependencies are installed, and the user sees a progress message
    the whole time.  If anything fails it is silently skipped so the
    normal launch flow is never blocked.

    Returns True if an update was applied (caller should restart).
    """
    from rich.console import Console

    console = Console()

    try:
        cg_dir = Path(__file__).parent.parent
        git_dir = cg_dir / ".git"
        if not git_dir.exists():
            return False

        # --- Phase 1: fetch + compare ---
        console.print("[dim]Checking for updates...[/dim]")

        fetch = subprocess.run(
            ["git", "fetch", "origin", "--quiet"],
            cwd=cg_dir,
            capture_output=True,
            check=False,
            timeout=15,
        )
        if fetch.returncode != 0:
            console.print(
                "[dim]✓ Skipped update check "
                "(offline or no remote)[/dim]"
            )
            return False

        branch = _get_default_branch(cg_dir)

        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        remote = subprocess.run(
            ["git", "rev-parse", f"origin/{branch}"],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
        )

        if local.returncode != 0 or remote.returncode != 0:
            return False

        local_hash = local.stdout.strip()
        remote_hash = remote.stdout.strip()

        if local_hash == remote_hash:
            console.print(
                f"[green]✓[/green] ClaudeGhost "
                f"v{CURRENT_VERSION} — up to date"
            )
            return False

        # How far behind?
        behind = subprocess.run(
            [
                "git", "rev-list", "--count",
                f"HEAD..origin/{branch}",
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

        # --- Phase 2: pull + install ---
        console.print(
            f"[yellow]Updating ClaudeGhost "
            f"({count} update(s))...[/yellow]"
        )

        # Use reset --hard instead of pull to avoid
        # conflicts with local changes or diverged
        # branches.  User config (.env, session_logs/)
        # is gitignored and safe.
        reset = subprocess.run(
            [
                "git", "reset", "--hard",
                f"origin/{branch}",
            ],
            cwd=cg_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if reset.returncode != 0:
            err = (
                reset.stderr.strip()
                or reset.stdout.strip()
            )
            console.print(
                f"[red]✗ Update failed: {err}[/red]\n"
                f"[dim]Try manually: git reset "
                f"--hard origin/{branch}[/dim]"
            )
            logger.debug("git reset stderr: %s", err)
            return False

        # Auto-bump version based on what changed
        _auto_bump_version(
            cg_dir, local_hash, branch,
        )

        console.print("[dim]Installing dependencies...[/dim]")
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
        console.print(
            "[cyan]Restarting ClaudeGhost with latest code...[/cyan]\n"
        )
        return True

    except Exception as exc:
        logger.debug("Auto-update failed: %s", exc)
        return False


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
