from __future__ import annotations

import re
from enum import IntEnum
from typing import Optional

from src.utils import logger, ghost_status


class RiskCategory(IntEnum):
    READ_ONLY = 1
    WRITE = 2
    EXECUTE = 3
    HIGH_RISK = 4


class Decision(IntEnum):
    AUTO_APPROVE = 1
    ASK_USER = 2


# ---------------------------------------------------------------------------
# Command classification patterns
# ---------------------------------------------------------------------------
_READ_PATTERNS = re.compile(
    r"^(ls|cat|head|tail|less|more|find|grep|rg|wc|du|df|pwd|echo|tree|"
    r"file|stat|which|type|env|printenv|hostname|whoami|id|uname|date|"
    r"git\s+(status|log|diff|show|branch|remote\b(?!\s+add)))\b",
    re.IGNORECASE,
)
_WRITE_PATTERNS = re.compile(
    r"^(edit|mv|cp|mkdir|touch|sed|awk|chmod|chown|tee|truncate|"
    r"git\s+(add|commit|stash|checkout|switch|merge|rebase|tag|reset\b(?!\s+--hard)))\b"
    r"|(>\s|>>)",
    re.IGNORECASE,
)
_HIGH_RISK_PATTERNS = re.compile(
    r"^(rm\b|rmdir|git\s+push|git\s+reset\s+--hard|git\s+clean|"
    r"docker\s+(rm|rmi|system\s+prune)|"
    r"drop\s+(table|database)|truncate\s+table|"
    r"sudo|shutdown|reboot|kill|pkill|killall|"
    r"format|fdisk|mkfs|dd\b|"
    r":(){ :|:& };:)",  # fork bomb
    re.IGNORECASE,
)
_EXECUTE_PATTERNS = re.compile(
    r"^(npm|npx|node|python|python3|pip|pip3|yarn|pnpm|bun|deno|"
    r"cargo|go\s+run|go\s+build|make|cmake|gcc|g\+\+|clang|"
    r"javac|java|mvn|gradle|"
    r"bash|sh|zsh|powershell|pwsh|"
    r"curl|wget|"
    r"docker\s+(run|build|compose|exec)|"
    r"kubectl|terraform|ansible|"
    r"pytest|jest|vitest|mocha)\b",
    re.IGNORECASE,
)

# Level -> {category: decision}
_AUTONOMY_MATRIX: dict[int, dict[RiskCategory, Decision]] = {
    1: {
        RiskCategory.READ_ONLY: Decision.ASK_USER,
        RiskCategory.WRITE: Decision.ASK_USER,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    2: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.ASK_USER,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    3: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.ASK_USER,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    4: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.AUTO_APPROVE,
        RiskCategory.HIGH_RISK: Decision.ASK_USER,
    },
    5: {
        RiskCategory.READ_ONLY: Decision.AUTO_APPROVE,
        RiskCategory.WRITE: Decision.AUTO_APPROVE,
        RiskCategory.EXECUTE: Decision.AUTO_APPROVE,
        RiskCategory.HIGH_RISK: Decision.AUTO_APPROVE,
    },
}

_RISK_LABELS: dict[RiskCategory, tuple[str, str]] = {
    RiskCategory.READ_ONLY: ("Read-Only", "🟢"),
    RiskCategory.WRITE: ("Write", "🟡"),
    RiskCategory.EXECUTE: ("Execute", "🟠"),
    RiskCategory.HIGH_RISK: ("Critical", "🔴"),
}

_LEVEL_NAMES: dict[int, str] = {
    1: "Paranoid",
    2: "Auditor",
    3: "Manager",
    4: "Director",
    5: "God Mode",
}


