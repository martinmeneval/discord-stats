"""Discord client for fetching statistics."""

import asyncio
import logging
from datetime import datetime

import discord

from .collectors.message_stats import MessageStatisticsCollector


async def fetch_statistics(
    token: str, guild_id: int, start_date: datetime, end_date: datetime
):
    """
    Fetch statistics data from Discord.

    Args:
        token: Discord bot token
        guild_id: ID of the guild to fetch statistics from
        start_date: Start date for statistics collection
        end_date: End date for statistics collection

    Returns:
        Statistics data object or None if an error occurred
    """
    client = StatisticsClient(guild_id, start_date, end_date)
    task = None

    try:
        # Start the client
        task = asyncio.create_task(client.start(token))

        # Wait for the bot to be ready and data to be collected
        await asyncio.wait_for(client.ready.wait(), timeout=60)

        # Return the collected data
        return client.data
    except asyncio.TimeoutError:
        logging.error("Timed out waiting for Discord client to be ready")
        return None
    except Exception as e:
        logging.error(f"Error connecting to Discord: {e}")
        return None
    finally:
        # Ensure the client is properly closed
        if client and client.is_ready():
            await client.close()

        # Cancel any pending tasks
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class StatisticsClient(discord.Client):
    """Discord client for collecting server statistics."""

    def __init__(self, guild_id: int, start_date: datetime, end_date: datetime):
        """
        Initialize the statistics client.

        Args:
            guild_id: ID of the guild to collect statistics from
            start_date: Start date for statistics collection
            end_date: End date for statistics collection
        """
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True  # For reading message content
        intents.members = True  # For accessing member information
        intents.guild_messages = True  # For message history

        super().__init__(intents=intents)

        # Store parameters
        self.target_guild_id = guild_id
        self.start_date = start_date
        self.end_date = end_date

        # Initialize state
        self.guild = None
        self.data = None
        self.ready = asyncio.Event()

    async def on_ready(self):
        """Called when the bot is ready and connected."""
        try:
            # Get the target guild
            self.guild = self.get_guild(self.target_guild_id)
            if not self.guild:
                logging.error(f"Guild with ID {self.target_guild_id} not found")
                self.ready.set()
                return

            # Collect statistics
            collector = MessageStatisticsCollector()
            self.data = await collector.collect(
                self.guild, self.start_date, self.end_date
            )

        except Exception as e:
            logging.error(f"Error collecting statistics: {e}")

        finally:
            # Signal that we're done
            self.ready.set()
