import asyncio
import logging

import discord
from dateutil import parser as date_parser
from discord.ext import commands

from ..collectors.message_stats import MessageStatisticsCollector
from ..config import Config
from ..formatters.message_stats import MessageStatisticsFormatter

logger = logging.getLogger(__name__)


class StatisticsBot(commands.Bot):
    """Discord bot for fetching and displaying server statistics."""

    def __init__(self, config: Config):
        """
        Initialize the bot with the given configuration.

        Args:
            config: The bot configuration
        """
        intents = discord.Intents.default()
        intents.message_content = True  # For reading message content
        intents.members = True  # For accessing member information

        super().__init__(
            command_prefix=config.bot.command_prefix,
            intents=intents,
            description="Discord Statistics Bot",
        )

        self.config = config
        self._setup_commands()

    async def on_ready(self):
        """Called when the bot is ready and connected."""
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    def _setup_commands(self):
        """Set up the bot commands."""

        @self.command(name="stats")
        async def stats_command(
            ctx, start_date: str | None = None, end_date: str | None = None
        ):
            """
            Fetch and display server statistics.

            Usage:
                !stats - Shows stats for the last 4 weeks
                !stats YYYY-MM-DD - Shows stats from the specified date until now
                !stats YYYY-MM-DD YYYY-MM-DD - Shows stats between the specified dates
            """
            async with ctx.typing():
                try:
                    # Parse the date arguments
                    stats_config = self.config.bot.stats_config

                    if start_date is not None:
                        try:
                            parsed_start_date = date_parser.parse(start_date)
                            stats_config.start_date = parsed_start_date
                        except ValueError:
                            await ctx.send(
                                "Invalid start date format. Please use YYYY-MM-DD."
                            )
                            return

                    if end_date is not None:
                        try:
                            parsed_end_date = date_parser.parse(end_date)
                            stats_config.end_date = parsed_end_date
                        except ValueError:
                            await ctx.send(
                                "Invalid end date format. Please use YYYY-MM-DD."
                            )
                            return

                    # Validate date range
                    if stats_config.end_date < stats_config.start_date:
                        await ctx.send("End date must be after start date.")
                        return

                    # Collect statistics
                    collector = MessageStatisticsCollector()
                    formatter = MessageStatisticsFormatter()

                    data = await collector.collect(
                        ctx.guild, stats_config.start_date, stats_config.end_date
                    )

                    # Format and send statistics
                    embed = formatter.format(data)
                    await ctx.send(embed=embed)

                except Exception as e:
                    logger.exception("Error fetching statistics")
                    await ctx.send(
                        f"An error occurred while fetching statistics: {str(e)}"
                    )

        @self.command(name="help_stats")
        async def help_stats_command(ctx):
            """Show help information for the statistics commands."""
            embed = discord.Embed(
                title="Statistics Bot Help",
                description="Commands for fetching server statistics",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="!stats",
                value=(
                    "Fetch server statistics for a time period.\n\n"
                    "**Usage:**\n"
                    "!stats - Shows stats for the last 4 weeks\n"
                    "!stats YYYY-MM-DD - From specified date until now\n"
                    "!stats YYYY-MM-DD YYYY-MM-DD - Between specified dates"
                ),
                inline=False,
            )

            embed.add_field(
                name="!help_stats", value="Show this help message", inline=False
            )

            await ctx.send(embed=embed)


def create_bot(config: Config) -> StatisticsBot:
    """
    Create a new statistics bot instance.

    Args:
        config: The bot configuration

    Returns:
        A new StatisticsBot instance
    """
    return StatisticsBot(config)


async def run_bot(bot: StatisticsBot):
    """
    Run the bot asynchronously.

    Args:
        bot: The bot instance to run
    """
    async with bot:
        await bot.start(bot.config.bot.token)


def run(config: Config):
    """
    Create and run a bot with the given configuration.

    Args:
        config: The bot configuration
    """
    bot = create_bot(config)
    asyncio.run(run_bot(bot))
