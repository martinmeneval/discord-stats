import json
import os
from pathlib import Path

from .models import Config


def load_config(config_path: str | None = None) -> Config:
    """
    Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file. If None, looks for config.json in the current directory.

    Returns:
        Config object with the loaded configuration.
    """
    if config_path is None:
        config_path = os.environ.get("DISCORD_STATS_CONFIG", "config.json")

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r") as f:
        config_data = json.load(f)

    return Config(**config_data)

