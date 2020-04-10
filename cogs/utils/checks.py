import json
from discord.ext import commands

from .converters import get_rank


def is_premium():
    def t(ctx):
        rank = get_rank(ctx.bot, ctx.author)
        if rank != 2:
            raise commands.CheckFailure(f"You are not premium! You are rank {rank}, you need to be rank 2!")
        else:
            return True

    return commands.check(t)


def is_member():
    def t(ctx):
        rank = get_rank(ctx.bot, ctx.author)
        if rank < 1:
            raise commands.CheckFailure(f"You are not a member! You need to join the support server. "
                                        f"visit <https://dragdev.xyz/bumper> to join it.")
        else:
            return True

    return commands.check(t)


def bot_admin():
    def t(ctx):
        with open('./data/meta.json', 'r') as x:
            data = json.load(x)
            cr = ctx.author.id in data['admins']
            if not cr:
                raise commands.CheckFailure("This command is bot-admin only.")
            else:
                return cr

    return commands.check(t)
