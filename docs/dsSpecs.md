# Product Requirements Document: ClaudeGhost

**Version:** 2.0
**Target System:** Python 3.10+
**Integration Target:** Anthropic Claude CLI + Telegram Bot API

## 1. Executive Summary

ClaudeGhost is a headless supervisor wrapper for the Anthropic Claude CLI. It allows developers to execute autonomous coding tasks while AFK by bridging the CLI's decision requests to a Telegram Bot interface.

CG wraps the claude process in a pseudo-terminal (PTY), interprets its TUI state in real-time, and governs execution based on a user-defined Autonomy Matrix.

## 2. Core User Flow

1. User runs: `python -m src.launcher "Refactor auth_service.py" --level 3`
2. ClaudeGhost spawns claude CLI with the task
3. Safe operations auto-approve based on AFK level
4. Risky operations -> Telegram notification to user
5. User replies A/B/C/D on Telegram
6. Session ends with summary

## 3. Key Components

- **Bridge** (`bridge.py`): PTY/subprocess wrapper for claude CLI
- **Guardian** (`guardian.py`): Risk classification engine (5 levels)
- **TelegramBot** (`telegram_bot.py`): Official Telegram Bot API client
- **ScreenNotifier** (`screen_notifier.py`): Terminal-only fallback
- **Config** (`config.py`): Pydantic-based settings from .env
- **Launcher** (`launcher.py`): Interactive session setup
- **Utils** (`utils.py`): Rich TUI dashboard, logging, stats

## 4. Autonomy Matrix

| Level | Name | Read | Write | Execute | Critical |
|-------|------|------|-------|---------|----------|
| 1 | Paranoid | Ask | Ask | Ask | Ask |
| 2 | Auditor | Auto | Ask | Ask | Ask |
| 3 | Manager | Auto | Auto | Ask | Ask |
| 4 | Director | Auto | Auto | Auto | Ask |
| 5 | God Mode | Auto | Auto | Auto | Auto |

## 5. Notification Flow

- Telegram Bot API (official, free, unlimited)
- Long-polling for incoming replies
- Fallback: terminal-only mode when Telegram disabled
- Reply format: A=approve, B=block, C=context, D=kill

## 6. Budget Control

- Per-session spending limit in USD
- Automatic pause when exceeded
- User can approve continuation or kill
