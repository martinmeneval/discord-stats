from datetime import datetime, timedelta

from pydantic import BaseModel, Field


class StatisticsConfig(BaseModel):
    """Configuration for statistics collection."""

    start_date: datetime = Field(
        default_factory=lambda: datetime.now() - timedelta(weeks=4),
        description="Start date for statistics collection",
    )
    end_date: datetime = Field(
        default_factory=datetime.now, description="End date for statistics collection"
    )

    @property
    def time_range_days(self) -> int:
        """Calculate the number of days in the time range."""
        delta = self.end_date - self.start_date
        return max(1, delta.days)  # Ensure at least 1 day


class BotConfig(BaseModel):
    """Configuration for the Discord bot."""

    token: str = Field(..., description="Discord bot token")
    command_prefix: str = Field("!", description="Command prefix for the bot")
    guild_id: int = Field(None, description="Discord guild/server ID")
    stats_config: StatisticsConfig = Field(default_factory=StatisticsConfig)


class Config(BaseModel):
    """Main configuration for the Discord stats application."""

    bot: BotConfig
