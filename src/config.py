"""Configuration loader — YAML settings + environment variables."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    """Configuration loaded from YAML + environment variables."""

    def __init__(self, config_path: Path | None = None):
        self._data = _load_yaml(config_path or DEFAULT_CONFIG_PATH)

    @property
    def api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def cms_webhook_url(self) -> str:
        return os.getenv("CMS_WEBHOOK_URL", "")

    @property
    def cms_api_key(self) -> str:
        return os.getenv("CMS_API_KEY", "")

    @property
    def output_dir(self) -> Path:
        return Path(os.getenv("OUTPUT_DIR", "./output"))

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def languages(self) -> dict[str, str]:
        return self._data.get("languages", {})

    @property
    def platforms(self) -> dict:
        return self._data.get("platforms", {})

    def agent_config(self, agent_name: str) -> dict:
        defaults = {"model": "claude-sonnet-4-6", "max_tokens": 2000, "temperature": 0.3}
        agent_cfg = self._data.get("agents", {}).get(agent_name, {})
        return {**defaults, **agent_cfg}

    @property
    def retry_config(self) -> dict:
        defaults = {"max_retries": 3, "backoff_factor": 2.0, "initial_delay_seconds": 1.0}
        return {**defaults, **self._data.get("retry", {})}

    @property
    def brand_defaults(self) -> dict:
        return self._data.get("brand_defaults", {})

    def validate(self) -> list[str]:
        """Validate configuration, return list of issues."""
        issues = []
        if not self.api_key:
            issues.append("ANTHROPIC_API_KEY environment variable is not set")
        if not self.languages:
            issues.append("No languages configured in settings.yaml")
        if not self.platforms:
            issues.append("No platforms configured in settings.yaml")
        return issues


# Global singleton
config = Config()
