"""Base formatter interfaces for the Discord statistics tool."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import discord

T = TypeVar("T")


class BaseFormatter(Generic[T], ABC):
    """
    Base class for all statistics formatters.

    Formatters are responsible for turning raw statistics data into
    human-readable output, such as Discord messages.
    """

    @abstractmethod
    def format(self, data: T) -> discord.Embed:
        """
        Format the given statistics data into a Discord embed.

        Args:
            data: Statistics data to format

        Returns:
            A Discord embed containing the formatted statistics
        """
        pass


from .message_stats import MessageStatisticsFormatter

__all__ = ["BaseFormatter", "MessageStatisticsFormatter"]
