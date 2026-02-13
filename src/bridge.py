from __future__ import annotations

import os
import re
import sys
import time
import threading
import subprocess
from enum import Enum
from typing import Callable, Optional

from src.config import settings
from src.utils import logger, ghost_status

# ---------------------------------------------------------------------------
# Try pexpect (Unix / WSL / Docker), fall back to subprocess (Windows native)
# ---------------------------------------------------------------------------
_USE_PEXPECT = True
try:
    import pexpect
except ImportError:
    _USE_PEXPECT = False

# On Windows, always use subprocess for better compatibility with .cmd files
if sys.platform == "win32":
    _USE_PEXPECT = False

# ---------------------------------------------------------------------------
# ANSI cleaner
# ---------------------------------------------------------------------------
_ANSI_RE = re.compile(
    r"\x1b\[[0-9;]*[A-Za-z]"
    r"|\x1b\].*?(?:\x07|\x1b\\)"
    r"|\x1b\(B"
    r"|\x1b[=>]"
    r"|[\x00-\x08\x0e-\x1f]"
)


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ---------------------------------------------------------------------------
# State detection patterns
# ---------------------------------------------------------------------------
_QUERY_RE = re.compile(
    r"(?i)"
    r"(do you want to (run|create|edit|delete|execute|overwrite|write|allow|remove))"
    r"|(\(y\/n\))"
    r"|(\(Y\)es|\(N\)o)"
    r"|(approve this|allow this|proceed\s*\?)"
    r"|(yes.*?/.*?no)"
    r"|(Allow|Deny|Skip)\s",
)
_PROMPT_RE = re.compile(r"(?:^|\n)\s*>\s*$", re.MULTILINE)
_COST_RE = re.compile(r"(?i)(?:cost|total|spent)[:\s]*\$?([\d]+\.[\d]{2})")

# Claude Code's actual tool-use permission patterns
_TOOL_QUERY_RE = re.compile(
    r"(?i)"
    r"(claude wants to (run|execute|use|call))"
    r"|(tool:\s*\w+)"
    r"|(bash\s*\()"
    r"|(command:\s*.+)"
)


