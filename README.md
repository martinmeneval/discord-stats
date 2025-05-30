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
  - Visual graphs of activity over time
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

To generate graphs of server activity:

```bash
poetry run discord-stats graphs --config config.json --output-dir ./graphs
```

To generate graphs with smoothing disabled:

```bash
poetry run discord-stats graphs --config config.json --output-dir ./graphs --no-smooth
```

To generate both text stats and graphs:

```bash
poetry run discord-stats stats --config config.json --generate-graphs --graphs-dir ./graphs
```

### Command Line Options

#### Stats Command

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
  --generate-graphs              Generate graphs alongside text output
  --graphs-dir PATH              Directory for graph output (default: same as text output)
  --smooth / --no-smooth         Apply smoothing to line graphs when generating graphs (default: on)
  --debug / --no-debug           Enable debug logging
  --help                         Show this message and exit
```

#### Graphs Command

```bash
Usage: discord-stats graphs [OPTIONS]

  Generate graphs from Discord server statistics.

Options:
  --config PATH                  Path to the configuration file
  --token TEXT                   Discord bot token
  --guild-id INTEGER             Discord guild/server ID
  --start-date TEXT              Start date (YYYY-MM-DD)
  --end-date TEXT                End date (YYYY-MM-DD)
  --output-dir PATH              Output directory for graphs (default: '.')
  --prefix TEXT                  Prefix for graph filenames (default: 'discord_stats')
  --smooth / --no-smooth         Apply smoothing to line graphs (default: on)
  --debug / --no-debug           Enable debug logging
  --help                         Show this message and exit
```

## Graph Types

The tool generates several types of graphs to visualize Discord server activity:

1. **Messages Per Day**: Line graph showing daily message activity with optional smoothing
2. **Top Channels Over Time**: Multi-line graph showing cumulative message activity for the most active channels
3. **Top Reactions Over Time**: Multi-line graph showing cumulative usage for the most popular reaction emojis
4. **Daily Activity Heatmap**: Heatmap showing which days of the week are most active

The top channels and reactions graphs show cumulative data (running totals) rather than daily counts, making growth trends much clearer and easier to interpret. All line graphs support smoothing to make trends easier to read. Smoothing can be disabled with the `--no-smooth` option.

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

When running as a bot, use the following commands in your Discord server:

- `!stats` - Fetch and display server statistics
- `!graphs` - Generate and upload visual graphs of server activity
- `!graphs smooth=off` - Generate graphs with smoothing disabled
- `!help_stats` - Show help information for available commands

Bot commands support date ranges and smoothing options:

- `!graphs 2025-01-01 2025-01-31` - Generate graphs for January 2025
- `!graphs 2025-01-01 2025-01-31 smooth=off` - Generate non-smoothed graphs for January 2025

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
