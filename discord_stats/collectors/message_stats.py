import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta

import discord
from discord.channel import TextChannel
from discord.guild import Guild
from discord.threads import Thread


class MessageStatisticsData:
    """Container for message statistics data."""

    def __init__(self):
        self.total_messages: int = 0
        self.messages_per_author: Counter[str] = Counter()
        self.messages_per_author_id: dict[str, str] = {}  # Map author name to ID
        self.messages_per_author_username: dict[str, str] = {}  # Map author name to Discord username
        self.messages_per_channel: Counter[str] = Counter()
        self.messages_per_channel_id: dict[str, int] = {}  # Map channel name to ID
        self.messages_per_thread: Counter[str] = Counter()  # Track messages per thread
        self.messages_per_thread_id: dict[str, int] = {}  # Map thread name to ID
        self.total_thread_messages: int = 0  # Track total messages in all threads
        self.pictures_per_author: Counter[str] = Counter()
        self.total_pictures: int = 0
        self.days_in_period: int = 0
        self.bot_id: int | None = None  # Store the bot's user ID
        self.reactions_count: Counter[str] = Counter()  # Count of each reaction emoji
        self.total_reactions: int = 0  # Total number of reactions
        self.messages_per_author_per_channel: dict[
            str, Counter[str]
        ] = {}  # author -> {channel -> count}

        # Time-series data for graphs
        self.messages_per_day: dict[str, int] = {}  # ISO date string -> message count
        self.messages_per_day_per_channel: dict[
            str, dict[str, int]
        ] = {}  # channel -> {date -> count}
        self.messages_per_day_per_author: dict[
            str, dict[str, int]
        ] = {}  # author -> {date -> count}
        self.reactions_per_day: dict[
            str, dict[str, int]
        ] = {}  # emoji -> {date -> count}
        self.start_date: datetime | None = None
        self.end_date: datetime | None = None

        # Pre-period counts for cumulative graph offsets
        self.pre_period_messages_per_channel: dict[str, int] = {}
        self.pre_period_messages_per_author: dict[str, int] = {}
        self.pre_period_reactions_count: Counter[str] = Counter()

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
        Get the top active channels (excluding threads).

        Returns a list of tuples containing (channel_name, message_count, percentage)
        """
        if not self.total_messages:
            return []

        # Filter out thread channels (they start with #)
        non_thread_channels = {
            channel: count
            for channel, count in self.messages_per_channel.items()
            if channel.startswith("#") and channel not in self.messages_per_thread
        }

        # Get the most common non-thread channels
        top_channels = sorted(
            non_thread_channels.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        # Calculate percentages
        return [
            (channel, count, (count / self.total_messages) * 100)
            for channel, count in top_channels
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

        Returns a list of tuples containing (thread_name, message_count, percentage_of_all_messages)
        """
        if not self.total_thread_messages or not self.total_messages:
            return []

        return [
            (
                thread,
                count,
                (count / self.total_messages) * 100,
            )  # Percentage of all messages
            for thread, count in self.messages_per_thread.most_common(limit)
        ]

    def get_top_reactions(self, limit: int = 3) -> list[tuple[str, int, float]]:
        """
        Get the top reactions.

        Returns a list of tuples containing (emoji, reaction_count, percentage)
        """
        if not self.total_reactions:
            return []

        return [
            (emoji, count, (count / self.total_reactions) * 100)
            for emoji, count in self.reactions_count.most_common(limit)
        ]

    def get_all_dates_in_range(self) -> list[str]:
        """
        Get all dates in the statistics period as ISO date strings.

        Returns:
            List of ISO date strings (YYYY-MM-DD) for every day in the range
        """
        if not self.start_date or not self.end_date:
            return []

        dates = []
        current_date = self.start_date.date()
        end_date = self.end_date.date()

        while current_date <= end_date:
            dates.append(current_date.isoformat())
            current_date += timedelta(days=1)

        return dates

    def get_top_channels_with_daily_data(
        self, limit: int = 5
    ) -> list[tuple[str, int, dict[str, int]]]:
        """
        Get top channels with their daily message counts.

        Returns:
            List of tuples containing (channel_name, total_count, daily_data)
            where daily_data is {date -> count}
        """
        top_channels = self.get_top_channels(limit)
        result = []

        for channel_name, total_count, _ in top_channels:
            daily_data = self.messages_per_day_per_channel.get(channel_name, {})
            result.append((channel_name, total_count, daily_data))

        return result

    def get_top_reactions_with_daily_data(
        self, limit: int = 5
    ) -> list[tuple[str, int, dict[str, int]]]:
        """
        Get top reactions with their daily usage counts.

        Returns:
            List of tuples containing (emoji, total_count, daily_data)
            where daily_data is {date -> count}
        """
        top_reactions = self.get_top_reactions(limit)
        if not top_reactions:
            return []

        result = []
        for emoji, total_count, _ in top_reactions:
            # Get daily data for this reaction
            daily_data = self.reactions_per_day.get(emoji, {})
            result.append((emoji, total_count, daily_data))

        return result

    def get_top_authors_channel_distribution(
        self, limit: int = 5
    ) -> list[tuple[str, int, dict[str, tuple[int, float]]]]:
        """
        Get the channel distribution for top message authors.

        Args:
            limit: Maximum number of authors to return

        Returns:
            List of tuples containing (author_name, total_count, channel_data)
            where channel_data is {channel_name -> (message_count, percentage)}
        """
        top_authors = self.get_top_posters(limit)
        result = []

        for author_name, total_count, _ in top_authors:
            # Get channel distribution
            channel_counts = self.messages_per_author_per_channel.get(
                author_name, Counter()
            )

            # Calculate percentages for all channels
            channel_data = {}
            for channel, count in channel_counts.items():
                percentage = (count / total_count) * 100
                channel_data[channel] = (count, percentage)

            result.append((author_name, total_count, channel_data))

        return result

    def get_top_authors_with_daily_data(
        self, limit: int = 5
    ) -> list[tuple[str, int, dict[str, int]]]:
        """
        Get top message authors with their daily message counts.

        Args:
            limit: Maximum number of authors to return

        Returns:
            List of tuples containing (author_name, total_count, daily_data)
            where daily_data is {date -> count}
        """
        top_authors = self.get_top_posters(limit)
        result = []

        for author_name, total_count, _ in top_authors:
            daily_data = self.messages_per_day_per_author.get(author_name, {})
            result.append((author_name, total_count, daily_data))

        return result


