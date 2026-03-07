"""Graph generator for message statistics."""

import logging
from datetime import datetime
from datetime import datetime as dt
from datetime import timedelta
from pathlib import Path
from typing import Literal, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d

from ..collectors.message_stats import MessageStatisticsData

logger = logging.getLogger(__name__)


class MessageGraphGenerator:
    """Generates various graphs from message statistics data."""

    def __init__(
        self,
        style: Literal["white", "dark", "whitegrid", "darkgrid", "ticks"] = "whitegrid",
    ):
        """
        Initialize the graph generator.

        Args:
            style: Seaborn style to use for graphs
        """
        sns.set_style(style)
        plt.style.use("seaborn-v0_8")

    def _smooth_data(
        self, x_data: list, y_data: list, smoothing_factor: float = 1.0
    ) -> tuple[list, list]:
        """
        Apply smoothing to line data for better readability.

        Args:
            x_data: X-axis data (dates)
            y_data: Y-axis data (values)
            smoothing_factor: Smoothing intensity (0 = no smoothing, higher = more smoothing)

        Returns:
            Tuple of (smoothed_x, smoothed_y) data
        """
        if len(x_data) < 3 or smoothing_factor <= 0:
            return x_data, y_data

        try:
            # Convert dates to numeric values for interpolation
            x_numeric = [
                x.timestamp() if hasattr(x, "timestamp") else float(x) for x in x_data
            ]

            # Apply gaussian smoothing to y data
            y_smoothed = gaussian_filter1d(y_data, sigma=smoothing_factor)

            # Create more points for smoother curves if we have enough data
            if len(x_data) >= 5:
                # Create interpolation function
                f = interp1d(
                    x_numeric,
                    y_smoothed,
                    kind="cubic",
                    bounds_error=False,
                    fill_value=0,
                )

                # Generate more x points for smoother curve
                x_new_numeric = np.linspace(
                    min(x_numeric), max(x_numeric), len(x_data) * 3
                )
                y_new = f(x_new_numeric)

                # Convert back to datetime if needed
                if hasattr(x_data[0], "timestamp"):
                    x_new = [dt.fromtimestamp(ts) for ts in x_new_numeric]
                else:
                    x_new = x_new_numeric.tolist()

                return x_new, y_new.tolist()
            else:
                return x_data, y_smoothed.tolist()

        except Exception as e:
            logger.debug(f"Error smoothing data: {e}, returning original data")
            return x_data, y_data

    def generate_all_graphs(
        self,
        data: MessageStatisticsData,
        output_dir: str = ".",
        prefix: str = "discord_stats",
        smooth: bool = True,
    ) -> list[str]:
        """
        Generate all available graphs and save them to files.

        Args:
            data: Message statistics data
            output_dir: Directory to save graphs
            prefix: Prefix for graph filenames
            smooth: Whether to apply smoothing to line graphs (default: True)

        Returns:
            List of generated file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        generated_files = []

        try:
            # Generate messages per day graph
            file_path = self.generate_messages_per_day_graph(
                data, str(output_path / f"{prefix}_messages_per_day.png"), smooth=smooth
            )
            if file_path:
                generated_files.append(file_path)

            # Generate top authors over time graph
            file_path = self.generate_top_authors_over_time_graph(
                data,
                str(output_path / f"{prefix}_top_authors_over_time.png"),
                smooth=False,
            )
            if file_path:
                generated_files.append(file_path)

            # Generate top channels over time graph
            file_path = self.generate_top_channels_over_time_graph(
                data,
                str(output_path / f"{prefix}_top_channels_over_time.png"),
                smooth=False,
            )
            if file_path:
                generated_files.append(file_path)

            # Generate top reactions over time graph
            file_path = self.generate_top_reactions_over_time_graph(
                data,
                str(output_path / f"{prefix}_top_reactions_over_time.png"),
                smooth=False,
            )
            if file_path:
                generated_files.append(file_path)

            # Generate top authors channel distribution pie charts
            file_path = self.generate_top_authors_channel_distribution_pies(
                data,
                str(output_path / f"{prefix}_top_authors_channel_distribution.png"),
                top_n=9,
            )
            if file_path:
                generated_files.append(file_path)

            # Generate daily activity heatmap
            file_path = self.generate_daily_activity_heatmap(
                data, str(output_path / f"{prefix}_daily_activity_heatmap.png")
            )
            if file_path:
                generated_files.append(file_path)

        except Exception as e:
            logger.error(f"Error generating graphs: {e}")

        return generated_files

    def generate_messages_per_day_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        smooth: bool = True,
    ) -> Optional[str]:
        """
        Generate a line graph showing messages per day.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            smooth: Whether to apply smoothing to the line (default: True)

        Returns:
            Path to saved file or None if not saved
        """
        if not data.messages_per_day or not data.start_date or not data.end_date:
            logger.warning("Insufficient data for messages per day graph")
            return None

        # Create DataFrame with all dates in range
        all_dates = data.get_all_dates_in_range()
        df_data = []

        for date_str in all_dates:
            count = data.messages_per_day.get(date_str, 0)
            df_data.append({"date": dt.fromisoformat(date_str), "messages": count})

        df = pd.DataFrame(df_data)

        # Create the plot
        plt.figure(figsize=(12, 6))

        # Apply smoothing if requested
        if smooth and len(df) > 2:
            x_smooth, y_smooth = self._smooth_data(
                df["date"].tolist(), df["messages"].tolist(), smoothing_factor=1.5
            )
            plt.plot(x_smooth, y_smooth, linewidth=3, alpha=0.8, label="Smoothed trend")
            plt.plot(
                df["date"],
                df["messages"],
                marker="o",
                linewidth=1,
                markersize=3,
                alpha=0.6,
                label="Daily data",
            )
            plt.legend()
        else:
            plt.plot(df["date"], df["messages"], marker="o", linewidth=2, markersize=4)

        # Formatting
        plt.title("Messages Per Day", fontsize=16, fontweight="bold")
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Number of Messages", fontsize=12)
        plt.grid(True, alpha=0.3)

        # Format x-axis
        ax = plt.gca()
        ax.xaxis.set_major_locator(
            mdates.DayLocator(interval=max(1, len(all_dates) // 10))
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

        # Add some statistics as text
        avg_messages = df["messages"].mean()
        max_messages = df["messages"].max()
        plt.text(
            0.02,
            0.98,
            f"Avg: {avg_messages:.1f}/day\nMax: {max_messages}/day",
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize=10,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Messages per day graph saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_top_channels_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """
        Generate a line graph showing cumulative message activity for top channels over time.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top channels to display
            smooth: Whether to apply smoothing to the lines (default: True)

        Returns:
            Path to saved file or None if not saved
        """
        top_channels_data = data.get_top_channels_with_daily_data(top_n)
        if not top_channels_data or not data.start_date or not data.end_date:
            logger.warning("Insufficient data for top channels over time graph")
            return None

        all_dates = data.get_all_dates_in_range()

        # Create the plot
        plt.figure(figsize=(12, 8))

        # Plot each channel with cumulative data
        for channel_name, total_count, daily_data in top_channels_data:
            # Create series with zeros for missing dates
            daily_counts = [daily_data.get(date_str, 0) for date_str in all_dates]
            dates = [dt.fromisoformat(date_str) for date_str in all_dates]

            # Calculate cumulative counts
            cumulative_counts = []
            running_total = 0
            for count in daily_counts:
                running_total += count
                cumulative_counts.append(running_total)

            # Clean channel name for display
            display_name = channel_name.replace("#", "")

            # Apply smoothing if requested and we have enough data points
            if smooth and len(dates) > 2:
                x_smooth, y_smooth = self._smooth_data(
                    dates, cumulative_counts, smoothing_factor=1.5
                )
                plt.plot(
                    x_smooth,
                    y_smooth,
                    linewidth=3,
                    label=f"{display_name} ({total_count} total)",
                    alpha=0.8,
                )
            else:
                plt.plot(
                    mdates.date2num(dates),
                    cumulative_counts,
                    marker="o",
                    linewidth=2,
                    markersize=3,
                    label=f"{display_name} ({total_count} total)",
                )

        # Formatting
        plt.title(
            f"Top {top_n} Channels - Cumulative Messages Over Time",
            fontsize=16,
            fontweight="bold",
        )
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Cumulative Message Count", fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.grid(True, alpha=0.3)

        # Format x-axis
        ax = plt.gca()
        ax.xaxis.set_major_locator(
            mdates.DayLocator(interval=max(1, len(all_dates) // 10))
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Top channels cumulative graph saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_top_reactions_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """
        Generate a line graph showing cumulative usage of top reactions over time.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top reactions to display
            smooth: Whether to apply smoothing to the lines (default: True)

        Returns:
            Path to saved file or None if not saved
        """
        top_reactions_data = data.get_top_reactions_with_daily_data(top_n)
        if not top_reactions_data or not data.start_date or not data.end_date:
            logger.warning("Insufficient data for top reactions over time graph")
            return None

        all_dates = data.get_all_dates_in_range()

        # Create the plot
        plt.figure(figsize=(12, 8))

        # Try to use a font that supports emojis if available
        try:
            # Set a font that might have better emoji support
            plt.rcParams["font.family"] = "DejaVu Sans"
        except Exception:
            logger.debug("Could not set DejaVu Sans font")

        # Plot each reaction with cumulative data
        for emoji, total_count, daily_data in top_reactions_data:
            # Create series with zeros for missing dates
            daily_counts = [daily_data.get(date_str, 0) for date_str in all_dates]
            dates = [dt.fromisoformat(date_str) for date_str in all_dates]

            # Calculate cumulative counts
            cumulative_counts = []
            running_total = 0
            for count in daily_counts:
                running_total += count
                cumulative_counts.append(running_total)

            # Get Unicode name of emoji for display
            import unicodedata

            # Try to get the official Unicode name, fallback to the emoji itself
            try:
                # For combined emojis (like country flags), we use the first character
                emoji_char = emoji[0] if emoji else "?"
                emoji_name = unicodedata.name(emoji_char).lower().replace("_", " ")
                # Capitalize the name for better display
                emoji_name = emoji_name.title()
            except (ValueError, TypeError):
                emoji_name = f"Emoji {ord(emoji[0]) if emoji else 0}"

            # Apply smoothing if requested and we have enough data points
            if smooth and len(dates) > 2:
                x_smooth, y_smooth = self._smooth_data(
                    dates, cumulative_counts, smoothing_factor=1.5
                )
                plt.plot(
                    x_smooth,
                    y_smooth,
                    linewidth=3,
                    label=f"{emoji_name} ({total_count} total)",
                    alpha=0.8,
                )
            else:
                plt.plot(
                    mdates.date2num(dates),
                    cumulative_counts,
                    marker="o",
                    linewidth=2,
                    markersize=3,
                    label=f"{emoji_name} ({total_count} total)",
                )

        # Formatting
        plt.title(
            f"Top {top_n} Reactions - Cumulative Usage Over Time",
            fontsize=16,
            fontweight="bold",
        )
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Cumulative Reaction Count", fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
        plt.grid(True, alpha=0.3)

        # Format x-axis
        ax = plt.gca()
        ax.xaxis.set_major_locator(
            mdates.DayLocator(interval=max(1, len(all_dates) // 10))
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Top reactions cumulative graph saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_daily_activity_heatmap(
        self, data: MessageStatisticsData, output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a heatmap showing daily activity patterns.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)

        Returns:
            Path to saved file or None if not saved
        """
        if not data.messages_per_day or not data.start_date or not data.end_date:
            logger.warning("Insufficient data for daily activity heatmap")
            return None

        all_dates = data.get_all_dates_in_range()

        # Prepare data for heatmap
        df_data = []
        for date_str in all_dates:
            date_obj = dt.fromisoformat(date_str)
            count = data.messages_per_day.get(date_str, 0)
            df_data.append(
                {
                    "date": date_obj,
                    "day_of_week": date_obj.strftime("%A"),
                    "week": date_obj.isocalendar()[1],
                    "messages": count,
                }
            )

        df = pd.DataFrame(df_data)

        # Create pivot table for heatmap
        pivot_table = df.pivot_table(
            values="messages", index="day_of_week", columns="week", fill_value=0
        )

        # Reorder days of week
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        pivot_table = pivot_table.reindex(day_order)

        # Create the heatmap
        plt.figure(figsize=(max(8, len(pivot_table.columns) * 0.5), 6))
        sns.heatmap(
            pivot_table, annot=False, cmap="YlOrRd", cbar_kws={"label": "Messages"}
        )

        plt.title("Daily Activity Heatmap", fontsize=16, fontweight="bold")
        plt.xlabel("Week Number", fontsize=12)
        plt.ylabel("Day of Week", fontsize=12)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Daily activity heatmap saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def generate_top_authors_channel_distribution_pies(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 5,
    ) -> Optional[str]:
        """
        Generate pie charts showing where top authors post their messages across channels.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top authors to display (default: 5)

        Returns:
            Path to saved file or None if not saved
        """
        author_channel_data = data.get_top_authors_channel_distribution(limit=top_n)

        if not author_channel_data:
            logger.warning(
                "No data available for top authors channel distribution pie charts"
            )
            return None

        # Determine layout based on number of authors
        n_authors = len(author_channel_data)
        if n_authors <= 0:
            return None

        # Calculate grid dimensions
        if n_authors <= 2:
            n_cols, n_rows = n_authors, 1
        elif n_authors <= 4:
            n_cols, n_rows = 2, (n_authors + 1) // 2
        else:
            n_cols, n_rows = 3, (n_authors + 2) // 3

        # Set figure size proportionally
        fig_width = 7 * n_cols
        fig_height = 5 * n_rows

        # Create figure with subplots
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(fig_width, fig_height))

        # Convert to array for easier indexing if there's only one pie chart
        if n_authors == 1:
            axes = np.array([axes])

        # Flatten axes array if we have a grid
        if n_authors > 2:
            axes = axes.flatten()  # Collect all unique channel names across all authors
        all_channels = set()
        for _, _, channel_data in author_channel_data:
            all_channels.update(channel_data.keys())

        # Create a consistent color mapping for all channels, prioritizing popular channels
        channel_colors = self._generate_channel_color_map(list(all_channels), data)

        # Generate pie charts for each author
        chart_index = 0
        for author_name, total_count, channel_data in author_channel_data:
            if chart_index >= len(axes):
                break

            ax = axes[chart_index]

            # Extract channel names, counts and percentages for this author
            channels = list(channel_data.keys())
            counts = [channel_data[ch][0] for ch in channels]
            percentages = [channel_data[ch][1] for ch in channels]

            # Sort channels by count for better visibility
            sorted_indices = np.argsort(counts)[::-1]  # Sort in descending order
            channels = [channels[i] for i in sorted_indices]
            counts = [counts[i] for i in sorted_indices]
            percentages = [percentages[i] for i in sorted_indices]

            # Keep top 5 channels, collapse the rest into "Others"
            max_channels = 5
            if len(channels) > max_channels:
                others_count = sum(counts[max_channels:])
                others_pct = sum(percentages[max_channels:])
                channels = channels[:max_channels] + ["Others"]
                counts = counts[:max_channels] + [others_count]
                percentages = percentages[:max_channels] + [others_pct]

            # Get colors in the same order as the channels
            colors = [
                (0.75, 0.75, 0.75) if ch == "Others" else channel_colors[ch]
                for ch in channels
            ]

            # Format labels as channel names without the # symbol
            labels = [ch if ch == "Others" else f"{ch.replace('#', '')}" for ch in channels]

            # Generate pie chart
            wedges, texts, autotexts = ax.pie(
                counts,
                labels=None,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                wedgeprops={"width": 0.5, "edgecolor": "w"},
            )

            # Customize text appearance
            plt.setp(autotexts, size=9, weight="bold")

            # Create legend items sorted by percentage
            legend_labels = [
                f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)
            ]

            # Add legend with custom labels showing channel names
            ax.legend(
                wedges,
                legend_labels,
                title="Channels",
                loc="center left",
                bbox_to_anchor=(0.9, 0.5),
                fontsize=7,
            )

            # Set title for this subplot — use Discord username if available
            display_label = data.messages_per_author_username.get(author_name, author_name)
            ax.set_title(f"{display_label}\n({total_count} total messages)", fontsize=12)

            # Increment chart index
            chart_index += 1

        # Adjust layout, reserving top 8% for suptitle and tightening row spacing
        plt.tight_layout(rect=(0, 0, 1, 0.92), h_pad=2.0)

        # Add overall title in the reserved top band
        fig.suptitle(
            "Channel Distribution for Top Authors",
            fontsize=16,
            fontweight="bold",
            y=0.97,
        )

        # Remove any unused subplots
        for j in range(chart_index + 1, len(axes)):
            fig.delaxes(axes[j])

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(
                f"Author channel distribution pie charts saved to {output_path}"
            )
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    def _generate_channel_color_map(
        self, all_channel_names: list[str], data: Optional[MessageStatisticsData] = None
    ) -> dict[str, tuple]:
        """
        Generate a consistent color mapping for channels, prioritizing most popular channels.

        Args:
            all_channel_names: List of all unique channel names to assign colors to
            data: Message statistics data to determine channel popularity

        Returns:
            Dictionary mapping channel names to color tuples
        """
        import colorsys

        # Use these distinct starting hues for the most popular channels
        # We start with these to avoid having too many similar colors for top channels
        distinct_hues = [
            0.0,
            0.1,
            0.58,
            0.35,
            0.7,
            0.9,
            0.2,
            0.45,
            0.8,
            0.55,
        ]  # red, orange, blue, green, purple, etc.

        colors = {}

        # If we have data, sort channels by popularity
        if data:
            # Sort channels by message count (popularity)
            channel_counts = {}
            for channel in all_channel_names:
                count = data.messages_per_channel.get(channel, 0)
                channel_counts[channel] = count

            # Sort channels by count (descending)
            sorted_channels = sorted(
                channel_counts.items(), key=lambda x: x[1], reverse=True
            )
            sorted_channel_names = [channel for channel, _ in sorted_channels]

            # Assign distinct hues to the most popular channels
            for i, channel in enumerate(sorted_channel_names):
                if i < len(distinct_hues):
                    # Use predefined distinct hues for top channels
                    hue = distinct_hues[i]
                else:
                    # For remaining channels, distribute evenly in HSV space
                    hue = (
                        (i - len(distinct_hues))
                        / (len(sorted_channel_names) - len(distinct_hues))
                        if len(sorted_channel_names) > len(distinct_hues)
                        else 0
                    )

                # Create slightly different saturations and values for visual interest
                sat = 0.8 + (i % 3) * 0.05  # Slight variation in saturation
                val = 0.9 - (i % 3) * 0.05  # Slight variation in value

                rgb = colorsys.hsv_to_rgb(hue, sat, val)
                colors[channel] = rgb
        else:
            # If no data, just distribute colors evenly
            num_channels = len(all_channel_names)
            for i, channel in enumerate(sorted(all_channel_names)):
                hue = i / num_channels
                rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
                colors[channel] = rgb

        return colors

    def generate_top_authors_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """
        Generate a line graph showing cumulative message activity for top authors over time.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top authors to display (default: 5)
            smooth: Whether to apply smoothing to the lines (default: True)

        Returns:
            Path to saved file or None if not saved
        """
        top_authors_data = data.get_top_authors_with_daily_data(top_n)
        if not top_authors_data or not data.start_date or not data.end_date:
            logger.warning("Insufficient data for top authors over time graph")
            return None

        all_dates = data.get_all_dates_in_range()

        # Create the plot with adequate size for multiple lines
        plt.figure(figsize=(14, 8))

        # Plot each author with cumulative data
        for author_name, total_count, daily_data in top_authors_data:
            # Create series with zeros for missing dates
            daily_counts = [daily_data.get(date_str, 0) for date_str in all_dates]
            dates = [dt.fromisoformat(date_str) for date_str in all_dates]

            # Calculate cumulative counts
            cumulative_counts = []
            running_total = 0
            for count in daily_counts:
                running_total += count
                cumulative_counts.append(running_total)

            # Apply smoothing if requested and we have enough data points
            if smooth and len(dates) > 2:
                x_smooth, y_smooth = self._smooth_data(
                    dates, cumulative_counts, smoothing_factor=1.5
                )
                plt.plot(
                    x_smooth,
                    y_smooth,
                    linewidth=3,
                    label=f"{author_name} ({total_count} total)",
                    alpha=0.8,
                )
            else:
                # Convert dates to numbers for matplotlib
                date_nums = mdates.date2num(dates)
                plt.plot(
                    date_nums,
                    cumulative_counts,
                    marker="o",
                    linewidth=2,
                    markersize=3,
                    label=f"{author_name} ({total_count} total)",
                )

        # Formatting
        plt.title(
            f"Top {top_n} Authors - Cumulative Messages Over Time",
            fontsize=16,
            fontweight="bold",
        )
        plt.xlabel("Date", fontsize=12)
        plt.ylabel("Cumulative Message Count", fontsize=12)
        plt.legend(loc="upper left", frameon=True, framealpha=0.9)
        plt.grid(True, alpha=0.3)

        # Format x-axis
        ax = plt.gca()
        ax.xaxis.set_major_locator(
            mdates.DayLocator(interval=max(1, len(all_dates) // 10))
        )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"Top authors over time graph saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None
