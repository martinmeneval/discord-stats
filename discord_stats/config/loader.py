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

    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        config_data = json.load(f)

    return Config(**config_data)


def create_default_config(config_path: str = "config.json") -> None:
    """
    Create a default configuration file.

    Args:
        config_path: Path where the configuration file will be created.
    """
    # Create a bare minimum configuration file template
    config_data = {
        "bot": {
            "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
            "command_prefix": "!",
            "stats_config": {
                # Default statistics config will use the defaults from the model
            },
        }
    }

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=4)

    print(f"Default configuration file created at: {config_path}")
    print("Please edit the file and add your Discord bot token before running the bot.")
