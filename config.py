import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "mdm" / "config.json"

DEFAULT_CONFIG: dict = {
    "download_dir": str(Path("~/Music/Songs-Downloaded").expanduser()),
    "default_quality": "320",
    "browser_cookies": "none",
}


def load_config() -> dict:
    """Load config from disk, returning defaults merged with stored values."""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        stored = json.loads(CONFIG_PATH.read_text())
        if not isinstance(stored, dict):
            return DEFAULT_CONFIG.copy()
        return {**DEFAULT_CONFIG, **stored}
    except (json.JSONDecodeError, OSError, TypeError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Write config dict to disk as JSON, creating parent dirs if needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