class MessageStatisticsCollector:
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
        self,
        guild: Guild,
        start_date: datetime,
        end_date: datetime,
        concurrency: int = 10,
        history_offset: bool = True,
    ) -> MessageStatisticsData:
        """
        Collect message statistics from the guild between the given dates.

        Args:
            guild: The Discord guild to collect statistics from
            start_date: The start date for collection (inclusive)
            end_date: The end date for collection (inclusive)
            concurrency: Maximum number of channels to fetch simultaneously

        Returns:
            MessageStatisticsData object with collected statistics
        """
        stats = MessageStatisticsData()
        stats.days_in_period = (
            end_date - start_date
        ).days or 1  # Ensure at least 1 day
        stats.start_date = start_date
        stats.end_date = end_date

        # Log information about the guild
        logging.info(f"Collecting statistics for guild: {guild.name} (ID: {guild.id})")

        # Get accessible text channels
        channels = self._get_text_channels(guild)
        logging.info(
            f"Found {len(channels)} text channels to process (concurrency={concurrency})"
        )

        # Process channels concurrently, bounded by semaphore
        semaphore = asyncio.Semaphore(concurrency)
        remaining = len(channels)

        async def _bounded(channel: TextChannel):
            nonlocal remaining
            async with semaphore:
                before = stats.total_messages
                await self._process_channel_with_threads(
                    channel, stats, start_date, end_date
                )
                fetched = stats.total_messages - before
                remaining -= 1
                logging.info(
                    f"#{channel.name} done — {fetched:,} messages ({remaining} channels remaining)"
                )

        _ = await asyncio.gather(*(_bounded(ch) for ch in channels))

        # Optionally count pre-period messages to seed cumulative graph offsets
        if history_offset:
            logging.info("Collecting pre-period message counts for history offset...")
            pre_semaphore = asyncio.Semaphore(1)

            async def _pre_bounded(channel: TextChannel) -> None:
                async with pre_semaphore:
                    await self._collect_pre_period_counts(channel, stats, start_date)

            _ = await asyncio.gather(*(_pre_bounded(ch) for ch in channels))  # type: ignore[arg-type]
            logging.info("Pre-period count collection complete.")

        logging.info(
            f"Statistics collection complete. Found {stats.total_messages:,} messages across {len(stats.messages_per_channel)} channels"
        )
        return stats

    async def _collect_pre_period_counts(
        self,
        channel: TextChannel,
        stats: MessageStatisticsData,
        start_date: datetime,
    ) -> None:
        """
        Count messages posted before start_date in the channel (and its threads).
        Only counts; does not process content.
        """
        channel_key = f"#{channel.name}"
        channel_count = 0
        author_counts: Counter[str] = Counter()
        reaction_counts: Counter[str] = Counter()

        def _tally(message: discord.Message) -> None:
            if getattr(message.author, "bot", False):
                return
            nonlocal channel_count
            channel_count += 1
            author_counts[message.author.display_name] += 1
            for reaction in message.reactions:
                emoji_key = str(reaction.emoji)
                reaction_counts[emoji_key] += reaction.count

        try:
            async for message in channel.history(
                before=start_date, limit=None, oldest_first=False
            ):
                _tally(message)
        except discord.Forbidden:
            pass
        except Exception as exc:
            logging.warning(f"Pre-period count failed for #{channel.name}: {exc}")

        # Also count archived threads
        try:
            async for thread in channel.archived_threads(limit=None):
                try:
                    async for message in thread.history(
                        before=start_date, limit=None, oldest_first=False
                    ):
                        _tally(message)
                except Exception:
                    pass
        except Exception:
            pass

        if channel_count > 0:
            stats.pre_period_messages_per_channel[channel_key] = (
                stats.pre_period_messages_per_channel.get(channel_key, 0) + channel_count
            )
            for author, count in author_counts.items():
                stats.pre_period_messages_per_author[author] = (
                    stats.pre_period_messages_per_author.get(author, 0) + count
                )
        for emoji_key, count in reaction_counts.items():
            stats.pre_period_reactions_count[emoji_key] += count

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
        author_username = getattr(message.author, "name", author_name)

        # Get message date as ISO string for time series
        message_date = message.created_at.date().isoformat()

        # Update message counters
        stats.total_messages += 1
        stats.messages_per_author[author_name] += 1
        stats.messages_per_author_id[author_name] = author_id
        stats.messages_per_author_username[author_name] = author_username
        stats.messages_per_channel[channel_name] += 1
        stats.messages_per_channel_id[channel_name] = message.channel.id

        # Update per-author per-channel message count
        if author_name not in stats.messages_per_author_per_channel:
            stats.messages_per_author_per_channel[author_name] = Counter()
        stats.messages_per_author_per_channel[author_name][channel_name] += 1

        # Update time-series data
        stats.messages_per_day[message_date] = (
            stats.messages_per_day.get(message_date, 0) + 1
        )

        # Update per-channel daily data
        if channel_name not in stats.messages_per_day_per_channel:
            stats.messages_per_day_per_channel[channel_name] = {}
        stats.messages_per_day_per_channel[channel_name][message_date] = (
            stats.messages_per_day_per_channel[channel_name].get(message_date, 0) + 1
        )

        # Update per-author daily data
        if author_name not in stats.messages_per_day_per_author:
            stats.messages_per_day_per_author[author_name] = {}
        stats.messages_per_day_per_author[author_name][message_date] = (
            stats.messages_per_day_per_author[author_name].get(message_date, 0) + 1
        )

        # Track thread messages separately
        if is_thread:
            stats.messages_per_thread[channel_name] += 1
            stats.messages_per_thread_id[channel_name] = message.channel.id
            stats.total_thread_messages += 1

        # Check for image attachments
        self._process_attachments(message, author_name, stats)

        # Process reactions
        self._process_reactions(message, stats, message_date)

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

    def _process_reactions(
        self, message: discord.Message, stats: MessageStatisticsData, message_date: str
    ) -> None:
        """Process reactions on a message and update reaction statistics."""
        try:
            # Process each reaction on the message
            for reaction in message.reactions:
                # Get the emoji name or unicode character
                emoji = str(reaction.emoji)
                # Count each reaction (counts all users who reacted)
                count = reaction.count

                # Update reaction counters
                stats.reactions_count[emoji] += count
                stats.total_reactions += count

                # Update time-series data for reactions
                if emoji not in stats.reactions_per_day:
                    stats.reactions_per_day[emoji] = {}
                stats.reactions_per_day[emoji][message_date] = (
                    stats.reactions_per_day[emoji].get(message_date, 0) + count
                )

        except Exception as e:
            # Log but continue with other messages
            logging.debug(f"Error processing reactions: {e}")
