"""ClaudeGhost configuration module."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

BUDGET_PRESETS: dict[str, float] = {
    "micro": 0.50,
    "small": 2.00,
    "medium": 5.00,
    "large": 10.00,
    "xlarge": 25.00,
    "unlimited": 999.99,
}

LEVEL_NAMES: dict[int, str] = {
    1: "Paranoid",
    2: "Auditor",
    3: "Manager",
    4: "Director",
    5: "God Mode",
}

LEVEL_DESCRIPTIONS: dict[int, str] = {
    1: "Ask user for EVERY action before proceeding",
    2: "Auto: read — Ask user: write, execute, high-risk",
    3: "Auto: read, write — Ask user: execute, high-risk",
    4: "Auto: read, write, execute — Ask user: high-risk",
    5: "Fully autonomous — notify on critical errors only",
}

MODEL_OPTIONS: dict[str, str] = {
    "sonnet": "Claude Sonnet (fast, balanced)",
    "opus": "Claude Opus (smartest, slower)",
    "haiku": "Claude Haiku (fastest, cheapest)",
}


class Settings(BaseSettings):
    """Global application settings loaded from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram Bot API
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    telegram_enabled: bool = Field(default=True)

    # Autonomy
    default_afk_level: int = Field(default=3, ge=1, le=5)

    # Budget
    max_budget_usd: float = Field(default=5.00, ge=0)
    budget_preset: str = Field(default="medium")

    # Claude
    claude_binary: str = Field(default="claude")
    claude_model: str = Field(default="sonnet")
    working_directory: str = Field(default=".")

    # Timing
    poll_interval_seconds: float = Field(default=3.0)
    heartbeat_timeout_seconds: float = Field(default=60.0)


settings = Settings()


class SessionConfig:
    """Runtime configuration for a single ClaudeGhost session."""

    def __init__(
        self,
        task: str,
        afk_level: int = 3,
        budget_usd: float = 5.0,
        telegram_enabled: bool = True,
        working_directory: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.task = task
        self.afk_level = max(1, min(5, afk_level))
        self.budget_usd = budget_usd
        self.telegram_enabled = telegram_enabled
        self.working_directory = (
            working_directory or settings.working_directory
        )
        self.model = model or settings.claude_model

    @property
    def level_name(self) -> str:
        return LEVEL_NAMES.get(self.afk_level, "Unknown")

    @property
    def level_description(self) -> str:
        return LEVEL_DESCRIPTIONS.get(self.afk_level, "")
