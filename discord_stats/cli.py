"""CLI functionality for Discord statistics tool."""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from dateutil import parser as date_parser

from .config import load_config
from .discord_client import fetch_statistics
from .formatters.message_stats import format_statistics_text
from .graphs.message_graphs import MessageGraphGenerator


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def parse_date(date_str, default_date, config_date=None, date_name="date"):
    """Parse a date string with robust error handling and fallbacks."""
    if date_str:
        try:
            return date_parser.parse(date_str)
        except ValueError:
            logging.error(f"Invalid {date_name} format. Please use YYYY-MM-DD.")
            sys.exit(1)
    elif config_date is not None:
        logging.info(f"Using {date_name} from config: {config_date}")
        return config_date

    return default_date


def _resolve_credentials(config_data, token, guild_id):
    """Merge CLI flags with config file values, preferring explicit flags."""
    if config_data:
        token = token or config_data.bot.token
        guild_id = guild_id or config_data.bot.guild_id
    if not token:
        logging.error("Discord bot token is required (--token or config file)")
        sys.exit(1)
    if not guild_id:
        logging.error("Discord guild ID is required (--guild-id or config file)")
        sys.exit(1)
    return token, guild_id


def _resolve_dates(start_date_str, end_date_str, config_data):
    """Resolve start/end dates from CLI flags, config, or sensible defaults."""
    now = datetime.now()
    default_start = now - timedelta(weeks=4)

    config_start = None
    config_end = None
    if config_data:
        stats_cfg = config_data.bot.stats_config
        config_start = stats_cfg.start_date
        config_end = stats_cfg.end_date

    start = parse_date(start_date_str, default_start, config_start, "start date")
    end = parse_date(end_date_str, now, config_end, "end date")

    if end < start:
        logging.error("End date must be after start date.")
        sys.exit(1)

    return start, end


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Discord Statistics CLI Tool."""
    pass


@cli.command()
@click.option(
    "--config", type=click.Path(exists=True), help="Path to the configuration file"
)
@click.option("--token", help="Discord bot token")
@click.option("--guild-id", type=int, help="Discord guild/server ID")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--output", type=click.Path(), help="Output file path (optional)")
@click.option(
    "--generate-graphs", is_flag=True, help="Generate graphs alongside text output"
)
@click.option(
    "--graphs-dir",
    type=click.Path(),
    help="Directory for graph output (default: same as text output)",
)
@click.option(
    "--smooth/--no-smooth",
    default=True,
    help="Apply smoothing to line graphs when generating graphs (default: on)",
)
@click.option(
    "--history-offset/--no-history-offset",
    default=False,
    help="Generate cumulative graphs seeded from pre-period message counts (adds an extra fetch pass)",
)
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def stats(
    config,
    token,
    guild_id,
    start_date,
    end_date,
    output,
    generate_graphs,
    graphs_dir,
    smooth,
    history_offset,
    debug,
):
    """Fetch statistics from a Discord server and output them as plain text."""
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level)

    config_data = None
    if config:
        try:
            config_data = load_config(config)
        except FileNotFoundError as e:
            logging.error(f"Error: {e}")
            sys.exit(1)

    token, guild_id = _resolve_credentials(config_data, token, guild_id)
    start, end = _resolve_dates(start_date, end_date, config_data)

    logging.info(
        f"Fetching statistics for guild {guild_id} from {start.date()} to {end.date()}"
    )

    try:
        stats_data = asyncio.run(fetch_statistics(token, guild_id, start, end, history_offset=history_offset))

        if not stats_data:
            logging.error("Failed to fetch statistics data")
            sys.exit(1)

        # Format and output the statistics
        formatted_stats = format_statistics_text(stats_data, start, end)

        if output:
            with open(output, "w") as f:
                f.write(formatted_stats)
            logging.info(f"Statistics saved to {output}")
        else:
            click.echo(formatted_stats)

        # Generate graphs if requested
        if generate_graphs:
            # Determine output directory for graphs
            if graphs_dir:
                graph_output_dir = graphs_dir
            elif output:
                # Use same directory as text output
                graph_output_dir = str(Path(output).parent)
            else:
                graph_output_dir = "."

            # Generate graphs
            graph_generator = MessageGraphGenerator()
            generated_files = graph_generator.generate_all_graphs(
                stats_data, graph_output_dir, "discord_stats", smooth=smooth, history_offset=history_offset
            )

            if generated_files:
                click.echo(f"\nGenerated {len(generated_files)} graphs:")
                for file_path in generated_files:
                    click.echo(f"  - {file_path}")
            else:
                click.echo("\nNo graphs were generated. Check the logs for errors.")

    except Exception:
        logging.exception("Error fetching statistics")
        sys.exit(1)


@cli.command()
@click.option(
    "--config", type=click.Path(exists=True), help="Path to the configuration file"
)
@click.option("--token", help="Discord bot token")
@click.option("--guild-id", type=int, help="Discord guild/server ID")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option(
    "--output-dir", type=click.Path(), default=".", help="Output directory for graphs"
)
@click.option("--prefix", default="discord_stats", help="Prefix for graph filenames")
@click.option(
    "--smooth/--no-smooth",
    default=True,
    help="Apply smoothing to line graphs (default: on)",
)
@click.option("--debug/--no-debug", default=False, help="Enable debug logging")
def graphs(
    config, token, guild_id, start_date, end_date, output_dir, prefix, smooth, debug
):
    """Generate graphs from Discord server statistics."""
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level)

    config_data = None
    if config:
        try:
            config_data = load_config(config)
        except FileNotFoundError as e:
            logging.error(f"Error: {e}")
            sys.exit(1)

    token, guild_id = _resolve_credentials(config_data, token, guild_id)
    start, end = _resolve_dates(start_date, end_date, config_data)

    logging.info(
        f"Fetching statistics for guild {guild_id} from {start.date()} to {end.date()}"
    )

    try:
        stats_data = asyncio.run(fetch_statistics(token, guild_id, start, end))

        if not stats_data:
            logging.error("Failed to fetch statistics data")
            sys.exit(1)

        # Generate graphs
        graph_generator = MessageGraphGenerator()
        generated_files = graph_generator.generate_all_graphs(
            stats_data, output_dir, prefix, smooth=smooth
        )

        if generated_files:
            click.echo(f"Generated {len(generated_files)} graphs:")
            for file_path in generated_files:
                click.echo(f"  - {file_path}")
        else:
            click.echo("No graphs were generated. Check the logs for errors.")

    except Exception:
        logging.exception("Error generating graphs")
        sys.exit(1)


@cli.command()
@click.argument("output", type=click.Path(), default="config.json")
def create_config(output):
    """Create a default configuration file."""
    config_data = {
        "bot": {
            "token": "YOUR_DISCORD_BOT_TOKEN_HERE",
            "guild_id": 123456789012345678,  # Replace with your server ID
            "stats_config": {
                "start_date": (datetime.now() - timedelta(weeks=4)).isoformat(),
                "end_date": datetime.now().isoformat(),
            },
        }
    }

    with open(output, "w") as f:
        json.dump(config_data, f, indent=4)

    click.echo(f"Default configuration file created at: {output}")
    click.echo(
        "Please edit the file and add your Discord bot token before running the tool."
    )


def main():
    """Entry point for the CLI tool."""
    try:
        cli()
    except Exception:
        logging.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
