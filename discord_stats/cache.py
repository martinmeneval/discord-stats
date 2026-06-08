"""SQLite-backed message cache for Discord statistics.

Stores every fetched Discord message so that subsequent runs can skip
re-fetching channels (or date ranges) that are already cached.
"""

import logging
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    message_id   INTEGER PRIMARY KEY,
    guild_id     INTEGER NOT NULL,
    channel_id   INTEGER NOT NULL,
    channel_name TEXT    NOT NULL,
    is_thread    INTEGER NOT NULL DEFAULT 0,
    author_id    INTEGER NOT NULL,
    author_name  TEXT    NOT NULL,
    author_username TEXT NOT NULL,
    is_bot       INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL,
    image_count  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reactions (
    message_id INTEGER NOT NULL,
    emoji      TEXT    NOT NULL,
    count      INTEGER NOT NULL,
    PRIMARY KEY (message_id, emoji)
);

CREATE INDEX IF NOT EXISTS idx_msg_guild_channel_date
    ON messages (guild_id, channel_id, created_at);
CREATE INDEX IF NOT EXISTS idx_msg_guild_date
    ON messages (guild_id, created_at);
"""


@dataclass(slots=True)
class CachedMessage:
    """Lightweight representation of a cached message row."""

    message_id: int
    guild_id: int
    channel_id: int
    channel_name: str
    is_thread: bool
    author_id: int
    author_name: str
    author_username: str
    is_bot: bool
    created_at: str  # ISO-8601 date-only (YYYY-MM-DD)
    image_count: int
    reactions: list[tuple[str, int]]  # [(emoji, count), ...]


class MessageCache:
    """Thin wrapper around a SQLite database for message caching."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info(f"Message cache opened: {db_path}")

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_newest_timestamp(self, guild_id: int, channel_id: int) -> datetime | None:
        """Return the *created_at* of the newest cached message in a channel.

        Always returns a naive (UTC) datetime so callers can safely compare
        with the naive datetimes produced by the CLI date parser.
        """
        row = self._conn.execute(
            "SELECT MAX(created_at) FROM messages WHERE guild_id=? AND channel_id=?",
            (guild_id, channel_id),
        ).fetchone()
        if row and row[0]:
            dt = datetime.fromisoformat(row[0])
            return dt.replace(tzinfo=None)
        return None

    def has_messages_before(
        self, guild_id: int, channel_id: int, before: datetime
    ) -> bool:
        """Check whether the cache contains *any* message before *before*."""
        row = self._conn.execute(
            "SELECT 1 FROM messages WHERE guild_id=? AND channel_id=? AND created_at<? LIMIT 1",
            (guild_id, channel_id, before.isoformat()),
        ).fetchone()
        return row is not None

    def iter_messages(
        self,
        guild_id: int,
        channel_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Iterator[CachedMessage]:
        """Yield cached messages for *channel_id* in ``[start_date, end_date)``."""
        cur = self._conn.execute(
            """
            SELECT m.message_id, m.guild_id, m.channel_id, m.channel_name,
                   m.is_thread, m.author_id, m.author_name, m.author_username,
                   m.is_bot, m.created_at, m.image_count
              FROM messages m
             WHERE m.guild_id=? AND m.channel_id=? AND m.created_at>=? AND m.created_at<?
             ORDER BY m.created_at
            """,
            (guild_id, channel_id, start_date.isoformat(), end_date.isoformat()),
        )
        for r in cur:
            msg_id = r[0]
            rxns = self._conn.execute(
                "SELECT emoji, count FROM reactions WHERE message_id=?", (msg_id,)
            ).fetchall()
            yield CachedMessage(
                message_id=msg_id,
                guild_id=r[1],
                channel_id=r[2],
                channel_name=r[3],
                is_thread=bool(r[4]),
                author_id=r[5],
                author_name=r[6],
                author_username=r[7],
                is_bot=bool(r[8]),
                created_at=r[9],
                image_count=r[10],
                reactions=rxns,
            )

    def get_pre_period_counts(
        self, guild_id: int, channel_id: int, before: datetime
    ) -> tuple[int, Counter[str], Counter[str]]:
        """
        Return aggregate pre-period counts from cache for one channel.

        Returns:
            (channel_msg_count, author_counts, reaction_counts)
        """
        # Channel total
        row = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE guild_id=? AND channel_id=? AND created_at<? AND is_bot=0",
            (guild_id, channel_id, before.isoformat()),
        ).fetchone()
        channel_count: int = row[0] if row else 0

        # Per-author
        author_counts: Counter[str] = Counter()
        for r in self._conn.execute(
            "SELECT author_name, COUNT(*) FROM messages "
            "WHERE guild_id=? AND channel_id=? AND created_at<? AND is_bot=0 "
            "GROUP BY author_name",
            (guild_id, channel_id, before.isoformat()),
        ):
            author_counts[r[0]] = r[1]

        # Per-reaction
        reaction_counts: Counter[str] = Counter()
        for r in self._conn.execute(
            "SELECT rx.emoji, SUM(rx.count) FROM reactions rx "
            "JOIN messages m ON rx.message_id = m.message_id "
            "WHERE m.guild_id=? AND m.channel_id=? AND m.created_at<? AND m.is_bot=0 "
            "GROUP BY rx.emoji",
            (guild_id, channel_id, before.isoformat()),
        ):
            reaction_counts[r[0]] = int(r[1])

        return channel_count, author_counts, reaction_counts

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def cache_message(
        self,
        *,
        message_id: int,
        guild_id: int,
        channel_id: int,
        channel_name: str,
        is_thread: bool,
        author_id: int,
        author_name: str,
        author_username: str,
        is_bot: bool,
        created_at: str,
        image_count: int,
        reactions: list[tuple[str, int]],
    ) -> None:
        """Insert or replace a single message (and its reactions) in the cache."""
        self._conn.execute(
            "INSERT OR REPLACE INTO messages "
            "(message_id, guild_id, channel_id, channel_name, is_thread, "
            " author_id, author_name, author_username, is_bot, created_at, image_count) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                message_id,
                guild_id,
                channel_id,
                channel_name,
                int(is_thread),
                author_id,
                author_name,
                author_username,
                int(is_bot),
                created_at,
                image_count,
            ),
        )
        if reactions:
            self._conn.executemany(
                "INSERT OR REPLACE INTO reactions (message_id, emoji, count) VALUES (?,?,?)",
                [(message_id, emoji, count) for emoji, count in reactions],
            )

    def flush(self) -> None:
        """Commit pending writes."""
        self._conn.commit()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Commit and close the database connection."""
        try:
            self._conn.commit()
            self._conn.close()
            logger.info(f"Message cache closed: {self._db_path}")
        except Exception as exc:
            logger.warning(f"Error closing message cache: {exc}")