def classify_command(command: str) -> RiskCategory:
    cmd = command.strip()
    if not cmd:
        return RiskCategory.EXECUTE
    
    # Check if this is a Claude Code tool (format: "ToolName: args")
    tool_match = re.match(r"^(\w+):\s*", cmd)
    if tool_match:
        tool_name = tool_match.group(1).lower()
        # Classify Claude Code tools
        if tool_name in ("read", "readfile", "list", "listfiles"):
            return RiskCategory.READ_ONLY
        elif tool_name in ("write", "writefile", "edit", "editfile", "create", "createfile"):
            return RiskCategory.WRITE
        elif tool_name in ("bash", "execute", "shell", "run"):
            return RiskCategory.EXECUTE
        elif tool_name in ("websearch", "search", "fetch", "http", "api"):
            return RiskCategory.EXECUTE  # Web operations are execute-level
        else:
            # Unknown tool, treat as execute
            return RiskCategory.EXECUTE
    
    # Regular bash command classification
    if _HIGH_RISK_PATTERNS.search(cmd):
        return RiskCategory.HIGH_RISK
    if _EXECUTE_PATTERNS.search(cmd):
        return RiskCategory.EXECUTE
    if _WRITE_PATTERNS.search(cmd):
        return RiskCategory.WRITE
    if _READ_PATTERNS.search(cmd):
        return RiskCategory.READ_ONLY
    return RiskCategory.EXECUTE


def evaluate(command: str, afk_level: int) -> tuple[Decision, RiskCategory]:
    category = classify_command(command)
    level = max(1, min(5, afk_level))
    decision = _AUTONOMY_MATRIX[level][category]
    label, icon = _RISK_LABELS[category]
    logger.info(
        "Guardian: cmd=%r  risk=%s %s  level=%d (%s)  -> %s",
        command[:60], icon, label, level, _LEVEL_NAMES[level], decision.name,
    )
    ghost_status.add_log(
        f"[bold]Guardian:[/bold] {icon} {label} -> {decision.name}"
    )
    return decision, category


def extract_command_from_query(query_text: str) -> Optional[str]:
    """Extract the actual command from claude's TUI query output.

    Claude Code typically shows something like:
        Do you want to run this command?
          rm -rf ./db
    or:
        Claude wants to run: bash("rm -rf ./db")
    or:
        Command: rm -rf ./db
    or:
        Do you want to run this tool?
          WebSearch: {'query': 'weather forecast'}
    """
    # Pattern for Claude Code tools (WebSearch, Read, Write, etc.)
    m = re.search(
        r"(?:tool|use)\s*\?\s*\n\s*(\w+):\s*(.+)",
        query_text, re.IGNORECASE | re.DOTALL
    )
    if m:
        tool_name = m.group(1).strip()
        tool_args = m.group(2).strip()[:200]  # Limit length
        return f"{tool_name}: {tool_args}"
    
    # Pattern 1: "Do you want to run this command?\n  <cmd>"
    m = re.search(
        r"(?:do you want to|wants to)\s+(?:run|execute|use).*?\n\s*(.+)",
        query_text, re.IGNORECASE,
    )
    if m:
        return _clean_extracted(m.group(1))

    # Pattern 2: bash("cmd") or Bash("cmd")
    m = re.search(r'(?:bash|shell|exec)\s*\(\s*["\'](.+?)["\']\s*\)', query_text, re.IGNORECASE)
    if m:
        return _clean_extracted(m.group(1))

    # Pattern 3: "Command: <cmd>"
    m = re.search(r"command:\s*(.+)", query_text, re.IGNORECASE)
    if m:
        return _clean_extracted(m.group(1))

    # Pattern 4: Indented line after a question
    m = re.search(r"\?\s*\n\s{2,}(.+)", query_text)
    if m:
        return _clean_extracted(m.group(1))

    # Fallback: last non-empty line that looks like a command
    lines = [ln.strip() for ln in query_text.strip().splitlines() if ln.strip()]
    for line in reversed(lines):
        if re.match(r"^[a-zA-Z./~$]", line) and not re.match(
            r"^(Do |Would |Should |Reply|Yes|No|\(|Allow|Deny)", line, re.I
        ):
            return _clean_extracted(line)
    return None


def _clean_extracted(cmd: str) -> str:
    """Remove surrounding quotes and whitespace from extracted command."""
    cmd = cmd.strip().strip("'\"").strip()
    cmd = re.sub(r"\s*\(y/n\)\s*$", "", cmd, flags=re.IGNORECASE)
    return cmd


def format_approval_message(command: str, category: RiskCategory) -> str:
    label, icon = _RISK_LABELS[category]
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ⚠️  ACTION DETECTED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"🔧 Tool: {command}\n"
        f"🎯 Risk: {icon} {label}\n"
        f"\n"
        f"Reply:\n"
        f"  A - ✅ Approve\n"
        f"  B - 🚫 Block & Redo\n"
        f"  C - 💬 Add Context\n"
        f"  D - 💀 Detonate (kill)"
    )
