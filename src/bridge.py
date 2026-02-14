from __future__ import annotations

import json
import re
import shutil
import sys
import time
import threading
import subprocess
from enum import Enum
from typing import Callable, Optional

from src.config import settings
from src.utils import logger, ghost_status

# ---------------------------------------------------------------------------
# Windows: use winpty for real-time PTY output (Node buffers
# stdout when it detects a non-TTY pipe).
# ---------------------------------------------------------------------------
_HAS_WINPTY = False
_PtyProcess = None  # type: ignore
if sys.platform == "win32":
    try:
        from winpty import PtyProcess as _PtyProcess
        _HAS_WINPTY = True
    except ImportError:
        pass

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
# State detection patterns
# ---------------------------------------------------------------------------
_QUERY_RE = re.compile(
    r"(?i)"
    r"(do you want to "
    r"(run|create|edit|delete|execute"
    r"|overwrite|write|allow|remove))"
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
    r"|(command:\s*.+)",
)


class CliState(str, Enum):
    IDLE = "IDLE"
    QUERY = "QUERY"
    THINKING = "THINKING"
    EXITED = "EXITED"


# ---------------------------------------------------------------------------
# Stream-JSON event parser
# ---------------------------------------------------------------------------
class StreamEvent:
    """Parsed stream-json event with display and changelog data."""
    __slots__ = ("display", "tool_name", "tool_input",
                 "file_path", "result_text", "cost",
                 "num_turns")

    def __init__(self) -> None:
        self.display: Optional[str] = None
        self.tool_name: Optional[str] = None
        self.tool_input: Optional[str] = None
        self.file_path: Optional[str] = None
        self.result_text: Optional[str] = None
        self.cost: Optional[float] = None
        self.num_turns: Optional[int] = None


