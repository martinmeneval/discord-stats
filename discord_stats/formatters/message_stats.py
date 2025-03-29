from datetime import datetime

import discord

from ..collectors.message_stats import MessageStatisticsData
from . import BaseFormatter


class MessageStatisticsFormatter(BaseFormatter[MessageStatisticsData]):
    """Formatter for message statistics data."""

    def format(self, data: MessageStatisticsData) -> discord.Embed:
        """
        Format message statistics data into a Discord embed.

        Args:
            data: The message statistics data to format

        Returns:
            A Discord embed containing the formatted statistics
        """
        embed = discord.Embed(
            title="Server Message Statistics",
            description=f"Statistics from the past {data.days_in_period} days",
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )

        # Add general message stats
        embed.add_field(
            name="Total Messages", value=f"{data.total_messages:,}", inline=True
        )
        embed.add_field(
            name="Daily Average",
            value=f"{data.avg_messages_per_day:.1f} messages/day",
            inline=True,
        )

        # Add top posters stats with clickable mentions
        top_posters = data.get_top_posters(3)
        if top_posters:
            top_posters_text = "\n".join(
                f"**{i+1}. <@{data.messages_per_author_id.get(name, name)}>**: {count:,} messages ({percent:.1f}%)"
                for i, (name, count, percent) in enumerate(top_posters)
            )
            embed.add_field(
                name="Top Posters",
                value=top_posters_text or "No messages found",
                inline=False,
            )

        # Add top channels stats with clickable links and percentages
        top_channels = data.get_top_channels(3)
        if top_channels:
            top_channels_text = "\n".join(
                f"**{i+1}. <#{data.messages_per_channel_id.get(name, name)}>**: {count:,} messages ({percent:.1f}%)"
                for i, (name, count, percent) in enumerate(top_channels)
            )
            embed.add_field(
                name="Most Active Channels",
                value=top_channels_text or "No messages found",
                inline=False,
            )

        # Add top threads stats with clickable links
        top_threads = data.get_top_threads(1)  # Get only the top thread
        if top_threads and data.total_thread_messages > 0:
            thread_name, thread_count, thread_percent = top_threads[0]
            thread_id = data.messages_per_thread_id.get(thread_name, "")
            thread_mention = f"<#{thread_id}>" if thread_id else thread_name

            thread_text = (
                f"**{thread_mention}**: {thread_count:,} messages "
                f"({thread_percent:.1f}% of all thread messages)\n"
                f"Total messages in all threads: {data.total_thread_messages:,}"
            )
            embed.add_field(
                name="Top Thread",
                value=thread_text,
                inline=False,
            )

        # Add top picture poster with clickable mention
        if data.total_pictures > 0:
            top_picture_posters = data.get_top_picture_posters(
                1
            )  # Get only the top picture poster
            if top_picture_posters:
                name, count, percent = top_picture_posters[0]
                user_id = data.messages_per_author_id.get(name, name)
                mention = f"<@{user_id}>" if user_id != name else name

                picture_text = (
                    f"**{mention}**: {count:,} pictures ({percent:.1f}% of all pictures)\n"
                    f"Total pictures: {data.total_pictures:,}"
                )
                embed.add_field(
                    name="Top Picture Poster",
                    value=picture_text,
                    inline=False,
                )

        # Add footer
        embed.set_footer(text="Discord Stats Bot")

        return embed


def format_statistics_text(data, start_date: datetime, end_date: datetime) -> str:
    """
    Format statistics data as plain text for copying and pasting.

    Args:
        data: The statistics data object
        start_date: Start date for the statistics period
        end_date: End date for the statistics period

    Returns:
        Formatted text representation of the statistics
    """
    days = (end_date - start_date).days or 1

    output = [
        "**Server Message Statistics**",
        f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({days} days)",
        "",
        f"**Total Messages:** {data.total_messages:,}",
        f"**Daily Average:** {data.avg_messages_per_day:.1f} messages/day",
        f"**Total Pictures:** {data.total_pictures:,}",
        "",
    ]

    # Add top posters
    _add_top_posters_section(output, data)

    # Add top channels
    _add_top_channels_section(output, data)

    # Add top thread
    _add_top_thread_section(output, data)

    # Add top picture poster
    _add_top_picture_posters_section(output, data)

    # Add "Powered by discord-stats" footer with link to GitHub
    output.append(
        "\n\nThis report is powered by [discord-stats](https://github.com/martinmeneval/discord-stats)"
    )

    return "\n".join(output)


def _add_top_posters_section(output: list, data) -> None:
    """Add the top posters section to the output list."""
    top_posters = data.get_top_posters()
    if top_posters:
        output.append("**Top Posters:**")
        for i, (name, count, percent) in enumerate(top_posters):
            user_id = data.messages_per_author_id.get(name, name)
            mention = f"<@{user_id}>" if user_id != name else name
            output.append(f"{i+1}. {mention}: {count:,} messages ({percent:.1f}%)")
        output.append("")


def _add_top_channels_section(output: list, data) -> None:
    """Add the top channels section to the output list."""
    top_channels = data.get_top_channels()
    if top_channels:
        output.append("**Most Active Channels:**")
        for i, (name, count, percent) in enumerate(top_channels):
            channel_id = data.messages_per_channel_id.get(name, name)
            mention = f"<#{channel_id}>" if channel_id != name else name
            output.append(f"{i+1}. {mention}: {count:,} messages ({percent:.1f}%)")
        output.append("")


def _add_top_thread_section(output: list, data) -> None:
    """Add the top thread section to the output list."""
    top_threads = data.get_top_threads(1)  # Get only the top thread
    if top_threads and data.total_thread_messages > 0:
        thread_name, thread_count, thread_percent = top_threads[0]
        thread_id = data.messages_per_thread_id.get(thread_name, "")
        thread_mention = f"<#{thread_id}>" if thread_id else thread_name

        output.append("**Top Thread:**")
        output.append(
            f"{thread_mention}: {thread_count:,} messages ({thread_percent:.1f}% of all thread messages)"
        )
        output.append("")


def _add_top_picture_posters_section(output: list, data) -> None:
    """Add the top picture poster section to the output list."""
    if data.total_pictures > 0:
        top_picture_posters = data.get_top_picture_posters(
            1
        )  # Get only the top picture poster
        if top_picture_posters:
            name, count, percent = top_picture_posters[0]
            user_id = data.messages_per_author_id.get(name, name)
            mention = f"<@{user_id}>" if user_id != name else name

            output.append("**Top Picture Poster:**")
            output.append(
                f"{mention}: {count:,} pictures ({percent:.1f}% of all pictures)"
            )
