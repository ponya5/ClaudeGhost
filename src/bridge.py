from __future__ import annotations

import json
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
# AFK level -> --allowedTools mapping for headless (-p) mode
# ---------------------------------------------------------------------------
_LEVEL_ALLOWED_TOOLS: dict[int, list[str]] = {
    1: [],
    2: ["Read"],
    3: ["Read", "Write", "Edit"],
    4: ["Read", "Write", "Edit", "Bash"],
    5: [
        "Read", "Write", "Edit",
        "Bash", "WebFetch", "WebSearch",
    ],
}

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
# Cost-parsing patterns
# ---------------------------------------------------------------------------
_COST_RE = re.compile(
    r"(?i)(?:cost|total|spent)[:\s]*\$?([\d]+\.[\d]{2})"
)
_JSON_COST_RE = re.compile(
    r'"costUSD"\s*:\s*([\d]+\.[\d]+)'
)
_JSON_COST_TOTAL_RE = re.compile(
    r'"cost"\s*:\s*\{[^}]*"total"\s*:\s*([\d]+\.[\d]+)'
)
_TOTAL_COST_RE = re.compile(
    r"Total cost:\s*\$?([\d]+\.[\d]{2})"
)

# ---------------------------------------------------------------------------
# State detection patterns (used for pexpect / TUI mode)
# ---------------------------------------------------------------------------
_QUERY_RE = re.compile(
    r"(?i)"
    r"(do you want to "
    r"(run|create|edit|delete|execute|overwrite|write|allow|remove))"
    r"|(\(y\/n\))"
    r"|(\(Y\)es|\(N\)o)"
    r"|(approve this|allow this|proceed\s*\?)"
    r"|(yes.*?/.*?no)"
    r"|(Allow|Deny|Skip)\s",
)
_PROMPT_RE = re.compile(
    r"(?:^|\n)\s*>\s*$", re.MULTILINE
)
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
# Stream-JSON event parser
# ---------------------------------------------------------------------------
def _parse_stream_event(line: str) -> Optional[str]:
    """Parse a stream-json line into a human-readable summary.

    Returns None if the line is not interesting.
    """
    line = line.strip()
    if not line:
        return None
    try:
        evt = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None

    etype = evt.get("type", "")

    # --- Assistant messages ---
    if etype == "assistant":
        msg = evt.get("message", {})
        content = msg.get("content", [])
        parts: list[str] = []
        for block in (
            content if isinstance(content, list) else []
        ):
            btype = block.get("type", "")
            if btype == "text":
                text = block.get("text", "")
                if text:
                    for ln in text.strip().splitlines():
                        ln = ln.strip()
                        if ln:
                            parts.append(ln[:120])
                            break
            elif btype == "tool_use":
                name = block.get("name", "tool")
                inp = block.get("input", {})
                if name.lower() in ("bash", "execute"):
                    cmd = inp.get("command", "")
                    parts.append(
                        f"[cyan]⚡ {name}:[/cyan] "
                        f"{cmd[:100]}"
                    )
                elif name.lower() in (
                    "read", "readfile",
                ):
                    path = inp.get(
                        "file_path",
                        inp.get("path", ""),
                    )
                    parts.append(
                        f"[dim]📖 Read:[/dim] {path}"
                    )
                elif name.lower() in (
                    "write", "edit", "editfile",
                    "writefile", "create",
                ):
                    path = inp.get(
                        "file_path",
                        inp.get("path", ""),
                    )
                    parts.append(
                        f"[yellow]✏️  Edit:[/yellow]"
                        f" {path}"
                    )
                else:
                    parts.append(
                        f"[magenta]🔧 {name}[/magenta]"
                    )
        if parts:
            return " | ".join(parts)

    # --- Streaming text delta ---
    if etype == "content_block_delta":
        delta = evt.get("delta", {})
        if delta.get("type") == "text_delta":
            text = delta.get("text", "").strip()
            if text and len(text) > 5:
                return text[:120]

    # --- Result / completion ---
    if etype == "result":
        cost = (
            evt.get("total_cost_usd")
            or evt.get("cost_usd")
            or evt.get("costUSD")
        )
        # Also check modelUsage for cost
        if not cost:
            mu = evt.get("modelUsage", {})
            for v in mu.values():
                if isinstance(v, dict):
                    c = v.get("costUSD")
                    if c:
                        cost = c
                        break
        num_turns = evt.get("num_turns", "")
        duration = evt.get("duration_ms", 0)
        dur_s = f"{duration / 1000:.1f}s" if duration else ""
        if cost:
            return (
                f"[green]✓ Done[/green] — "
                f"cost: ${float(cost):.4f}"
                f" turns: {num_turns}"
                f" {dur_s}"
            )
        result_text = evt.get("result", "")
        if (
            isinstance(result_text, str)
            and result_text.strip()
        ):
            return (
                f"[green]✓[/green] "
                f"{result_text[:100]}"
            )

    # --- System messages ---
    if etype == "system":
        sub = evt.get("subtype", "")
        if sub == "init":
            model = evt.get("model", "")
            cwd = evt.get("cwd", "")
            return (
                f"[green]⚙ Initialized[/green]"
                f" model={model}"
                f" cwd={cwd[-40:]}"
            )
        if sub == "hook_started":
            name = evt.get("hook_name", "")
            return f"[dim]🔗 Hook: {name}[/dim]"
        if sub == "hook_response":
            name = evt.get("hook_name", "")
            outcome = evt.get("outcome", "")
            return (
                f"[dim]🔗 Hook done: {name}"
                f" ({outcome})[/dim]"
            )
        msg = evt.get("message", "")
        if isinstance(msg, str) and msg.strip():
            return f"[dim]{msg[:120]}[/dim]"

    return None


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------
class GhostBridge:
    """Wraps the claude CLI in a subprocess and provides
    programmatic I/O with state detection.

    Both Windows and macOS/Linux use headless mode
    (``claude -p`` with ``--output-format stream-json``)
    so that ClaudeGhost can reliably parse events and
    display them in the dashboard.
    """

    def __init__(
        self,
        task: str,
        on_query: Callable[[str], None],
        on_idle: Optional[Callable[[], None]] = None,
        on_stall: Optional[Callable[[], None]] = None,
        afk_level: int = 3,
    ) -> None:
        self.task = task
        self._on_query = on_query
        self._on_idle = on_idle
        self._on_stall = on_stall
        self._afk_level = max(1, min(5, afk_level))

        self._child: Optional[subprocess.Popen] = None
        self._buffer: str = ""
        self._state = CliState.THINKING
        self._running = False
        self._last_output_time = time.time()
        self._total_cost: float = 0.0
        self._lock = threading.Lock()
        self._query_fired_for: Optional[str] = None

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
        logger.info(
            "Spawning: %s %r  (cwd=%s)",
            binary, self.task, cwd,
        )
        ghost_status.add_log(
            f'[bold]Spawning:[/bold] {binary} '
            f'"{self.task[:50]}"'
        )
        self._start_headless(binary, cwd)
        self._running = True
        threading.Thread(
            target=self._read_loop, daemon=True,
        ).start()
        threading.Thread(
            target=self._heartbeat_loop, daemon=True,
        ).start()

    def send(self, text: str) -> None:
        """Inject text into the running process stdin."""
        logger.info("Injecting: %r", text)
        ghost_status.add_log(f"[yellow]>>> {text}[/yellow]")
        if (
            self._child
            and self._child.stdin
            and self._child.poll() is None
        ):
            self._child.stdin.write(text + "\n")
            self._child.stdin.flush()

    def kill(self) -> None:
        self._running = False
        try:
            if self._child:
                self._child.terminate()
                try:
                    self._child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._child.kill()
        except Exception as exc:
            logger.error("Kill error: %s", exc)
        self._state = CliState.EXITED
        ghost_status.state = "EXITED"
        ghost_status.add_log(
            "[red]Process terminated.[/red]"
        )

    # ------------------------------------------------------------------
    # Spawn (headless on all platforms)
    # ------------------------------------------------------------------
    def _start_headless(
        self, binary: str, cwd: str,
    ) -> None:
        args = [
            binary, "-p", self.task,
            "--output-format", "stream-json",
            "--verbose",
        ]

        allowed = _LEVEL_ALLOWED_TOOLS.get(
            self._afk_level, []
        )
        for tool in allowed:
            args.extend(["--allowedTools", tool])

        budget = settings.max_budget_usd
        if budget and 0 < budget < 999:
            args.extend([
                "--max-budget-usd", str(budget),
            ])

        use_shell = sys.platform == "win32"
        logger.info("Subprocess args: %s", args)
        ghost_status.add_log(
            f"[bold]Headless mode:[/bold] "
            f"level {self._afk_level}, "
            f"tools: "
            f"{', '.join(allowed) or 'none'}, "
            f"budget: ${budget:.2f}"
        )
        ghost_status.add_event(
            "[bold green]Claude Code launched — "
            "events will appear here ↓[/bold green]"
        )

        self._child = subprocess.Popen(
            args,
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
                ghost_status.add_log(
                    "[bold red]CLI process exited."
                    "[/bold red]"
                )
                ghost_status.add_event(
                    "[bold red]Claude Code exited."
                    "[/bold red]"
                )
                if self._on_idle:
                    self._on_idle()
                break
            if not chunk:
                continue

            with self._lock:
                self._last_output_time = time.time()

            clean = strip_ansi(chunk)
            self._buffer += clean

            # Parse each line of output
            for line in clean.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue

                # Try stream-json parsing first
                readable = _parse_stream_event(stripped)
                if readable:
                    ghost_status.add_event(readable)
                elif not stripped.startswith("{"):
                    # Non-JSON (stderr, plain text)
                    ghost_status.add_log(
                        stripped[:120]
                    )

            self._parse_cost(clean)
            self._detect_state()

            if len(self._buffer) > 20_000:
                self._buffer = self._buffer[-10_000:]

    def _read_chunk(self) -> Optional[str]:
        """Read a line from stdout. None on EOF."""
        if self._child is None or self._child.stdout is None:
            return None
        try:
            line = self._child.stdout.readline()
            if not line and self._child.poll() is not None:
                return None
            return line
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------
    # State detection
    # ------------------------------------------------------------------
    def _detect_state(self) -> None:
        tail = self._buffer[-3000:]

        if (
            _QUERY_RE.search(tail)
            or _TOOL_QUERY_RE.search(tail)
        ):
            dedup_key = tail[-500:]
            if (
                self._state != CliState.QUERY
                or self._query_fired_for != dedup_key
            ):
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
        best = self._total_cost

        for m in _JSON_COST_RE.finditer(text):
            try:
                val = float(m.group(1))
                if val > best:
                    best = val
            except ValueError:
                pass

        for m in _JSON_COST_TOTAL_RE.finditer(text):
            try:
                val = float(m.group(1))
                if val > best:
                    best = val
            except ValueError:
                pass

        for m in _TOTAL_COST_RE.finditer(text):
            try:
                val = float(m.group(1))
                if val > best:
                    best = val
            except ValueError:
                pass

        for m in _COST_RE.finditer(text):
            try:
                val = float(m.group(1))
                if val > best:
                    best = val
            except ValueError:
                pass

        if best > self._total_cost:
            self._total_cost = best
            ghost_status.budget_used = best
            logger.info("Budget update: $%.4f", best)

    # ------------------------------------------------------------------
    # Heartbeat / stall detection
    # ------------------------------------------------------------------
    def _heartbeat_loop(self) -> None:
        while self._running:
            time.sleep(5)
            with self._lock:
                elapsed = (
                    time.time() - self._last_output_time
                )
            timeout = settings.heartbeat_timeout_seconds
            if (
                elapsed > timeout
                and self._state == CliState.THINKING
            ):
                logger.warning(
                    "Heartbeat: stall (%0.fs)", elapsed,
                )
                ghost_status.add_log(
                    f"[bold yellow]Stall detected "
                    f"({elapsed:.0f}s)[/bold yellow]"
                )
                if self._on_stall:
                    self._on_stall()
                with self._lock:
                    self._last_output_time = time.time()
