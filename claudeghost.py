#!/usr/bin/env python3
"""
ClaudeGhost - Headless Supervisor for Claude Code CLI

Main entry point for running ClaudeGhost from the command line.

Usage:
    python claudeghost.py                           # Interactive mode
    python claudeghost.py "task" --level 3          # Quick mode
    python claudeghost.py "task" --level 3 --budget 10.00
    python claudeghost.py "task" --no-telegram      # Screen-only mode

Examples:
    python claudeghost.py "Add user authentication to the app" --level 3
    python claudeghost.py "Fix the bug in payment processing" --level 4 --budget 5.00
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.launcher import run_interactive_launcher, run_quick_launcher
from src.main import ClaudeGhost
from src.updater import auto_update
from src.utils import logger


def main():
    """Main entry point for ClaudeGhost."""
    # Auto-update before anything else
    auto_update()

    parser = argparse.ArgumentParser(
        description="ClaudeGhost - Headless Supervisor for Claude Code CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python claudeghost.py                                    # Interactive mode
  python claudeghost.py "Add authentication" --level 3     # Quick mode
  python claudeghost.py "Fix bug" --level 4 --budget 5.00  # With budget
  python claudeghost.py "Analyze code" --no-telegram       # Screen-only

AFK Levels:
  1 = Paranoid   (ask everything)
  2 = Auditor    (auto: read)
  3 = Manager    (auto: read, write) [recommended]
  4 = Director   (auto: read, write, execute)
  5 = God Mode   (auto: everything)
        """
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="Task description for Claude (if omitted, runs interactive mode)"
    )
    parser.add_argument(
        "--level",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=3,
        help="AFK autonomy level (1-5, default: 3)"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=10.0,
        help="Budget limit in USD (default: 10.00)"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disable Telegram notifications (screen-only mode)"
    )
    
    args = parser.parse_args()
    
    try:
        # Interactive mode if no task provided
        if not args.task:
            config = run_interactive_launcher()
            if not config:
                return 0
        else:
            # Quick mode with task provided
            config = run_quick_launcher(
                task=args.task,
                level=args.level,
                budget=args.budget,
                telegram=not args.no_telegram
            )
        
        # Run ClaudeGhost
        ghost = ClaudeGhost(config)
        ghost.run()
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
