"""Arrow-key selector for terminal menus. No extra dependencies."""
from __future__ import annotations

import sys
from typing import Optional

from rich.console import Console
from rich.text import Text

_console = Console()


def _read_key_windows() -> str:
    """Read a single keypress on Windows."""
    import msvcrt
    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        code = msvcrt.getwch()
        if code == "H":
            return "up"
        if code == "P":
            return "down"
        return "other"
    if ch == "\r":
        return "enter"
    return ch


def _read_key_unix() -> str:
    """Read a single keypress on Unix/macOS."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            return "other"
        if ch in ("\r", "\n"):
            return "enter"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key() -> str:
    if sys.platform == "win32":
        return _read_key_windows()
    return _read_key_unix()


def arrow_select(
    options: list[tuple[str, str]],
    default_index: int = 0,
    title: str = "",
) -> Optional[int]:
    """Show an arrow-key menu and return the selected index.

    Args:
        options: list of (label, description) tuples.
        default_index: initially highlighted row.
        title: optional header printed above the menu.

    Returns:
        Selected index, or None if the user pressed Ctrl-C.
    """
    idx = max(0, min(default_index, len(options) - 1))

    def _render(selected: int) -> None:
        # Move cursor up to overwrite previous render
        lines: list[str] = []
        for i, (label, desc) in enumerate(options):
            if i == selected:
                lines.append(
                    f"  [bold cyan]> {label:<14}[/bold cyan]"
                    f" [bold]{desc}[/bold]"
                )
            else:
                lines.append(
                    f"    [dim]{label:<14} {desc}[/dim]"
                )
        _console.print("\n".join(lines))

    if title:
        _console.print(title)
    _console.print(
        "[dim]  Use ↑↓ arrows to select, Enter to confirm[/dim]\n"
    )
    _render(idx)

    while True:
        try:
            key = _read_key()
        except (KeyboardInterrupt, EOFError):
            return None

        if key == "up":
            idx = (idx - 1) % len(options)
        elif key == "down":
            idx = (idx + 1) % len(options)
        elif key == "enter":
            return idx
        else:
            continue

        # Move cursor up to overwrite the menu
        _console.file.write(f"\033[{len(options)}A\r")
        _console.file.flush()
        _render(idx)
