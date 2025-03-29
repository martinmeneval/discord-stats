import logging
from datetime import datetime
from typing import Counter

import discord
from discord.channel import TextChannel, Thread
from discord.guild import Guild

from . import BaseCollector


class MessageStatisticsData:
    """Container for message statistics data."""

    def __init__(self):
        self.total_messages = 0
        self.messages_per_author: Counter[str] = Counter()
        self.messages_per_author_id: dict[str, str] = {}  # Map author name to ID
        self.messages_per_channel: Counter[str] = Counter()
        self.messages_per_channel_id: dict[str, int] = {}  # Map channel name to ID
        self.messages_per_thread: Counter[str] = Counter()  # Track messages per thread
        self.messages_per_thread_id: dict[str, int] = {}  # Map thread name to ID
        self.total_thread_messages = 0  # Track total messages in all threads
        self.pictures_per_author: Counter[str] = Counter()
        self.total_pictures = 0
        self.days_in_period = 0
        self.bot_id = None  # Store the bot's user ID

    @property
    def avg_messages_per_day(self) -> float:
        """Calculate average messages per day."""
        if self.days_in_period > 0:
            return self.total_messages / self.days_in_period
        return 0.0

    def get_top_posters(self, limit: int = 3) -> list[tuple[str, int, float]]:
        """
        Get the top message posters.

        Returns a list of tuples containing (author_name, message_count, percentage)
        """
        if not self.total_messages:
            return []

        return [
            (author, count, (count / self.total_messages) * 100)
            for author, count in self.messages_per_author.most_common(limit)
        ]

    def get_top_channels(self, limit: int = 3) -> list[tuple[str, int, float]]:
        """
        Get the top active channels.

        Returns a list of tuples containing (channel_name, message_count, percentage)
        """
        if not self.total_messages:
            return []

        return [
            (channel, count, (count / self.total_messages) * 100)
            for channel, count in self.messages_per_channel.most_common(limit)
        ]

    def get_top_picture_posters(self, limit: int = 1) -> list[tuple[str, int, float]]:
        """
        Get the top picture posters.

        Returns a list of tuples containing (author_name, picture_count, percentage)
        """
        if not self.total_pictures:
            return []

        return [
            (author, count, (count / self.total_pictures) * 100)
            for author, count in self.pictures_per_author.most_common(limit)
        ]

    def get_top_threads(self, limit: int = 3) -> list[tuple[str, int, float]]:
        """
        Get the top active threads.

        Returns a list of tuples containing (thread_name, message_count, percentage_of_thread_messages)
        """
        if not self.total_thread_messages:
            return []

        return [
            (thread, count, (count / self.total_thread_messages) * 100)
            for thread, count in self.messages_per_thread.most_common(limit)
        ]


class MessageStatisticsCollector(BaseCollector[MessageStatisticsData]):
    """
    Collector for message statistics.

    Collects:
    - Total messages in the period
    - Messages per user
    - Messages per channel
    - Pictures per user
    - Daily averages
    """

    async def collect(
        self, guild: Guild, start_date: datetime, end_date: datetime
    ) -> MessageStatisticsData:
        """
        Collect message statistics from the guild between the given dates.

        Args:
            guild: The Discord guild to collect statistics from
            start_date: The start date for collection (inclusive)
            end_date: The end date for collection (inclusive)

        Returns:
            MessageStatisticsData object with collected statistics
        """
        stats = MessageStatisticsData()
        stats.days_in_period = (
            end_date - start_date
        ).days or 1  # Ensure at least 1 day

        # Log information about the guild
        logging.info(f"Collecting statistics for guild: {guild.name} (ID: {guild.id})")

        # Get accessible text channels
        channels = self._get_text_channels(guild)
        logging.info(f"Found {len(channels)} text channels to process")

        # Process each channel
        for channel in channels:
            await self._process_channel_with_threads(
                channel, stats, start_date, end_date
            )

        logging.info(
            f"Statistics collection complete. Found {stats.total_messages} messages across {len(stats.messages_per_channel)} channels"
        )
        return stats

    def _get_text_channels(self, guild: Guild) -> list[TextChannel]:
        """Get a list of accessible text channels in the guild."""
        return [c for c in guild.channels if isinstance(c, TextChannel)]

    async def _process_channel_with_threads(
        self,
        channel: TextChannel,
        stats: MessageStatisticsData,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Process a channel and its threads."""
        # Check if we have permission to read message history
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.read_message_history:
            logging.warning(
                f"Skipping channel #{channel.name} - Missing read_message_history permission"
            )
            return

        # Process the main channel
        logging.info(f"Processing channel: #{channel.name}")
        await self._process_channel(channel, stats, start_date, end_date)

        # Process threads if available
        try:
            threads = channel.threads
            if threads:
                logging.info(f"Found {len(threads)} threads in #{channel.name}")
                for thread in threads:
                    if thread.permissions_for(thread.guild.me).read_message_history:
                        logging.info(f"Processing thread: #{thread.name}")
                        await self._process_channel(thread, stats, start_date, end_date)
        except (AttributeError, discord.errors.Forbidden) as e:
            logging.debug(f"Could not access threads in #{channel.name}: {e}")

    async def _process_channel(
        self,
        channel: TextChannel | Thread,
        stats: MessageStatisticsData,
        start_date: datetime,
        end_date: datetime,
    ) -> None:
        """Process messages in a channel or thread."""
        channel_name = f"#{channel.name}"

        # Check if this is a thread
        is_thread = isinstance(channel, Thread)

        try:
            # Fetch messages within date range
            async for message in channel.history(
                limit=None, after=start_date, before=end_date
            ):
                self._process_message(message, stats, channel_name, is_thread)

        except Exception as e:
            logging.error(f"Error fetching messages from {channel_name}: {str(e)}")

    def _process_message(
        self,
        message: discord.Message,
        stats: MessageStatisticsData,
        channel_name: str,
        is_thread: bool = False,
    ) -> None:
        """Process a single message and update statistics."""
        # Skip bot messages
        if not hasattr(message.author, "bot") or message.author.bot:
            return

        # Get author name (with fallback)
        author_name = getattr(
            message.author, "display_name", f"User {message.author.id}"
        )
        author_id = str(message.author.id)

        # Update message counters
        stats.total_messages += 1
        stats.messages_per_author[author_name] += 1
        stats.messages_per_author_id[author_name] = author_id
        stats.messages_per_channel[channel_name] += 1
        stats.messages_per_channel_id[channel_name] = message.channel.id

        # Track thread messages separately
        if is_thread:
            stats.messages_per_thread[channel_name] += 1
            stats.messages_per_thread_id[channel_name] = message.channel.id
            stats.total_thread_messages += 1

        # Check for image attachments
        self._process_attachments(message, author_name, stats)

    def _process_attachments(
        self, message: discord.Message, author_name: str, stats: MessageStatisticsData
    ) -> None:
        """Process attachments in a message and update image statistics."""
        try:
            # Find all image attachments in the message
            image_attachments = [
                a
                for a in message.attachments
                if a.content_type and a.content_type.startswith("image/")
            ]
            # Update image counters if any images found
            if image_attachments:
                count = len(image_attachments)
                stats.total_pictures += count
                stats.pictures_per_author[author_name] += count
        except Exception as e:
            # Log but continue with other messages
            logging.debug(f"Error processing attachments: {e}")
