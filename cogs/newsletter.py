import discord
from discord.ext import commands
from jishaku import paginators

from .utils.config import read, write


def de_str(*, items: list, allow_floats: bool = True, choose_ints_first: bool = True):
    resolved = []
    for thing in items:
        if not isinstance(thing, int) and not isinstance(thing, float):  # it's not an int OR float
            try:
                if choose_ints_first or not allow_floats:
                    thing = int(thing)
                else:
                    thing = float(thing)
            except ValueError:
                continue
            else:
                resolved.append(thing)

    return resolved


class Newsletter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def subscribe(self, ctx, toggle: bool = None):
        """Signs you up to get the bot's announcements. these will come in DMs, and usually consist of updates, and
        important information."""
        data = read('./data/newsletter.json')
        if toggle is None:
            if str(ctx.author.id) in data["subs"]:
                toggle = False
                del data["subs"][str(ctx.author.id)]
            else:
                toggle = True
                data["subs"][str(ctx.author.id)] = None
        idid = {
            True: "Signed you up to the newsletter.",
            False: "Unsubscribed you. you will no longer get DMs with important information."
        }

        write('./data/newsletter.json', data)
        return await ctx.send(idid[toggle])

    @commands.command(name="newletter", aliases=['nl', 'newsletter'])
    @commands.is_owner()
    async def newletter(self, ctx, number: int, *, message: commands.clean_content):
        """Make a new newsletter to send to the subscribers."""
        message = str(message)
        x = f"**Newsletter #{number}:**\n\n{message}\n\n*You subscribed to this message by `b-subscribe`. run that again" \
            f" to stop getting this."
        users = read('./data/newsletter.json')
        try:
            for user in users['subs'].keys():
                user = self.bot.get_user(int(user))
                if user:
                    await user.send(x)
                    continue
                continue
        except:
            pass
        finally:
            return await ctx.message.add_reaction(self.bot.speakers['full'])

    @commands.command()
    @commands.is_owner()
    async def subscribers(self, ctx):
        """List all peoples who are subscribed to the newsletter"""
        data = read('./data/newsletter.json')
        del data['last']
        data = data['subs']
        _p = commands.Paginator(prefix='', suffix='')
        for user in data:
            u = self.bot.get_user(int(user))
            if u is not None:
                _p.add_line(u.mention)
            else:
                _p.add_line('@unknown `(NONE)`')
        for page in _p.pages:
            await ctx.send(embed=discord.Embed(description=page))

    @commands.command(name="stats", aliases=['info', 'about'])
    @commands.bot_has_permissions(embed_links=True)
    async def infos(self, ctx):
        """Gets information on the bot"""


def setup(bot):
    bot.add_cog(Newsletter(bot))
