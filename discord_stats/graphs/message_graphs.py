"""Graph generator for message statistics."""

import colorsys
import logging
import unicodedata
from collections.abc import Callable
from datetime import datetime as dt
from pathlib import Path
from typing import Literal, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.axes import Axes
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

        # Use fonts with broad Unicode coverage (CJK, accents, emoji in names, etc.)
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [
            "Arial Unicode MS",   # macOS – full Unicode incl. CJK
            "Segoe UI",           # Windows – broad Unicode
            "Noto Sans CJK JP",   # Linux / installed Noto
            "Noto Sans",
            "MS Gothic",          # Windows – CJK fallback
            "DejaVu Sans",        # matplotlib default (limited CJK)
        ]
        plt.rcParams["axes.unicode_minus"] = False

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _save_or_show(output_path: Optional[str], log_msg: str) -> Optional[str]:
        """Save the current figure to *output_path* or show interactively."""
        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches="tight")
            logger.info(f"{log_msg} saved to {output_path}")
            plt.close()
            return output_path
        else:
            plt.show()
            return None

    @staticmethod
    def _format_date_axis(
        ax: Axes,
        n_dates: int,
        *,
        use_auto: bool = False,
    ) -> None:
        """Apply common date-axis formatting to *ax*."""
        if use_auto:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        else:
            ax.xaxis.set_major_locator(
                mdates.DayLocator(interval=max(1, n_dates // 10))
            )
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

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

    def _generate_multi_series_line_graph(
        self,
        items: list[tuple[str, int, dict[str, int]]],
        data: MessageStatisticsData,
        *,
        title: str,
        ylabel: str,
        log_msg: str,
        output_path: Optional[str] = None,
        smooth: bool = True,
        weekly: bool = False,
        cumulative: bool = False,
        display_name_fn: Callable[[str], str] | None = None,
        pre_period_fn: Callable[[str], int] | None = None,
        figsize: tuple[int, int] = (14, 8),
        legend_kwargs: dict | None = None,
    ) -> Optional[str]:
        """
        Shared implementation for multi-series line graphs (cumulative and weekly).

        Args:
            items: List of (name, total_count, daily_data) tuples.
            data: The statistics data object (used for date range).
            title: Graph title.
            ylabel: Y-axis label.
            log_msg: Prefix for the log message on save.
            output_path: Path to save the graph (optional).
            smooth: Whether to apply smoothing.
            weekly: Aggregate daily data into weekly buckets.
            cumulative: Plot cumulative sums instead of raw counts.
            display_name_fn: Maps item name → display label (default: identity).
            pre_period_fn: Maps item name → pre-period offset for cumulative graphs.
            figsize: Figure size.
            legend_kwargs: Extra kwargs passed to plt.legend().
        """
        if not items or not data.start_date or not data.end_date:
            logger.warning(f"Insufficient data for {log_msg}")
            return None

        all_dates = data.get_all_dates_in_range()
        plt.figure(figsize=figsize)

        for i, (name, total_count, daily_data) in enumerate(items):
            color = self._LINE_COLORS[i % len(self._LINE_COLORS)]
            if weekly:
                agg = data.get_weekly_data(daily_data)
                if not agg:
                    continue
                sorted_keys = sorted(agg.keys())
                dates = [dt.fromisoformat(k) for k in sorted_keys]
                counts = [agg[k] for k in sorted_keys]
            else:
                dates = [dt.fromisoformat(d) for d in all_dates]
                counts = [daily_data.get(d, 0) for d in all_dates]

            if cumulative:
                offset = pre_period_fn(name) if pre_period_fn else 0
                running = offset
                cum: list[int] = []
                for c in counts:
                    running += c
                    cum.append(running)
                counts = cum

            display = display_name_fn(name) if display_name_fn else name
            # Matplotlib silently hides labels starting with '_'
            if display.startswith("_"):
                display = "\u200B" + display
            label = f"{display} ({total_count} total)"

            if smooth and len(dates) > 2:
                sigma = 1.0 if weekly else 1.5
                x_s, y_s = self._smooth_data(dates, counts, smoothing_factor=sigma)
                plt.plot(x_s, y_s, linewidth=3, alpha=0.8, label=label, color=color)
            else:
                if cumulative and not weekly:
                    plt.plot(
                        mdates.date2num(dates), counts,
                        marker="o", linewidth=2, markersize=3, label=label, color=color,
                    )
                else:
                    plt.plot(
                        dates, counts,
                        marker="o", linewidth=2, markersize=4, label=label, color=color,
                    )

        plt.title(title, fontsize=16, fontweight="bold")
        plt.xlabel("Week" if weekly else "Date", fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        lkw = legend_kwargs or {}
        plt.legend(**{"loc": "upper left", "frameon": True, "framealpha": 0.9, **lkw})
        plt.grid(True, alpha=0.3)

        ax = plt.gca()
        if cumulative:
            ax.set_yscale("function", functions=(np.sqrt, np.square))
        self._format_date_axis(ax, len(all_dates), use_auto=weekly)

        return self._save_or_show(output_path, log_msg)

    # ------------------------------------------------------------------
    # Colour helpers
    # ------------------------------------------------------------------

    # 12 muted line-graph colours (tab10 hues at reduced saturation / higher
    # lightness so they blend well with the seaborn-v0_8 dark background).
    _LINE_COLORS: list[str] = [
        "#5B9BD5",  # steel blue
        "#ED8B67",  # salmon
        "#6DBE6D",  # sage green
        "#D47DBF",  # orchid
        "#C4A96A",  # tan
        "#9EC4E8",  # powder blue
        "#E8A0CB",  # pink
        "#8FD18F",  # mint
        "#D4B76A",  # gold
        "#A1A1D6",  # lavender
        "#76C9C9",  # teal
        "#E8C48A",  # peach
    ]

    # Brighter base colours for per-pie palettes (tab10-inspired HLS values).
    # Each sub-slice is lightened by 0.035; "Others" is desaturated grey.
    _PIE_BASE_COLORS: list[tuple[float, float, float]] = [
        (214 / 360, 0.48, 0.68),  # Blue
        ( 24 / 360, 0.55, 0.72),  # Orange
        (120 / 360, 0.45, 0.54),  # Green
        (330 / 360, 0.52, 0.60),  # Rose
        ( 45 / 360, 0.52, 0.58),  # Tan
        (190 / 360, 0.50, 0.60),  # Teal
        (280 / 360, 0.52, 0.56),  # Purple
        (  0 / 360, 0.55, 0.64),  # Red
        (160 / 360, 0.48, 0.52),  # Mint
    ]

    def _get_pie_colors(
        self, chart_index: int, channels: list[str]
    ) -> list[tuple[float, float, float]]:
        """
        Generate per-pie slice colours from the base palette.

        The first slice (largest) uses the base lightness; each subsequent main
        slice is lightened by 0.035.  The "Others" slice is desaturated to a
        near-grey.
        """
        h, l_base, s_base = self._PIE_BASE_COLORS[chart_index % len(self._PIE_BASE_COLORS)]
        colors: list[tuple[float, float, float]] = []
        main_idx = 0
        for ch in channels:
            if ch == "Others":
                colors.append(colorsys.hls_to_rgb(h, 0.80, 0.10))
            else:
                l = min(l_base + main_idx * 0.035, 0.84)
                colors.append(colorsys.hls_to_rgb(h, l, s_base))
                main_idx += 1
        return colors

    @staticmethod
    def _emoji_display_name(emoji_str: str) -> str:
        """
        Return a human-readable display name for an emoji without rendering
        the glyph character (avoids 'missing from font' warnings).

        Custom Discord emoji  →  'emoji_name'
        Unicode emoji         →  full Unicode name, title-cased
        """
        if emoji_str.startswith("<") and ":" in emoji_str:
            # '<:name:123>' or '<a:name:123>'
            parts = emoji_str.strip("<>").split(":")
            name = parts[1] if len(parts) >= 2 else emoji_str
            return name.replace("_", " ")

        try:
            # Find first non-ASCII char (skip variation selectors)
            char = next(c for c in emoji_str if ord(c) > 0xFF)
            return unicodedata.name(char).title()
        except (StopIteration, ValueError):
            return emoji_str[:15]

    def _generate_channel_color_map(
        self, all_channel_names: list[str], data: Optional[MessageStatisticsData] = None
    ) -> dict[str, tuple[float, ...]]:
        """
        Generate a consistent color mapping for channels, prioritizing most popular channels.

        Args:
            all_channel_names: List of all unique channel names to assign colors to
            data: Message statistics data to determine channel popularity

        Returns:
            Dictionary mapping channel names to color tuples
        """
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

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def generate_all_graphs(
        self,
        data: MessageStatisticsData,
        output_dir: str = ".",
        prefix: str = "discord_stats",
        smooth: bool = True,
        history_offset: bool = False,
    ) -> list[str]:
        """
        Generate all available graphs and save them to files.

        Args:
            data: Message statistics data
            output_dir: Directory to save graphs
            prefix: Prefix for graph filenames
            smooth: Whether to apply smoothing to line graphs (default: True)
            history_offset: Whether to generate cumulative over-time graphs seeded
                from pre-period counts (default: False)

        Returns:
            List of generated file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        generated_files: list[str] = []

        def _try_generate(func, *args, **kwargs) -> None:
            try:
                result = func(*args, **kwargs)
                if result:
                    generated_files.append(result)
            except Exception as exc:
                logger.error(f"Error generating {func.__name__}: {exc}")

        _try_generate(
            self.generate_messages_per_day_graph,
            data, str(output_path / f"{prefix}_daily_messages.png"), smooth=smooth,
        )

        # Cumulative over-time graphs — only when pre-period data was collected
        if history_offset:
            _try_generate(
                self.generate_top_authors_over_time_graph,
                data, str(output_path / f"{prefix}_cumulative_top_authors.png"), smooth=False,
            )
            _try_generate(
                self.generate_top_channels_over_time_graph,
                data, str(output_path / f"{prefix}_cumulative_top_channels.png"), smooth=False,
            )
            _try_generate(
                self.generate_top_reactions_over_time_graph,
                data, str(output_path / f"{prefix}_cumulative_top_reactions.png"), smooth=False,
            )

        # Weekly line graphs (always generated)
        _try_generate(
            self.generate_top_authors_per_week_graph,
            data, str(output_path / f"{prefix}_weekly_top_authors.png"), smooth=smooth,
        )
        _try_generate(
            self.generate_top_channels_per_week_graph,
            data, str(output_path / f"{prefix}_weekly_top_channels.png"), smooth=smooth,
        )
        _try_generate(
            self.generate_top_reactions_per_week_graph,
            data, str(output_path / f"{prefix}_weekly_top_reactions.png"), smooth=smooth,
        )

        _try_generate(
            self.generate_top_authors_channel_distribution_pies,
            data, str(output_path / f"{prefix}_periodic_author_channel_distribution.png"), top_n=9,
        )
        _try_generate(
            self.generate_daily_activity_heatmap,
            data, str(output_path / f"{prefix}_periodic_daily_activity_heatmap.png"),
        )
        _try_generate(
            self.generate_top_threads_bar_chart,
            data, str(output_path / f"{prefix}_periodic_top_threads.png"),
        )
        _try_generate(
            self.generate_author_share_over_time_graph,
            data, str(output_path / f"{prefix}_periodic_author_share.png"), smooth=smooth,
        )
        _try_generate(
            self.generate_channel_weekday_heatmap,
            data, str(output_path / f"{prefix}_periodic_channel_weekday_heatmap.png"),
        )

        return generated_files

    # ------------------------------------------------------------------
    # Individual graph methods
    # ------------------------------------------------------------------

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

        # Weekly average overlay when smoothing is enabled
        if smooth and len(df) > 2:
            weekly_agg = data.get_weekly_data(data.messages_per_day)
            if weekly_agg:
                sorted_weeks = sorted(weekly_agg.keys())
                week_dates = [dt.fromisoformat(w) for w in sorted_weeks]
                week_counts = [weekly_agg[w] / 7 for w in sorted_weeks]
                plt.plot(week_dates, week_counts, linewidth=3, alpha=0.8, label="Weekly avg")
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
        self._format_date_axis(ax, len(all_dates))

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

        return self._save_or_show(output_path, "Messages per day graph")

    # -- Cumulative over-time graphs (thin wrappers) -------------------

    def generate_top_authors_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a cumulative line graph for the top authors over time."""
        return self._generate_multi_series_line_graph(
            data.get_top_authors_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Authors - Cumulative Messages Over Time",
            ylabel="Cumulative Message Count",
            log_msg="Top authors cumulative graph",
            output_path=output_path,
            smooth=smooth,
            cumulative=True,
            display_name_fn=lambda n: data.messages_per_author_username.get(n, n),
            pre_period_fn=lambda n: data.pre_period_messages_per_author.get(n, 0),
        )

    def generate_top_channels_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a cumulative line graph for the top channels over time."""
        return self._generate_multi_series_line_graph(
            data.get_top_channels_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Channels - Cumulative Messages Over Time",
            ylabel="Cumulative Message Count",
            log_msg="Top channels cumulative graph",
            output_path=output_path,
            smooth=smooth,
            cumulative=True,
            display_name_fn=lambda n: n.replace("#", ""),
            pre_period_fn=lambda n: data.pre_period_messages_per_channel.get(n, 0),
            legend_kwargs={"bbox_to_anchor": (1.05, 1), "loc": "upper left"},
        )

    def generate_top_reactions_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a cumulative line graph for the top reactions over time."""
        return self._generate_multi_series_line_graph(
            data.get_top_reactions_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Reactions - Cumulative Usage Over Time",
            ylabel="Cumulative Reaction Count",
            log_msg="Top reactions cumulative graph",
            output_path=output_path,
            smooth=smooth,
            cumulative=True,
            figsize=(14, 8),
            display_name_fn=self._emoji_display_name,
            pre_period_fn=lambda n: data.pre_period_reactions_count.get(n, 0),
            legend_kwargs={"bbox_to_anchor": (1.02, 1), "loc": "upper left", "fontsize": 9},
        )

    # -- Weekly line graphs (thin wrappers) ----------------------------

    def generate_top_authors_per_week_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a weekly line graph for the top authors."""
        return self._generate_multi_series_line_graph(
            data.get_top_authors_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Authors - Messages Per Week",
            ylabel="Messages Per Week",
            log_msg="Top authors per week graph",
            output_path=output_path,
            smooth=smooth,
            weekly=True,
            display_name_fn=lambda n: data.messages_per_author_username.get(n, n),
        )

    def generate_top_channels_per_week_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a weekly line graph for the top channels."""
        return self._generate_multi_series_line_graph(
            data.get_top_channels_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Channels - Messages Per Week",
            ylabel="Messages Per Week",
            log_msg="Top channels per week graph",
            output_path=output_path,
            smooth=smooth,
            weekly=True,
            figsize=(12, 8),
            display_name_fn=lambda n: n.replace("#", ""),
            legend_kwargs={"bbox_to_anchor": (1.05, 1), "loc": "upper left"},
        )

    def generate_top_reactions_per_week_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """Generate a weekly line graph for the top reactions."""
        return self._generate_multi_series_line_graph(
            data.get_top_reactions_with_daily_data(top_n),
            data,
            title=f"Top {top_n} Reactions - Usage Per Week",
            ylabel="Reactions Per Week",
            log_msg="Top reactions per week graph",
            output_path=output_path,
            smooth=smooth,
            weekly=True,
            display_name_fn=self._emoji_display_name,
            legend_kwargs={"bbox_to_anchor": (1.02, 1), "loc": "upper left", "fontsize": 9},
        )

    # -- Unique graph types --------------------------------------------

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

        return self._save_or_show(output_path, "Daily activity heatmap")

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
            axes = axes.flatten()

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
            sorted_indices = np.argsort(counts)[::-1]
            channels = [channels[i] for i in sorted_indices]
            counts = [counts[i] for i in sorted_indices]
            percentages = [percentages[i] for i in sorted_indices]

            # Keep top 9 channels, collapse the rest into "Others"
            max_channels = 9
            if len(channels) > max_channels:
                others_count = sum(counts[max_channels:])
                others_pct = sum(percentages[max_channels:])
                channels = channels[:max_channels] + ["Others"]
                counts = counts[:max_channels] + [others_count]
                percentages = percentages[:max_channels] + [others_pct]

            # Per-pie earthy palette — each pie has its own base colour
            colors = self._get_pie_colors(chart_index, channels)

            # Format labels as channel names without the # symbol
            labels = [ch if ch == "Others" else ch.replace("#", "") for ch in channels]

            wedges, _, autotexts = ax.pie(
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

    def generate_top_threads_bar_chart(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
    ) -> Optional[str]:
        """
        Generate a horizontal bar chart showing top threads by message count.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top threads to display

        Returns:
            Path to saved file or None if not saved
        """
        if not data.messages_per_thread:
            logger.warning("Insufficient data for top threads bar chart")
            return None

        top_threads = data.messages_per_thread.most_common(top_n)
        if not top_threads:
            return None

        thread_names = [t[0].replace("#", "") for t in top_threads]
        counts = [t[1] for t in top_threads]

        # Reverse so highest bar appears at the top
        thread_names = thread_names[::-1]
        counts = counts[::-1]

        fig, ax = plt.subplots(figsize=(10, max(4, len(thread_names) * 0.6)))
        colors = sns.color_palette("husl", len(thread_names))
        bars = ax.barh(thread_names, counts, color=colors)

        max_count = max(counts) if counts else 1
        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_width() + max_count * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(count),
                va="center",
                fontsize=9,
            )

        ax.set_title(f"Top {top_n} Threads by Message Count", fontsize=16, fontweight="bold")
        ax.set_xlabel("Number of Messages", fontsize=12)
        ax.grid(True, axis="x", alpha=0.3)

        return self._save_or_show(output_path, "Top threads bar chart")

    def generate_author_share_over_time_graph(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
        smooth: bool = True,
    ) -> Optional[str]:
        """
        Generate a 100%-normalised stacked area chart showing each top author's
        weekly share of total server messages.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top authors to include
            smooth: Whether to apply Gaussian smoothing to the area bands (default: True)

        Returns:
            Path to saved file or None if not saved
        """
        top_authors_data = data.get_top_authors_with_daily_data(top_n)
        if not top_authors_data or not data.messages_per_day:
            logger.warning("Insufficient data for author share graph")
            return None

        all_weekly = data.get_weekly_data(data.messages_per_day)
        all_weeks = sorted(all_weekly.keys())
        if len(all_weeks) < 2:
            logger.warning("Too few weeks for author share graph")
            return None

        dates = [dt.fromisoformat(w) for w in all_weeks]
        week_totals = [all_weekly.get(w, 0) for w in all_weeks]

        # Compute per-author weekly share (%)
        author_shares: list[list[float]] = []
        labels: list[str] = []
        for author_name, _, daily_data in top_authors_data:
            weekly = data.get_weekly_data(daily_data)
            shares = [
                (weekly.get(w, 0) / total * 100) if total > 0 else 0.0
                for w, total in zip(all_weeks, week_totals)
            ]
            author_shares.append(shares)
            labels.append(data.messages_per_author_username.get(author_name, author_name))

        # "Others" band = remainder not covered by top authors
        others: list[float] = [
            max(0.0, 100.0 - sum(s[i] for s in author_shares))
            for i in range(len(all_weeks))
        ]

        # Apply Gaussian smoothing if requested (clamp to >= 0)
        if smooth and len(dates) >= 3:
            author_shares = [
                np.clip(gaussian_filter1d(s, sigma=1.0), 0, None).tolist()
                for s in author_shares
            ]
            others = np.clip(gaussian_filter1d(others, sigma=1.0), 0, None).tolist()

        fig, ax = plt.subplots(figsize=(14, 8))
        colors = sns.color_palette("tab10", len(labels))
        ax.stackplot(dates, *author_shares, labels=labels, colors=colors, alpha=0.85)
        ax.stackplot(dates, others, labels=["Others"], colors=["#cccccc"], alpha=0.5)

        ax.set_title(
            f"Top {top_n} Authors - Weekly Message Share",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_xlabel("Week", fontsize=12)
        ax.set_ylabel("Share of Weekly Messages (%)", fontsize=12)
        ax.set_ylim(0, 100)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), framealpha=0.9, fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        plt.xticks(rotation=45)

        return self._save_or_show(output_path, "Author share graph")

    def generate_channel_weekday_heatmap(
        self,
        data: MessageStatisticsData,
        output_path: Optional[str] = None,
        top_n: int = 10,
    ) -> Optional[str]:
        """
        Generate a heatmap showing average message activity per channel by day of week.

        Args:
            data: Message statistics data
            output_path: Path to save the graph (optional)
            top_n: Number of top channels to include

        Returns:
            Path to saved file or None if not saved
        """
        if not data.messages_per_day_per_channel:
            logger.warning("Insufficient data for channel weekday heatmap")
            return None

        top_channels = [ch for ch, _, _ in data.get_top_channels(top_n)]
        if not top_channels:
            return None

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Count how many times each weekday appears in the period (for averaging)
        all_dates = data.get_all_dates_in_range()
        weekday_occurrences = [0] * 7
        for date_str in all_dates:
            weekday_occurrences[dt.fromisoformat(date_str).weekday()] += 1

        # Build pivot: channel -> avg messages per weekday
        pivot: dict[str, list[float]] = {}
        for channel in top_channels:
            daily = data.messages_per_day_per_channel.get(channel, {})
            weekday_totals = [0] * 7
            for date_str, count in daily.items():
                weekday_totals[dt.fromisoformat(date_str).weekday()] += count
            avg = [
                weekday_totals[wd] / weekday_occurrences[wd] if weekday_occurrences[wd] > 0 else 0.0
                for wd in range(7)
            ]
            pivot[channel.replace("#", "")] = avg

        df = pd.DataFrame(pivot, index=day_names).T  # channels as rows, weekdays as columns

        plt.figure(figsize=(10, max(4, len(top_channels) * 0.6)))
        sns.heatmap(
            df,
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            cbar_kws={"label": "Avg messages / day"},
            linewidths=0.5,
        )
        plt.title("Channel Activity by Day of Week", fontsize=16, fontweight="bold")
        plt.xlabel("Day of Week", fontsize=12)
        plt.ylabel("Channel", fontsize=12)

        return self._save_or_show(output_path, "Channel weekday heatmap")
