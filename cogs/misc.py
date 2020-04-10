import asyncio
import discord
import matplotlib.pyplot as mpl
import random
from datetime import datetime
from discord.ext import commands, tasks
from jishaku.paginators import PaginatorInterface

from .utils.config import read, write
from .utils.converters import CustomConverters


class Misc(commands.Cog, name="Secondary"):
    def __init__(self, bot):
        self.bot = bot
        self.update_status.start()
        self.update_stats_data.start()

    @commands.group(name="prefix", case_insensitive=True, invoke_without_command=True, aliases=['prefixes'])
    async def prefix(self, ctx):
        """Get the bot's prefix, change it, or reset it. your choice."""
        data = read('./data/prefixes.json')
        prefixes = data[str(ctx.guild.id)]
        msg = None
        if prefixes:
            msg = '`' + '`, `'.join(prefixes) + '`'
            msg = discord.utils.escape_mentions(msg)
        else:
            msg = "No custom prefixes"
        await ctx.send(str(f"Prefixes:\n{msg}")[:2000])

    @prefix.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def prefix_add(self, ctx, *prefixes: str):
        """Adds prefixes. to have a multi word prefix, put it in "some quotes".
        e.g: b-prefix add a b c "d e" """
        data = read('./data/prefixes.json')
        prefixess = data[str(ctx.guild.id)]
        _p = len(prefixess)
        for prefix in prefixes:
            if prefix in prefixess:
                continue
            else:
                prefixess.append(prefix)
        write('./data/prefixes.json', data)
        if len(prefixess) - _p == 1:
            await ctx.send(f"Added **{len(prefixess) - _p}** prefix.")
        else:
            await ctx.send(f"Added **{len(prefixess) - _p}** prefixes.")

    @prefix.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def prefix_remove(self, ctx, *prefixes: str):
        """removes prefixes. to have a multi word prefix, put it in "some quotes".
        e.g: b-prefix remove a b c "d e"

        You can not have less then 1 prefix, and you can not remove the mention prefix."""
        data = read('./data/prefixes.json')
        prefixess = data[str(ctx.guild.id)]
        _p = len(prefixess)
        for prefix in prefixes:
            if prefix in prefixess and prefixes != 'b-':
                prefixess.remove(prefix)
            else:
                continue
        write('./data/prefixes.json', data)
        if _p - len(prefixess) == 1:
            await ctx.send(f"Removed **{_p - len(prefixess)}** prefix.")
        else:
            await ctx.send(f"Removed **{_p - len(prefixess)}** prefixes.")

    @prefix.command(name="reset")
    @commands.has_permissions(manage_guild=True)
    async def prefix_reset(self, ctx):
        """resets the prefix to the defaults."""
        data = read('./data/prefixes.json')
        data[str(ctx.guild.id)] = ['b-']
        write('./data/prefixes.json', data)
        await ctx.send(f"Reset your prefixes to defaults `b-`")

    @prefix.before_invoke
    @prefix_add.before_invoke
    @prefix_remove.before_invoke
    @prefix_reset.before_invoke
    async def addthedata(self, ctx):
        d = read('./data/prefixes.json')
        if str(ctx.guild.id) not in d.keys():
            d[str(ctx.guild.id)] = []
            write('./data/prefixes.json', d)

    @commands.group(name='leaderboard', aliases=['lb'], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def lb(self, ctx):
        """Displays the leaderboard for this server
        to get the global leaderboard, run "b-leaderboard top"."""
        data = read('./data/leaderboard.json')
        info = data.get(str(ctx.guild.id))
        if info is None:
            return await ctx.send("No records for this guild. have you bumped yet?")
        else:
            e = discord.Embed(title=f"{ctx.guild.name}'s statistics:", description="Most bumps: ",
                              color=ctx.guild.owner.color,
                              timestamp=ctx.guild.me.joined_at if ctx.guild.me.joined_at else ctx.message.created_at)
            resolved = sorted(info.keys(), key=lambda _bumps: info[_bumps], reverse=True)
            try:
                top_user = await self.bot.fetch_user(int(resolved[0]))
            except (discord.NotFound, discord.HTTPException):
                e.description += f"**@Unknown** with **{info[resolved[0]]}** bumps!"
            else:
                e.description += f"**{top_user.mention}** with **{info[resolved[0]]}** bumps!"
            for num, user in enumerate(resolved, start=1):
                if str(ctx.author.id) == user:
                    if str(num).endswith('1'):
                        ending = 'st'
                    elif str(num).endswith('2'):
                        ending = 'nd'
                    elif str(num).endswith('3'):
                        ending = 'rd'
                    else:
                        ending = 'th'
                    my_rank = f"{num}{ending} on the leaderboard"
                    break
            else:
                my_rank = "not on the leaderboard"
            if len(resolved) > 1:
                rest = resolved[1:6]
                res_rest = []
                for num, _user in enumerate(rest, start=2):
                    # runner-ups are less-prioritised then top, so we just get_ them.
                    user = self.bot.get_user(int(_user))
                    if user is None:
                        mention = '@Unknown'
                    else:
                        mention = user.mention
                    res_rest.append(f"**{mention}** with **{info[_user]}** bumps!")
                e.add_field(name="Runner Ups:", value='\n'.join(res_rest), inline=False)
                e.set_footer(text=f"You are {my_rank} | started recording: ")
            try:
                return await ctx.send(embed=e)
            except discord.HTTPException as e:
                return await ctx.send(f"An error occurred when sending the embed: {e}")

    @lb.command(name='global', aliases=['top', 'total', 'all'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def lb_global(self, ctx):
        """Lists the global stats"""
        # here you will see a lot of '{x.name if x else "unknown"} with {...[x]...}'.
        # the reason for this is that `get_` can return None, however the entry is still available.
        data = read('./data/leaderboard.json')
        for guild in data.keys():
            data[guild]['total'] = 0
            for user in data[guild].keys():
                data[guild]['total'] += data[guild][user]
        resolved_guilds = sorted(data.keys(), key=lambda _: data[_]['total'], reverse=True)
        e = discord.Embed(
            title="Global Leaderboard:", color=0x2a515d, timestamp=self.bot.user.created_at
        )
        tg = self.bot.get_guild(int(resolved_guilds[0]))
        if tg:
            if len(tg.name) > 15:
                name = tg.name[:15] + '...'
            else:
                name = tg.name
        else:
            name = 'unavailable'
        e.add_field(name="Top guild:", value=f"**{name}** with "
                                             f"**{data[resolved_guilds[0]]['total']}** total bumps!",
                    inline=True)

        runner_guilds = resolved_guilds[1:6]
        runner_resolved = []
        for x in runner_guilds:
            tg = self.bot.get_guild(int(x))
            if tg:
                if len(tg.name) > 10:
                    name = tg.name[:15] + '...'
                else:
                    name = tg.name
            else:
                name = 'unavailable'
            runner_resolved.append(f"**{name}** with **{data[x]['total']}** bumps")
        if '\n'.join(runner_resolved) == '':
            pass
        else:
            e.add_field(name="Runner up guilds:", value='\n'.join(runner_resolved), inline=True)

        users = {}
        for guild in resolved_guilds:
            for user in data[guild].keys():
                if user not in users.keys():
                    users[user] = 0
                users[user] += data[guild][user]
        sorted_users = sorted(users.keys(), key=lambda _: users[_], reverse=True)
        sorted_users.remove('total')
        top_user = self.bot.get_user(int(sorted_users[0]))
        runners = []
        for user in sorted_users[1:6]:
            u = self.bot.get_user(int(user))
            runners.append(f"**{u.display_name if u else 'unavailable'}** with **{users[user]}** bumps")
        e.add_field(name="\u200B", value="\u200B", inline=False)  # break
        e.add_field(name="\u200B", value="\u200B", inline=False)  # break
        e.add_field(name="Top user:", value=f"**{top_user.display_name if top_user else 'Unavailable'}** with "
                                            f"**{users[sorted_users[0]]}** bumps")
        if '\n'.join(runners) == '':
            pass
        else:
            e.add_field(name="Runner ups:", value='\n'.join(runners))
        return await ctx.send(embed=e)

    @tasks.loop(minutes=12, seconds=30)
    async def update_status(self):
        servers = len(self.bot.guilds)
        await self.bot.change_presence(activity=discord.Game(name=f"bumping {servers} servers via \"b-bump\"!"),
                                       status=discord.Status.dnd)

    @commands.Cog.listener()
    async def on_bump_done(self, ctx, author):
        """This is the custom bump event sent by ::do_bump::.

        ctx is guaranteed to not be None."""
        xp = random.randint(1, 100)
        data = read('./data/level.json')
        if str(author.id) in data.keys():
            if str(ctx.guild.id) in data[str(author.id)]:
                data[str(author.id)][str(ctx.guild.id)]['xp'] += xp
            else:
                data[str(author.id)][str(ctx.guild.id)] = {"xp": xp}
        else:
            data[str(author.id)] = {}
            data[str(author.id)][str(ctx.guild.id)] = {"xp": xp}
        write('./data/level.json', data)
        abc = data['metadata']
        rewards = abc.get(str(ctx.guild.id))
        if rewards is None or ctx.guild.me.guild_permissions.manage_roles is False:
            return
        else:
            level = CustomConverters.level_converter(ctx, data[str(author.id)][str(ctx.guild.id)]['xp'])
            level = str(level)
            if level in rewards.keys():
                role = ctx.guild.get_role(rewards[level])
                if role:
                    if role in author.roles:
                        return
                    else:
                        if role >= ctx.guild.me.top_role:
                            return
                        else:
                            await author.add_roles(role, reason=f"Reward role for bump level {level}.")
                else:
                    return
            else:
                return
        return

    async def add_rewards(self, ctx, data):
        author = ctx.author
        level = CustomConverters.level_converter(ctx, data[str(author.id)][str(ctx.guild.id)]['xp'])
        level = str(level)
        abc = data['metadata']
        rewards = abc.get(str(ctx.guild.id))
        if level in rewards.keys():
            role = ctx.guild.get_role(rewards[level])
            if role:
                if role in author.roles:
                    return
                else:
                    if role >= ctx.guild.me.top_role:
                        return
                    else:
                        await author.add_roles(role, reason=f"Reward role for bump level {level}.")
            else:
                return
        else:
            return

    async def remove_rewards(self, ctx, data):
        author = ctx.author
        level = CustomConverters.level_converter(ctx, data[str(author.id)][str(ctx.guild.id)]['xp'])
        level = str(level)
        abc = data['metadata']
        rewards = abc.get(str(ctx.guild.id))
        rewardroles = []
        for role in author.roles:
            if role.id in rewards.items():
                for _level, _id in list(rewards.items()):
                    if _id == role.id:
                        if int(_level) > int(level):
                            await author.remove_roles(role, reason="Rank lost - underleveled.")
        return

    @commands.command(aliases=['perms', 'debug'])
    @commands.has_permissions(manage_roles=True)
    @commands.guild_only()
    async def diagnose(self, ctx):
        """Diagnoses some permissions, makes sure the bot has required."""
        required = discord.Permissions(355393)
        recommended = discord.Permissions(268790897)

        required = [(x, y) for x, y in tuple(required) if y]
        recommended = [(x, y) for x, y in tuple(recommended) if y]
        for thing in required:
            recommended.remove(thing)

        warning = '\U000026a0'
        critical = '\U00002757'
        passed = '\U00002705'

        re = f"> key:\n> {passed} = passed\n> {warning} = should be fixed\n> {critical} = required to use core " \
             f"features of bot\n\n"

        x = dict(ctx.channel.permissions_for(ctx.me))

        re += "**Required:**\n"
        for name, enabled in required:
            have = x.get(name)
            name = name.replace('_', ' ')
            if have is None:  # uhh
                re += f"> {warning} {name} -> could not check automatically.\n"
                continue
            if have == enabled or have is True:
                re += f"> {passed} {name}\n"
            elif have is False and enabled is True:
                re += f"> {critical} {name}\n"
            else:
                re += f"> {warning} {name} -> could not check automatically.\n"

        msg = await ctx.send(re)
        re += "**Recommended:**\n"

        for name, enabled in recommended:
            have = x.get(name)
            name = name.replace('_', ' ')
            if have is None:  # uhh
                re += f"> {warning} {name} -> could not check automatically.\n"
                continue
            if have == enabled or have is True:
                re += f"> {passed} {name}\n"
            elif have is False and enabled is True:
                re += f"> {warning} {name}\n"
            else:
                re += f"> {warning} {name} -> could not check automatically.\n"
        await asyncio.sleep(2)
        return await msg.edit(content=re)

    # leveling

    @commands.command(name='rewards', aliases=['listrewards', 'lr'])
    @commands.guild_only()
    async def list_rewards(self, ctx):
        """Lists rewards"""
        data = read("./data/level.json")
        data = data["metadata"].get(str(ctx.guild.id))
        if data is None:
            return await ctx.send("There are none!")
        else:
            data = data['reward_roles']
            x = commands.Paginator()
            for level, roleid in list(data.items()):
                role = ctx.guild.get_role(roleid)
                if role:
                    mention = str(role.name)
                    mention = discord.utils.escape_mentions(mention)
                else:
                    mention = str(roleid)
                x.add_line(f"level {level}: {mention}")
            for page in x.pages:
                await ctx.send(page)

    @commands.group(name="level", aliases=['levels', 'xp', 'points'], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    @commands.guild_only()
    async def exp(self, ctx, *, user: discord.User = None):
        """See your bump points. or someone else's."""
        user = user if user else ctx.author
        data = read('./data/level.json')
        if str(user.id) not in data.keys():
            dude = 'that user hasn\'t' if user != ctx.author else 'you have\'t'
            u = 'you' if user == ctx.author else 'they'
            return await ctx.send(f"{dude} got any levels! Have {u} bumped yet?")
        else:
            points = 0
            for guild in data[str(user.id)]:  # {guild: {"xp": 420}, gui...}
                points += data[str(user.id)][guild]["xp"]
            actual_level = CustomConverters.level_converter(ctx, points)
            e = discord.Embed(title=f"{user.display_name}'s points:", description=f"**Level `{actual_level}`**\n"
                                                                                  f"**xp (points):** {points}",
                              color=discord.Color.blue(), timestamp=user.created_at)
            if user in ctx.guild.members:
                ig_l = CustomConverters.level_converter(ctx, data[str(user.id)][str(ctx.guild.id)]["xp"])
                ig_points = data[str(user.id)][str(ctx.guild.id)]["xp"]
                e.add_field(name="In this server:", value=f"**Level `{ig_l}`**\n**xp (points):** {ig_points}",
                            inline=False)
            await ctx.send(embed=e)

    @commands.command(aliases=['addrank'])
    @commands.has_permissions(manage_roles=True, manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True, manage_guild=True)
    @commands.guild_only()
    async def addreward(self, ctx, at_level: int, *, reward_role: discord.Role):
        """Adds a role to the rewards. this role is automatically added at level-up."""
        if reward_role > ctx.author.top_role or reward_role >= ctx.guild.me.top_role:
            return await ctx.send("That role is too high.")
        x = reward_role.permissions
        if x.manage_channels or x.manage_guild or x.manage_messages or x.manage_roles or x.ban_members or x.kick_members:
            return await ctx.send("That role has 1 or more `manage` permissions and can not be used as a reward role.")
        if x.administrator:
            return await ctx.send("Administrator roles can not be used as reward roles.")
        data = read("./data/level.json")
        _dir = data["metadata"]
        if _dir.get(str(ctx.guild.id)) is None:
            _dir[str(ctx.guild.id)] = {"reward_roles": {str(at_level): reward_role.id}}
        else:
            _dir[str(ctx.guild.id)]["reward_roles"][str(at_level)] = reward_role.id
        write("./data/level.json", data)
        await ctx.send(
            f"Added {discord.utils.escape_mentions(reward_role.name)} as a reward role for level {at_level}.")

    @commands.command(aliases=['remrank'])
    @commands.has_permissions(manage_roles=True, manage_guild=True)
    @commands.bot_has_permissions(manage_roles=True, manage_guild=True)
    async def remreward(self, ctx, at_level: int):
        """removes a role from the rewards."""
        data = read("./data/level.json")
        _dir = data["metadata"]
        if _dir.get(str(ctx.guild.id)) is None:
            return await ctx.send("You don't have any set roles yet...")
        else:
            x = _dir[str(ctx.guild.id)]["reward_roles"].get(str(at_level))
            if x:
                del x
            else:
                return await ctx.send(f"{at_level} has no reward role set.")
        write("./data/level.json", data)
        await ctx.send(f"removed level {at_level}'s reward role.")

    @commands.command(name="transferxp", aliases=['txp', 'givexp', 'exp'])
    @commands.bot_has_permissions(send_messages=True)
    @commands.guild_only()
    async def give_xp(self, ctx, amount: int, *, user: discord.Member):
        """give someone else your XP. this will take the level number away and give it to the other user."""
        if user.bot:
            return await ctx.send("Bots can't bump and therefor can't get xp. Nice try.")
        elif user == ctx.author:
            return await ctx.send("No. We thought ahead. We're smarter then dumb people who try to give themselves XP.")
        data = read("./data/level.json")
        if str(ctx.author.id) not in data.keys():
            return await ctx.send("You don't have any xp to give!")
        elif str(ctx.guild.id) not in data[str(ctx.author.id)].keys():
            return await ctx.send("You have no xp in this guild to give!")
        table = {}
        cur = 300
        for i in range(1, 101):  # 1 - 100
            table[i] = cur
            cur += 250
        if data[str(ctx.author.id)][str(ctx.guild.id)]['xp'] - table[amount] < 0:
            return await ctx.send("You don't have enough xp.")
        if str(user.id) in data.keys():
            if str(ctx.guild.id) in data[str(user.id)][str(ctx.guild.id)].keys():
                data[str(user.id)][str(ctx.guild.id)]['xp'] += table[amount]
                data[str(ctx.author.id)][str(ctx.guild.id)]['xp'] -= table[amount]
            else:
                data[str(user.id)][str(ctx.guild.id)] = {"xp": table[amount]}
                data[str(ctx.author.id)][str(ctx.guild.id)]['xp'] -= table[amount]
            _ctx = ctx
            _ctx.author = user
            try:
                await self.add_rewards(_ctx, data)
                await self.remove_rewards(_ctx, data)
                await self.add_rewards(ctx, data)
                await self.remove_rewards(ctx, data)
            except (KeyError, AttributeError):
                pass  # probably 'No Rewards'
            write("./data/level.json", data)
            return await ctx.send(f"Gave {user.name} {table[amount]} xp.")
        else:
            return await ctx.send("That user has not bumped before.")

    @exp.command(name="lb", aliases=['leaderboard'])
    @commands.bot_has_permissions(send_messages=True, embed_links=True)
    async def xp_lb(self, ctx):
        """Displays the xp leaderboard"""
        data = read("./data/level.json")
        users = {}
        for user in data.keys():
            for guild in data[user].keys():
                if users.get(user):
                    try:
                        users[user] += data[user][guild]['xp']
                    except KeyError:
                        continue
                else:
                    try:
                        users[user] = data[user][guild]['xp']
                    except KeyError:
                        pass
        sorted_keys = sorted(users.keys(), key=lambda a: users[a], reverse=True)
        paginator = PaginatorInterface(self.bot, commands.Paginator(max_size=1000, prefix='', suffix=''))
        for n, u in enumerate(sorted_keys, start=1):
            # await ctx.send(u)
            us = self.bot.get_user(int(u))
            # await ctx.send(str(us))
            mention = discord.utils.escape_markdown(discord.utils.escape_mentions(str(us))) if us else 'Unknown#0000'
            level = CustomConverters.level_converter(ctx, users[u])
            await paginator.add_line(f"{n}. {mention}: {users[u]}xp (level {level})")
        return await paginator.send_to(ctx.channel)

    @tasks.loop(hours=1)
    async def update_stats_data(self):
        now = datetime.utcnow()
        print(now)
        try:
            data = read("./data/stats.json")
            print(f"READ {data}")
        except FileNotFoundError:
            print("FILENOTFOUND")
            data = {}
            file = open("./data/stats.json", "w+")
            file.write('{"days": {}}')
            file.close()

        tod = list(range(2, 14, 2))
        print(tod)
        last_month = datetime.utcnow().month - 1
        if last_month == 0:  # 1/20 or smthn is current date
            last_month = 12
        last_month = str(last_month)
        yesterday = str(now.day - 1)
        if yesterday == 0:
            yesterday = 31 if int(last_month) in tod else 30
        last_year = str(now.year - 1)

        current_month = str(now.month)
        current_year = str(now.year)
        current_day = str(now.day)
        print(f"Last_:\n\t{last_month} MONTH\n\t{last_year} YEAR\n\t{yesterday} YESTERDAY\n")
        print(f"Current:\n\t{current_month} month\n\t{current_year} year\n\t{current_day} day")
        data[current_month + '/' + current_year] = {
            "total": len(self.bot.guilds),
            "diff": len(self.bot.guilds) - data[last_month + '/' + last_year]["total"]
        }
        print("written")
        print(data)
        data["days"][current_day + '/' + current_month] = {} if data["days"].get(
            current_day + '/' + current_month) is None else data["days"][current_day + '/' + current_month]
        data["days"][current_day + '/' + current_month][str(now.hour)] = {
            "total": len(self.bot.guilds),
            "diff": len(self.bot.guilds) - data["days"][yesterday + '/' + last_month]["total"]
        }
        print(data)
        write("./data/stats.json", data)
        print(str(read("./data/stats.json")))
        print("DONE")

    def generate_graph(self, date):
        data = read("./data/stats.json")
        got = data.get(date)
        if got:
            totals = [x["total"] for x in list(got.values())]

            dates = list(got.keys())
            mpl.plot(dates, totals)
            mpl.xlabel("dates")
            mpl.ylabel("total guilds")
            mpl.title("Growth in servers over time")
            mpl.savefig("./data/graph.png")
        else:
            raise FileNotFoundError("Unable to find date " + date)

    @commands.command(name="serverstats")
    @commands.cooldown(3, 1, commands.BucketType.guild)
    async def viewstats(self, ctx, *, date: str = None):
        """View the growth of the bot!

        Provide a date in the format of either `dd/mm` to see that date's stats, or `mm/yyyy` to get that month's stats
        Leave date blank to get from 31/12/19 to now's stats"""
        if self.update_stats_data.failed:
            return await ctx.send(
                f"Task `self.update_stats_data` failed to run. Please ask my dev to reload the module.")
        if date:
            items = date.split("/")
            if items[0].startswith("0"):
                return await ctx.send("Dates should not start with 0!")
            if len(items) == 3:
                date = f"{items[1]}/{items[2]}"  # 4/20
            elif len(items) == 2:
                date = f"{items[0]}/{items[1]}"  # 6/9
                if int(items[1]) > 12:
                    await ctx.send(f"Detected `mm/dd` format. Switching to `{items[1]}/{items[0]}`")
                    date = f"{items[1]}/{items[0]}"
            else:
                var = 'too many' if len(items) > 3 else 'not enough'
                return await ctx.send(f"{var} dates! Must be in the format `mm/yyyy`, `dd/mm` or `dd/mm/yyyy`!")
        else:
            date = list(read("./data/stats.json").keys())[0]
        async with ctx.channel.typing():
            loop: asyncio.AbstractEventLoop = self.bot.loop
            graph = await loop.run_in_executor(None, self.generate_graph, date)
        await ctx.send(embed=discord.Embed().set_image(url="attachment://graph.png"),
                       file=discord.File("./data/graph.png"))

    @commands.command()
    @commands.is_owner()
    async def adddate(self, ctx):
        now = datetime.utcnow()
        print(now)
        try:
            data = read("./data/stats.json")
            print(f"READ {data}")
        except FileNotFoundError:
            print("FILENOTFOUND")
            data = {}
            file = open("./data/stats.json", "w+")
            file.write('{"days": {}}')
            file.close()

        tod = list(range(2, 14, 2))
        print(tod)
        last_month = datetime.utcnow().month - 1
        if last_month == 0:  # 1/20 or smthn is current date
            last_month = 12
        last_month = str(last_month)
        yesterday = str(now.day - 1)
        if yesterday == 0:
            yesterday = 31 if int(last_month) in tod else 30
        last_year = str(now.year - 1)

        current_month = str(now.month)
        current_year = str(now.year)
        current_day = str(now.day)
        print(f"Last_:\n\t{last_month} MONTH\n\t{last_year} YEAR\n\t{yesterday} YESTERDAY\n")
        print(f"Current:\n\t{current_month} month\n\t{current_year} year\n\t{current_day} day")
        data[current_month + '/' + current_year] = {
            "total": len(self.bot.guilds),
            "diff": len(self.bot.guilds) - data[last_month + '/' + last_year]["total"]
        }
        print("written")
        print(data)
        print(data["days"])
        print()
        print()
        data["days"][current_day + '/' + current_month] = {
            "total": len(self.bot.guilds),
            "diff": len(self.bot.guilds) - data["days"][yesterday + '/' + last_month + '/' + last_year]["total"]
        }
        print(data)
        write("./data/stats.json", data)
        print(str(read("./data/stats.json")))
        print("DONE")
        return await ctx.send("Manually ran update_stats_loop")

    def cog_unload(self):
        self.update_status.stop()
        self.update_stats_data.stop()


def setup(bot):
    bot.add_cog(Misc(bot))
