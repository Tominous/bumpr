import json
from typing import Union


def read(fp) -> dict:
    with open(fp, 'r') as x:
        return json.load(x)


def write(fp, data) -> None:
    with open(fp, 'w') as x:
        return json.dump(data, x, indent=1)


def get_guild_data(guildid: str, *, specific_key: str = None, fp) -> (dict, bool):
    fp = fp.replace('./data/', '')
    data = read('./data/' + fp)
    if data.get(guildid):
        if specific_key:
            res = data[guildid].get(specific_key)
            if res:
                return res, True
            else:
                return data[guildid], False
        else:
            return data[guildid], False
    else:
        return {}, False
