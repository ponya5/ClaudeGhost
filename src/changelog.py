"""Changelog tracking for ClaudeGhost sessions."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from src.utils import logger


class ChangeLog:
    """Track and save changes made during a ClaudeGhost session."""

    def __init__(self, task: str, session_id: str):
        self.task = task
        self.session_id = session_id
        self.changes: List[str] = []
        self.commands_executed: List[str] = []
        self.files_modified: List[str] = []
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        # Session data populated before save
        self.activity_log: List[str] = []
        self.event_log: List[str] = []
        self.stats_data: Optional[dict] = None
        self.session_outcome: str = ""
        self.session_error: str = ""

    def add_command(self, command: str) -> None:
        """Record a command that was executed."""
        self.commands_executed.append(command)

    def add_file_change(self, filepath: str) -> None:
        """Record a file that was modified."""
        if filepath not in self.files_modified:
            self.files_modified.append(filepath)

    def add_change(self, description: str) -> None:
        """Add a general change description."""
        self.changes.append(description)

    def finalize(self) -> None:
        """Mark the session as complete."""
        self.end_time = datetime.now()

    def save(self, output_dir: str = "session_logs") -> str:
        """Save changelog to a file and return the filepath."""
        # Create output directory
        log_dir = Path(output_dir)
        log_dir.mkdir(exist_ok=True)

        # Generate filename
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}_{self.session_id[:8]}.txt"
        filepath = log_dir / filename

        # Build changelog content
        duration = "Unknown"
        if self.end_time:
            delta = self.end_time - self.start_time
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            duration = f"{minutes}m {seconds}s"

        content = self._build_changelog_content(duration)

        # Write to file
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Changelog saved to %s", filepath)
            return str(filepath.absolute())
        except Exception as e:
            logger.error("Failed to save changelog: %s", e)
            return ""

    def _build_changelog_content(self, duration: str) -> str:
        """Build the formatted changelog content with full session data."""
        lines = []
        lines.append("=" * 70)
        lines.append("ClaudeGhost Session Changelog")
        lines.append("=" * 70)
        lines.append("")

        # Session outcome (matches Telegram summary)
        if self.session_outcome:
            lines.append(f"Outcome: {self.session_outcome}")
        if self.session_error:
            lines.append(f"Error:   {self.session_error}")
        lines.append("")

        lines.append(f"Session ID: {self.session_id}")
        lines.append(f"Task: {self.task}")
        started = self.start_time.strftime(
            '%Y-%m-%d %H:%M:%S'
        )
        lines.append(f"Started: {started}")
        if self.end_time:
            ended = self.end_time.strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            lines.append(f"Ended: {ended}")
        lines.append(f"Duration: {duration}")
        lines.append("")

        # Session Statistics (matches terminal "Statistics" panel)
        if self.stats_data:
            sd = self.stats_data
            lines.append("-" * 70)
            lines.append("Session Status")
            lines.append("-" * 70)
            model = sd.get('model', 'N/A')
            lines.append(f"  Model:          {model}")
            afk = sd.get('afk_level', 'N/A')
            lvl = sd.get('level_name', '')
            lines.append(
                f"  AFK Level:      {afk} ({lvl})"
            )
            used = sd.get('budget_used', 0)
            bmax = sd.get('budget_max', 0)
            lines.append(
                f"  Budget:         "
                f"${used:.4f} / ${bmax:.2f}"
            )
            lines.append("")
            lines.append("-" * 70)
            lines.append("Statistics")
            lines.append("-" * 70)
            elapsed = sd.get('elapsed', duration)
            lines.append(f"  Elapsed:        {elapsed}")
            turns = sd.get('turns', 0)
            lines.append(f"  Turns:          {turns}")
            qt = sd.get('queries_total', 0)
            lines.append(f"  Queries Total:  {qt}")
            qa = sd.get('queries_auto', 0)
            lines.append(f"    Auto-approved:  {qa}")
            qu = sd.get('queries_user', 0)
            lines.append(f"    User-approved:  {qu}")
            qb = sd.get('queries_blocked', 0)
            lines.append(f"    Blocked:        {qb}")
            cmds = sd.get('commands', 0)
            lines.append(f"  Commands:       {cmds}")
            if sd.get('telegram_enabled'):
                ts = sd.get('telegram_sent', 0)
                tr = sd.get('telegram_received', 0)
                lines.append(
                    f"  Telegram I/O:   {ts} / {tr}"
                )
            lines.append("")

        # Activity Log
        if self.activity_log:
            lines.append("-" * 70)
            lines.append(f"Activity Log ({len(self.activity_log)} entries)")
            lines.append("-" * 70)
            for entry in self.activity_log:
                lines.append(f"  {entry}")
            lines.append("")

        # Claude Code Events
        if self.event_log:
            lines.append("-" * 70)
            lines.append(f"Claude Code Events ({len(self.event_log)} entries)")
            lines.append("-" * 70)
            for entry in self.event_log:
                lines.append(f"  {entry}")
            lines.append("")

        # Files Modified
        lines.append("-" * 70)
        lines.append(f"Files Modified ({len(self.files_modified)})")
        lines.append("-" * 70)
        if self.files_modified:
            for filepath in self.files_modified:
                lines.append(f"  * {filepath}")
        else:
            lines.append("  (No files modified)")
        lines.append("")

        # Commands Executed
        lines.append("-" * 70)
        lines.append(f"Commands Executed ({len(self.commands_executed)})")
        lines.append("-" * 70)
        if self.commands_executed:
            for i, cmd in enumerate(self.commands_executed, 1):
                lines.append(f"  {i}. {cmd}")
        else:
            lines.append("  (No commands executed)")
        lines.append("")

        # General Changes
        if self.changes:
            lines.append("-" * 70)
            lines.append("Changes Summary")
            lines.append("-" * 70)
            for change in self.changes:
                lines.append(f"  * {change}")
            lines.append("")

        lines.append("=" * 70)
        lines.append("End of Changelog")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_summary(self) -> str:
        """Get a brief summary for Telegram notification."""
        parts = []
        if self.files_modified:
            parts.append(
                f"📂 Files modified: "
                f"{len(self.files_modified)}"
            )
            for f in self.files_modified[-5:]:
                parts.append(f"  • {f}")
        else:
            parts.append("📂 Files modified: 0")
        parts.append(
            f"⚡ Commands executed: "
            f"{len(self.commands_executed)}"
        )
        return "\n".join(parts)
