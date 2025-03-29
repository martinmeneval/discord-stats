"""Base collector interfaces for the Discord statistics tool."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar

from discord.guild import Guild

T = TypeVar("T")


class BaseCollector(Generic[T], ABC):
    """
    Base class for all statistics collectors.

    Collectors are responsible for fetching specific types of statistics
    data from a Discord server within a given date range.
    """

    @abstractmethod
    async def collect(
        self, guild: Guild, start_date: datetime, end_date: datetime
    ) -> T:
        """
        Collect statistics from the specified guild between the given dates.

        Args:
            guild: The Discord guild to collect statistics from
            start_date: The start date for the statistics collection period
            end_date: The end date for the statistics collection period

        Returns:
            Statistics data in a format specific to the collector
        """
        pass
