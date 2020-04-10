import datetime
import json
from discord.ext import commands


def get_rank(bot_instance, user):
    with open('./data/premium.json', 'r') as x:
        data = json.load(x)
        if str(user.id) in data:
            return 2
        else:
            guild = bot_instance.get_guild(606866057998762023)
            if user in guild.members:
                return 1
            else:
                return 0


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


class CustomConverters:
    @classmethod
    def level_converter(cls, ctx, argument: int, *, rounded: bool = False) -> int:
        """Convert a raw XP value to a single level."""
        if rounded:
            argument = argument / 10
            argument = round(argument)
            argument *= 10
        table = {}
        cur = 300
        for i in range(1, 9e99):  # 1 - 100
            table[i] = cur
            cur += 250
        # this automatically brings us up to level 100.
        for level, xp in reversed(list(table.items())):
            if argument >= xp:
                return level
        else:
            return 0


class IntegerOverflow(Exception):
    def __init__(self, *, current_value, max_value):
        self.current = current_value
        self.max = max_value

    def __str__(self):
        return f"IntegerOverflow: {self.current} > {self.max}, with {self.max} being the highest permitted value."


def ago_time(time):
    """Convert a time (datetime) to a human readable format.
    """
    date_join = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f")
    date_now = datetime.datetime.now(datetime.timezone.utc)
    date_now = date_now.replace(tzinfo=None)
    since_join = date_now - date_join

    m, s = divmod(int(since_join.total_seconds()), 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    y = 0
    while d >= 365:
        d -= 365
        y += 1

    if y > 0:
        msg = "{4}y, {0}d {1}h {2}m {3}s ago"
    elif d > 0 and y == 0:
        msg = "{0}d {1}h {2}m {3}s ago"
    elif d == 0 and h > 0:
        msg = "{1}h {2}m {3}s ago"
    elif d == 0 and h == 0 and m > 0:
        msg = "{2}m {3}s ago"
    elif d == 0 and h == 0 and m == 0 and s > 0:
        msg = "{3}s ago"
    else:
        msg = ""
    return msg.format(d, h, m, s, y)


def fix_time(time: int = None, *, return_ints: bool = False, brief: bool = False):
    """Convert a time (in seconds) into a readable format, e.g:
    86400 -> 1d
    3666 -> 1h, 1m, 1s

    set ::return_ints:: to True to get a tuple of (days, minutes, hours, seconds).
    --------------------------------
    :param time: int -> the time (in seconds) to convert to format.
    :keyword return_ints: bool -> whether to return the tuple or (default) formatted time.
    :raises ValueError: -> ValueError: time is larger then 7 days.
    :returns Union[str, tuple]:
    to satisfy pycharm:
    """
    seconds = round(time, 2)
    minutes = 0
    hours = 0
    overflow = 0

    d = 'day(s)' if not brief else 'd'
    h = 'hour(s)' if not brief else 'h'
    m = 'minute(s)' if not brief else 'm'
    s = 'seconds(s)' if not brief else 's'
    a = 'and' if not brief else '&'

    while seconds >= 60:
        minutes += 1
        seconds -= 60
    while minutes >= 60:
        hours += 1
        minutes -= 60
    while hours > 23:
        overflow += 1
        hours -= 23

    if return_ints:
        return overflow, hours, minutes, seconds
    if overflow > 0:
        return f'{overflow} day(s), {hours} hour(s), {minutes} minute(s) and {seconds} second(s)'
    elif overflow == 0 and hours > 0:
        return f'{hours} hour(s), {minutes} minute(s) and {seconds} second(s)'
    elif overflow == 0 and hours == 0 and minutes > 0:
        return f'{minutes} minute(s) and {seconds} second(s)'
    else:
        return f'{seconds} second(s)'


class DynamicGuild(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            argument = int(argument)
        except:
            pass
        bot = ctx.bot
        if isinstance(argument, int):
            # check if its an ID first, else check enumerator
            guild = bot.get_guild(argument)
            if guild is not None:  # YAY
                return guild
            else:  # AWW
                for number, guild in enumerate(bot.guilds, start=1):
                    if number == argument:
                        return guild
                else:
                    if guild is None:
                        raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None'")
                    else:
                        raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' as loop left.")
        elif isinstance(argument, str):  # assume its a name
            for guild in bot.guilds:
                if guild.name.lower() == argument.lower():
                    return guild
            else:
                raise commands.BadArgument(f"Could not convert '{argument}' to 'Guild' with reason 'type None' at 1")
        else:
            raise commands.BadArgument(f"Could not convert argument of type '{type(argument)}' to 'Guild'")
