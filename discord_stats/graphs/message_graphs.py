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

    def __init__(self, style: Literal["white", "dark", "whitegrid", "darkgrid", "ticks"] = "whitegrid"):
        """
        Initialize the graph generator.

        Args:
            style: Seaborn style to use for graphs
        """
        sns.set_style(style)
        plt.style.use("seaborn-v0_8")

    def _smooth_data(self, x_data: list, y_data: list, smoothing_factor: float = 1.0) -> tuple[list, list]:
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
            x_numeric = [x.timestamp() if hasattr(x, 'timestamp') else float(x) for x in x_data]
            
            # Apply gaussian smoothing to y data
            y_smoothed = gaussian_filter1d(y_data, sigma=smoothing_factor)
            
            # Create more points for smoother curves if we have enough data
            if len(x_data) >= 5:
                # Create interpolation function
                f = interp1d(x_numeric, y_smoothed, kind='cubic', bounds_error=False, fill_value=0)
                
                # Generate more x points for smoother curve
                x_new_numeric = np.linspace(min(x_numeric), max(x_numeric), len(x_data) * 3)
                y_new = f(x_new_numeric)
                
                # Convert back to datetime if needed
                if hasattr(x_data[0], 'timestamp'):
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

            # Generate top channels over time graph
            file_path = self.generate_top_channels_over_time_graph(
                data, str(output_path / f"{prefix}_top_channels_over_time.png"), smooth=False
            )
            if file_path:
                generated_files.append(file_path)

            # Generate top reactions over time graph
            file_path = self.generate_top_reactions_over_time_graph(
                data, str(output_path / f"{prefix}_top_reactions_over_time.png"), smooth=False
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
        self, data: MessageStatisticsData, output_path: Optional[str] = None, smooth: bool = True
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
            x_smooth, y_smooth = self._smooth_data(df["date"].tolist(), df["messages"].tolist(), smoothing_factor=1.5)
            plt.plot(x_smooth, y_smooth, linewidth=3, alpha=0.8, label="Smoothed trend")
            plt.plot(df["date"], df["messages"], marker="o", linewidth=1, markersize=3, alpha=0.6, label="Daily data")
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
        top_n: int = 5,
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
                x_smooth, y_smooth = self._smooth_data(dates, cumulative_counts, smoothing_factor=1.5)
                plt.plot(x_smooth, y_smooth, linewidth=3, label=f"{display_name} ({total_count} total)", alpha=0.8)
            else:
                plt.plot(mdates.date2num(dates), cumulative_counts, marker="o", linewidth=2, markersize=3, label=f"{display_name} ({total_count} total)")

        # Formatting
        plt.title(f"Top {top_n} Channels - Cumulative Messages Over Time", fontsize=16, fontweight="bold")
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
        top_n: int = 5,
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
                emoji_char = emoji[0] if emoji else '?'
                emoji_name = unicodedata.name(emoji_char).lower().replace('_', ' ')
                # Capitalize the name for better display
                emoji_name = emoji_name.title()
            except (ValueError, TypeError):
                emoji_name = f"Emoji {ord(emoji[0]) if emoji else 0}"
                
            # Apply smoothing if requested and we have enough data points
            if smooth and len(dates) > 2:
                x_smooth, y_smooth = self._smooth_data(dates, cumulative_counts, smoothing_factor=1.5)
                plt.plot(x_smooth, y_smooth, linewidth=3, label=f"{emoji_name} ({total_count} total)", alpha=0.8)
            else:
                plt.plot(mdates.date2num(dates), cumulative_counts, marker="o", linewidth=2, markersize=3, label=f"{emoji_name} ({total_count} total)")

        # Formatting
        plt.title(f"Top {top_n} Reactions - Cumulative Usage Over Time", fontsize=16, fontweight="bold")
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
