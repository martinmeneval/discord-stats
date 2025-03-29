# Discord Stats CLI

A vibe-coded Python-based CLI tool that collects and outputs statistics from Discord
servers.

## Features

- Fetch message statistics between specified dates (default: past 4 weeks)
- Output statistics as formatted text that can be copied and pasted into Discord
- Show:
  - Total messages in the server
  - Average messages per day
  - Top members by message count
  - Most active channels and threads
  - Picture posting statistics
- Modular architecture for easy extension with new statistics types

## Requirements

- Python 3.12 or higher
- Poetry for dependency management

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/yourusername/discord-stats.git
   cd discord-stats
   ```

2. Install dependencies with Poetry:

   ```bash
   poetry install
   ```

3. Create a configuration file:

   ```bash
   poetry run discord-stats create-config
   ```

4. Edit the created `config.json` file and add your Discord bot token and guild ID:

   ```json
   {
     "bot": {
       "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
       "guild_id": 123456789012345678,
       "stats_config": {}
     }
   }
   ```

## Usage

### Getting Statistics

To fetch statistics for the default period (last 4 weeks) and output them to the
console:

```bash
poetry run discord-stats stats --config config.json
```

To specify a date range:

```bash
poetry run discord-stats stats --config config.json --start-date 2025-02-01 --end-date 2025-03-01
```

To save the output to a file:

```bash
poetry run discord-stats stats --config config.json --output stats.txt
```

### Command Line Options

```bash
Usage: discord-stats stats [OPTIONS]

  Fetch statistics from a Discord server and output them as plain text.

Options:
  --config PATH                  Path to the configuration file
  --token TEXT                   Discord bot token
  --guild-id INTEGER             Discord guild/server ID
  --start-date TEXT              Start date (YYYY-MM-DD)
  --end-date TEXT                End date (YYYY-MM-DD)
  --output PATH                  Output file path (optional)
  --debug / --no-debug           Enable debug logging
  --help                         Show this message and exit
```

## Running as a Discord Bot

This tool can also be used as an interactive Discord bot. You can run it as a bot from
Python code like this:

```python
from discord_stats.config import load_config
from discord_stats.bot import run

# Load configuration
config = load_config("config.json")

# Run the bot
run(config)
```

When running as a bot, use the `!stats` command in your Discord server to fetch
statistics.

## Project Structure

- `discord_stats/` - Main package
  - `collectors/` - Statistics collection modules
  - `formatters/` - Statistics formatting modules
  - `config/` - Configuration handling
  - `bot/` - Discord bot functionality

## Adding New Statistics

The tool is designed to be modular, making it easy to add new types of statistics:

1. Create a new collector in the `collectors/` directory
2. Create a corresponding formatter in the `formatters/` directory
3. Update the CLI and bot commands to support your new statistics

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