def _parse_stream_event(line: str) -> Optional[StreamEvent]:
    """Parse a stream-json line into a StreamEvent."""
    line = line.strip()
    if not line:
        return None
    try:
        evt = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None

    etype = evt.get("type", "")
    se = StreamEvent()

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
                se.tool_name = name
                if name.lower() in ("bash", "execute"):
                    cmd = inp.get("command", "")
                    se.tool_input = cmd
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
                    se.file_path = path
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
                    se.file_path = path
                    se.tool_input = path
                    parts.append(
                        f"[yellow]✏️  Edit:[/yellow]"
                        f" {path}"
                    )
                else:
                    se.tool_input = str(inp)[:200]
                    parts.append(
                        f"[magenta]🔧 {name}[/magenta]"
                    )
        if parts:
            se.display = " | ".join(parts)
            return se

    if etype == "content_block_delta":
        delta = evt.get("delta", {})
        if delta.get("type") == "text_delta":
            text = delta.get("text", "").strip()
            if text and len(text) > 5:
                se.display = text[:120]
                return se

    if etype == "result":
        cost = (
            evt.get("total_cost_usd")
            or evt.get("cost_usd")
            or evt.get("costUSD")
        )
        if not cost:
            mu = evt.get("modelUsage", {})
            for v in mu.values():
                if isinstance(v, dict):
                    c = v.get("costUSD")
                    if c:
                        cost = c
                        break
        if cost:
            se.cost = float(cost)
        num_turns = evt.get("num_turns", 0)
        if num_turns:
            try:
                se.num_turns = int(num_turns)
            except (ValueError, TypeError):
                pass
        duration = evt.get("duration_ms", 0)
        dur_s = (
            f"{duration / 1000:.1f}s" if duration else ""
        )
        result_text = evt.get("result", "")
        if isinstance(result_text, str) and result_text.strip():
            se.result_text = result_text.strip()
        if cost:
            se.display = (
                f"[green]✓ Done[/green] — "
                f"cost: ${float(cost):.4f}"
                f" turns: {se.num_turns or num_turns}"
                f" {dur_s}"
            )
            return se
        if se.result_text:
            se.display = (
                f"[green]✓[/green] "
                f"{se.result_text[:100]}"
            )
            return se

    if etype == "system":
        sub = evt.get("subtype", "")
        if sub == "init":
            model = evt.get("model", "")
            cwd = evt.get("cwd", "")
            se.display = (
                f"[green]⚙ Initialized[/green]"
                f" model={model}"
                f" cwd={cwd[-40:]}"
            )
            return se
        if sub == "hook_started":
            name = evt.get("hook_name", "")
            se.display = f"[dim]🔗 Hook: {name}[/dim]"
            return se
        if sub == "hook_response":
            name = evt.get("hook_name", "")
            outcome = evt.get("outcome", "")
            se.display = (
                f"[dim]🔗 Hook done: {name}"
                f" ({outcome})[/dim]"
            )
            return se
        msg = evt.get("message", "")
        if isinstance(msg, str) and msg.strip():
            se.display = f"[dim]{msg[:120]}[/dim]"
            return se

    return None


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------
class GhostBridge:
    """Wraps the claude CLI and provides programmatic I/O
    with state detection.

    On Windows: uses ``winpty`` (ConPTY) so that Node.js
    sees a real TTY and flushes output in real-time.
    On macOS/Linux: uses ``subprocess.Popen`` (no buffering
    issue on Unix with line-buffered pipes).
    """

    def __init__(
        self,
        task: str,
        on_query: Callable[[str], None],
        on_idle: Optional[Callable[[], None]] = None,
        on_stall: Optional[Callable[[], None]] = None,
        on_event: Optional[Callable[["StreamEvent"], None]] = None,
        afk_level: int = 3,
        model: str = "sonnet",
    ) -> None:
        self.task = task
        self._on_query = on_query
        self._on_idle = on_idle
        self._on_stall = on_stall
        self._on_event = on_event
        self._afk_level = max(1, min(5, afk_level))
        self._model = model

        self._pty = None          # winpty PtyProcess
        self._child = None        # subprocess.Popen
        self._buffer: str = ""
        self._state = CliState.THINKING
        self._running = False
        self._last_output_time = time.time()
        self._total_cost: float = 0.0
        self._num_turns: int = 0
        self._lock = threading.Lock()
        self._query_fired_for: Optional[str] = None

    @property
    def state(self) -> CliState:
        return self._state

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def num_turns(self) -> int:
        return self._num_turns

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

        self._build_and_spawn(binary, cwd)
        self._running = True

        threading.Thread(
            target=self._read_loop, daemon=True,
        ).start()
        threading.Thread(
            target=self._heartbeat_loop, daemon=True,
        ).start()

    def send(self, text: str) -> None:
        """Inject text into the running process."""
        logger.info("Injecting: %r", text)
        ghost_status.add_log(
            f"[yellow]>>> {text}[/yellow]"
        )
        if self._pty is not None:
            self._pty.write(text + "\r\n")
        elif (
            self._child
            and self._child.stdin
            and self._child.poll() is None
        ):
            self._child.stdin.write(text + "\n")
            self._child.stdin.flush()

    def kill(self) -> None:
        self._running = False
        try:
            if self._pty is not None:
                self._pty.close(force=True)
            elif self._child:
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
    # Spawn
    # ------------------------------------------------------------------
    def _build_and_spawn(
        self, binary: str, cwd: str,
    ) -> None:
        """Build the command and spawn via winpty or
        subprocess depending on platform."""
        cmd_parts = [binary, "-p", self.task]
        cmd_parts += [
            "--output-format", "stream-json",
            "--verbose",
        ]

        if self._model:
            cmd_parts += ["--model", self._model]

        allowed = _LEVEL_ALLOWED_TOOLS.get(
            self._afk_level, []
        )
        for tool in allowed:
            cmd_parts += ["--allowedTools", tool]

        budget = settings.max_budget_usd
        if budget and 0 < budget < 999:
            cmd_parts += [
                "--max-budget-usd", str(budget),
            ]

        logger.info("Command: %s", cmd_parts)
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

        if _HAS_WINPTY and sys.platform == "win32":
            self._spawn_winpty(cmd_parts, cwd)
        else:
            self._spawn_subprocess(cmd_parts, cwd)

    def _spawn_winpty(
        self, cmd_parts: list[str], cwd: str,
    ) -> None:
        """Spawn via winpty ConPTY (Windows).

        winpty gives us a real TTY so Node.js flushes
        output line-by-line instead of buffering.
        """
        # Resolve the binary to its full path so winpty
        # can find it via cmd.exe
        binary = cmd_parts[0]
        resolved = shutil.which(binary)
        if resolved:
            binary = resolved

        # Build a single command string for cmd.exe.
        # Only quote args that contain spaces/quotes.
        # NOTE: cmd.exe /c has special quoting rules —
        # if the first char after /c is a double-quote,
        # cmd strips the outermost quotes from the
        # entire string, which breaks paths. So we only
        # quote the binary when it actually has spaces.
        def _quote_if_needed(s: str) -> str:
            if " " in s or '"' in s:
                return f'"{s}"'
            return s

        parts = [_quote_if_needed(binary)]
        for arg in cmd_parts[1:]:
            parts.append(_quote_if_needed(arg))
        cmd_str = "cmd.exe /c " + " ".join(parts)

        logger.info("winpty cmd: %s", cmd_str)
        ghost_status.add_log(
            "[dim]Using winpty (ConPTY) for "
            "real-time output[/dim]"
        )

        self._pty = _PtyProcess.spawn(
            cmd_str,
            cwd=cwd if cwd != "." else None,
        )

    def _spawn_subprocess(
        self, cmd_parts: list[str], cwd: str,
    ) -> None:
        """Spawn via subprocess (macOS / Linux)."""
        self._child = subprocess.Popen(
            cmd_parts,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd if cwd != "." else None,
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

            for line in clean.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                se = _parse_stream_event(stripped)
                if se and se.display:
                    ghost_status.add_event(se.display)
                    # Count turns from assistant events
                    if se.tool_name:
                        self._num_turns += 1
                        ghost_status.num_turns = self._num_turns
                    # Or use num_turns from result event
                    if (se.num_turns
                            and se.num_turns > self._num_turns):
                        self._num_turns = se.num_turns
                        ghost_status.num_turns = self._num_turns
                    if self._on_event:
                        self._on_event(se)
                elif not stripped.startswith("{"):
                    ghost_status.add_log(
                        stripped[:120]
                    )

            self._parse_cost(clean)
            self._detect_state()

            if len(self._buffer) > 20_000:
                self._buffer = self._buffer[-10_000:]

    def _read_chunk(self) -> Optional[str]:
        """Read a line of output. None on EOF."""
        # winpty path
        if self._pty is not None:
            try:
                if not self._pty.isalive():
                    return None
                line = self._pty.readline()
                return line if line else ""
            except EOFError:
                return None
            except Exception:
                return None

        # subprocess path
        if (
            self._child is not None
            and self._child.stdout is not None
        ):
            try:
                line = self._child.stdout.readline()
                if (
                    not line
                    and self._child.poll() is not None
                ):
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