class CliState(str, Enum):
    IDLE = "IDLE"
    QUERY = "QUERY"
    THINKING = "THINKING"
    EXITED = "EXITED"


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------
class GhostBridge:
    """Wraps the claude CLI in a PTY (or subprocess on Windows) and provides
    programmatic I/O with state detection."""

    def __init__(
        self,
        task: str,
        on_query: Callable[[str], None],
        on_idle: Optional[Callable[[], None]] = None,
        on_stall: Optional[Callable[[], None]] = None,
    ) -> None:
        self.task = task
        self._on_query = on_query
        self._on_idle = on_idle
        self._on_stall = on_stall

        self._child: Optional[object] = None  # pexpect.spawn or subprocess.Popen
        self._buffer: str = ""
        self._state = CliState.THINKING
        self._running = False
        self._last_output_time = time.time()
        self._total_cost: float = 0.0
        self._lock = threading.Lock()
        self._query_fired_for: Optional[str] = None  # dedup key

    @property
    def state(self) -> CliState:
        return self._state

    @property
    def total_cost(self) -> float:
        return self._total_cost

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        binary = settings.claude_binary
        cwd = settings.working_directory
        logger.info("Spawning: %s %r  (cwd=%s, backend=%s)",
                     binary, self.task, cwd,
                     "pexpect" if _USE_PEXPECT else "subprocess")
        ghost_status.add_log(f"[bold]Spawning:[/bold] {binary} \"{self.task[:50]}\"")

        if _USE_PEXPECT:
            self._start_pexpect(binary, cwd)
        else:
            self._start_subprocess(binary, cwd)

        self._running = True

        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def send(self, text: str) -> None:
        """Inject text + newline into the running process."""
        logger.info("Injecting: %r", text)
        ghost_status.add_log(f"[yellow]>>> {text}[/yellow]")
        if _USE_PEXPECT and self._child is not None:
            child = self._child  # type: ignore[assignment]
            if child.isalive():
                child.sendline(text)
        elif isinstance(self._child, subprocess.Popen):
            if self._child.stdin and self._child.poll() is None:
                self._child.stdin.write(text + "\n")
                self._child.stdin.flush()

    def kill(self) -> None:
        self._running = False
        try:
            if _USE_PEXPECT and self._child is not None:
                self._child.terminate(force=True)  # type: ignore[union-attr]
            elif isinstance(self._child, subprocess.Popen):
                self._child.terminate()
                try:
                    self._child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._child.kill()
        except Exception as exc:
            logger.error("Kill error: %s", exc)
        self._state = CliState.EXITED
        ghost_status.state = "EXITED"
        ghost_status.add_log("[red]Process terminated.[/red]")

    # ------------------------------------------------------------------
    # Spawn backends
    # ------------------------------------------------------------------
    def _start_pexpect(self, binary: str, cwd: str) -> None:
        import pexpect as _pexpect

        if sys.platform == "win32":
            self._child = _pexpect.popen_spawn.PopenSpawn(
                f'{binary} "{self.task}"',
                encoding="utf-8",
                timeout=None,
                maxread=4096,
                cwd=cwd if cwd != "." else None,
            )
        else:
            self._child = _pexpect.spawn(
                binary,
                args=[self.task],
                encoding="utf-8",
                timeout=None,
                maxread=4096,
                cwd=cwd if cwd != "." else None,
            )

    def _start_subprocess(self, binary: str, cwd: str) -> None:
        # On Windows, .cmd files need shell=True to execute properly
        use_shell = sys.platform == "win32"
        self._child = subprocess.Popen(
            [binary, self.task],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd if cwd != "." else None,
            shell=use_shell,
        )

    # ------------------------------------------------------------------
    # Read loop
    # ------------------------------------------------------------------
    def _read_loop(self) -> None:
        while self._running:
            chunk = self._read_chunk()
            if chunk is None:
                self._state = CliState.EXITED
                self._running = False
                ghost_status.state = "EXITED"
                ghost_status.add_log("[bold red]CLI process exited.[/bold red]")
                if self._on_idle:
                    self._on_idle()
                break
            if not chunk:
                continue

            with self._lock:
                self._last_output_time = time.time()

            clean = strip_ansi(chunk)
            self._buffer += clean

            for line in clean.splitlines():
                stripped = line.strip()
                if stripped:
                    ghost_status.add_log(stripped[:120])

            self._parse_cost(clean)
            self._detect_state()

            if len(self._buffer) > 20_000:
                self._buffer = self._buffer[-10_000:]

    def _read_chunk(self) -> Optional[str]:
        """Return a chunk of text, empty string on timeout, None on EOF."""
        if _USE_PEXPECT and self._child is not None:
            import pexpect as _pexpect
            try:
                data = self._child.read_nonblocking(size=4096, timeout=1)  # type: ignore[union-attr]
                return data
            except _pexpect.TIMEOUT:
                return ""
            except (_pexpect.EOF, OSError):
                return None
        elif isinstance(self._child, subprocess.Popen):
            if self._child.stdout is None:
                return None
            try:
                line = self._child.stdout.readline()
                if not line and self._child.poll() is not None:
                    return None
                return line
            except (OSError, ValueError):
                return None
        return None

    # ------------------------------------------------------------------
    # State detection
    # ------------------------------------------------------------------
    def _detect_state(self) -> None:
        tail = self._buffer[-3000:]

        if _QUERY_RE.search(tail) or _TOOL_QUERY_RE.search(tail):
            dedup_key = tail[-500:]
            if self._state != CliState.QUERY or self._query_fired_for != dedup_key:
                self._state = CliState.QUERY
                self._query_fired_for = dedup_key
                ghost_status.state = "QUERY"
                logger.info("State -> QUERY")
                self._on_query(tail)
        elif _PROMPT_RE.search(tail):
            if self._state != CliState.IDLE:
                self._state = CliState.IDLE
                self._query_fired_for = None
                ghost_status.state = "IDLE"
                logger.info("State -> IDLE")
                if self._on_idle:
                    self._on_idle()
        else:
            if self._state not in (CliState.QUERY,):
                self._state = CliState.THINKING
                ghost_status.state = "THINKING"

    def _parse_cost(self, text: str) -> None:
        for m in _COST_RE.finditer(text):
            try:
                val = float(m.group(1))
                if val > self._total_cost:
                    self._total_cost = val
                    ghost_status.budget_used = val
                    logger.info("Budget update: $%.2f", val)
            except ValueError:
                pass

    # ------------------------------------------------------------------
    # Heartbeat / stall detection
    # ------------------------------------------------------------------
    def _heartbeat_loop(self) -> None:
        while self._running:
            time.sleep(5)
            with self._lock:
                elapsed = time.time() - self._last_output_time
            if (
                elapsed > settings.heartbeat_timeout_seconds
                and self._state == CliState.THINKING
            ):
                logger.warning("Heartbeat: stall detected (%0.fs)", elapsed)
                ghost_status.add_log(
                    f"[bold yellow]Stall detected ({elapsed:.0f}s)[/bold yellow]"
                )
                if self._on_stall:
                    self._on_stall()
                with self._lock:
                    self._last_output_time = time.time()
