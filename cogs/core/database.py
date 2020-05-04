import math
import string
import random
import asyncpg
from datetime import datetime, timedelta
from discord.ext import commands, tasks


class Database(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

        self.update_videos.start()

        bot.algorithm = {
            'fail': {
                'views': {
                    1: 8,
                    2: 20,
                    3: 10,
                    4: 10,
                    5: 10,
                    6: 5,
                    7: 5,
                    8: 5,
                    9: 5,
                    10: 5,
                    11: 5
                },
                'subscribers': -30,
                'stats': {
                    'likes': [1, 3],
                    'dislikes': [5, 7]
                }
            },

            'poor': {
                'views': {
                    1: 2,
                    2: 30,
                    3: 20,
                    4: 20,
                    5: 20,
                    6: 10,
                    7: 5,
                    8: 5,
                    9: 5,
                    10: 5,
                    11: 5
                },
                'subscribers': 10,
                'stats': {
                    'likes': [2, 4],
                    'dislikes': [2, 4]
                }
            },

            'average': {
                'views': {
                    1: 15,
                    2: 30,
                    3: 20,
                    4: 20,
                    5: 20,
                    6: 10,
                    7: 5,
                    8: 5,
                    9: 5,
                    10: 5,
                    11: 5
                },
                'subscribers': 15,
                'stats': {
                    'likes': [3, 5],
                    'dislikes': [1, 3]
                }
            },

            'good': {
                'views': {
                    1: 20,
                    2: 40,
                    3: 30,
                    4: 20,
                    5: 10,
                    6: 10,
                    7: 5,
                    8: 5,
                    9: 5,
                    10: 5,
                    11: 5
                },
                'subscribers': 20,
                'stats': {
                    'likes': [8, 10],
                    'dislikes': [1, 3]
                }
            },

            'trending': {
                'views': {
                    1: 10000,
                    2: 10,
                    3: 10,
                    4: 8,
                    5: 8,
                    6: 5,
                    7: 3,
                    8: 3,
                    9: 3,
                    10: 3,
                    11: 3
                },
                'subscribers': 10,
                'stats': {
                    'likes': [8, 10],
                    'dislikes': [1, 3]
                }
            }
        }

    async def check_banned(self, user_id):

        bans = await self.db.fetch("SELECT * FROM bans WHERE user_id = $1",
                                   user_id)

        if bans:
            return True
        else:
            return False

    async def check_award(self, ctx, channel):

        if 100000 <= channel.get('subscribers') < 1000000:
            award = 'silver'
        elif 1000000 <= channel.get('subscribers') < 10000000:
            award = 'gold'
        elif 10000000 <= channel.get('subscribers') < 100000000:
            award = 'diamond'
        elif 100000000 < channel.get('subscribers'):
            award = 'ruby'
        else:
            return

        awards = await self.db.fetch("SELECT award FROM awards WHERE channel_id = $1",
                                     channel.get('channel_id'))
        if award in awards:
            return

        async with self.db.acquire() as conn:

            await self.db.execute("INSERT INTO awards (channel_id, award) VALUES ($1, $2)",
                                  channel.get('channel_id'), award)

            await ctx.send(f':tada: **<@{ctx.author.id}> just got the :{award}_play_button: {award} play button!**')

        return

    async def on_vote(self, user_id, is_weekend):

        user = await self.db.fetchrow('SELECT * FROM users WHERE user_id = $1',
                                      user_id)
        if not user:
            return 'User doesn\'t exist'

        money = user[1]

        if is_weekend:
            added_money = math.ceil(8 * money / 100)
            money += added_money
        elif not is_weekend:
            added_money = math.ceil(5 * money / 100)
            money += added_money

        if added_money == 0:
            added_money += random.randint(1, 4)
            money += added_money

        async with self.db.acquire() as conn:

            await conn.execute("UPDATE users SET money = $1 WHERE user_id = $2",
                               money, user_id)

            await conn.execute("INSERT INTO votes (user_id, timestamp) VALUES ($1, $2)",
                               user_id, datetime.now())

        return [money, added_money]

    async def buy_decent_ad(self, ctx, user_id, channel_id):

        user = await self.get_user(user_id)
        user_money = user[1]

        channel = await self.get_channel(channel_id)
        subscribers = channel[0][4]
        cost = 2 * subscribers

        if cost > user_money:
            return 'Not enough money'

        subscriber_percentage = random.randint(8, 15)

        new_subscribers = math.ceil(subscriber_percentage * subscribers / 100)
        new_user_money = math.ceil(user_money - cost)
        subscribers += new_subscribers

        async with self.db.acquire() as conn:

            await self.db.execute("UPDATE channels SET subscribers = $1 WHERE channel_id = $2",
                                  subscribers, channel_id)

            await self.db.execute("UPDATE users SET money = $1 WHERE user_id = $2",
                                  new_user_money, user_id)

        return {'new_subs': new_subscribers, 'cost': cost}

    async def buy_average_ad(self, ctx, user_id, channel_id):

        user = await self.get_user(user_id)
        user_money = user[1]

        channel = await self.get_channel(channel_id)
        subscribers = channel[0][4]

        if subscribers > user_money:
            return 'Not enough money'

        subscriber_percentage = random.randint(3, 8)

        new_subscribers = math.ceil(subscriber_percentage * subscribers / 100)
        new_user_money = math.ceil(user_money - subscribers)
        cost = user_money - new_user_money
        subscribers += new_subscribers

        async with self.db.acquire() as conn:

            await self.db.execute("UPDATE channels SET subscribers = $1 WHERE channel_id = $2",
                                  subscribers, channel_id)

            await self.db.execute("UPDATE users SET money = $1 WHERE user_id = $2",
                                  new_user_money, user_id)

        data_channel = {
            'channel_id': channel_id,
            'subscribers': subscribers}

        await self.check_award(ctx, data_channel)

        return {'new_subs': new_subscribers, 'cost': cost}

    async def buy_subbot(self, ctx, user_id, channel_id, amount):

        user = await self.get_user(user_id)
        user_money = user[1]

        channel = await self.get_channel(channel_id)
        subscribers = channel[0][4]

        cost = amount * 5

        if cost > user_money:
            return 'Not enough money'

        subscribers += amount
        new_user_money = user_money - cost

        async with self.db.acquire() as conn:

            await self.db.execute("UPDATE channels SET subscribers = $1 WHERE channel_id = $2",
                                  subscribers, channel_id)

            await self.db.execute("UPDATE users SET money = $1 WHERE user_id = $2",
                                  new_user_money, user_id)

        data_channel = {
            'channel_id': channel_id,
            'subscribers': subscribers}

        await self.check_award(ctx, data_channel)

        return {'new_subs': amount, 'cost': cost}

    async def add_channel(self, user_id, name, description, category):

        async with self.db.acquire() as conn:
            user = await self.bot.db.fetch(
                "SELECT * FROM users WHERE user_id = $1",
                user_id,)
            if not user:
                await conn.execute(
                    "INSERT INTO users (user_id, money) VALUES ($1, $2)",
                    user_id, 0)

            channels = await self.get_channel(user_id)

            if not channels == "Channel doesn't exist":
                for channel in channels:
                    if channel[2].lower() == name.lower():
                        return 'Channel with same name exists'

            await conn.execute(
                "INSERT INTO channels (user_id, name, description, subscribers, "
                "total_views, category, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                user_id, name, description, 0, 0, category, datetime.today())

        return 'Successful'

    async def add_ban(self, user_id):

        async with self.db.acquire() as conn:

            await conn.execute("INSERT INTO bans (user_id) VALUES ($1)",
                               user_id)

    async def add_subscriber(self, user_id, channel_id):

        async with self.db.acquire() as conn:

            subscribed = await self.db.fetch("SELECT * FROM subscribers WHERE subscriber = $1 AND channel = $2",
                                             user_id, channel_id)

            if subscribed:
                return 'Already subscribed to this user'

            channels = await self.get_channel(user_id)
            channelids = []
            if channels != 'Channel doesn\'t exist':
                for channel in channels:
                    channelids.append(channel[1])

                if channel_id in channelids:
                    return 'You cannot subscribe to your own channels.'

            await conn.execute("INSERT INTO subscribers (subscriber, channel) VALUES ($1, $2)",
                               user_id, channel_id)

    async def remove_subscriber(self, user_id, channel_id):

        async with self.db.acquire() as conn:

            status = await self.db.fetch("SELECT * FROM subscribers WHERE subscriber = $1 AND channel = $2",
                                         user_id, channel_id)
            if not status:
                return 'Subscription doesn\'t exist'

            await conn.execute("DELETE FROM subscribers WHERE subscriber = $1 AND channel = $2",
                               user_id, channel_id)

    async def remove_ban(self, user_id):

        async with self.db.acquire() as conn:

            await conn.execute("DELETE FROM bans WHERE user_id = $1",
                               user_id)

    async def remove_channel(self, user_id, cid):

        async with self.db.acquire() as conn:

            await conn.execute("DELETE FROM channels WHERE channel_id = $1 AND user_id = $2",
                               cid, user_id)

    async def add_guild(self, guild):

        async with self.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO guilds (guild_id, prefix) VALUES ($1, $2)",
                guild.id, '-')

    async def get_channel(self, query_id):

        if isinstance(query_id, int):
            if len(str(query_id)) >= 15:  # Provided id is a a discord snowflake.
                channel = await self.db.fetch(
                    "SELECT * FROM channels WHERE user_id = $1 ORDER BY channel_id",
                    query_id)
                if channel:
                    return channel
                else:
                    return "Channel doesn't exist"

            else:  # Provided id is a channel id.
                channel = await self.db.fetch(
                    "SELECT * FROM channels WHERE channel_id = $1 ORDER BY channel_id",
                    query_id)
                if channel:
                    return channel
                else:
                    return "Channel doesn't exist"
        else:
            raise TypeError(f'Expected int, received {type(query_id)}')

    async def get_leaderboard(self, by):

        leaderboard = await self.db.fetch(
            "SELECT user_id, name, subscribers, total_views FROM channels "
            f"ORDER BY {by} DESC LIMIT 10")

        return leaderboard

    async def get_user_leaderboard(self):

        leaderboard = await self.db.fetch(
            "SELECT user_id, money FROM users "
            f"ORDER BY money DESC LIMIT 10")

        return leaderboard

    async def get_subscribed(self, user_id):

        channels = await self.db.fetch("SELECT * FROM subscribers WHERE subscriber = $1",
                                       user_id)
        return channels

    async def get_subscribers(self, channel_id):

        subscribers = await self.db.fetch("SELECT * FROM subscribers WHERE channel = $1",
                            channel_id)
        return subscribers

    async def get_channels_count(self):

        length = await self.db.fetchrow("SELECT COUNT(*) FROM channels")

        return length[0]

    async def get_all_videos(self, cid, amount):

        videos = await self.db.fetch(
            "SELECT * FROM videos WHERE channel_id = $1 "
            "ORDER BY uploaded_at DESC LIMIT $2",
            cid, amount)

        if not videos:
            return 'No videos'

        return videos

    async def get_video(self, cid, name):

        videos = await self.db.fetch(
            "SELECT * FROM videos WHERE channel_id = $1 AND name LIKE $2",
            cid, name)

        if not videos:
            return 'No videos'

        return videos

    async def get_user(self, user_id):

        user = await self.db.fetchrow('SELECT * FROM users WHERE user_id = $1',
                                      user_id)
        if not user:
            return 'User doesn\'t exist'
        return user

    async def get_prefix(self, guild):

        prefix = await self.db.fetchrow(
            "SELECT prefix FROM guilds WHERE guild_id = $1",
            guild.id)

        if not prefix:
            return '-'
        return prefix

    async def set_prefix(self, guild, prefix):

        async with self.db.acquire() as conn:
            c_prefix = await self.db.fetchrow(
                "SELECT prefix FROM guilds WHERE guild_id = $1",
                guild.id, )
            if not c_prefix:
                await conn.execute(
                    "INSERT INTO guilds (guild_id, prefix) VALUES ($1, $2)",
                    guild.id, prefix)
                return prefix
            else:
                await conn.execute(
                    "UPDATE guilds SET prefix = $1 WHERE guild_id = $2",
                    prefix, guild.id)

        return prefix

    async def set_description(self, cid, description):

        async with self.db.acquire() as conn:

            await conn.execute("UPDATE channels SET description = $1 WHERE channel_id = $2",
                               description, cid)

    async def set_channel_name(self, cid, name):

        async with self.db.acquire() as conn:

            await conn.execute("UPDATE channels SET name = $1 WHERE channel_id = $2",
                               name, cid)

    async def set_vote_reminder(self, user_id, status):

        already_active = await self.db.fetchrow("SELECT vote_reminder FROM users WHERE user_id = $1",
                                                user_id)
        already_active = already_active[0]
        if already_active == status:
            return 'Already active'

        last_vote = await self.db.fetchrow(
            "SELECT timestamp FROM votes WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 1",
            user_id)
        if not last_vote:
            last_vote = datetime.now()

        async with self.db.acquire() as conn:

            await conn.execute("UPDATE users SET vote_reminder = $1, last_reminded = $2 WHERE user_id = $3",
                               status, last_vote, user_id)

        return True

    async def upload_video(self, ctx, user_id, channel, name, description):

        choices = ['fail', 'poor', 'average', 'good', 'trending']
        status = random.choices(choices, weights=[15, 20, 50, 14.9999, 0.0001])[0]

        channel_data = await self.db.fetchrow(
            "SELECT channel_id, name, subscribers, total_views FROM channels WHERE user_id = $1 AND channel_id = $2",
            user_id, channel)

        total_money = await self.db.fetchrow(
            "SELECT money FROM users WHERE user_id = $1",
            user_id)

        total_money = total_money[0]

        channel_id = int(channel_data[0])
        channel_name = channel_data[1]
        subscribers = int(channel_data[2])
        total_views = int(channel_data[3])

        last_percentage = 1

        views = math.ceil(self.bot.algorithm[status]['views'][last_percentage] * subscribers / 100)

        if subscribers > 1000:
            money = 1 * views / 10
            money = math.ceil(money)
        else:
            money = 0

        total_money += money
        total_money = math.ceil(total_money)

        new_subscribers = math.ceil(self.bot.algorithm[status]['subscribers'] * views / 100)

        likes = random.randint(
            self.bot.algorithm[status]['stats']['likes'][0],
            self.bot.algorithm[status]['stats']['likes'][1]) * views / 100
        dislikes = random.randint(
            self.bot.algorithm[status]['stats']['dislikes'][0],
            self.bot.algorithm[status]['stats']['dislikes'][1]
        ) * views / 100

        if subscribers < 20:
            status = 'average'
            new_subscribers = random.randint(5, 10)
            views = math.ceil(80 * new_subscribers / 100)
            likes = math.ceil(20 * views / 100)
            dislikes = math.ceil(10 * views / 100)

        total_views += views
        subscribers += new_subscribers

        async with self.db.acquire() as conn:
            await conn.execute(
                "INSERT INTO videos (channel_id, name, description, status, new_subs, views, "
                "likes, dislikes, last_percentage, last_updated, uploaded_at, money) VALUES ($1, $2, $3, "
                "$4, $5, $6, $7, $8, $9, $10, $11, $12)",
                channel_id, name, description, status, new_subscribers, views, likes, dislikes,
                last_percentage, datetime.now(), datetime.today(), money)

            await conn.execute(
                "UPDATE channels SET subscribers = $1, total_views = $2 WHERE channel_id = $3",
                subscribers, total_views, channel_id)

            await conn.execute(
                "UPDATE users SET money = $1 WHERE user_id = $2",
                total_money, user_id)

        data_channel = {
            'channel_id': channel_id,
            'subscribers': subscribers}

        await self.check_award(ctx, data_channel)

        return {'status': status,
                'channel': channel_name,
                'new_subs': new_subscribers,
                'money': money,
                'views': views,
                'likes': likes,
                'dislikes': dislikes}

    @tasks.loop(minutes=10)
    async def update_videos(self):
        try:

            videos = await self.db.fetch("SELECT * FROM videos WHERE now() - last_updated > make_interval(hours := 12) "
                                         "AND last_percentage < 10")

            for video in videos:

                video_id = video[0]
                channel_id = video[1]
                name = video[2]
                description = video[3]
                status = video[4]
                new_subscribers = video[5]
                views = video[6]
                likes = video[7]
                dislikes = video[8]
                last_percentage = video[9]
                last_updated = video[10]
                uploaded_at = video[11]
                money = video[12]

                if last_percentage == 10:
                    continue

                last_percentage += 1
                status = status.lower()

                channel_data = await self.db.fetchrow(
                    "SELECT user_id, subscribers, total_views FROM channels WHERE channel_id = $1",
                    channel_id)

                user_id = int(channel_data[0])
                subscribers = int(channel_data[1])
                total_views = int(channel_data[2])

                total_money = await self.db.fetchrow(
                    "SELECT money FROM users WHERE user_id = $1",
                    user_id)

                total_money = total_money[0]

                if subscribers < 20:
                    continue

                new_views = math.ceil(self.bot.algorithm[status]['views'][last_percentage] * views / 100)
                views += new_views

                if subscribers > 1000:
                    new_money = math.ceil(new_views / 10)
                    money += new_money
                    total_money += new_money

                    money = math.ceil(money)
                    total_money = math.ceil(total_money)

                new_subscribers = math.ceil(self.bot.algorithm[status]['subscribers'] * views / 100)

                likes = math.ceil(random.randint(
                    self.bot.algorithm[status]['stats']['likes'][0],
                    self.bot.algorithm[status]['stats']['likes'][1]) * views / 100)
                dislikes = math.ceil(random.randint(
                    self.bot.algorithm[status]['stats']['dislikes'][0],
                    self.bot.algorithm[status]['stats']['dislikes'][1]
                ) * views / 100)

                subscribers += new_subscribers
                total_views += views

                async with self.db.acquire() as conn:
                    await conn.execute(
                        "UPDATE videos SET new_subs = $1, views = $2, likes = $3, "
                        "dislikes = $4, last_percentage = $5, last_updated = $6, money = $7 "
                        "WHERE video_id = $8",
                        new_subscribers, views, likes, dislikes, last_percentage, datetime.now(), money, video_id)

                    await conn.execute(
                        "UPDATE channels SET subscribers = $1, total_views = $2 WHERE channel_id = $3",
                        subscribers, total_views, channel_id)

                    await conn.execute("UPDATE users SET money = $1 WHERE user_id = $2",
                                       total_money, user_id)

        except Exception as e:
            print(e)

    @tasks.loop(minutes=10)
    async def remind_voters(self):

        users = await self.db.fetch("SELECT * FROM votes WHERE now() - timestamp > make_interval(hours := 12) ")

        for user in users:

            await self.db.fetchrow("SELECT * FROM users WHERE user_id = $1",
                                   user[0])

            if user[2] and (datetime.now() - user[3]) > timedelta(hours=12):

                user_object = self.bot.get_user(user[0])
                if not user_object:
                    continue

                if datetime.today().weekday() == 5 or datetime.today().weekday() == 6:
                    message = f'{self.bot.heartbeat} **Hey! It\'s been 12 hours since you last upvoted **vidio**! ' \
                              f'You don\'t want to miss out today, it\'s a weekend, so vote prizes are doubled!'
                else:
                    message = f'{self.bot.heartbeat} **Hey! It\'s been 12 hours since you last upvoted **vidio**! ' \
                              f'Upvote the bot and get some cool prizes!'
                await user_object.send(message)

                async with self.db.acquire() as conn:

                    conn.execute("UPDATE users SET last_reminded = $1 WHERE user_id = $2",
                                 datetime.now(), user[0])

    @update_videos.before_loop
    async def before_updating(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Database(bot))
