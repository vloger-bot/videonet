import asyncpg
import discord
import classyjson
from typing import Union
from ..exceptions import *
from datetime import datetime
from discord.ext import commands


class Database(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = self.bot.database

    async def populate_cache(self):
        """Repopulates all bot cache"""

        self.bot.cache.prefixes = await self.get_all_prefixes()
        self.bot.cache.emoji_genre, self.bot.cache.genre_emoji = await self.get_all_genres()

    async def get_all_prefixes(self) -> dict:
        """Fetches all guilds' prefixes for cache"""

        guilds = await self.db.fetch("SELECT guild_id, prefix FROM guilds")

        return dict( (guild["guild_id"], guild["prefix"]) for guild in guilds if (guild["prefix"] != self.bot.c.default_prefix and guild["prefix"]) )

    async def get_all_genres(self) -> list:
        """Fetches all genres from the database"""

        genres = await self.db.fetch("SELECT emoji, genre FROM genres")
        emoji_genre = {}
        genre_emoji = {}

        for genre in genres:
            emoji_genre[genre["emoji"]] = genre["genre"]
            genre_emoji[genre["genre"]] = genre["emoji"]

        return emoji_genre, genre_emoji

    async def add_guild(self, guild_id: int, prefix: Union[str, None] = None):
        """Adds a guild to the database"""

        prefix = prefix if prefix else self.bot.c.default_prefix

        guild = await self.get_guild(guild_id)
        if guild:
            raise GuildError("Provided guild already exists!")
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO guilds VALUES ($1, $2, $3)",
                *[guild_id, prefix, 0]
            )

    async def get_guild(self, guild_id: int) -> Union[asyncpg.Record, None]:
        """Fetches a guild from the database"""

        guild = await self.db.fetchrow(
            "SELECT * FROM guilds WHERE guild_id = $1",
            *[guild_id]
        )

        return guild

    async def update_guild_prefix(self, guild_id: int, prefix: str):
        """Updates a guild's prefix in the database"""

        if len(prefix) > 10:
            raise GuildError("Invalid prefix provided!")

        guild = await self.get_guild(guild_id)
        if not guild:
            await self.add_guild(guild_id, prefix)
            self.bot.cache.prefixes[guild_id] = prefix

        async with self.db.acquire() as conn:
            await conn.execute(
                "UPDATE guilds SET prefix = $1 WHERE guild_id = $2",
                *[prefix, guild_id]
            )
            self.bot.cache.prefixes[guild_id] = prefix

    async def remove_guild(self, guild_id: int):
        """Removes a guild from the database"""

        guild = await self.get_guild(guild_id)
        if not guild:
            raise GuildError("Provided guild does not exist!")
            return

        async with self.db.acquire() as conn:
            await conn.execute(
                "DELETE FROM guilds WHERE guild_id = $1",
                *[guild_id]
            )

    async def add_channel(self, user_id: int, name: str, description: str, genre: str):
        """Adds a channel to the database"""

        if len(name) < 3 or len(description) < 25 or len(name) > 32 or len(description) > 200 or genre not in self.bot.cache.genre_emoji.keys():
            raise ChannelError("Invalid channel fields provided")

        async with self.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO channels (user_id, name, description, subscribers, balance, views, genre, created_at) VALUES ($1, $2, $3, 0, 0, 0, $4, $5)",
                *[user_id, name, description, genre, datetime.now()]
            )

    async def get_channel(self, user_id: int) -> asyncpg.Record:
        """Fetches a channel from the database"""

        channel = await self.db.fetchrow(
            "SELECT * FROM channels WHERE user_id = $1",
            *[user_id]
        )

        return channel

    async def edit_name(self, user_id: int, name: str):
        """Edit the channel's name"""

        if len(name) < 3 or len(name) > 32:
            raise ChannelError("Invalid channel fields provided")

        async with self.db.acquire() as conn:
            await conn.execute(
                "UPDATE channels SET name = $1 WHERE user_id = $2",
                *[name, user_id]
            )

    async def edit_description(self, user_id: int, description: str):
        """Edits the channel's description"""

        if len(description) < 25 or len(description) > 200:
            raise ChannelError("Invalid channel fields provided")

        async with self.db.acquire() as conn:
            await conn.execute(
                "UPDATE channels SET description = $1 WHERE user_id = $2",
                *[description, user_id]
            )

    async def edit_genre(self, user_id: int, genre: str):
        """Edits the channel's genre"""

        if genre not in self.bot.cache.genre_emoji.keys():
            raise ChannelError("Invalid channel fields provided")

        async with self.db.acquire() as conn:
            await conn.execute(
                "UPDATE channels SET genre = $1 WHERE user_id = $2",
                *[genre, user_id]
            )

    async def remove_channel(self, user_id: int):
        """Removes a channel from the database"""

        async with self.db.acquire() as conn:
            await conn.execute(
                "DELETE FROM channels WHERE user_id = $1",
                *[user_id]
            )


def setup(bot: commands.Bot):
    bot.add_cog(Database(bot))
